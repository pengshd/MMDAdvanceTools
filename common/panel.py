from .op import *


class MMD_PT_common_panel(bpy.types.Panel):
    """在场景属性窗口创建一个面板"""
    
    bl_label = "MMD动画调整"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MMD增强工具"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        if context.active_object and context.active_object.type == "ARMATURE":
            armature = context.active_object
            if armature.name.endswith("_ref"):
                row.label(text = "请不要操作参考骨骼。")
                return
            row.operator(operator=MMD_OT_fix_mmd_bone.bl_idname)
            row.operator(operator=MMD_OT_simplify_twist_bone.bl_idname)
            row = layout.row()
            row.operator(operator=MMD_OT_clean_action.bl_idname,text= "清理动画通道")
            row = layout.row()
            row.operator(operator="mmd_tools.import_vmd",text="导入动作")
            layout.separator(factor=1)
            row = layout.row()
            row.prop(armature.mmd_advance_data,"covert_frame_start",text = "开始时间")
            row.operator(operator=MMD_OT_set_frame_now.bl_idname,text = "",icon = "EYEDROPPER").flag = "begin"
            row.prop(armature.mmd_advance_data,"covert_frame_end",text = "结束时间")
            row.operator(operator=MMD_OT_set_frame_now.bl_idname,text = "",icon = "EYEDROPPER").flag = "end"
        else:
            row.label(text="请选中骨骼",icon="ERROR")

classes = [
    MMD_PT_common_panel,
]
