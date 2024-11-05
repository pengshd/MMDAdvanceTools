import bpy
from . import boneAdvanceData


# 绑定到姿态的变换矩阵
def get_pose_transform_matrix(
    pbone: bpy.types.PoseBone
):
    matrix_local = pbone.bone.matrix_local

    boneData: boneAdvanceData.BoneData = boneAdvanceData.get_bone_data(pbone)
    rotation_quaternion = boneData.merged_rotation
    scale = boneData.scale
    location = boneData.location
    matrix_basis = rotation_quaternion.normalized().to_matrix().to_4x4()

    if scale.x != 1.0 or scale.y != 1.0 or scale.z != 1.0:
        matrix_basis[0][0] *= scale.x
        matrix_basis[1][0] *= scale.x
        matrix_basis[2][0] *= scale.x
        matrix_basis[0][1] *= scale.y
        matrix_basis[1][1] *= scale.y
        matrix_basis[2][1] *= scale.y
        matrix_basis[0][2] *= scale.z
        matrix_basis[1][2] *= scale.z
        matrix_basis[2][2] *= scale.z
    matrix_basis.translation = location

    # print(f"{pbone.name} lm1 = {matrix_basis}")
    # matrix_basis = pbone.matrix_basis
    # print(f"{pbone.name} lm2 = {matrix_basis}")

    p = matrix_local @ matrix_basis @ matrix_local.inverted()
    p.normalize()
    # 如果没有父级，返回当前骨骼的矩阵
    if pbone.parent is None:
        return p
    else:
        return get_pose_transform_matrix(pbone.parent) @ p
