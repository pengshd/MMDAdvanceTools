from .op import *

class MMD_PT_panel(bpy.types.Panel):
    """在场景属性窗口创建一个面板"""
    
    bl_label = "MMD动画调整"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "自制MMD工具"

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
                row = layout.row()
                row.operator(operator="mmd_tools.import_vmd",text="导入动作")
                return_msg = self.check(context)
                if not return_msg:
                    layout.separator(factor=1)
                    row = layout.row()
                    row.prop(armature.mmd_advance_data,"covert_frame_start",text = "开始时间")
                    row.operator(operator=MMD_OT_set_frame_now.bl_idname,text = "",icon = "EYEDROPPER").flag = "begin"
                    row.prop(armature.mmd_advance_data,"covert_frame_end",text = "结束时间")
                    row.operator(operator=MMD_OT_set_frame_now.bl_idname,text = "",icon = "EYEDROPPER").flag = "end"
                    layout.separator(factor=2)
                    row = layout.row()
                    row.label(text="上臂/前臂形成的夹角：")
                    row = layout.row()
                    row.label(text="<直臂角度,则仅清除前臂XY旋转（因为近似直臂无需对齐）；")
                    row = layout.row()
                    row.label(text=">曲臂角度，则清除前臂XY旋转后先旋转上臂，再旋转前臂以对齐原动作；")
                    row = layout.row()
                    row.label(text="在两者之间则插值处理。")
                    row = layout.row()
                    row.prop(armature.mmd_advance_data,"arm_forearm_angle_lowerbound",text = "直臂角度")
                    row.prop(armature.mmd_advance_data,"arm_forearm_angle_upperbound",text = "曲臂角度")
                    row = layout.row()
                    row.operator(operator=MMD_OT_fix_arm_rotation.bl_idname,text="转换旋转",icon="EVENT_F1")
                    row.operator(operator=MMD_OT_fix_arm_quaternion.bl_idname,text="修复和原动作相反的旋转",icon="EVENT_F2")
                    layout.separator(factor=1)
                    row = layout.row()
                    row.label(text="超过偏离上限的帧会插入关键帧，")
                    row = layout.row()
                    row.label(text="在每两个关键帧之间的最大偏差帧插入关键帧重新拟合。")
                    row = layout.row()
                    row.label(text="（操作前请先转换参考骨架的捩旋转。）")
                    row = layout.row()
                    row.prop(armature.mmd_advance_data,"fix_angle_limit",text = "插值角度偏离上限")
                    row = layout.row()
                    row.operator(operator=MMD_OT_fix_interpolation_exceed.bl_idname,text="超出界限帧插值重新计算",icon="EVENT_F3")
                    layout.separator(factor=1) 
                    row = layout.row()
                    row.operator(operator=MMD_OT_fix_bone_index.bl_idname)
                    row.operator(operator=MMD_OT_simplify_twist_bone.bl_idname)
                    row = layout.row()
                    row.operator(operator=MMD_OT_clean_action.bl_idname,text= "清理动画通道")

                    if context.active_object:
                        self.draw_ik_toggle(context)

                    layout.separator(factor=5)
                    self.draw_monitor_list(context)    
                else:
                    layout.label(text=return_msg,icon="ERROR")
                    
            else:
                row.label(text = "上臂/前臂/手骨骼未设置旋转模式为四元数旋转。")
                row = layout.row()
                row.label(text = "或上臂/前臂/手骨骼未设置MMD骨骼名。")

        else:
            row.label(text="请选中骨骼",icon="ERROR")

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


    def draw_monitor_list(self, context):
        layout = self.layout
        row = layout.row()                
        remove_index = 0
        armature = context.active_object
        armature_ref = armature.mmd_advance_data.reference
        monitor_bone_list = armature.mmd_advance_data.rotation_monitor_bone_list
        if not monitor_bone_list:
            row = layout.row()
            row.operator(operator=MMD_OT_add_delete_monitor_bone.bl_idname,text="添加监控",icon="ADD").add = True
        for monitor_bone in monitor_bone_list:
            row = layout.row()
            row.label(text="",icon="BONE_DATA")
            row.prop_search(monitor_bone,"bone_name",armature.pose,"bones",text="")
            monitor_pbone = armature.pose.bones.get(monitor_bone.bone_name)
            monitor_pbone_ref = armature_ref.pose.bones.get(monitor_bone.bone_name)
            if monitor_pbone:
                if monitor_pbone.rotation_mode == "QUATERNION":
                    rotation_str = tuple(round(q, 2) for q in monitor_pbone.rotation_quaternion)
                    rotation_str_ref = tuple(round(q, 2) for q in monitor_pbone_ref.rotation_quaternion)
                else:
                    rotation_str = tuple(round(q, 2) for q in monitor_pbone.rotation_euler)
                    rotation_str_ref = tuple(round(q, 2) for q in monitor_pbone_ref.rotation_euler)
                # row = layout.row()    
                row.label(text=f" = {rotation_str}")
                row.label(text=f"\tref = {rotation_str_ref}")
            op = row.operator(operator=MMD_OT_add_delete_monitor_bone.bl_idname,text="",icon="REMOVE")
            op.add, op.remove_index = False, remove_index
            remove_index+=1
            row.operator(operator=MMD_OT_add_delete_monitor_bone.bl_idname,text="",icon="ADD").add = True

    def check(self, context):
        ref_armature = context.active_object.mmd_advance_data.reference
        if not ref_armature:
            return "请创建参考骨骼后再使用"   
        if ref_armature.animation_data and ref_armature.animation_data.action:    
            ref_action = ref_armature.animation_data.action
            if ref_action.name != context.active_object.animation_data.action.name+"_ref":
                return "参考骨骼动作不属于当前骨骼的复制动作！"
        else:
            return "参考骨骼动作不属于当前骨骼的复制动作！"
        return None   

classes = [
    MMD_PT_panel,
]