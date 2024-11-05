from ..common import logger
from ..common.utils import *
from .function.fix_ik import fix_frame
from .function.utils import get_leg_chains, create_more_keyframes

#将leg从IK转成FK，只转换现有的关键帧
#0.关闭腿部IK
#1.获取一组腿部骨骼的链条及IK的所有关键帧，补充关键帧
#2.获取上述关键帧的帧数，在对应帧数计算IK算法下的旋转，并插入帧(只需要插入大腿的帧就行了)
#3.打开腿部IK
def convert_leg_rotation(context,side):
    armature = context.active_object
    current_frame = context.scene.frame_current
    posebone_data,posebone_data_ref = get_leg_chains(armature)
    for i in range(len(posebone_data)):
        pbones = posebone_data[i]
        thigh, leg, ik = pbones
        side_name = "leftside" if ".L" in thigh.name.upper() or "_L" in thigh.name.upper() else "rightside"
        if side != side_name:
            continue
        logger.info(f"fix {side_name} all 3 steps 。")
        frames = get_key_frames(armature,pbones,armature.mmd_advance_data.covert_frame_start,armature.mmd_advance_data.covert_frame_end)
        if armature.mmd_advance_data.leg_ik_convert_interval > 0:
            more_frames = create_more_keyframes(armature.mmd_advance_data.covert_frame_start,armature.mmd_advance_data.covert_frame_end,armature.mmd_advance_data.leg_ik_convert_interval)
            frames = sorted(set(more_frames + frames))

        logger.info(f"step 1/3 get {len(frames)} frames.")
        pb = logger.ProgressBar(f"step 2/3 {side_name} supply frames",len(frames))
        for frame in frames:
            pb.show_progress_bar() 
            supply_keyframe(armature, [thigh, leg], frame)
        pb = logger.ProgressBar(f"step 3/3 {side_name} adjust rotation",len(frames))
        for frame in frames:   
            pb.show_progress_bar() 
            # context.scene.frame_set(frame)
            fix_frame([thigh, leg, ik], armature.mmd_advance_data.leg_ik_loop_count, armature.animation_data.action, frame)
            # armature.mmd_advance_data.leg_ik_loop_count
    context.scene.frame_current = current_frame
       
