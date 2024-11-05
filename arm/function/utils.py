import bpy
from mathutils import  Quaternion, Euler

from ...common.properties import TransformChannel
from ...common.utils import *


def get_arm_twist_bone(pbone):
    armature = pbone.id_data
    twist_bone = armature.pose.bones.get(pbone.name.replace("_mmd","_twist_mmd")) 
    if twist_bone.name != pbone.name:
        return twist_bone
    if pbone.mmd_bone:
        twist_bone = get_pbone_by_mmd_name(armature,pbone.mmd_bone.name_j.replace("ひじ","手捩").replace("腕","腕捩")) 
        if twist_bone and twist_bone.name != pbone.name:
            return twist_bone
    return None

def get_arm_chains(armature):
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

def get_arm_twist_data(armature):
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


# 用清除twist旋转后的骨骼对齐ref的没有清除twist旋转的骨骼
def align_after_clear_twist(armature,pbones,frame):
    armature_ref = armature.mmd_advance_data.reference    
    for pbone in pbones:
        pbone_ref = armature_ref.pose.bones[pbone.name]
        set_rotation(pbone,frame,get_rotation(pbone_ref,frame,add_twist_rotation_y = True),False)

#删除全部twist关键帧
def clear_twist(armature,pbones):
    for pbone in pbones:
        twist_pbone = get_arm_twist_bone(pbone)
        if twist_pbone:
            channel_type = TransformChannel.QUATERNION.value if pbone.rotation_mode == 'QUATERNION' else "rotation_euler"
            zero_twist_rotation = Quaternion() if twist_pbone.rotation_mode == 'QUATERNION' else Euler()
            set_rotation(twist_pbone,armature.mmd_advance_data.covert_frame_start,zero_twist_rotation)    
            set_rotation(twist_pbone,armature.mmd_advance_data.covert_frame_end,zero_twist_rotation)    
            fcurves = get_fcurves(armature.animation_data.action,twist_pbone,channel_type)
            for fcurve in fcurves:
                keyframes_to_delete = []
                for kf in fcurve.keyframe_points:
                    if kf.co[0] > armature.mmd_advance_data.covert_frame_start and kf.co[0] < armature.mmd_advance_data.covert_frame_end:
                        keyframes_to_delete.append(kf)
                for kf in reversed(keyframes_to_delete):
                    fcurve.keyframe_points.remove(kf)    

# 通过action/fcurve获得骨骼在指定时间的旋转通道值
# plus:加上子捩骨骼的y旋转，例如arm的旋转加上arm_twist
def get_rotation(pbone,frame,add_twist_rotation_y = False):

    def to_Euler(rotation,order):
        return rotation.to_euler(order) if isinstance(rotation,Quaternion) else rotation.to_quaternion().to_euler(order)
    
    def to_blender_rotation(rotation_values):
        return Quaternion(rotation_values).normalized() if len(rotation_values) == 4 else Euler(rotation_values)

    action = pbone.id_data.animation_data.action
    rotation_values = get_values_at_frame(action, pbone, TransformChannel.QUATERNION.value if pbone.rotation_mode == 'QUATERNION' else TransformChannel.EULER.value, frame)
    rotation = to_blender_rotation(rotation_values)
    if add_twist_rotation_y:
        twist_pbone = get_arm_twist_bone(pbone)
        if twist_pbone:
            twist_rotation = get_rotation(twist_pbone,frame)
            twist_euler_rotation = to_Euler(twist_rotation,"YXZ")
            euler_rotation = to_Euler(rotation,"YXZ")
            euler_rotation.y += twist_euler_rotation.y
            rotation = euler_rotation.to_quaternion() if pbone.rotation_mode == 'QUATERNION' else euler_rotation.to_quaternion().to_euler(pbone.rotation_euler.order)
    return rotation

# plus:清空捩骨骼的旋转
def set_rotation(pbone,frame,rotation,update_curve = True):
    action = pbone.id_data.animation_data.action
    channel_type = TransformChannel.QUATERNION.value if pbone.rotation_mode == 'QUATERNION' else TransformChannel.EULER.value
    fcurves = get_fcurves(action,pbone,channel_type)
    if pbone.rotation_mode == 'QUATERNION':
        value = [rotation.w, rotation.x, rotation.y, rotation.z,]
    else:
        value = [rotation.x, rotation.y, rotation.z,]
    update_keyframe(fcurves, frame, value,update_curve)

def check_rotation_mode(armature):
    pbone_data = get_arm_chains(armature)[0] + get_arm_twist_data(armature)[0]
    for pbones in pbone_data:
        if not pbones:
            return False
        for pbone in pbones:
            if not pbone:
                return False
            if pbone.rotation_mode != 'QUATERNION':
                return False
    return True        

def close_limit_rotation(armature):
    pbone_data, pbone_data_ref = get_arm_chains(armature)
    for i in range(len(pbone_data)):
        posebones = pbone_data[i]
        posebones_ref = pbone_data_ref[i]
        arm, forearm, hand  = posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref
        for pbone in [arm,arm_ref,forearm,forearm_ref,hand,hand_ref,]:
            for cns in pbone.constraints:
                if cns.type == "LIMIT_ROTATION":
                    cns.enabled = False
