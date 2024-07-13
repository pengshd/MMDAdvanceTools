from math import pi
import sys
from .commonFunction import *
from .. import logger
from .changeRotationFunction import convert_rotation_mode_and_align

# 对于和参考动作差异超过阈值的帧写入关键帧，为重新计算做准备
# chain_pbones 整条链上的骨骼都要在同一帧写入关键帧
def supply_frame_for_exceed_diff(armature,chain_pbones,pbone,frames):
    def calc_rotation_diff(matrix1,matrix2,ignore_y):  
        if ignore_y:
            return abs(matrix1.to_3x3().col[1].angle(matrix2.to_3x3().col[1]) * 180 / pi)
        else:
            return max(abs(matrix1.to_3x3().col[1].angle(matrix2.to_3x3().col[1]) * 180 / pi) ,\
                abs(matrix1.to_3x3().col[0].angle(matrix2.to_3x3().col[0]) * 180 / pi))
    
    def generate_adjacent_pairs(frames):
        # 生成相邻元素对组成的数组
        adjacent_pairs = [(frames[i], frames[i + 1]) for i in range(len(frames) - 1)]
        return adjacent_pairs
        
    fix_angle_limit = armature.mmd_advance_data.fix_angle_limit
    armature_ref = armature.mmd_advance_data.reference
    frame_pairs = generate_adjacent_pairs(frames)
    exceed_frames = []
    for frame_pair in frame_pairs:
        frame_start = frame_pair[0]
        frame_end = frame_pair[1]
        exceed_data = []
        for frame in range(frame_start+1, frame_end):
            matrix = calc_final_matrix(pbone,frame)
            ref_matrix = calc_final_matrix(armature_ref.pose.bones[pbone.name],frame)
            ignore_y = ("hand" not in pbone.name)
            diff = calc_rotation_diff(matrix,ref_matrix,ignore_y)
            logger.debug(f"diff={diff}")
            if diff > fix_angle_limit:
                exceed_data.append((frame,diff))
        if exceed_data:
            max_diff_tuple = max(exceed_data, key=lambda x: x[1]) 
            logger.debug(f"frame = {max_diff_tuple[0]}, diff = {max_diff_tuple[1]}")
            supply_keyframe(armature,chain_pbones,max_diff_tuple[0])
            clear_twist_align(armature,chain_pbones,max_diff_tuple[0])
            exceed_frames.append(max_diff_tuple[0])
    return exceed_frames

#根据旋转变换求骨骼最终的矩阵
def calc_final_matrix(pbone,frame):
    def get_parent_posebone(pbone):
        armature = pbone.id_data
        if "hand_" in pbone.name:
            return armature.pose.bones.get(pbone.name.replace("hand","forearm"))
        if "forearm_" in pbone.name:
            return armature.pose.bones.get(pbone.name.replace("forearm","arm"))
        if pbone.name.startswith("arm_"):
            return None
        return pbone.parent
    #绕骨骼rotate_parent_pbone旋转
    def rotate_bone(matrix,rotate_pivot_pbone,frame):

        homogeneous_point = matrix
        # 将点的坐标从世界空间转换到骨骼空间
        # 如果不归一化结果会不一样, 查了一整天
        pbone_rotation_quaternion = get_rotation(rotate_pivot_pbone,frame,True).normalized()
        point_in_bone_space = pbone_rotation_quaternion.to_matrix().to_4x4() @ rotate_pivot_pbone.bone.matrix_local.inverted() @ homogeneous_point
        matrix_world = rotate_pivot_pbone.bone.matrix_local @ point_in_bone_space
        return matrix_world
    #带local是bone于骨架空间的坐标
    rotation_bone_order = []
    rotate_pivot_pbone = pbone
    rotation_bone_order.append(rotate_pivot_pbone)
    for i in range(10):
        #先从末端算起，因为先端旋转后末端的matrix_local位置就无法和过程匹配了
        rotate_pivot_pbone = get_parent_posebone(rotate_pivot_pbone)
        if not rotate_pivot_pbone:
            break
        rotation_bone_order.append(rotate_pivot_pbone) 

    pbone_matrix_local = rotation_bone_order[0].bone.matrix_local.copy()
    for rotate_pivot_pbone in rotation_bone_order:
        pbone_matrix_local = rotate_bone(pbone_matrix_local,rotate_pivot_pbone,frame) 
    final_matrix = pbone_matrix_local.normalized()
    logger.debug(f"direction={final_matrix.to_3x3().col[1].normalized()}")
    final_head_pos = final_matrix.to_translation()  
    # logger.debug(f"final_matrix={final_matrix}")    
    return final_matrix

def fix_bone_rotation_difference(context,armature,pbone_for_check):
    current_frame = context.scene.frame_current
    pbone_chains, pbone_chains_ref = get_pbone_chains(armature)
    close_limit_rotation(armature)
    pending_frames = []
    for i in range(len(pbone_chains)):
        chain_pbones = pbone_chains[i]
        if not pbone_for_check in chain_pbones:
            continue
        chain_pbones_ref = pbone_chains_ref[i]
        frame_start = armature.mmd_advance_data.covert_frame_start
        frame_end = armature.mmd_advance_data.covert_frame_end
        frames = get_key_frames(armature,chain_pbones,frame_start,frame_end)
        if frames:       
            pending_frames = supply_frame_for_exceed_diff(armature,chain_pbones,pbone_for_check,frames)
        progress = 0
        for frame in pending_frames:   
            context.scene.frame_set(frame)
            convert_rotation_mode_and_align(context, armature, chain_pbones, chain_pbones_ref)
            progress+=1
        fixed_frames_str = logger.concatenate_elements(pending_frames)
        logger.info(f"{pbone_for_check.name} fix exceed {len(pending_frames)} frames: {fixed_frames_str} ")
    context.scene.frame_current = current_frame
    return pending_frames