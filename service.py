from . import logger
from .function.commonFunction import *
from .function.changeRotationFunction import adjust_bone_rotation_for_ergonomics
from .function.calcExceedFunction import fix_interpolation_exceed_rotation_difference
from .function.fixWrongRotationFunction import fix_wrong_rotation

def convert_arm_rotation(context):
    armature = context.active_object
    current_frame = context.scene.frame_current
    posebone_data,posebone_data_ref = get_pbone_data(armature)
    for i in range(len(posebone_data)):
        posebones = posebone_data[i]
        posebones_ref = posebone_data_ref[i]
        arm, forearm, hand = posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref
        ##关掉前臂的限制旋转
        close_limit_rotation(armature)

        frames = get_keyframe_frames(armature,posebones)
        logger.info(f"get {len(frames)} keyframes.")
        progress = 0
        for frame in frames:
            logger.show_progress_bar(arm.name+" step1/step2 fix_keyframes",progress,len(frames)) 
            supply_keyframe(armature, posebones, frame, True)
            progress+=1
        
        progress = 0
        for frame in frames:   
            logger.show_progress_bar(arm.name+" step2/step2 fix_arm_rotation",progress,len(frames)) 
            context.scene.frame_set(frame)
            adjust_bone_rotation_for_ergonomics(context, armature, [arm, forearm, hand], [arm_ref, forearm_ref, hand_ref])
            progress+=1
    context.scene.frame_current = current_frame

def fix_quaternion(context):
    armature = context.active_object
    pbones_data = get_pbone_data(armature)[0]
    for pbones in pbones_data:
        for pbone in pbones:
            frames = get_keyframe_frames(armature,[pbone])
            fix_wrong_rotation(armature,[pbone],frames)        

def completely_fix_interpolation_exceed_rotation_difference(context,armature,sel_pbones,only_now):
    sel_bones_str = [pbone.name for pbone in sel_pbones]
    for i in range(10):
        logger.info(f"fix {sel_bones_str} {i+1} round>>>>")
        if i == 0:
            fix_quaternion(context)
        fix_frames = fix_interpolation_exceed_rotation_difference(context,armature,sel_pbones,only_now)
        fix_quaternion(context)
        if not fix_frames:
            logger.info(f"fix {sel_bones_str} complete!")
            return

def check_rotation_mode(armature):
    pbone_data = get_pbone_data(armature)[0] + get_twist_pbone_data(armature)[0]
    for pbones in pbone_data:
        if not pbones:
            return False
        for pbone in pbones:
            if not pbone:
                return False
            if pbone.rotation_mode != 'QUATERNION':
                return False
    return True        