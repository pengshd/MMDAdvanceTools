from .op import *
from .function import find_root

class MMD_PT_panel(bpy.types.Panel):
    """在场景属性窗口创建一个面板"""
    
    bl_label = "MMD动画调整"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "自制MMD工具"



    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator(operator="mmd_tools.import_vmd",text="导入动作")
        row = layout.row()
        row.operator(operator=MMD_OT_fix_bone_index.bl_idname)
        row.operator(operator=MMD_OT_simplify_twist_bone.bl_idname)
        row = layout.row()
        row.operator(operator=MMD_OT_fix_arm_rotation.bl_idname,text="修复肘旋转(去除前臂Z轴以外的旋转并保持和原动作对齐)")
        row.operator(operator=MMD_OT_fix_arm_quaternion.bl_idname,text="修复手四元数旋转")
        row = layout.row()
        row.operator(operator=MMD_OT_clean_action.bl_idname,text= "清理动画通道")
        row.operator(operator=MMD_OT_clear_transformation.bl_idname,text= "清除变换")
        row = layout.row()
        row.operator(operator=MMD_OT_create_tmp_armature.bl_idname,text= "创建临时骨骼")
        row.operator(operator=MMD_OT_delete_tmp_armature.bl_idname,text= "删除临时骨骼")
        if context.active_object:
            self.draw_ik_toggle(context)

    def draw_ik_toggle(self, context):
        col = self.layout.column(align=True)
        row = col.row(align=False)
        row.label(text='约束控制', icon='CON_KINEMATIC')
        if context.active_object.type == "ARMATURE":
            grid = col.grid_flow(row_major=True, align=True,columns=2)
            for posebone, cns in get_toggle_list(context.active_object):
                icon = "NONE" if cns.is_valid else "ERROR"
                text = cns.name.replace("toggle_","")
                grid.row(align=True).prop(cns, 'enabled', text=text, toggle=True, icon=icon)

classes = [
    MMD_PT_panel,
]