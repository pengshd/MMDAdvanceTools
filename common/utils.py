from typing import List
import bpy

from .properties import TransformChannel

def get_pbone_by_mmd_name(armature,mmd_name):
    return next((pbone for pbone in armature.pose.bones if pbone.mmd_bone.name_j == mmd_name), None)

def fix_mmd_bone_name(armature):
    for pbone in (pbone for pbone in armature.pose.bones if pbone.mmd_bone):
        mirror_name = get_symmetrical_bone_name(pbone.name)
        if mirror_name:
            mirror_pbone = armature.pose.bones.get(mirror_name)   
            if mirror_pbone:
                mmd_bone_pair = (pbone.mmd_bone, mirror_pbone.mmd_bone)
                for i, b in enumerate(mmd_bone_pair):
                    #用存在name的对称骨骼补充不存在name的骨骼的属性
                    if b.name_j and not mmd_bone_pair[1-i].name_j:
                        mmd_bone_pair[1-i].name_j = get_symmetrical_bone_name(b.name_j)
                        mmd_bone_pair[1-i].name_e = get_symmetrical_bone_name(b.name_e) if b.name_e else ""

        suffix_pairs = [('.l','.r'),('_l','_r'),('.L','.R'),('_L','_R'),('左','右')]
        if pbone.mmd_bone.name_j:
            is_right_side = (pbone.bone.head_local.x>0)
            for pair in suffix_pairs:
                suffix_from, suffix_to = pair[0], pair[1]
                if is_right_side:
                    suffix_from, suffix_to = suffix_to, suffix_from
                pbone.mmd_bone.name_e = pbone.mmd_bone.name_e.replace(suffix_from,suffix_to)
                pbone.mmd_bone.name_j = pbone.mmd_bone.name_j.replace(suffix_from,suffix_to)
        

def fix_mmd_bone_id(armature):
    for pbone in (pbone for pbone in armature.pose.bones if pbone.mmd_bone):
        mirror_name = get_symmetrical_bone_name(pbone.name)
        if mirror_name:
            mirror_pbone = armature.pose.bones.get(mirror_name)   
            if mirror_pbone:
                pair = (pbone.mmd_bone, mirror_pbone.mmd_bone)
                for i, b in enumerate(pair):
                    if b.bone_id >=0 and pair[1-i].bone_id < 0:
                        pair[1-i].bone_id = b.bone_id + 1
            if not pbone.mmd_bone.is_id_unique(): 
                used_bone_ids = {b.mmd_bone.bone_id for b in armature.pose.bones if b != pbone}
                # 然后尝试找到未被使用的 bone_id
                for i in range(max(used_bone_ids)+2):
                    if i not in used_bone_ids:
                        pbone.mmd_bone.bone_id = i
                        break                    

def get_symmetrical_bone_name(bone_name):
    suffix_pairs = [('.l','.r'),('_l','_r'),('.L','.R'),('_L','_R'),]
    chinese_pair = ('左','右')
    # 检查并替换英文后缀
    for suffix_pair in suffix_pairs:
        for i, suffix in enumerate(suffix_pair):
            if bone_name.endswith(suffix):
                return bone_name[:-2] + suffix_pair[1-i]
    # 检查并替换中文
    for i, c_word in enumerate(chinese_pair):
        if c_word in bone_name:
            return bone_name.replace(c_word, chinese_pair[1-i])
    return None

#获取在>=frame_start且<=frame_end范围内的关键帧的帧数
def get_key_frames(armature,pbones : List[bpy.types.PoseBone],frame_start:int,frame_end:int):
    keyframe_frames = set()  # 使用集合来确保不重复
    action = armature.animation_data.action
    if not action:
        return None
    for pbone in pbones:
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith("pose.bones[\"{}\"].".format(pbone.name)):
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
                # if not has_keyframe_at_frame(fcurve,frame):
                value = fcurve.evaluate(frame)
                fcurve.keyframe_points.add(1)
                fcurve.keyframe_points[-1].co=(frame,value)       
                fcurve.update()                    


def find_fcurve(fcurves, bonename, type, index):
    return fcurves.find(data_path=f'pose.bones[\"{bonename}\"].{type}', index=index)

def get_fcurves(action,pbone,type )-> List[bpy.types.FCurve]:
    fcurves = []
    channel_count = 4 if type == TransformChannel.QUATERNION.value else 3
    for i in range(channel_count):
        fcurves.append(find_fcurve(action.fcurves, pbone.name, type, index=i))
    return fcurves    

def get_values_at_frame(action,pbone:bpy.types.PoseBone,type,frame):
    fcurves = get_fcurves(action,pbone,type)
    if not fcurves:
        return getattr(pbone, type).to_tuple()
    list = []
    for i in range(len(fcurves)):
        fcurve = fcurves[i]
        if not fcurve:
            list.append(getattr(pbone, type)[i])
        else:
            list.append(fcurve.evaluate(frame))
    return list            

def update_keyframe(fcurves, frame, values, update_curve = True):
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
        if update_curve:
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
