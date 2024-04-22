import bpy
from mathutils import Matrix, Quaternion, Vector, Euler
from math import radians, pi

from . import logger

def get_posebone_by_mmd_name(armature,mmd_name):
    for posebone in armature.pose.bones:
        if posebone.mmd_bone.name_j == mmd_name:
            return posebone
    return None


def convert_arm_rotation(context):
    def rotate_local(posebone,axis_index,rad):
        axis = (posebone.matrix.to_3x3().col)[axis_index]
        # rotation matrix 30 degrees around local x axis thru head
        R = (Matrix.Translation(posebone.head) @
            Matrix.Rotation(rad, 4, axis) @
            Matrix.Translation(-posebone.head)
            )
        posebone.matrix = R @ posebone.matrix

    armature = context.active_object
    armature_copy = context.scene.objects.get(armature.name+"_copy")
    current_frame = context.scene.frame_current
    posebone_data = (
        (get_posebone_by_mmd_name(armature,"左腕"),get_posebone_by_mmd_name(armature,"左ひじ"),get_posebone_by_mmd_name(armature,"左腕捩"),get_posebone_by_mmd_name(armature,"左手捩"),get_posebone_by_mmd_name(armature,"左手首")),
        (get_posebone_by_mmd_name(armature,"右腕"),get_posebone_by_mmd_name(armature,"右ひじ"),get_posebone_by_mmd_name(armature,"右腕捩"),get_posebone_by_mmd_name(armature,"右手捩"),get_posebone_by_mmd_name(armature,"右手首")),
    )
    posebone_data_copy = (
        (get_posebone_by_mmd_name(armature_copy,"左腕"),get_posebone_by_mmd_name(armature_copy,"左ひじ"),get_posebone_by_mmd_name(armature_copy,"左腕捩"),get_posebone_by_mmd_name(armature_copy,"左手捩"),get_posebone_by_mmd_name(armature_copy,"左手首")),
        (get_posebone_by_mmd_name(armature_copy,"右腕"),get_posebone_by_mmd_name(armature_copy,"右ひじ"),get_posebone_by_mmd_name(armature_copy,"右腕捩"),get_posebone_by_mmd_name(armature_copy,"右手捩"),get_posebone_by_mmd_name(armature_copy,"右手首")),
    )
    for i in range(len(posebone_data)):
        posebones = posebone_data[i]
        posebones_copy = posebone_data_copy[i]
        arm = posebones[0]
        forearm = posebones[1]
        arm_twist = posebones[2]
        forearm_twist = posebones[3]
        hand = posebones[4]
        arm_copy = posebones_copy[0]
        forearm_copy = posebones_copy[1]
        arm_twist_copy = posebones_copy[2]
        forearm_twist_copy = posebones_copy[3]
        hand_copy = posebones_copy[4]
        ##关掉前臂的限制旋转
        for cns in forearm.constraints:
            if cns.type == "LIMIT_ROTATION":
                cns.enabled = False
        frames = get_keyframe_frames(posebones)
        
        frames_copy = frames.copy()
        frames.clear()
        for frame in frames_copy:
            if frame > 27 and frame < 35:
                frames.append(frame)
        rate = 0
        for frame in frames:
            logger.show_progress_bar(arm.name+" step1/step2 fix_keyframes",rate,len(frames)) 
            fix_keyframes(context,posebones,frame)
            rate+=1
            
        rate = 0
        for frame in frames:   
            logger.show_progress_bar(arm.name+" step2/step2 fix_arm_rotation",rate,len(frames)) 
            context.scene.frame_set(frame)
            #清除arm_twist旋转将旋转转移到arm
            trans_twist(arm,arm_twist)
            trans_twist(forearm,forearm_twist)
            context.view_layer.update() 
            forearm_direction_state0 = (forearm_copy.tail - forearm_copy.head).normalized()
            arm_direction_state0 = (arm_copy.tail - arm_copy.head).normalized()
            # 计算两个矢量之间的夹角（弧度制）
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
            arm_head_pos = armature.matrix_world@arm_copy.head
            forearm_head_pos = armature.matrix_world@forearm_copy.head
            forearm_tail_pos = armature.matrix_world@forearm_copy.tail
            normal_state1 = (forearm_tail_pos - forearm_head_pos).cross(forearm_head_pos - arm_head_pos).normalized()
            forearm_direction_state1 = (forearm_copy.tail - forearm_copy.head).normalized()
            #step2
            forearm.rotation_euler.x = forearm.rotation_euler.y = 0
            if forearm.rotation_mode == 'QUATERNION':
                forearm.rotation_quaternion.x = forearm.rotation_quaternion.y = 0
            context.view_layer.update()    
            forearm_rotation_quaternion_step2 = forearm.rotation_quaternion.copy()
            forearm_rotation_euler_step2 = forearm.rotation_euler.copy()
            #step3
            if angle_degree > 10:
                arm_head_pos = armature.matrix_world@arm.head
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
                
                #如果forearm转向不可转的方向
                rotate_positive = True
                if forearm.rotation_mode == 'QUATERNION':
                    rotation_euler_zxy = forearm.rotation_quaternion.to_euler("ZXY")
                    if rotation_euler_zxy.z + forearm_rad <0:
                        rotate_positive = False
                elif forearm.rotation_euler.z + forearm_rad <0:
                        rotate_positive = False
                        
                if not rotate_positive:
                    rotate_local(arm,1,pi)
                    context.view_layer.update()
                    forearm_direction_state3=(forearm.tail - forearm.head).normalized()
                    world_z_axis = armature.matrix_world @ (forearm.matrix.to_quaternion() @ Vector((0, 0, 1)))
                    forearm_angle_sign = 1 if world_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
                    forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
                rotate_local(forearm,2,forearm_rad)
                
            #在不转和转动的情况间进行插值    
            if angle_degree > 10 and angle_degree < 20:
                factor = (angle_degree-10)/10
                if arm.rotation_mode == 'QUATERNION':
                    arm.rotation_quaternion = arm.rotation_quaternion.slerp(arm_copy.rotation_quaternion, factor)
                else:
                    arm_quat = arm.rotation_euler.to_quaternion().slerp(arm_copy.rotation_euler.to_quaternion(), factor)  
                    arm.rotation_euler = arm_quat.to_euler(arm.rotation_euler.order)
                if forearm.rotation_mode == 'QUATERNION':
                    forearm.rotation_quaternion = forearm.rotation_quaternion.slerp(forearm_rotation_quaternion_step2, factor)
                else:
                    forearm_quat = forearm.rotation_euler.to_quaternion().slerp(forearm_rotation_euler_step2, factor)  
                    forearm.rotation_euler = forearm_quat.to_euler(forearm.rotation_euler.order)    

            context.view_layer.update()
            if forearm.rotation_mode == 'QUATERNION':
                arm.keyframe_insert(data_path="rotation_quaternion")
                forearm.keyframe_insert(data_path="rotation_quaternion")
                arm_twist.keyframe_insert(data_path="rotation_quaternion")
                forearm_twist.keyframe_insert(data_path="rotation_quaternion")
            else:
                arm.keyframe_insert(data_path="rotation_euler")
                forearm.keyframe_insert(data_path="rotation_euler")
                arm_twist.keyframe_insert(data_path="rotation_euler")
                forearm_twist.keyframe_insert(data_path="rotation_euler")
            hand.matrix = hand_copy.matrix
            context.view_layer.update()
            if hand.rotation_mode == 'QUATERNION':
                hand.keyframe_insert(data_path="rotation_quaternion")
            else:
                hand.keyframe_insert(data_path="rotation_euler")
            rate+=1
        for cns in forearm.constraints:
            if cns.type == "LIMIT_ROTATION":
                cns.enabled = True
    context.scene.frame_current = current_frame


def fix_arm_quaternion(context):

    armature = context.active_object
    current_frame = context.scene.frame_current
    posebone_data = (
        (get_posebone_by_mmd_name(armature,"左腕"),get_posebone_by_mmd_name(armature,"左ひじ"),get_posebone_by_mmd_name(armature,"左腕捩"),get_posebone_by_mmd_name(armature,"左手捩"),get_posebone_by_mmd_name(armature,"左手首")),
        (get_posebone_by_mmd_name(armature,"右腕"),get_posebone_by_mmd_name(armature,"右ひじ"),get_posebone_by_mmd_name(armature,"右腕捩"),get_posebone_by_mmd_name(armature,"右手捩"),get_posebone_by_mmd_name(armature,"右手首")),
    )

    for posebones in posebone_data:
        arm = posebones[0]
        forearm = posebones[1]
        ##关掉前臂的限制旋转
        for cns in forearm.constraints:
            if cns.type == "LIMIT_ROTATION":
                cns.enabled = False
        hand = posebones[4]
        frames = get_keyframe_frames(posebones)
        for cns in forearm.constraints:
            if cns.type == "LIMIT_ROTATION":
                cns.enabled = True
        fix_quaternion([arm],frames)        
    context.scene.frame_current = current_frame

def get_symmetrical_bone_name(bone_name):
    if bone_name.endswith(".R"):
        return bone_name[:-2] + ".L"
    elif bone_name.endswith(".L"):
        return bone_name[:-2] + ".R"
    elif bone_name.endswith("_R"):
        return bone_name[:-2] + "_L"
    elif bone_name.endswith("_L"):
        return bone_name[:-2] + "_R"
    elif bone_name.endswith(".r"):
        return bone_name[:-2] + ".l"
    elif bone_name.endswith(".l"):
        return bone_name[:-2] + ".r"
    elif bone_name.endswith("_r"):
        return bone_name[:-2] + "_l"
    elif bone_name.endswith("_l"):
        return bone_name[:-2] + "_r"
    elif "左" in bone_name:
        return bone_name.replace("左","右")
    elif "右" in bone_name:
        return bone_name.replace("右","左")
    else:
        return ""


def get_keyframe_frames(posebones):
    # return [3584]
    # return [3570]
    # return [3566]
    # return [1867,1871,1876,1877,1881]
    keyframe_frames = set()  # 使用集合来确保不重复
    action = posebones[0].id_data.animation_data.action
    if not action:
        return None
    for posebone in posebones:
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith("pose.bones[\"{}\"].".format(posebone.name)):
                for keyframe_point in fcurve.keyframe_points:
                    keyframe_frames.add(round(keyframe_point.co[0]))
    return sorted(list(keyframe_frames))    

#如果frame帧posebones中任一骨骼有关键帧，就给posebones中的每根骨骼添加关键帧
def fix_keyframes(context,posebones,frame):    
    def is_fcurve_related_to_posebone(fcurve, posebone_name):
        data_path = fcurve.data_path
        return data_path.startswith("pose.bones[\"{}\"]".format(posebone_name))
    
    def has_keyframe_at_frame(fcurve, frame):
        for keyframe_point in fcurve.keyframe_points:
            if round(keyframe_point.co[0]) == frame:
                return True
        return False
    
    for posebone in posebones:
        for fcurve in context.active_object.animation_data.action.fcurves:
            if is_fcurve_related_to_posebone(fcurve,posebone.name) and not has_keyframe_at_frame(fcurve,frame):
                value = fcurve.evaluate(frame)
                fcurve.keyframe_points.add(1)
                fcurve.keyframe_points[-1].co=(frame,value)
                fcurve.update()  

def trans_twist(posebone,twist_posebone):
    def get_twist_rotation_y(pose_bone):
        if pose_bone.rotation_mode == 'QUATERNION':
            quaternion_rotation = pose_bone.rotation_quaternion
            euler_rotation = quaternion_rotation.to_euler("YXZ")
            return euler_rotation.y
        else:
            euler_rotation = pose_bone.rotation_euler
            return euler_rotation.y
    if posebone.rotation_mode == 'QUATERNION':
        quaternion_rotation = posebone.rotation_quaternion
        euler_rotation = quaternion_rotation.to_euler("YXZ")
        euler_rotation.y += get_twist_rotation_y(twist_posebone)
        posebone.rotation_quaternion = euler_rotation.to_quaternion()
        twist_posebone.rotation_quaternion = Quaternion((1,0,0,0))
    else:
        posebone.rotation_euler += get_twist_rotation_y(twist_posebone)
        twist_posebone.rotation_euler = Euler((0,0,0))
        



def find_root(obj):
    if not obj:
        return None
    if obj.mmd_type == 'ROOT':
        return obj
    return find_root(obj.parent)

def get_toggle_list(armature):
    pose_bones = armature.pose.bones
    cns_list = [
        [b, cns]
        for b in pose_bones
        for cns in b.constraints
        if "mmd" in b.name and cns.name.startswith("toggle_")
    ]

    if not cns_list:
        return []

    return sorted(cns_list, key=lambda x: -x[0].head.z)

def fix_quaternion(posebones,frames):
    def get_keyframe_at_frame(fcurve, frame):
        # 遍历关键帧点，查找与给定帧相匹配的关键帧
        for keyframe in fcurve.keyframe_points:
            if round(keyframe.co.x) == frame:
                return keyframe
        return None

    action = posebones[0].id_data.animation_data.action
    if not action:
        return None
    for posebone in posebones:
        euler_rotation_prev = None
        quat_prev = None
        for frame in frames:
            fcurves = []
            if posebone.rotation_mode == 'QUATERNION':
                fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_quaternion', index=0))
                fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_quaternion', index=1))
                fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_quaternion', index=2))
                fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_quaternion', index=3))

                quat = Quaternion(
                    (
                        fcurves[0].evaluate(frame),
                        fcurves[1].evaluate(frame),
                        fcurves[2].evaluate(frame),
                        fcurves[3].evaluate(frame),
                    )
                )
                # euler_rotation = quat.to_euler("YXZ")
            # else:
            #     fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_euler', index=0))
            #     fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_euler', index=1))
            #     fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{posebone.name}\"].rotation_euler', index=2))
            #     euler = Euler(
            #         (
            #             fcurves[0].evaluate(frame),
            #             fcurves[1].evaluate(frame),
            #             fcurves[2].evaluate(frame),
            #         )
            #     )
            #     euler_rotation = euler.to_quaternion().to_euler("YXZ")

            # if euler_rotation_prev and abs(euler_rotation_prev.y - euler_rotation.y) > pi:
            #     factor = 1 if euler_rotation_prev.y>euler_rotation.y else -1
            #     euler_rotation.y += (2*pi*factor)
                value = []
                if posebone.rotation_mode == "QUATERNION":
                    # quat_final = euler_rotation.to_quaternion().normalized()
                    factor = 1 if quat_prev and quat.dot(quat_prev) > 0 else -1
                    quat = Quaternion((factor*quat.w, factor*quat.x, factor*quat.y, factor*quat.z))
                    value = [
                        quat.w,
                        quat.x,
                        quat.y,
                        quat.z,
                    ]
                # else:
                #     euler_final = euler_rotation.to_quaternion().to_euler(posebone.rotation_euler.order)
                #     value = [
                #         euler_final.x,
                #         euler_final.y,
                #         euler_final.z,
                #     ]
                for i in range(len(fcurves)):
                    fcurve = fcurves[i]
                    point = get_keyframe_at_frame(fcurve,frame)
                    if not point:   
                        fcurve.keyframe_points.add(1)
                        point = fcurve.keyframe_points[-1]
                    value_changed = 0    
                    if point:
                        value_changed = value[i] - point.co[1]    
                    point.co = frame, value[i]
                    point.handle_left = point.handle_left[0], point.handle_left[1] + value_changed
                    point.handle_right = point.handle_right[0], point.handle_right[1] + value_changed
                    fcurve.update()
            # euler_rotation_prev = euler_rotation
                quat_prev = quat


def create_copy_armature(context,armature):
    # 复制骨骼对象
    if context.scene.objects.get(armature.name + "_copy") or armature.name.endswith("_copy"):
        return
    armature_copy = armature.copy()
    armature_copy.name = armature.name + "_copy"
    armature_copy.data = armature.data.copy()
    armature_copy.data.name = armature.data.name + "_copy"

    # 将复制的骨骼对象添加到场景中
    for collection in armature.users_collection:
        collection.objects.link(armature_copy)
    # 复制动作
    if armature.animation_data is not None and armature.animation_data.action is not None:
        # 复制动作
        temp_action = armature.animation_data.action.copy()
        temp_action.name = armature.animation_data.action.name+"_copy"

        # 将复制的动作与复制的骨骼对象关联
        armature_copy.animation_data_create()
        armature_copy.animation_data.action = temp_action
        armature_copy.hide_set(True)

def delete_copy_armature(context,armature):
    object = context.scene.objects.get(armature.name + "_copy")
    if armature.name.endswith("_copy"):  
        object = armature
    if object:
        action = object.animation_data.action
        if action:
            bpy.data.actions.remove(action)
        bpy.data.objects.remove(object)        
