from mathutils import Matrix, Vector
from math import pi
from .commonFunction import *

def adjust_bone_rotation_for_ergonomics(context, armature, posebones, posebones_ref):

    def rotate_local(posebone,axis_index,rad):
        axis = (posebone.matrix.to_3x3().col)[axis_index]
        # rotation matrix 30 degrees around local x axis thru head
        R = (Matrix.Translation(posebone.head) @
            Matrix.Rotation(rad, 4, axis) @
            Matrix.Translation(-posebone.head)
            )
        posebone.matrix = R @ posebone.matrix

    arm,forearm,hand = posebones
    arm_ref,forearm_ref,hand_ref = posebones_ref
    armature_ref = armature.mmd_advance_data.reference
    #forearm_ref实际的父级，复制了arm_ref的世界空间旋转
    arm_calc_ref = armature_ref.pose.bones[arm_ref.name.replace("mmd.","mmd_calc.")]
    forearm_direction_state0 = (forearm_ref.tail - forearm_ref.head).normalized()
    arm_direction_state0 = (arm_ref.tail - arm_ref.head).normalized()
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
    arm_head_pos = armature.matrix_world@arm_calc_ref.head
    forearm_head_pos = armature.matrix_world@forearm_ref.head
    forearm_tail_pos = armature.matrix_world@forearm_ref.tail
    normal_state1 = (forearm_tail_pos - forearm_head_pos).cross(forearm_head_pos - arm_head_pos).normalized()
    forearm_direction_state1 = (forearm_ref.tail - forearm_ref.head).normalized()
    #step2
    forearm.rotation_euler.x = forearm.rotation_euler.y = 0
    if forearm.rotation_mode == 'QUATERNION':
        forearm.rotation_quaternion.x = forearm.rotation_quaternion.y = 0
    context.view_layer.update()    
    forearm_rotation_quaternion_step2 = forearm.rotation_quaternion.copy()
    forearm_rotation_euler_step2 = forearm.rotation_euler.copy()
    #step3
    lower_bound = armature.mmd_advance_data.arm_forearm_angle_lowerbound
    upper_bound = armature.mmd_advance_data.arm_forearm_angle_upperbound
    if angle_degree > lower_bound:
        # arm_head_pos = armature.matrix_world@arm.head
        arm_head_pos = armature.matrix_world@arm_calc_ref.head
        forearm_head_pos = armature.matrix_world@forearm.head
        forearm_tail_pos = armature.matrix_world@forearm.tail
        normal_state2 = (forearm_tail_pos - forearm_head_pos).cross(forearm_head_pos - arm_head_pos).normalized()
        #step4 
        #从2旋转到1
        # 计算两个平面夹角
        plane_angle_sign = 1 if (forearm_head_pos - arm_head_pos).dot(normal_state2.cross(normal_state1)) >=0 else -1
        plane_rad = normal_state2.angle(normal_state1)*plane_angle_sign
        rotate_local(arm,1,plane_rad)
        context.view_layer.update()
        #step5
        forearm_direction_state3=(forearm.tail - forearm.head).normalized()
        #step6
        #从3旋转到1
        # 将局部 Z 轴方向转换为世界空间方向
        world_z_axis = armature.matrix_world @ (forearm.matrix.to_quaternion() @ Vector((0, 0, 1)))
        forearm_angle_sign = 1 if world_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
        forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
        #如果forearm旋转反关节
        forearm_reverse = False
        if forearm.rotation_mode == 'QUATERNION':
            rotation_euler_zxy = forearm.rotation_quaternion.to_euler("ZXY")
            if rotation_euler_zxy.z + forearm_rad <0:
                forearm_reverse = True
        elif forearm.rotation_euler.z + forearm_rad <0:
                forearm_reverse = True
        #如果forearm需要反关节才能达到目标位置，那就把arm反转再重新计算forearm该如何旋转                        
        if forearm_reverse:
            rotate_local(arm,1,pi)
            context.view_layer.update()
            forearm_direction_state3=(forearm.tail - forearm.head).normalized()
            world_z_axis = armature.matrix_world @ (forearm.matrix.to_quaternion() @ Vector((0, 0, 1)))
            forearm_angle_sign = 1 if world_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
            forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
        rotate_local(forearm,2,forearm_rad)
        #在不转和转动的情况间进行插值    
    if angle_degree > lower_bound and angle_degree < upper_bound:
        factor = (upper_bound- angle_degree)/(upper_bound - lower_bound)
        if arm.rotation_mode == 'QUATERNION':
            arm.rotation_quaternion = arm.rotation_quaternion.slerp(arm_ref.rotation_quaternion, factor)
        else:
            arm_quat = arm.rotation_euler.to_quaternion().slerp(arm_ref.rotation_euler.to_quaternion(), factor)  
            arm.rotation_euler = arm_quat.to_euler(arm.rotation_euler.order)
        if forearm.rotation_mode == 'QUATERNION':
            forearm.rotation_quaternion = forearm.rotation_quaternion.slerp(forearm_rotation_quaternion_step2, factor)
        else:
            forearm_quat = forearm.rotation_euler.to_quaternion().slerp(forearm_rotation_euler_step2, factor)  
            forearm.rotation_euler = forearm_quat.to_euler(forearm.rotation_euler.order)    
    context.view_layer.update()
    arm.keyframe_insert(data_path="rotation_quaternion")
    forearm.keyframe_insert(data_path="rotation_quaternion")
    hand.matrix = hand_ref.matrix
    context.view_layer.update()
    hand.keyframe_insert(data_path="rotation_quaternion")