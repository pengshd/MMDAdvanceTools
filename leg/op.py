import bpy
from .leg_service import *
from .function import *
from ..common.op import CustormOperator

class MMD_OT_fix_leg_rotation(CustormOperator):
    
    bl_label = "腿部IK旋转转换为等同MMD的IK算法"
    bl_description = "腿部IK旋转转换为等同MMD的IK算法，只调整大腿骨骼旋转"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type!="ARMATURE" :
            return False
        return True
    #因为步骤太长占用太高拖慢速度，分步骤进行
    def execute(self, context):    
        convert_leg_rotation(context, "leftside")
        convert_leg_rotation(context, "rightside")
        bpy.ops.play.working_end()
        return {"FINISHED"}    
    
    def invoke(self, context, event):
        bpy.ops.play.working_end()
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


classes = [
    MMD_OT_fix_leg_rotation,
]
