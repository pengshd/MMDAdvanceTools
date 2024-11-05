import bpy
from mathutils import Euler, Vector,Matrix,Quaternion

from ..common.properties import TransformChannel

from .utils import get_values_at_frame
from .calcMatrix import get_pose_transform_matrix

class BoneData:
    pbone : bpy.types.PoseBone = None
    head : Vector = None
    tail : Vector = None
    matrix : Matrix = None
    trans_matrix : Matrix = None
    rotation_quaternion : Quaternion = None
    location : Vector = None
    scale : Vector = None
    ik_rotation : Quaternion = None
    merged_rotation : Quaternion = None

    def __init__(self, pbone:bpy.types.PoseBone) -> None:
        self.pbone = None
        self.head = None
        self.tail = None
        self.matrix = None
        self.trans_matrix = None
        self.rotation_quaternion = None
        self.ik_rotation = None
        self.merged_rotation = None
        self.pbone = pbone
        self.ik_rotation = Quaternion()
            
    def initialize(self, action:bpy.types.Action, frame:int):
        self.rotation_quaternion = Quaternion(get_values_at_frame(action, self.pbone, TransformChannel.QUATERNION.value, frame))
        self.scale = Vector(get_values_at_frame(action, self.pbone, TransformChannel.SCALE.value, frame))
        self.location = Vector(get_values_at_frame(action, self.pbone, TransformChannel.LOCATION.value, frame))
        self.update_data()

    def update_data(self):
        self.merged_rotation = self.rotation_quaternion @ self.ik_rotation
        self.trans_matrix = get_pose_transform_matrix(self.pbone)  
        self.matrix = self.trans_matrix @ self.pbone.bone.matrix_local
        self.head = self.trans_matrix @ self.pbone.bone.head_local
        self.tail = self.trans_matrix @ self.pbone.bone.tail_local

boneDataList = {}

def initialize_link(pbone : bpy.types.PoseBone, action:bpy.types.Action, frame:int):
    obj_name = pbone.id_data.name
    list = []
    b = BoneData(pbone)
    list.append(b)
    while pbone.parent:
        pbone = pbone.parent
        b = BoneData(pbone)
        list.append(b)
    #必须反向初始化，否则get_pose_transform_matrix会依赖到未初始化的父级    
    for boneData in list:
        boneDataList[obj_name + "." + boneData.pbone.name] = boneData
    for boneData in reversed(list):
        boneData.initialize(action, frame)    
    
def get_bone_data(pbone : bpy.types.PoseBone) -> BoneData:
    return boneDataList[pbone.id_data.name + "." +pbone.name]

def update_link(action:bpy.types.Action, frame:int):
    for boneData in boneDataList:
        boneData.update_data(action, frame)

def clear_link():
    boneDataList.clear()  
