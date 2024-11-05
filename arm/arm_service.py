import gc
from ..common import logger
from ..common.utils import *
from ..common import boneAdvanceData
from .function.utils import *
from .function.convert_rotation import *
from .function.calc_exceed import * 
from .function.fix_rotation import * 

def convert_arm_rotation(context : bpy.types.Context,side):
    armature = context.active_object
    current_frame = context.scene.frame_current
    posebone_data,posebone_data_ref = get_arm_chains(armature)
    for i in range(len(posebone_data)):
        posebones = posebone_data[i]
        posebones_ref = posebone_data_ref[i]
        arm, forearm, hand = posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref
        arm_name = "leftside" if ".L" in arm.name.upper() or "_L" in arm.name.upper() else "rightside"
        if side != arm_name:
            continue
        logger.info(f"fix {arm_name} all 3 steps 。")
        ##关掉前臂的限制旋转
        close_limit_rotation(armature)
        frames = get_key_frames(armature,posebones,armature.mmd_advance_data.covert_frame_start,armature.mmd_advance_data.covert_frame_end)

        logger.info(f"step 1/3 get {len(frames)} frames.")

        clear_twist(armature,posebones)    
        pb = logger.ProgressBar(f"step 2/3 {arm_name} supply frames",len(frames))
        for frame in frames:
            pb.show_progress_bar() 
            supply_keyframe(armature, posebones, frame)
            align_after_clear_twist(armature, posebones, frame)
        pb = logger.ProgressBar(f"step 3/3 {arm_name} adjust rotation",len(frames))
        for frame in frames:   
            pb.show_progress_bar() 
            # context.scene.frame_set(frame)
            convert_rotation_mode_and_align(context, [arm, forearm, hand], [arm_ref, forearm_ref, hand_ref], frame)
    context.scene.frame_current = current_frame

def fix_all_rotation_path(armature):
    logger.swtitch = False
    pbone_chains = get_arm_chains(armature)[0]
    for chain_pbones in pbone_chains:
        for pbone in chain_pbones:
            frames = get_key_frames(armature,[pbone],armature.mmd_advance_data.covert_frame_start,armature.mmd_advance_data.covert_frame_end)
            fix_bone_rotation_path(armature,[pbone],frames)     
    logger.swtitch = True           

def fix_all_rotation_diff(context,armature):
    for chain_pbones in get_arm_chains(armature)[0]:
        for pbone in chain_pbones:
            for i in range(10):
                logger.info(f"{pbone.name} fix exceed round {i+1} >>>>")
                if i == 0:
                    fix_all_rotation_path(armature)
                fix_frames = fix_rotation_diff(context,armature,pbone)
                fix_all_rotation_path(armature)
                if not fix_frames:
                    logger.info(f"{pbone.name} fix exceed all complete!")
                    break
