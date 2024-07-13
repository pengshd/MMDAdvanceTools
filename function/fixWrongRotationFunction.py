from .. import logger
from .commonFunction import *
from math import pi

# 修复旋转方向错误的情况
def fix_bone_rotation_path(armature,posebones,frames):
    action = armature.animation_data.action
    armature_ref = armature.mmd_advance_data.reference
    action_ref = armature_ref.animation_data.action
    if not action or not action_ref:
        return None
    for pbone in posebones:
        frame_prev = None
        fixed_frame = []
        fixed_frame_str = ""
        for frame in frames:
            fcurves = []
            values = []
            if pbone.rotation_mode == 'QUATERNION':
                quat = get_rotation(pbone,frame,False)
                fcurves = get_fcurves(action,pbone,"rotation_quaternion")
                if frame_prev:
                    quat_prev = get_rotation(pbone,frame_prev,False)
                    #rot_dir为负证明旋转角度超过180，也就是所谓的“反转” 如果参考骨骼rot_dir_ref和rot_dir符号不一致，证明旋转方向不一致，那么就让当前骨骼换一个旋转方向
                    rot_dir = quat.dot(quat_prev)
                    posebone_ref = armature_ref.pose.bones[pbone.name]
                    rot_dir_ref = get_rotation(posebone_ref,frame,False).dot(get_rotation(posebone_ref,frame_prev,False)) + \
                        get_rotation(get_twist_bone(posebone_ref),frame,False).dot(get_rotation(get_twist_bone(posebone_ref),frame_prev,False)) if get_twist_bone(posebone_ref) else 0
                    factor = 1 if rot_dir * rot_dir_ref >= 0 else -1
                    quat = Quaternion((factor*quat.w, factor*quat.x, factor*quat.y, factor*quat.z)).normalized()
                    values = [quat.w, quat.x, quat.y, quat.z,]
            else:
                euler = get_rotation(pbone,frame,False)
                fcurves = get_fcurves(action,pbone,"rotation_euler")
                euler_rotation = euler.to_quaternion().to_euler("YXZ")
                if frame_prev:
                    euler_rotation_prev = get_rotation(pbone,frame_prev,False)
                    if euler_rotation_prev and abs(euler_rotation_prev.y - euler_rotation.y) > pi:
                        factor = 1 if euler_rotation_prev.y>euler_rotation.y else -1
                        euler_rotation.y += (2*pi*factor)
                        euler_final = euler_rotation.to_quaternion().to_euler(pbone.rotation_euler.order)
                        values = [euler_final.x, euler_final.y, euler_final.z,]
            if values:                        
                if factor == -1:
                    update_keyframe(fcurves, frame, values)
                    fixed_frame.append(frame)
            frame_prev = frame    
            fixed_frame_str = logger.concatenate_elements(fixed_frame)
        logger.info(f"fix rotation {pbone.name} {len(fixed_frame)} frames: {fixed_frame_str}")
