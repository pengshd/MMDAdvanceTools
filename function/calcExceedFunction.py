from math import pi
from .commonFunction import *
from . import logger
from .changeRotationFunction import adjust_bone_rotation_for_ergonomics

# 对于和参考动作差异超过阈值的帧写入关键帧，为重新计算做准备
def supply_frame_with_exceed_rotation_difference(armature,pbones,pbones_for_check,frames):
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
        
    interpolation_angle_gap = armature.mmd_advance_data.interpolation_angle_gap
    armature_ref = armature.mmd_advance_data.reference
    frames_adjacent_pairs = generate_adjacent_pairs(frames)
    for pbone in pbones_for_check:
        frames = []
        for frame_range in frames_adjacent_pairs:
            frame_start = frame_range[0]
            frame_end = frame_range[1]
            exceed_data = []
            for frame in range(frame_start+1, frame_end):
                matrix = calc_final_matrix(pbone,frame)
                ref_matrix = calc_final_matrix(armature_ref.pose.bones[pbone.name],frame)
                ignore_y = ("hand" not in pbone.name)
                diff = calc_rotation_diff(matrix,ref_matrix,ignore_y)
                logger.debug(f"diff={diff}")
                if diff > interpolation_angle_gap:
                    exceed_data.append((frame,diff))
            if exceed_data:
                max_diff_tuple = max(exceed_data, key=lambda x: x[1]) 
                logger.debug(f"frame = {max_diff_tuple[0]}, diff = {max_diff_tuple[1]}")
                supply_keyframe(armature,pbones,max_diff_tuple[0],True)
                frames.append(max_diff_tuple[0])
        return frames

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
        pbone_rotation_quaternion = get_rotation_keyframe(rotate_pivot_pbone,frame,True)[0].normalized()
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



#only_now:只取当前帧所在这一段进行填充
def fix_interpolation_exceed_rotation_difference(context,armature,sel_pbones,only_now):
    current_frame = context.scene.frame_current
    pbone_data, pbone_data_ref = get_pbone_data(armature)
    close_limit_rotation(armature)
    pending_frames = []
    for i in range(len(pbone_data)):
        pbones = pbone_data[i]
        pbones_ref = pbone_data_ref[i]
        pbones_for_check = set(sel_pbones)&set(pbones)
        if not pbones_for_check:
            continue
        frames = get_keyframe_frames(armature,pbones,only_now)
        if only_now:
            if current_frame in frames:
                frames = [current_frame-1,current_frame+1]
            else:
                frames = find_sandwiching_frames(frames,current_frame)
        pending_frames = supply_frame_with_exceed_rotation_difference(armature,pbones,pbones_for_check,frames)
        ##关掉前臂的限制旋转
        close_limit_rotation(armature)
        progress = 0
        for frame in pending_frames:   
            context.scene.frame_set(frame)
            adjust_bone_rotation_for_ergonomics(context, armature, pbones, pbones_ref)
            progress+=1
        fixed_frames_str = logger.concatenate_elements(pending_frames)
        fixed_bone_str = logger.concatenate_elements([pbone_fc.name for pbone_fc in pbones_for_check])
        logger.info(f"fix exceed: {fixed_bone_str} {len(pending_frames)} frames: {fixed_frames_str} ")
    context.scene.frame_current = current_frame
    return pending_frames