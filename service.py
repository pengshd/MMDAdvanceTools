from mathutils import Matrix, Quaternion, Vector, Euler
from math import pi
from . import logger
from .servicefunction import *

def get_pbone_data(armature):
    armature_ref = armature.mmd_advance_data.reference
    pbone_data = (
        (get_pbone_by_mmd_name(armature,"左腕"),get_pbone_by_mmd_name(armature,"左ひじ"),get_pbone_by_mmd_name(armature,"左手首")),
        (get_pbone_by_mmd_name(armature,"右腕"),get_pbone_by_mmd_name(armature,"右ひじ"),get_pbone_by_mmd_name(armature,"右手首")),
    )
    pbone_data_ref = None
    if armature_ref:
        pbone_data_ref = (
            (get_pbone_by_mmd_name(armature_ref,"左腕"),get_pbone_by_mmd_name(armature_ref,"左ひじ"),get_pbone_by_mmd_name(armature_ref,"左手首")),
            (get_pbone_by_mmd_name(armature_ref,"右腕"),get_pbone_by_mmd_name(armature_ref,"右ひじ"),get_pbone_by_mmd_name(armature_ref,"右手首")),
        )
    return pbone_data,pbone_data_ref

def get_twist_pbone_data(armature):
    armature_ref = armature.mmd_advance_data.reference
    twist_pbone_data = (
        (get_pbone_by_mmd_name(armature,"左腕捩"),get_pbone_by_mmd_name(armature,"左手捩"),),
        (get_pbone_by_mmd_name(armature,"右腕捩"),get_pbone_by_mmd_name(armature,"右手捩"),),
    )
    twist_pbone_data_ref = None
    if armature_ref:
        twist_pbone_data_ref = (
            (get_pbone_by_mmd_name(armature_ref,"左腕捩"),get_pbone_by_mmd_name(armature_ref,"左手捩"),),
            (get_pbone_by_mmd_name(armature_ref,"右腕捩"),get_pbone_by_mmd_name(armature_ref,"右手捩"),),
        )
    return twist_pbone_data,twist_pbone_data_ref

def convert_arm_rotation(context):
    armature = context.active_object
    current_frame = context.scene.frame_current
    posebone_data,posebone_data_ref = get_pbone_data(armature)
    twist_posebone_data,twist_posebone_data_ref = get_twist_pbone_data(armature)
    for i in range(len(posebone_data)):
        posebones = posebone_data[i]
        posebones_ref = posebone_data_ref[i]
        twist_posebones = twist_posebone_data[i]
        twist_posebones_ref = twist_posebone_data_ref[i]
        arm, forearm, hand = posebones
        arm_twist, forearm_twist = twist_posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref
        arm_twist_ref, forearm_twist_ref = twist_posebones_ref
        ##关掉前臂的限制旋转
        close_limit_rotation(armature)

        frames = get_keyframe_frames(armature,posebones + twist_posebones)
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

def close_limit_rotation(armature):
    pbone_data, pbone_data_ref = get_pbone_data(armature)
    for i in range(len(pbone_data)):
        posebones = pbone_data[i]
        posebones_ref = pbone_data_ref[i]
        arm, forearm, hand  = posebones
        arm_ref, forearm_ref, hand_ref = posebones_ref
        for pbone in [arm,arm_ref,forearm,forearm_ref,hand,hand_ref,]:
            for cns in pbone.constraints:
                if cns.type == "LIMIT_ROTATION":
                    cns.enabled = False

def adjust_bone_rotation_for_ergonomics(context, armature, posebones, posebones_ref):

    def rotate_local(posebone,axis_index,rad):
        axis = (posebone.matrix.to_3x3().col)[axis_index]
        # rotation matrix 30 degrees around local x axis thru head
        R = (Matrix.Translation(posebone.head) @
            Matrix.Rotation(rad, 4, axis) @
            Matrix.Translation(-posebone.head)
            )
        posebone.matrix = R @ posebone.matrix

    arm,forearm,hand = posebones
    arm_ref,forearm_ref,hand_ref = posebones_ref
    armature_ref = armature.mmd_advance_data.reference
    #forearm_ref实际的父级，复制了arm_ref的世界空间旋转
    arm_calc_ref = armature_ref.pose.bones[arm_ref.name.replace("mmd.","mmd_calc.")]
    forearm_direction_state0 = (forearm_ref.tail - forearm_ref.head).normalized()
    arm_direction_state0 = (arm_ref.tail - arm_ref.head).normalized()
    angle_radian_state0 = arm_direction_state0.angle(forearm_direction_state0)
    angle_degree = angle_radian_state0 * 180 / pi
    #将清除forearm的x,y轴上的旋转前的状态称为state1, 清除后状态称为state2, 再调整arm旋转后的状态称为state3, 调整forearm的Z旋转的终点状态称为state4。
    # 那么按以下逻辑编写代码：
    # 1.先计算state1下arm和forearm所构成平面的法线矢量normal_state1,以及forearm的骨骼指向矢量forearm_direction_state1
    # 2.清除forearm的x,y轴上的旋转，将骨骼调整到state2状态
    # 3.计算state2下arm和forearm所构成平面的法线矢量normal_state2
    # 4.获得normal_state1和normal_state2的夹角plane_angle,让arm骨骼在y方向旋转plane_angle,到达state3状态
    # 5.计算此时的forearm的骨骼指向矢量forearm_direction_state3
    # 6.计算forearm_direction_state3到forearm_direction_state1的夹角forearm_angle,将forearm骨骼在z方向旋转forearm_angle, 到达最终状态state4
    #step1
    # arm_head_pos = armature.matrix_world@arm_ref.head
    arm_head_pos = armature.matrix_world@arm_calc_ref.head
    forearm_head_pos = armature.matrix_world@forearm_ref.head
    forearm_tail_pos = armature.matrix_world@forearm_ref.tail
    normal_state1 = (forearm_tail_pos - forearm_head_pos).cross(forearm_head_pos - arm_head_pos).normalized()
    forearm_direction_state1 = (forearm_ref.tail - forearm_ref.head).normalized()
    #step2
    forearm.rotation_euler.x = forearm.rotation_euler.y = 0
    if forearm.rotation_mode == 'QUATERNION':
        forearm.rotation_quaternion.x = forearm.rotation_quaternion.y = 0
    context.view_layer.update()    
    forearm_rotation_quaternion_step2 = forearm.rotation_quaternion.copy()
    forearm_rotation_euler_step2 = forearm.rotation_euler.copy()
    #step3
    lower_bound = armature.mmd_advance_data.arm_forearm_angle_lowerbound
    upper_bound = armature.mmd_advance_data.arm_forearm_angle_upperbound
    if angle_degree > lower_bound:
        # arm_head_pos = armature.matrix_world@arm.head
        arm_head_pos = armature.matrix_world@arm_calc_ref.head
        forearm_head_pos = armature.matrix_world@forearm.head
        forearm_tail_pos = armature.matrix_world@forearm.tail
        normal_state2 = (forearm_tail_pos - forearm_head_pos).cross(forearm_head_pos - arm_head_pos).normalized()
        #step4 
        #从2旋转到1
        # 计算两个平面夹角
        plane_angle_sign = 1 if (forearm_head_pos - arm_head_pos).dot(normal_state2.cross(normal_state1)) >=0 else -1
        plane_rad = normal_state2.angle(normal_state1)*plane_angle_sign
        rotate_local(arm,1,plane_rad)
        context.view_layer.update()
        #step5
        forearm_direction_state3=(forearm.tail - forearm.head).normalized()
        #step6
        #从3旋转到1
        # 将局部 Z 轴方向转换为世界空间方向
        world_z_axis = armature.matrix_world @ (forearm.matrix.to_quaternion() @ Vector((0, 0, 1)))
        forearm_angle_sign = 1 if world_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
        forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
        #如果forearm旋转反关节
        forearm_reverse = False
        if forearm.rotation_mode == 'QUATERNION':
            rotation_euler_zxy = forearm.rotation_quaternion.to_euler("ZXY")
            if rotation_euler_zxy.z + forearm_rad <0:
                forearm_reverse = True
        elif forearm.rotation_euler.z + forearm_rad <0:
                forearm_reverse = True
        #如果forearm需要反关节才能达到目标位置，那就把arm反转再重新计算forearm该如何旋转                        
        if forearm_reverse:
            rotate_local(arm,1,pi)
            context.view_layer.update()
            forearm_direction_state3=(forearm.tail - forearm.head).normalized()
            world_z_axis = armature.matrix_world @ (forearm.matrix.to_quaternion() @ Vector((0, 0, 1)))
            forearm_angle_sign = 1 if world_z_axis.dot(forearm_direction_state3.cross(forearm_direction_state1)) >= 0 else -1
            forearm_rad = forearm_direction_state3.angle(forearm_direction_state1)*forearm_angle_sign
        rotate_local(forearm,2,forearm_rad)
        #在不转和转动的情况间进行插值    
    if angle_degree > lower_bound and angle_degree < upper_bound:
        factor = (upper_bound- angle_degree)/(upper_bound - lower_bound)
        if arm.rotation_mode == 'QUATERNION':
            arm.rotation_quaternion = arm.rotation_quaternion.slerp(arm_ref.rotation_quaternion, factor)
        else:
            arm_quat = arm.rotation_euler.to_quaternion().slerp(arm_ref.rotation_euler.to_quaternion(), factor)  
            arm.rotation_euler = arm_quat.to_euler(arm.rotation_euler.order)
        if forearm.rotation_mode == 'QUATERNION':
            forearm.rotation_quaternion = forearm.rotation_quaternion.slerp(forearm_rotation_quaternion_step2, factor)
        else:
            forearm_quat = forearm.rotation_euler.to_quaternion().slerp(forearm_rotation_euler_step2, factor)  
            forearm.rotation_euler = forearm_quat.to_euler(forearm.rotation_euler.order)    
    context.view_layer.update()

    if arm.rotation_mode == 'QUATERNION':
        arm.keyframe_insert(data_path="rotation_quaternion")
    else:
        arm.keyframe_insert(data_path="rotation_euler")
    if forearm.rotation_mode == 'QUATERNION':
        forearm.keyframe_insert(data_path="rotation_quaternion")
    else:
        forearm.keyframe_insert(data_path="rotation_euler")
    hand.matrix = hand_ref.matrix
    context.view_layer.update()
    if hand.rotation_mode == 'QUATERNION':
        hand.keyframe_insert(data_path="rotation_quaternion")
    else:
        hand.keyframe_insert(data_path="rotation_euler")

def fix_arm_quaternion(context):
    armature = context.active_object
    pbones_data = get_pbone_data(armature)[0]
    for pbones in pbones_data:
        for pbone in pbones:
            frames = get_keyframe_frames(armature,[pbone])
            fix_wrong_rotation(armature,[pbone],frames)        

def trans_twist(posebone,posebone_ref,frames,clear_twist=False):
       
    for frame in frames:
        if posebone.rotation_mode == 'QUATERNION':
            set_rotation_keyframe(posebone,frame,get_rotation_keyframe(posebone_ref,frame,True)[0],clear_twist)
            # rotation = get_rotation_keyframe(posebone,frame)[0]
            # euler_rotation = rotation.to_euler("YXZ")  if posebone.rotation_mode == 'QUATERNION' else rotation.to_quaternion().to_euler("YXZ")
            # twist_rotation = get_rotation_keyframe(twist_posebone_ref,frame)[0]
            # twist_euler_rotation = twist_rotation.to_euler("YXZ") if twist_posebone_ref.rotation_mode == 'QUATERNION' else twist_rotation.to_quaternion().to_euler("YXZ")
            # euler_rotation.y += twist_euler_rotation.y
            # final_rotation = euler_rotation.to_quaternion() if posebone.rotation_mode == 'QUATERNION' else euler_rotation.to_quaternion().to_euler(posebone.rotation_euler.order)
            # set_rotation_keyframe(posebone,frame,final_rotation,clear_twist)

# 修复旋转方向错误的情况
def fix_wrong_rotation(armature,posebones,frames):
    action = armature.animation_data.action
    armature_ref = armature.mmd_advance_data.reference
    action_ref = armature_ref.animation_data.action
    if not action or not action_ref:
        return None
    for posebone in posebones:
        frame_prev = None
        fixed_frame = []
        for frame in frames:
            fcurves = []
            value = []
            if posebone.rotation_mode == 'QUATERNION':
                quat, fcurves = get_rotation_keyframe(posebone,frame,False)
                euler_rotation = quat.to_euler("YXZ")
                if frame_prev:
                    quat_prev = get_rotation_keyframe(posebone,frame_prev,False)[0]
                    #rot_dir为负证明旋转角度超过180，也就是所谓的“反转” 如果参考骨骼rot_dir_ref和rot_dir符号不一致，证明旋转方向不一致，那么就让当前骨骼换一个旋转方向
                    rot_dir = quat.dot(quat_prev)
                    posebone_ref = armature_ref.pose.bones[posebone.name]
                    rot_dir_ref = get_rotation_keyframe(posebone_ref,frame,False)[0].dot(get_rotation_keyframe(posebone_ref,frame_prev,False)[0]) + \
                        get_rotation_keyframe(get_twist_bone(posebone_ref),frame,False)[0].dot(get_rotation_keyframe(get_twist_bone(posebone_ref),frame_prev,False)[0]) if get_twist_bone(posebone_ref) else 0
                    factor = 1 if rot_dir * rot_dir_ref >= 0 else -1
                    quat = Quaternion((factor*quat.w, factor*quat.x, factor*quat.y, factor*quat.z))
                    value = [quat.w, quat.x, quat.y, quat.z,]
            else:
                euler, fcurves = get_rotation_keyframe(posebone,frame,False)
                euler_rotation = euler.to_quaternion().to_euler("YXZ")
                if frame_prev:
                    euler_rotation_prev = get_rotation_keyframe(posebone,frame_prev,False)[0]
                    if euler_rotation_prev and abs(euler_rotation_prev.y - euler_rotation.y) > pi:
                        factor = 1 if euler_rotation_prev.y>euler_rotation.y else -1
                        euler_rotation.y += (2*pi*factor)
                        euler_final = euler_rotation.to_quaternion().to_euler(posebone.rotation_euler.order)
                        value = [euler_final.x, euler_final.y, euler_final.z,]
            if value:                        
                if factor == -1:
                    update_keyframe(fcurves, frame, value)
                    fixed_frame.append(frame)
            frame_prev = frame    
            fixed_frame_str = logger.concatenate_elements(fixed_frame)
        logger.info(f"fix rotation {posebone.name} {len(fixed_frame)} frames: {fixed_frame_str}")


def completely_fix_interpolation_exceed_rotation_difference(context,armature,sel_pbones,only_now):
    sel_bones_str = [pbone.name for pbone in sel_pbones]
    for i in range(10):
        logger.info(f"fix {sel_bones_str} {i+1} round>>>>")
        if i == 0:
            fix_arm_quaternion(context)
        fix_frames = fix_interpolation_exceed_rotation_difference(context,armature,sel_pbones,only_now)
        fix_arm_quaternion(context)
        if not fix_frames:
            logger.info(f"fix {sel_bones_str} complete!")
            return
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
                # dir = calc_final_direction(pbone,frame)
                # dir_ref = calc_final_direction(armature_ref.pose.bones[pbone.name],frame)
                # diff = abs(dir.angle(dir_ref))
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

def calc_final_direction(pbone,frame):
    def rotate_point(point,rotate_pivot_pbone):
        homogeneous_point = point.to_4d()
        # 将点的坐标从世界空间转换到骨骼空间
        # 如果不归一化结果会不一样, 查了一整天
        pbone_rotation_quaternion = get_rotation_keyframe(rotate_pivot_pbone,frame,True)[0].normalized()
        point_in_bone_space = pbone_rotation_quaternion.to_matrix().to_4x4() @ rotate_pivot_pbone.bone.matrix_local.inverted() @ homogeneous_point
        point_world = rotate_pivot_pbone.bone.matrix_local @ point_in_bone_space
        # 将结果转换为三维坐标
        return point_world.to_3d()
    
    rotation_bone_order = [pbone]
    #设置旋转链
    rotate_pivot_pbone = pbone
    for i in range(10):
        rotate_pivot_pbone = get_parent_posebone(rotate_pivot_pbone)
        if rotate_pivot_pbone:
            rotation_bone_order.append(rotate_pivot_pbone)
        else:
            break    
    logger.debug(f"rotation_bone_order={rotation_bone_order}")
    tail = pbone.bone.tail_local
    head = pbone.bone.head_local    
    for pbone in rotation_bone_order:
        tail = rotate_point(tail,pbone)    
        head = rotate_point(head,pbone)    
    logger.debug(f"direction={(tail-head).normalized()}")
    return (tail-head).normalized()

#在更新context的情况下计算旋转差值
def calc_rotation_difference(armature,posebone):
    armature_ref = armature.mmd_advance_data.reference
    posebone_ref = armature_ref.pose.bones.get(posebone.name)
    direction = posebone.tail - posebone.head
    direction_ref = posebone_ref.tail - posebone_ref.head
    radians = direction.angle(direction_ref)
    return abs(radians) * 180 / pi


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