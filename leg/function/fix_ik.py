
import mathutils,math
from math import radians
from mathutils import Euler, Vector,Matrix,Quaternion

from ...common.properties import TransformChannel
from ...common import boneAdvanceData,logger


class TransformBoneData:
    pbone = None
    baseRotation = Quaternion()
    ikRotation = Quaternion()
    eulerType = ""
    fixAxis = ""
    IsLimit = False
    low = Vector((-math.pi, -math.pi, -math.pi))
    high = Vector((math.pi, math.pi, math.pi))

    def __init__(self, pbone):
        self.pbone = None
        self.baseRotation = Quaternion()
        self.ikRotation = Quaternion()
        self.eulerType = ""
        self.fixAxis = ""
        self.IsLimit = False
        self.low = Vector((-math.pi, -math.pi, -math.pi))
        self.high = Vector((math.pi, math.pi, math.pi))
        self.pbone = pbone
        self.baseRotation = self.pbone.rotation_quaternion.copy()
        self.ikRotation = Quaternion()
        self.setEuler()
        if self.pbone.lock_ik_x or self.pbone.lock_ik_y or self.pbone.lock_ik_z or self.pbone.use_ik_limit_x or self.pbone.use_ik_limit_y or self.pbone.use_ik_limit_z:
            self.IsLimit = True
    
    def setEuler(self):
        if self.pbone.lock_ik_x:
            self.low.x = self.high.x = 0.0
        if self.pbone.lock_ik_y:
            self.low.y = self.high.y = 0.0
        if self.pbone.lock_ik_z:
            self.low.z = self.high.z = 0.0
        if self.pbone.use_ik_limit_x:
            self.low.x = self.pbone.ik_min_x
            self.high.x = self.pbone.ik_max_x
        if self.pbone.use_ik_limit_y:
            self.low.y = self.pbone.ik_min_y
            self.high.y = self.pbone.ik_max_y
        if self.pbone.use_ik_limit_z:
            self.low.z = self.pbone.ik_min_z
            self.high.z = self.pbone.ik_max_z
        if ( -math.pi / 2 < self.low.x and self.high.x < math.pi / 2):
            self.eulerType = "ZXY"
        elif (-math.pi / 2 < self.low.y and self.high.y < math.pi / 2):
            self.eulerType = "XYZ"
        else:
            self.eulerType = "YZX"
        if (self.low.x == 0.0 and self.high.x == 0.0 and self.low.y == 0.0 and self.high.y == 0.0 and self.low.z == 0.0 and self.high.z == 0.0):
            self.fixAxis = "FIX"
        elif (self.low.y == 0.0 and self.high.y == 0.0 and self.low.z == 0.0 and self.high.z == 0.0):
            self.fixAxis = "X"
        elif (self.low.x == 0.0 and self.high.x == 0.0 and self.low.z == 0.0 and self.high.z == 0.0):
            self.fixAxis = "Y"
        elif (self.low.x == 0.0 and self.high.x == 0.0 and self.low.y == 0.0 and self.high.y == 0.0):
            self.fixAxis = "Z"
        else:
            self.fixAxis = "None"   


class IKTransform:
    # IK 计算设置
    distance_threshold = 0.0001 * 12.5 #ik链末端和目标的最终距离
    once_angle = 2 #单次最大旋转，弧度为2，tda式的骨骼单位角属性就是这么设置的
    target_pbone = None
    target_position = None
    ik_position = None
    action = None
    frame = None
    ikLink = []

    def __init__(self) -> None:
        self.target_position = None
        self.target_pbone = None
        self.ik_position = None
        self.action = None
        self.frame = None
        self.ikLink = []

    # 限制旋转的函数
    #rotation_quat = ik_rotation_quat @ pbone.rotation_quaternion
    def limitRotation(self, transformBoneData:TransformBoneData, rotation_quat:Quaternion, axis_lim:bool):
        euler = rotation_quat.to_euler(transformBoneData.eulerType)
        if (euler.x < transformBoneData.low.x):
            num = 2 * transformBoneData.low.x - euler.x
            euler.x = num if (num <= transformBoneData.high.x and axis_lim) else transformBoneData.low.x
        elif (euler.x > transformBoneData.high.x):
            num2 = 2 * transformBoneData.high.x - euler.x
            euler.x = num2 if (num2 >= transformBoneData.low.x and axis_lim) else transformBoneData.high.x
        if (euler.y < transformBoneData.low.y):
            num3 = 2 * transformBoneData.low.y - euler.y
            euler.y = num3 if (num3 <= transformBoneData.high.y and axis_lim) else transformBoneData.low.y
        elif (euler.y > transformBoneData.high.y):
            num4 = 2 * transformBoneData.high.y - euler.y
            euler.y = num4 if (num4 >= transformBoneData.low.y and axis_lim) else transformBoneData.high.y
        if (euler.z < transformBoneData.low.z):
            num5 = 2 * transformBoneData.low.z - euler.z
            euler.z = num5 if (num5 <= transformBoneData.high.z and axis_lim) else transformBoneData.low.z
        elif (euler.z > transformBoneData.high.z):
            num6 = 2 * transformBoneData.high.z - euler.z
            euler.z = num6 if (num6 >= transformBoneData.low.z and axis_lim) else transformBoneData.high.z
        return euler.to_quaternion()

    def apply_axis_local(self, transformBoneData : TransformBoneData, rotation_axis):
        pbone = transformBoneData.pbone
        current_matrix = boneAdvanceData.get_bone_data(pbone).matrix
        # 获取当前位置的轴向量  
        x_axis = current_matrix.to_3x3() @ Vector((1, 0, 0))
        y_axis = current_matrix.to_3x3() @ Vector((0, 1, 0))
        z_axis = current_matrix.to_3x3() @ Vector((0, 0, 1))

        if transformBoneData.fixAxis == "X":
            x = 1.0 if rotation_axis.dot(x_axis) >= 0.0 else -1.0
            return Vector((x, 0, 0))
        elif transformBoneData.fixAxis == "Y":
            y = 1.0 if rotation_axis.dot(y_axis) >= 0.0 else -1.0
            return Vector((0, y, 0))
        elif transformBoneData.fixAxis == "Z":
            z = 1.0 if rotation_axis.dot(z_axis) >= 0.0 else -1.0
            return Vector((0, 0, z))
        else:
            matrix = boneAdvanceData.get_bone_data(pbone).matrix
            return matrix.inverted().to_3x3() @ rotation_axis

    def IKProc_Link(self, linkNum, axis_lim = True):
        trans_data = self.ikLink[linkNum]
        pbone = trans_data.pbone
        boneOtherData : boneAdvanceData.BoneData = boneAdvanceData.get_bone_data(pbone)
        # 获取当前骨骼到目标位置的向量
        self.target_position = boneAdvanceData.get_bone_data(self.target_pbone).trans_matrix @ self.target_pbone.bone.tail_local
        bone_head = boneOtherData.trans_matrix @ pbone.bone.head_local
        vector_to_ik = (bone_head - self.ik_position).normalized()
        vector_to_target = (bone_head - self.target_position).normalized()
        
        # 计算两个向量之间的旋转轴
        rotation_axis = vector_to_target.cross(vector_to_ik).normalized()
        logger.debug(f"{pbone.name}, axis_lim={axis_lim}")
        logger.debug(f"bone_head = {pbone.head}, ik = {self.ik_position}, target = {self.target_position}")
        logger.debug(f"rotation_axis = {rotation_axis}")
        logger.debug(f"eulerType = {trans_data.eulerType}， fixAxis = {trans_data.fixAxis}, isLimit = {trans_data.IsLimit}")

        logger.debug(f"low.x = {trans_data.low.x}")
        logger.debug(f"high.x = {trans_data.high.x}")
        if trans_data.IsLimit and axis_lim:
            rotation_axis_local = self.apply_axis_local(trans_data, rotation_axis)
        else:
            matrix = boneAdvanceData.get_bone_data(pbone).matrix
            rotation_axis_local = matrix.inverted().to_3x3() @ rotation_axis  

        logger.debug(f"rotation_axis_local = {rotation_axis_local}")
        dot_product = vector_to_target.dot(vector_to_ik)
        dot_product = max(-1.0, min(1.0, dot_product))
        rotate_rad = math.acos(dot_product)
        rotate_rad_limit = self.once_angle * (linkNum + 1)
        rotate_rad = min(rotate_rad, rotate_rad_limit)

        logger.debug(f"rotate_rad = {rotate_rad}")
        #绕轴旋转的四元数
        rotation_quat_axis = mathutils.Quaternion(rotation_axis_local, rotate_rad) 
        logger.debug(f"rotation_quat_axis = {rotation_quat_axis}")
        #上一轮的ik贡献旋转*本轮的
        boneOtherData.ik_rotation = boneOtherData.ik_rotation @ rotation_quat_axis
        logger.debug(f"ik_rotation = {boneOtherData.ik_rotation}")

        if trans_data.IsLimit:
            merged_quaternion = boneOtherData.rotation_quaternion @ boneOtherData.ik_rotation
            limitQuat = self.limitRotation(trans_data, merged_quaternion, axis_lim)
            #限制完毕后逆变换得到ik贡献的旋转
            boneOtherData.ik_rotation = boneOtherData.rotation_quaternion.inverted().normalized() @ limitQuat

        # pbone.keyframe_insert(data_path=TransformChannel.QUATERNION.value, frame = self.frame)
        

    def get_ik_distance(self):
        return (self.ik_position - self.target_position).length   

def ccd_ik_solver(iKTransform : IKTransform, max_iterations=40, test_count = 100000):
    """
    使用 CCD IK 算法调整骨骼链到目标位置。

    :param armature: 目标骨骼系统 (Armature) 对象
    :param max_iterations: 最大迭代次数
    """
    num = int(max_iterations / 2)
    ikLink = iKTransform.ikLink
    count = 1 
    for i in range(max_iterations):
        # 从末端骨骼向根骨骼遍历
        # 是否限制IK旋转
        axis_lim = i < num
        for linkNum in range(len(ikLink)):
            iKTransform.IKProc_Link(linkNum, axis_lim)

            for i in range(linkNum, -1, -1):
                boneAdvanceData.get_bone_data(ikLink[i].pbone).update_data()
            
            count+=1
            if count > test_count:
                return

        distance_to_target = iKTransform.get_ik_distance()
        # 如果末端骨骼已经接近目标位置，停止迭代
        if distance_to_target < iKTransform.distance_threshold:
            logger.debug(f"CCD IK 迭代完成，位置误差为: {distance_to_target}")
            break
        logger.debug("==============================")
    
   
#pbones 先大腿再小腿
def fix_frame(pbones, max_iterations : int, action, frame : int):
    boneAdvanceData.clear_link()
    boneAdvanceData.initialize_link(pbones[1],action,frame)
    boneAdvanceData.initialize_link(pbones[2],action,frame)

    ikLink = [TransformBoneData(pbones[1]),
           TransformBoneData(pbones[0]),
           ]
    iKTransform = IKTransform() 
    iKTransform.ikLink = ikLink
    iKTransform.ik_position = boneAdvanceData.get_bone_data(pbones[2]).trans_matrix @ pbones[2].bone.head_local
    iKTransform.target_pbone = pbones[1]
    iKTransform.target_position = boneAdvanceData.get_bone_data(iKTransform.target_pbone).trans_matrix @ iKTransform.target_pbone.bone.tail_local
    iKTransform.action = action
    iKTransform.frame = frame
    ccd_ik_solver(iKTransform, max_iterations, 100000)

    pbone = ikLink[-1].pbone
    pbone.rotation_quaternion = boneAdvanceData.get_bone_data(pbone).merged_rotation
    pbone.keyframe_insert(data_path=TransformChannel.QUATERNION.value, frame = frame)  
    
