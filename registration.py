import bpy

from bpy.utils import register_classes_factory
from .common import op as common_op, panel as common_panel, properties
from .arm import op as arm_op, panel as arm_panel
from .leg import op as leg_op, panel as leg_panel

classes = [
    *common_op.classes,
    *common_panel.classes,
    *arm_op.classes,
    *arm_panel.classes,
    *leg_op.classes,
    *leg_panel.classes,
    *properties.classes

]

_register, _unregister = register_classes_factory(classes)


def register():
    initID(classes)
    _register()
    bpy.types.Object.mmd_advance_data = bpy.props.PointerProperty(type=properties.MMDAdvanceData)
    bpy.types.Scene.redraw_count = bpy.props.IntProperty()

def unregister():
    _unregister()

def initID(classes):
    for cls in classes:
        if hasattr(cls, "bl_idname"):
            if issubclass(cls,bpy.types.Operator):
                cls.bl_idname = properties.bl_idname_prefix + "." + cls.__name__
                cls.bl_idname = cls.bl_idname.lower()   
            else:
                 cls.bl_idname = cls.__name__
                
            
if __name__ == "__main__":
    register()
