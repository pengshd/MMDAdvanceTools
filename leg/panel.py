from ..common import properties
from ..common.panel import MMD_PT_common_panel
from .function import *
from .op import *
from .function.utils import check_rotation_mode
class MMD_PT_leg_panel(bpy.types.Panel):
    """在场景属性窗口创建一个面板"""
    
    bl_label = "腿部调整"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MMD增强工具"
    bl_parent_id = MMD_PT_common_panel.__name__

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        if context.active_object and context.active_object.type == "ARMATURE":
            armature = context.active_object
            if armature.name.endswith("_ref"):
                row.label(text = "请不要操作参考骨骼。")
                return
            
            row = layout.row()
            if check_rotation_mode(armature) :
                row.operator(operator=MMD_OT_fix_leg_rotation.bl_idname,text="转换腿部旋转",icon="EVENT_F1")
                row.prop(armature.mmd_advance_data,"leg_ik_loop_count",text = "算法循环计算次数")
                row.prop(armature.mmd_advance_data,"leg_ik_convert_interval",text = "插值间隔")
                row = layout.row()
            else:
                row.label(text = "大腿/小腿骨骼未设置旋转模式为四元数旋转。")
                row = layout.row()
                row.label(text = "或大腿/小腿骨骼未设置MMD骨骼名。")
        else:
            row.label(text="请选中骨架",icon="ERROR")

classes = [
    MMD_PT_leg_panel,
]
