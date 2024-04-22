import bpy
from .function import *

class CustormOperator(bpy.types.Operator):
    bl_idname = ""

class MMD_OT_fix_bone_index(CustormOperator):
    
    bl_label = "修复mmd骨骼编号和名称"
    bl_description = "修复骨骼编号和名称"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.mode!='POSE':
            return False
        if not context.selected_pose_bones:
            return False
        return True
    
    def execute(self, context):     
        armature = context.active_object

        for posebone in context.selected_pose_bones:
            if posebone.mmd_bone:
                if posebone.mmd_bone.name_j:
                    if posebone.head.x>0:
                        posebone.mmd_bone.name_e = posebone.mmd_bone.name_e.replace('_R','_L')
                        posebone.mmd_bone.name_j = posebone.mmd_bone.name_j.replace('右','左')
                    if posebone.head.x<0:    
                        posebone.mmd_bone.name_e = posebone.mmd_bone.name_e.replace('_L','_R')
                        posebone.mmd_bone.name_j = posebone.mmd_bone.name_j.replace('左','右')    
                #如果id是重复的重新分配id
                if not posebone.mmd_bone.is_id_unique(): 
                    for i in range(0,len(armature.pose.bones)): 
                        flag = True   
                        for other_bone in armature.pose.bones:
                            if posebone.name == other_bone.name:
                                continue
                            if other_bone.mmd_bone.bone_id == i:
                                flag = False
                        if flag == True:
                            posebone.mmd_bone.bone_id = i
                            break   
                mirror_posebone_name = get_symmetrical_bone_name(posebone.name)     
                mirror_posebone = armature.pose.bones.get(mirror_posebone_name)   
                if mirror_posebone:
                    if not mirror_posebone.mmd_bone.name_j and posebone.mmd_bone.name_j:
                        mirror_posebone.mmd_bone.name_j = get_symmetrical_bone_name(posebone.mmd_bone.name_j)
                        mirror_posebone.mmd_bone.name_e = get_symmetrical_bone_name(posebone.mmd_bone.name_e)
                    if not posebone.mmd_bone.name_j and mirror_posebone.mmd_bone.name_j:
                        posebone.mmd_bone.name_j = get_symmetrical_bone_name(mirror_posebone.mmd_bone.name_j)
                        posebone.mmd_bone.name_e = get_symmetrical_bone_name(mirror_posebone.mmd_bone.name_e)
                    if mirror_posebone.mmd_bone.bone_id * posebone.mmd_bone.bone_id < 0:
                        if mirror_posebone.mmd_bone.bone_id < 0:
                            mirror_posebone.mmd_bone.bone_id = posebone.mmd_bone.bone_id + 1
                        if posebone.mmd_bone.bone_id < 0:
                            posebone.mmd_bone.bone_id = mirror_posebone.mmd_bone.bone_id + 1


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
    

    
class MMD_OT_fix_arm_rotation(CustormOperator):
    
    bl_label = "修复手旋转"
    bl_description = "将手臂调整为上臂自由旋转，下臂只能局部Z轴旋转"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type!="ARMATURE" :
            return False
        return True
    
    def execute(self, context):  
        if not context.scene.objects.get(context.active_object.name + "_copy"):
            self.report({'INFO'}, "请创建临时骨骼后再使用")
            return {"CANCELLED"}    
        convert_arm_rotation(context)
        return {"FINISHED"}    
    
class MMD_OT_fix_arm_quaternion(CustormOperator):
    
    bl_label = "修复手四元数旋转"
    bl_description = "修复防止出现两个四元数旋转之间出现超出范围旋转的情况"
    bl_options = {"REGISTER","UNDO"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        if context.mode!='POSE':
            return False
        return True
    
    def execute(self, context):  
        fix_arm_quaternion(context)

        return {"FINISHED"}    
       

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
                print("Invalid data path:", data_path)                    
                action.fcurves.remove(fcurve)
                if group:
                    group_name = group.name
                    if len(action.groups[group_name].channels) == 0 and group_name not in empty_groups:
                        empty_groups.append(group_name)
        empty_groups.sort(reverse=True)
        for group_name in empty_groups:
            print("Empty group index:", group_name)
            action.groups.remove(action.groups[group_name])            
        return {'FINISHED'}   



class MMD_OT_clear_transformation(CustormOperator):
    
    bl_label = "清除变换"
    bl_description = "清除变换"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
        return True
    
    def execute(self, context):
        # 获取当前选中的物体
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                for pbone in obj.pose.bones:
                    pbone.location = (0, 0, 0)
                    pbone.rotation_quaternion = (1, 0, 0, 0)
                    pbone.rotation_euler = (0,0,0)
                    pbone.scale = (1, 1, 1)
            else:
                obj.location = (0, 0, 0)
                obj.rotation_quaternion = (1, 0, 0, 0)
                obj.rotation_euler = (0,0,0)
                obj.scale = (1, 1, 1)    
        return {'FINISHED'}   

class MMD_OT_create_tmp_armature(CustormOperator):
    
    bl_label = "创建临时骨骼"
    bl_description = "创建临时骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != "ARMATURE":
            return False
        return True
    
    def execute(self, context):
        # 获取当前选中的物体
        create_copy_armature(context,context.active_object)
        return {'FINISHED'}   
    
class MMD_OT_delete_tmp_armature(CustormOperator):
    
    bl_label = "删除临时骨骼"
    bl_description = "删除临时骨骼"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.active_object or context.active_object.type != "ARMATURE":
            return False
        return True
    
    def execute(self, context):
        # 获取当前选中的物体
        delete_copy_armature(context,context.active_object)
        bpy.ops.outliner.orphans_purge()
        return {'FINISHED'}       
    

classes = [
    MMD_OT_fix_bone_index,
    MMD_OT_simplify_twist_bone,
    MMD_OT_fix_arm_rotation,
    MMD_OT_fix_arm_quaternion,
    MMD_OT_clean_action,
    MMD_OT_clear_transformation,
    MMD_OT_create_tmp_armature,
    MMD_OT_delete_tmp_armature,
]
