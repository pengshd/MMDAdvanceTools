from mathutils import Matrix, Vector, Quaternion
from math import pi

from ...common.properties import TransformChannel
from ...common import boneAdvanceData
from ...common.utils import *

switch = False

def convert_rotation_mode_and_align(context, posebones, posebones_ref, frame = 0):

    def rotate_local(posebone,axis_index,rad):
        axis = Vector((0,0,0))
        axis[axis_index] = 1
        posebone.rotation_quaternion @= Quaternion(axis, rad) 
        boneAdvanceData.get_bone_data(posebone).rotation_quaternion @= Quaternion(axis, rad) 
        if switch:
            axis = (posebone.matrix.to_3x3().col)[axis_index]
            # rotation matrix 30 degrees around local x axis thru head
            R = (Matrix.Translation(posebone.head) @
                Matrix.Rotation(rad, 4, axis) @
                Matrix.Translation(-posebone.head)
                )
            posebone.matrix = R @ posebone.matrix
            
                 
    arm,forearm,hand = posebones
    armature = arm.id_data
    arm_ref,forearm_ref,hand_ref = posebones_ref
    armature_ref = armature.mmd_advance_data.reference
    boneAdvanceData.clear_link()
    boneAdvanceData.initialize_link(hand,armature.animation_data.action,frame)
    boneAdvanceData.initialize_link(hand_ref,armature_ref.animation_data.action,frame)   
    forearm_bonedata = boneAdvanceData.get_bone_data(forearm)
    arm_bonedata = boneAdvanceData.get_bone_data(arm)
    hand_bonedata = boneAdvanceData.get_bone_data(hand)

    forearm_ref_bonedata = boneAdvanceData.get_bone_data(forearm_ref)
    arm_ref_bonedata = boneAdvanceData.get_bone_data(arm_ref)
    hand_ref_bonedata = boneAdvanceData.get_bone_data(hand_ref)
    forearm_ref_head = forearm_ref_bonedata.head
    forearm_ref_tail = forearm_ref_bonedata.tail
    arm_ref_head = arm_ref_bonedata.head
    arm_ref_tail = arm_ref_bonedata.tail

    if switch:
        forearm_ref_head = forearm_ref.head
        forearm_ref_tail = forearm_ref.tail
        arm_ref_head = arm_ref.head
        arm_ref_tail = arm_ref.tail
    
    forearm_direction_state0 = (forearm_ref_tail - forearm_ref_head).normalized()
    arm_direction_state0 = (arm_ref_tail - arm_ref_head).normalized()
    angle_radian_state0 = arm_direction_state0.angle(forearm_direction_state0)
    angle_degree = angle_radian_state0 * 180 / pi
    #将清除forearm的x,y轴上的旋转前的状态称为state1, 清除后状态称为state2, 再调整arm旋转后的状态称为state3, 调整forearm的Z旋转的终点状态称为state4。
    # 那么按以下逻辑编写代码：
    # 1.先计算state1下arm和forearm所构成平面的法线矢量normal_state1,以及forearm的骨骼指向矢量forearm_direction_state1
    # 2.清除forearm的x,y轴上的旋转，将骨骼调整到state2状态
    # 3.计算state2下arm和forearm所构成平面的法线矢量normal_state2
    # 4.获得normal_state1和normal_state2的夹角plane_angle,让arm骨骼在y方向旋转plane_angle,到达state3状态
    # 5.计算此时的forearm的骨骼指向矢量forearm_direction_state3
    # 6.计算forearm_direction_state3到forearm_direction_state1的夹角forearm_angle,将forearm骨骼在z方向旋转forearm_angle, 到达最终状态state4
    #step1
    # arm_head_pos = armature.matrix_world@arm_ref.head
    #TODO 修改成计算版本
    #forearm_ref实际的父级，复制了arm_ref的世界空间旋转
    arm_calc_ref = armature_ref.pose.bones[arm_ref.name.replace("mmd.","mmd_calc.")]
    arm_calc_ref_bonedata = boneAdvanceData.get_bone_data(arm_calc_ref)
    arm_calc_ref_head = arm_calc_ref_bonedata.head
    if switch:    
        arm_calc_ref_head = arm_calc_ref.head

    state1_normal = (forearm_ref_tail - forearm_ref_head).cross(forearm_ref_head - arm_calc_ref_head).normalized()
    forearm_direction_state1 = forearm_direction_state0

    #step2
    #清除forearm的Z轴以外的旋转
    forearm_bonedata.rotation_quaternion.x = forearm_bonedata.rotation_quaternion.y = 0
    forearm_bonedata.update_data()
    hand_bonedata.update_data()
    # if switch:
    forearm.rotation_quaternion.x = forearm.rotation_quaternion.y = 0
    if switch:
        context.evaluated_depsgraph_get().update()    

    forearm_rotation_quaternion_step2 = forearm_bonedata.rotation_quaternion
    if switch:
        forearm_rotation_quaternion_step2 = forearm.rotation_quaternion.copy()
    #step3
    lower_bound = armature.mmd_advance_data.arm_forearm_angle_lowerbound
    upper_bound = armature.mmd_advance_data.arm_forearm_angle_upperbound
    if angle_degree > lower_bound:
        # arm_head_pos = armature.matrix_world@arm.head
        arm_calc_ref_head = arm_calc_ref_bonedata.head
        forearm_head = forearm_bonedata.head
        forearm_tail = forearm_bonedata.tail
        
        if switch:
            arm_calc_ref_head = armature.matrix_world@arm_calc_ref.head
            forearm_head = armature.matrix_world@forearm.head
            forearm_tail = armature.matrix_world@forearm.tail
        state2_normal = (forearm_tail - forearm_head).cross(forearm_head - arm_calc_ref_head).normalized()
        #若下臂的Z轴以外旋转已经清除，上臂的Z轴方向，就是手部平面的法线
        #TODO 修改成计算版本
        # state2_normal = arm_calc_ref.matrix @ Vector((0,0,1))

        #step4 
        #从2旋转到1
        # 计算两个平面夹角
        plane_angle_sign = 1 if (forearm_head - arm_calc_ref_head).dot(state2_normal.cross(state1_normal)) >=0 else -1
        plane_rad = state2_normal.angle(state1_normal)*plane_angle_sign
        #TODO 修改成计算版本
        rotate_local(arm,1,plane_rad)
        arm_bonedata.update_data()
        forearm_bonedata.update_data()
        hand_bonedata.update_data()
        if switch:
            context.evaluated_depsgraph_get().update()
        #step5
        #TODO 修改成计算版本
        forearm_direction_state3 = (forearm_bonedata.tail - forearm_bonedata.head).normalized()
        if switch:
            forearm_direction_state3=(forearm.tail - forearm.head).normalized()
        #step6
        #从state3旋转到state1
        # 将局部 Z 轴方向转换为世界空间方向
        forearm_z_axis = forearm_bonedata.matrix.to_3x3() @ Vector((0, 0, 1))
        if switch:
            forearm_z_axis = forearm.matrix.to_3x3() @ Vector((0, 0, 1))
        forearm_angle_sign = 1 if forearm_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
        forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
        #如果forearm旋转反关节
        forearm_reverse = False
        rotation_euler_zxy = forearm_bonedata.rotation_quaternion.to_euler("ZXY")
        if switch:
            rotation_euler_zxy = forearm.rotation_quaternion.to_euler("ZXY")
        if rotation_euler_zxy.z + forearm_rad <0:
            forearm_reverse = True
        #如果forearm需要反关节才能达到目标位置，那就把arm反转再重新计算forearm该如何旋转                        
        if forearm_reverse:
            rotate_local(arm,1,pi)
            arm_bonedata.update_data()
            forearm_bonedata.update_data()
            hand_bonedata.update_data()
            if switch:
                context.evaluated_depsgraph_get().update()
            forearm_direction_state3 = (forearm_bonedata.tail - forearm_bonedata.head).normalized()
            if switch:
                forearm_direction_state3=(forearm.tail - forearm.head).normalized()
            forearm_z_axis = forearm_bonedata.matrix.to_3x3() @ Vector((0, 0, 1))
            if switch:
                forearm_z_axis = forearm.matrix.to_3x3() @ Vector((0, 0, 1))
            forearm_angle_sign = 1 if forearm_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
            forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
        rotate_local(forearm,2,forearm_rad)
    #在不转和转动的情况间进行插值    
    elif angle_degree > lower_bound and angle_degree < upper_bound:
        factor = (upper_bound- angle_degree)/(upper_bound - lower_bound)
        #接近直臂的情况下难以判断肘关节位置，清空forearm的xy旋转就行了
        arm_bonedata.rotation_quaternion = arm_bonedata.rotation_quaternion.slerp(arm_ref_bonedata.rotation_quaternion, factor)
        forearm_bonedata.rotation_quaternion = forearm_bonedata.rotation_quaternion.slerp(forearm_rotation_quaternion_step2, factor)
        if switch:
            arm.rotation_quaternion = arm.rotation_quaternion.slerp(arm_ref.rotation_quaternion, factor)
            forearm.rotation_quaternion = forearm.rotation_quaternion.slerp(forearm_rotation_quaternion_step2, factor)
    arm_bonedata.update_data()
    forearm_bonedata.update_data()
    hand_bonedata.update_data()        
    if not switch:
        forearm.rotation_quaternion = forearm_bonedata.rotation_quaternion
        arm.rotation_quaternion = arm_bonedata.rotation_quaternion
        hand_bonedata.matrix = hand_ref_bonedata.matrix
        #先做四元数旋转，再做静置相对于父骨骼的旋转bone.matrix，再做父骨骼带来的所有旋转parent_matrix = 当前在姿态空间的旋转matrix，反求四元数旋转
        hand_rotate_matrix : Matrix = hand.bone.matrix.to_4x4().inverted() @ forearm_bonedata.matrix.inverted() @ hand_ref_bonedata.matrix
        hand.rotation_quaternion = hand_rotate_matrix.to_quaternion().normalized()
        arm.keyframe_insert(data_path=TransformChannel.QUATERNION.value,frame = frame)
        forearm.keyframe_insert(data_path=TransformChannel.QUATERNION.value,frame = frame)
        hand.keyframe_insert(data_path=TransformChannel.QUATERNION.value,frame = frame)    
    else:
        context.evaluated_depsgraph_get().update()
        arm.keyframe_insert(data_path=TransformChannel.QUATERNION.value)
        forearm.keyframe_insert(data_path=TransformChannel.QUATERNION.value)
        hand.matrix = hand_ref.matrix
        context.evaluated_depsgraph_get().update()
        hand.keyframe_insert(data_path=TransformChannel.QUATERNION.value)    
