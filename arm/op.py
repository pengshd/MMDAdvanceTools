import bpy
from .arm_service import *
from .function import *
from ..common.op import CustormOperator


# 该方法还需要增加一个在第0帧添加0旋转关键帧并删除其他所有关键帧的功能
class MMD_OT_fix_arm_rotation(CustormOperator):

    bl_label = "手臂旋转转换成人体工学"

    bl_description = (
        "上臂/前臂形成的夹角：\n"
        + "<直臂角度,则仅清除前臂XY旋转（因为近似直臂无需对齐）；\n"
        + ">曲臂角度，则清除前臂XY旋转后先旋转上臂，再旋转前臂以对齐原动作；\n"
        + "在两者之间则插值处理。"
    )
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type!="ARMATURE" :
            return False
        return True
    # 因为步骤太长占用太高拖慢速度，分步骤进行
    def execute(self, context):    
        convert_arm_rotation(context, "leftside")
        convert_arm_rotation(context, "rightside")
        try:
            bpy.ops.play.working_end()
        except:
            pass
        return {"FINISHED"}    

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class MMD_OT_fix_interpolation_exceed(CustormOperator):

    bl_label = "修复手骨骼旋转超出范围的插值"
    bl_description = (
        "修复手骨骼旋转超出范围的插值。"
        + "超过偏离上限的帧会插入关键帧，"
        + "在每两个关键帧之间的最大偏差帧插入关键帧重新拟合"
    )
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type!="ARMATURE" :
            return False
        return True

    def execute(self, context):   
        armature = context.active_object
        fix_all_rotation_diff(context,armature)
        try:
            bpy.ops.play.working_end()
        except:
            pass
        return {"FINISHED"}    

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        pass

class MMD_OT_fix_arm_quaternion(CustormOperator):
    
    bl_label = "修复手反向旋转"
    bl_description = "修复防止出现两个四元数旋转之间出现超出范围旋转的情况"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != 'ARMATURE':
            return False
        if context.mode!='POSE':
            return False
        return True
    
    def execute(self, context):  
        fix_all_rotation_path(context.active_object)
        try:
            bpy.ops.play.working_end()
        except:
            pass

        return {"FINISHED"}    


class MMD_OT_create_ref_armature(CustormOperator):
    
    bl_label = "创建参考骨骼"
    bl_description = "创建参考骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != "ARMATURE":
            return False
        return True
    
    def execute(self, context):
        # 获取当前选中的物体
        armature = context.active_object
        if armature.mmd_advance_data.reference:
            self.report({'INFO'}, "已经存在参考骨骼")
            return {'CANCELLED'}   
        if context.scene.objects.get(armature.name + "_ref") or armature.name.endswith("_ref"):
            self.report({'INFO'}, "存在同名ref骨骼，请删除或选定其为参考骨骼")
            return
        create_reference_armature(context,armature)
        return {'FINISHED'}   

class MMD_OT_delete_ref_armature(CustormOperator):
    
    bl_label = "删除参考骨骼"
    bl_description = "删除参考骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != "ARMATURE":
            return False
        if not context.active_object.mmd_advance_data.reference:
            return False
        return True
    
    def execute(self, context):
        # 获取当前选中的物体
        delete_reference_armature(context,context.active_object)
        bpy.ops.outliner.orphans_purge()
        return {'FINISHED'}       


classes = [
    MMD_OT_fix_arm_rotation,
    MMD_OT_fix_arm_quaternion,
    MMD_OT_create_ref_armature,
    MMD_OT_delete_ref_armature,
    MMD_OT_fix_interpolation_exceed,
]
