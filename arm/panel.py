from ..common.panel import MMD_PT_common_panel
from .function.utils import *
from .op import *
from ..common.op import *


class MMD_PT_arm_panel(bpy.types.Panel):
    """在场景属性窗口创建一个面板"""
    
    bl_label = "手部调整"
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
            if check_rotation_mode(armature) :
                row.prop(armature.mmd_advance_data,"reference",text="参考骨骼")
                row = layout.row()
                row.operator(operator=MMD_OT_create_ref_armature.bl_idname,text= "创建临时骨骼")
                row.operator(operator=MMD_OT_delete_ref_armature.bl_idname,text= "删除临时骨骼")
                return_msg = self.check(context)
                if not return_msg:
                    layout.separator(factor=1)
                    row = layout.row()
                    row.prop(armature.mmd_advance_data,"arm_forearm_angle_lowerbound",text = "直臂角度")
                    row.prop(armature.mmd_advance_data,"arm_forearm_angle_upperbound",text = "曲臂角度")
                    row = layout.row()
                    row.operator(operator=MMD_OT_fix_arm_rotation.bl_idname,text="转换旋转",icon="EVENT_F1")
                    row.operator(operator=MMD_OT_fix_arm_quaternion.bl_idname,text="修复和原动作相反的旋转",icon="EVENT_F2")
                    layout.separator(factor=1)
                    row = layout.row()
                    row.prop(armature.mmd_advance_data,"arm_fix_angle_limit",text = "插值角度偏离上限")
                    row = layout.row()
                    row.operator(operator=MMD_OT_fix_interpolation_exceed.bl_idname,text="超出界限帧插值重新计算",icon="EVENT_F3")
                    layout.separator(factor=1) 
                else:
                    layout.label(text=return_msg,icon="ERROR")

            else:
                row.label(text = "上臂/前臂/手骨骼未设置旋转模式为四元数旋转。")
                row = layout.row()
                row.label(text = "或上臂/前臂/手骨骼未设置MMD骨骼名。")
                    

        else:
            row.label(text="请选中骨骼",icon="ERROR")

    def check(self, context):
        ref_armature = context.active_object.mmd_advance_data.reference
        if not ref_armature:
            return "请创建参考骨骼后再使用"  
        if not context.active_object.animation_data or not context.active_object.animation_data.action:
            return "请导入动作后再使用"
        if ref_armature.animation_data and ref_armature.animation_data.action:    
            ref_action = ref_armature.animation_data.action
            if ref_action.name != context.active_object.animation_data.action.name+"_ref":
                return "参考骨骼动作不属于当前骨骼的复制动作！"
        else:
            return "参考骨骼动作不属于当前骨骼的复制动作！"
        return None   

classes = [
    MMD_PT_arm_panel,
]
