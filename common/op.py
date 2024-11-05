import bpy

from . import logger
from .utils import fix_mmd_bone_id,  fix_mmd_bone_name 

class CustormOperator(bpy.types.Operator):
    bl_idname = ""

class MMD_OT_clean_action(CustormOperator):
    
    bl_label = "清理动画通道"
    bl_description = "删除没有对应骨骼的动画通道"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or not context.active_object.animation_data or not context.active_object.animation_data.action:
             return False
        return True
    
    def execute(self, context):
        # 获取当前选中的物体
        armature = context.active_object
        action = armature.animation_data.action
        empty_groups = []
        for fcurve in action.fcurves:
            data_path = fcurve.data_path
            group = fcurve.group
            try:
                #根据data_path访问对应属性，如果出现异常，说明数据路径无效，没有对应的物体属性
                attr = eval("armature." + data_path)
            except:
                action.fcurves.remove(fcurve)
                if group:
                    if not (action.groups[group.name].channels) and group.name not in empty_groups:
                        empty_groups.append(group)
        empty_groups.sort(reverse=True)
        for group in empty_groups:
            logger.info("Empty group index:", group.name)
            action.groups.remove(group)            
        return {'FINISHED'}   
    
class MMD_OT_fix_mmd_bone(CustormOperator):
    
    bl_label = "修复mmd骨骼编号和名称"
    bl_description = "修复骨骼编号和名称"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.mode!='POSE':
            return False
        return True
    
    def execute(self, context):     
        armature = context.active_object
        fix_mmd_bone_name(armature)
        fix_mmd_bone_id(armature)
        return {"FINISHED"}


class MMD_OT_simplify_twist_bone(CustormOperator):
    
    bl_label = "简化mmd捩骨骼"
    bl_description = "简化mmd捩骨骼"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        if context.mode!='POSE':
            return False
        return True
    
    def execute(self, context):     
        #将X捩n这种形变骨骼的约束简化
        for bone in context.active_object.pose.bones:
            for old_constraint in bone.constraints:
                if old_constraint.name == 'mmd_additional_rotation' and bone.name.find('捩')>=0:
                    parent = context.active_object.pose.bones[old_constraint.subtarget.replace('shadow','dummy')].parent
                    percent = (old_constraint.to_max_x_rot - old_constraint.to_min_x_rot) / (old_constraint.from_max_x_rot - old_constraint.from_min_x_rot)
                    copy_rot = bone.constraints.new('COPY_ROTATION')
                    copy_rot.name = "复制旋转"
                    copy_rot.target = context.active_object
                    copy_rot.subtarget = parent.name
                    copy_rot.mix_mode = 'ADD'  
                    copy_rot.target_space = 'LOCAL_OWNER_ORIENT'
                    copy_rot.owner_space = 'LOCAL'
                    if percent < 0:
                        copy_rot.invert_x = True
                        copy_rot.invert_y = True
                        copy_rot.invert_z = True
                    copy_rot.influence = min(abs(percent),1)
                    old_constraint.enabled = False
        return {"FINISHED"}
        
class MMD_OT_set_frame_now(bpy.types.Operator):
    bl_idname = "设置时间"
    bl_label = "set frame to now"
    bl_options = {'REGISTER','UNDO'}

    flag : bpy.props.StringProperty(default="begin")

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != "ARMATURE":
            return False
        return True
    
    def execute(self, context):
        armature = context.active_object
        settings = armature.mmd_advance_data
        if armature.mmd_advance_data.reference:
            settings2 = armature.mmd_advance_data.reference.mmd_advance_data
        if self.flag == "begin" :
            settings.covert_frame_start = context.scene.frame_current
            settings2.covert_frame_start = context.scene.frame_current
        if self.flag == "end" :
            settings.covert_frame_end = context.scene.frame_current   
            settings2.covert_frame_end = context.scene.frame_current   
        return {'FINISHED'}    

classes = [
    MMD_OT_clean_action,
    MMD_OT_fix_mmd_bone,
    MMD_OT_set_frame_now,
    MMD_OT_simplify_twist_bone,
]
