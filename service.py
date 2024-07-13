from . import logger
from .function.commonFunction import *
from .function.changeRotationFunction import convert_rotation_mode_and_align
from .function.calcExceedFunction import fix_bone_rotation_difference
from .function.fixWrongRotationFunction import fix_bone_rotation_path

def convert_arm_rotation(context):
    armature = context.active_object
    current_frame = context.scene.frame_current
    posebone_data,posebone_data_ref = get_pbone_chains(armature)
    for i in range(len(posebone_data)):
        posebones = posebone_data[i]
        posebones_ref = posebone_data_ref[i]
        arm, forearm, hand = posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref

        arm_name = "leftside" if ".L" in arm.name.upper() or "_L" in arm.name.upper() else "rightside"
        logger.info(f"fix {arm_name} all 3 steps 。")
        ##关掉前臂的限制旋转
        close_limit_rotation(armature)
        frames = get_key_frames(armature,posebones,armature.mmd_advance_data.covert_frame_start,armature.mmd_advance_data.covert_frame_end)

        logger.info(f"step 1/3 get {len(frames)} frames.")

        pb = logger.ProgressBar(f"step 2/3 {arm_name} supply frames",len(frames))
        for frame in frames:
            pb.show_progress_bar() 
            supply_keyframe(armature, posebones, frame)
            clear_twist_align(armature, posebones, frame)
        
        pb = logger.ProgressBar(f"step 3/3 {arm_name} adjust rotation",len(frames))
        for frame in frames:   
            pb.show_progress_bar() 
            context.scene.frame_set(frame)
            convert_rotation_mode_and_align(context, armature, [arm, forearm, hand], [arm_ref, forearm_ref, hand_ref])
    context.scene.frame_current = current_frame

def fix_all_rotation_path(armature):
    logger.swtitch = False
    pbone_chains = get_pbone_chains(armature)[0]
    for chain_pbones in pbone_chains:
        for pbone in chain_pbones:
            frames = get_key_frames(armature,[pbone],armature.mmd_advance_data.covert_frame_start,armature.mmd_advance_data.covert_frame_end)
            fix_bone_rotation_path(armature,[pbone],frames)     
    logger.swtitch = True           

def fix_all_bone_rotation_difference(context,armature):
    for chain_pbones in get_pbone_chains(armature)[0]:
        for pbone in chain_pbones:
            for i in range(10):
                logger.info(f"{pbone.name} fix exceed round {i+1} >>>>")
                if i == 0:
                    fix_all_rotation_path(armature)
                fix_frames = fix_bone_rotation_difference(context,armature,pbone)
                fix_all_rotation_path(armature)
                if not fix_frames:
                    logger.info(f"{pbone.name} fix exceed all complete!")
                    break

def check_rotation_mode(armature):
    pbone_data = get_pbone_chains(armature)[0] + get_twist_pbone_data(armature)[0]
    for pbones in pbone_data:
        if not pbones:
            return False
        for pbone in pbones:
            if not pbone:
                return False
            if pbone.rotation_mode != 'QUATERNION':
                return False
    return True        