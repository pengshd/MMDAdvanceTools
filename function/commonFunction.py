import bpy
from mathutils import  Quaternion, Euler
from ..properties import Transform

def get_pbone_by_mmd_name(armature,mmd_name):
    for pbone in armature.pose.bones:
        if pbone.mmd_bone.name_j == mmd_name:
            return pbone
    return None

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

#获取在>=frame_start且<=frame_end范围内的关键帧的帧数
def get_key_frames(armature,posebones,frame_start,frame_end):
    keyframe_frames = set()  # 使用集合来确保不重复
    action = armature.animation_data.action
    if not action:
        return None
    for posebone in posebones:
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith("pose.bones[\"{}\"].".format(posebone.name)):
                for keyframe_point in fcurve.keyframe_points:
                    if keyframe_point.co[0] < frame_start:
                        continue
                    if keyframe_point.co[0] > frame_end:
                        break
                    keyframe_frames.add(round(keyframe_point.co[0]))
    return sorted(list(keyframe_frames))   

def get_keyframe_at_frame(fcurve, frame):
    # 遍历关键帧点，查找与给定帧相匹配的关键帧
    for keyframe in fcurve.keyframe_points:
        if round(keyframe.co.x) == frame:
            return keyframe
    return None       


def close_limit_rotation(armature):
    pbone_data, pbone_data_ref = get_pbone_chains(armature)
    for i in range(len(pbone_data)):
        posebones = pbone_data[i]
        posebones_ref = pbone_data_ref[i]
        arm, forearm, hand  = posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref
        for pbone in [arm,arm_ref,forearm,forearm_ref,hand,hand_ref,]:
            for cns in pbone.constraints:
                if cns.type == "LIMIT_ROTATION":
                    cns.enabled = False

# 如果frame帧posebones中任一骨骼有关键帧，就给posebones中的每根骨骼添加关键帧
def supply_keyframe(armature,pbones,frame):    
    def is_fcurve_related_to_posebone(fcurve, posebone_name):
        data_path = fcurve.data_path
        return data_path.startswith("pose.bones[\"{}\"]".format(posebone_name))
    
    def has_keyframe_at_frame(fcurve, frame):
        for keyframe_point in fcurve.keyframe_points:
            if round(keyframe_point.co[0]) == frame:
                return True
        return False
    
    for pbone in pbones:
        for fcurve in armature.animation_data.action.fcurves:
            if is_fcurve_related_to_posebone(fcurve,pbone.name):
                if not has_keyframe_at_frame(fcurve,frame):
                    value = fcurve.evaluate(frame)
                    fcurve.keyframe_points.add(1)
                    fcurve.keyframe_points[-1].co=(frame,value)

# 用清除twist旋转后的骨骼对齐ref
def clear_twist_align(armature,pbones,frame):
    armature_ref = armature.mmd_advance_data.reference    
    for pbone in pbones:
        pbone_ref = armature_ref.pose.bones[pbone.name]
        set_rotation(pbone,frame,get_rotation(pbone_ref,frame,add_twist_rotation_y = True),clear_twist = True)


def find_fcurve(fcurves, bonename, type, index):
    return fcurves.find(data_path=f'pose.bones[\"{bonename}\"].{type}', index=index)

def get_fcurves(action,pbone,type):
    fcurves = []
    channel_count = 4 if type == "rotation_quaternion" else 3
    for i in range(channel_count):
        fcurves.append(find_fcurve(action.fcurves, pbone.name, type, index=i))
    return fcurves    

def get_values_at_frame(action,pbone,type,frame):
    fcurves = get_fcurves(action,pbone,type)
    list = []
    for fcurve in fcurves:
        list.append(fcurve.evaluate(frame))
    return list            

def to_blender_rotation(rotation_values):
    return Quaternion(rotation_values).normalized() if len(rotation_values) == 4 else Euler(rotation_values)

def to_Euler(rotation,order):
    return rotation.to_euler(order) if isinstance(rotation,Quaternion) else rotation.to_quaternion().to_euler(order)

# 通过action/fcurve获得骨骼在指定时间的旋转通道值
# plus:加上子捩骨骼的y旋转，例如arm的旋转加上arm_twist
def get_rotation(pbone,frame,add_twist_rotation_y = False):
    action = pbone.id_data.animation_data.action
    rotation_values = get_values_at_frame(action, pbone, "rotation_quaternion" if pbone.rotation_mode == 'QUATERNION' else "rotation_euler", frame)
    rotation = to_blender_rotation(rotation_values)
    if add_twist_rotation_y:
        twist_pbone = get_twist_bone(pbone)
        if twist_pbone:
            twist_rotation = get_rotation(twist_pbone,frame)
            twist_euler_rotation = to_Euler(twist_rotation,"YXZ")
            euler_rotation = to_Euler(rotation,"YXZ")
            euler_rotation.y += twist_euler_rotation.y
            rotation = euler_rotation.to_quaternion() if pbone.rotation_mode == 'QUATERNION' else euler_rotation.to_quaternion().to_euler(pbone.rotation_euler.order)
    return rotation

# plus:清空捩骨骼的旋转
def set_rotation(pbone,frame,rotation,clear_twist = False):
    action = pbone.id_data.animation_data.action
    channel_type = "rotation_quaternion" if pbone.rotation_mode == 'QUATERNION' else "rotation_euler"
    fcurves = get_fcurves(action,pbone,channel_type)
    if pbone.rotation_mode == 'QUATERNION':
        value = [rotation.w, rotation.x, rotation.y, rotation.z,]
    else:
        value = [rotation.x, rotation.y, rotation.z,]
    update_keyframe(fcurves, frame, value)
    if clear_twist:
        twist_pbone = get_twist_bone(pbone)
        if twist_pbone:
            final_twist_rotation = Quaternion() if twist_pbone.rotation_mode == 'QUATERNION' else Euler()
            set_rotation(twist_pbone,frame,final_twist_rotation)

def update_keyframe(fcurves, frame, values):
    for i in range(len(fcurves)):
        fcurve = fcurves[i]
        point = get_keyframe_at_frame(fcurve,frame)
        if not point:   
            fcurve.keyframe_points.add(1)
            point = fcurve.keyframe_points[-1]
        value_changed = values[i] - point.co[1]    
        point.co = frame, values[i]
        #0是帧数，1是值
        point.handle_left[1] += value_changed
        point.handle_right[1] += value_changed
        fcurve.update()

def create_reference_armature(context,armature):
    # 复制骨骼对象
    armature_ref = armature.copy()
    armature_ref.name = armature.name + "_ref"
    armature_ref.data = armature.data.copy()
    armature_ref.data.name = armature.data.name + "_ref"

    # 将复制的骨骼对象添加到场景中
    for collection in armature.users_collection:
        collection.objects.link(armature_ref)
    # 复制动作
    if armature.animation_data is not None and armature.animation_data.action is not None:
        # 复制动作
        temp_action = armature.animation_data.action.copy()
        temp_action.name = armature.animation_data.action.name+"_ref"

        # 将复制的动作与复制的骨骼对象关联
        armature_ref.animation_data_create()
        armature_ref.animation_data.action = temp_action
        armature_ref.hide_set(True)
        armature_ref.data.display_type = 'STICK'

    armature.mmd_advance_data.reference = armature_ref

def delete_reference_armature(context,armature):
    armature_ref = armature.mmd_advance_data.reference
    if armature_ref:
        action = armature_ref.animation_data.action
        if action:
            bpy.data.actions.remove(action)
        bpy.data.objects.remove(armature_ref)   
    armature.mmd_advance_data.reference = None         

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

def clear_bone_fcurves(armature, pbone):  
    # 获取骨骼的动画数据  
    if armature.animation_data:  
        action = pbone.animation_data.action  
        if action:  
            fcurves = action.fcurves  
            fcurves_to_remove = []  
            for fcurve in fcurves:  
                if fcurve.data_path.startswith(f"pose.bones[\"{pbone.name}\"]."):  
                    fcurves_to_remove.append(fcurve)  
            for fcurve in fcurves_to_remove:  
                action.fcurves.remove(fcurve)  


def get_twist_bone(pbone):
    return pbone.id_data.pose.bones.get(pbone.name.replace("_mmd","_twist_mmd")) 

def find_sandwiching_frames(frames, current_frame):  
    frame_start, frame_end = None, None  
    for frame in reversed(frames):  
        if frame < current_frame:  
            frame_start = frame  
            break  
    for frame in frames:  
        if frame > current_frame:  
            frame_end = frame  
            break  
    if not frame_start or not frame_end:
        return None
    return [frame_start, frame_end]  


def get_pbone_chains(armature):
    armature_ref = armature.mmd_advance_data.reference
    pbone_chains = (
        (get_pbone_by_mmd_name(armature,"左腕"),get_pbone_by_mmd_name(armature,"左ひじ"),get_pbone_by_mmd_name(armature,"左手首")),
        (get_pbone_by_mmd_name(armature,"右腕"),get_pbone_by_mmd_name(armature,"右ひじ"),get_pbone_by_mmd_name(armature,"右手首")),
    )
    pbone_chains_ref = None
    if armature_ref:
        pbone_chains_ref = (
            (get_pbone_by_mmd_name(armature_ref,"左腕"),get_pbone_by_mmd_name(armature_ref,"左ひじ"),get_pbone_by_mmd_name(armature_ref,"左手首")),
            (get_pbone_by_mmd_name(armature_ref,"右腕"),get_pbone_by_mmd_name(armature_ref,"右ひじ"),get_pbone_by_mmd_name(armature_ref,"右手首")),
        )
    return pbone_chains,pbone_chains_ref

def get_twist_pbone_data(armature):
    armature_ref = armature.mmd_advance_data.reference
    twist_pbone_chains = (
        (get_pbone_by_mmd_name(armature,"左腕捩"),get_pbone_by_mmd_name(armature,"左手捩"),),
        (get_pbone_by_mmd_name(armature,"右腕捩"),get_pbone_by_mmd_name(armature,"右手捩"),),
    )
    twist_pbone_chains_ref = None
    if armature_ref:
        twist_pbone_chains_ref = (
            (get_pbone_by_mmd_name(armature_ref,"左腕捩"),get_pbone_by_mmd_name(armature_ref,"左手捩"),),
            (get_pbone_by_mmd_name(armature_ref,"右腕捩"),get_pbone_by_mmd_name(armature_ref,"右手捩"),),
        )
    return twist_pbone_chains,twist_pbone_chains_ref
