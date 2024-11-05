from ...common.utils import * 


def get_leg_chains(armature):
    armature_ref = armature.mmd_advance_data.reference
    pbone_chains = (
        (get_pbone_by_mmd_name(armature,"左足"),get_pbone_by_mmd_name(armature,"左ひざ"),get_pbone_by_mmd_name(armature,"左足ＩＫ")),
        (get_pbone_by_mmd_name(armature,"右足"),get_pbone_by_mmd_name(armature,"右ひざ"),get_pbone_by_mmd_name(armature,"右足ＩＫ")),
    )
    pbone_chains_ref = None
    if armature_ref:
        pbone_chains_ref = (
            (get_pbone_by_mmd_name(armature_ref,"左足"),get_pbone_by_mmd_name(armature_ref,"左ひざ"),get_pbone_by_mmd_name(armature_ref,"左足ＩＫ")),
            (get_pbone_by_mmd_name(armature_ref,"右足"),get_pbone_by_mmd_name(armature_ref,"右ひざ"),get_pbone_by_mmd_name(armature_ref,"右足ＩＫ")),
        )
    return pbone_chains,pbone_chains_ref


def check_rotation_mode(armature):
    pbone_data = get_leg_chains(armature)[0]
    for pbones in pbone_data:
        if not pbones:
            return False
        for pbone in pbones:
            if not pbone:
                return False
            if pbone.rotation_mode != 'QUATERNION':
                return False
    return True        


def create_more_keyframes(frame_start, frame_end, interval):
    keyframes = []
    frame = frame_start
    # 循环直到达到 frame_end
    while frame <= frame_end:
        keyframes.append(frame)
        frame += interval  # 增加 interval
    return keyframes
