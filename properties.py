import bpy

bl_idname_prefix = "toolkit"

class MonitorBone(bpy.types.PropertyGroup):
    bone_name : bpy.props.StringProperty(default = "")
    value : bpy.props.FloatProperty(default = 0.0)

class MMDAdvanceData(bpy.types.PropertyGroup):
    # 给修改旋转后插值时相差过大的帧添加补帧
    interpolation_angle_gap: bpy.props.FloatProperty(default=20)
    # 两臂夹角大于这个值证明可以做完全的旋转转换
    arm_forearm_angle_upperbound: bpy.props.FloatProperty(default=20)
    # 两臂夹角小于这个值证明不能做旋转转换
    arm_forearm_angle_lowerbound: bpy.props.FloatProperty(default=10)
    # 参照的copy对象
    reference: bpy.props.PointerProperty(type=bpy.types.Object)
    covert_frame_start: bpy.props.IntProperty(default=0)
    covert_frame_end: bpy.props.IntProperty(default=18000)
    #监控骨骼旋转差值
    rotation_monitor_bone_list: bpy.props.CollectionProperty(type=MonitorBone)
    rotation_monitor_valid:bpy.props.BoolProperty(default=False)
classes = [
    MonitorBone,
    MMDAdvanceData,
]
