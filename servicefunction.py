import bpy
from mathutils import  Quaternion, Euler

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


def get_keyframe_frames(armature,posebones,only_now = False):
    keyframe_frames = set()  # 使用集合来确保不重复
    action = armature.animation_data.action
    if not action:
        return None
    for posebone in posebones:
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith("pose.bones[\"{}\"].".format(posebone.name)):
                for keyframe_point in fcurve.keyframe_points:
                    if not only_now:
                        if keyframe_point.co[0] < armature.mmd_advance_data.covert_frame_start:
                            continue
                        if keyframe_point.co[0] > armature.mmd_advance_data.covert_frame_end:
                            break
                    keyframe_frames.add(round(keyframe_point.co[0]))
    return sorted(list(keyframe_frames))   

def get_keyframe_at_frame(fcurve, frame):
    # 遍历关键帧点，查找与给定帧相匹配的关键帧
    for keyframe in fcurve.keyframe_points:
        if round(keyframe.co.x) == frame:
            return keyframe
    return None        

#如果frame帧posebones中任一骨骼有关键帧，就给posebones中的每根骨骼添加关键帧
def supply_keyframe(armature,pbones,frame,align=False):    
    def is_fcurve_related_to_posebone(fcurve, posebone_name):
        data_path = fcurve.data_path
        return data_path.startswith("pose.bones[\"{}\"]".format(posebone_name))
    
    def has_keyframe_at_frame(fcurve, frame):
        for keyframe_point in fcurve.keyframe_points:
            if round(keyframe_point.co[0]) == frame:
                return True
        return False
    
    def align_pbone(pbone,frame):
        armature_ref = armature.mmd_advance_data.reference
        pbone_ref = armature_ref.pose.bones[pbone.name]
        set_rotation_keyframe(pbone,frame,get_rotation_keyframe(pbone_ref,frame,True)[0],True)
        # set_rotation_keyframe(pbone,frame,get_rotation_keyframe(pbone_ref,frame)[0])
    
    for pbone in pbones:
        for fcurve in armature.animation_data.action.fcurves:
            if is_fcurve_related_to_posebone(fcurve,pbone.name):
                if not has_keyframe_at_frame(fcurve,frame):
                    value = fcurve.evaluate(frame)
                    fcurve.keyframe_points.add(1)
                    fcurve.keyframe_points[-1].co=(frame,value)
                if align:
                    align_pbone(pbone,frame)
                    # fcurve.update()  


#通过action/fcurve获得骨骼在指定时间的旋转通道值
#plus:加上捩骨骼的y旋转                    
def get_rotation_keyframe(pbone,frame,plus = False):
    action = pbone.id_data.animation_data.action
    fcurves = []
    if pbone.rotation_mode == 'QUATERNION':
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=0))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=1))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=2))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=3))
        rotation = Quaternion((fcurves[0].evaluate(frame), fcurves[1].evaluate(frame), fcurves[2].evaluate(frame), fcurves[3].evaluate(frame),))
    else:
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_euler', index=0))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_euler', index=1))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_euler', index=2))
        rotation = Euler((fcurves[0].evaluate(frame), fcurves[1].evaluate(frame), fcurves[2].evaluate(frame),))
    if plus:
        twist_pbone = get_twist_bone(pbone)
        if twist_pbone:
            twist_rotation = get_rotation_keyframe(twist_pbone,frame)[0]
            twist_euler_rotation = twist_rotation.to_euler("YXZ") if twist_pbone.rotation_mode == 'QUATERNION' else twist_rotation.to_quaternion().to_euler("YXZ")
            euler_rotation = rotation.to_euler("YXZ") if pbone.rotation_mode == 'QUATERNION' else rotation.to_quaternion().to_euler("YXZ")
            euler_rotation.y += twist_euler_rotation.y
            rotation = euler_rotation.to_quaternion() if pbone.rotation_mode == 'QUATERNION' else euler_rotation.to_quaternion().to_euler(pbone.rotation_euler.order)
    return rotation, fcurves

#plus:清空捩骨骼的旋转
def set_rotation_keyframe(pbone,frame,rotation,clear_twist = False):
    fcurves = []
    action = pbone.id_data.animation_data.action
    if pbone.rotation_mode == 'QUATERNION':
        value = [rotation.w, rotation.x, rotation.y, rotation.z,]
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=0))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=1))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=2))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_quaternion', index=3))
    else:
        value = [rotation.x, rotation.y, rotation.z,]
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_euler', index=0))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_euler', index=1))
        fcurves.append(action.fcurves.find(data_path=f'pose.bones[\"{pbone.name}\"].rotation_euler', index=2))
    update_keyframe(fcurves, frame, value)
    if clear_twist:
        twist_pbone = get_twist_bone(pbone)
        if twist_pbone:
            final_twist_rotation = Quaternion((1,0,0,0)) if twist_pbone.rotation_mode == 'QUATERNION' else Euler((0,0,0))
            set_rotation_keyframe(twist_pbone,frame,final_twist_rotation)

def update_keyframe(fcurves, frame, value):
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