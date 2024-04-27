import bpy
from . import op,panel
from . import properties
from .properties import MMDAdvanceData
from bpy.utils import register_classes_factory

classes = []
modules= (
    properties, op, panel,
)
for module in modules:
    if hasattr(module,"classes"):
        classes = classes + module.classes

_register, _unregister = register_classes_factory(classes)

def register():
    initID(classes)
    _register()
    bpy.types.Object.mmd_advance_data = bpy.props.PointerProperty(type=MMDAdvanceData)
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
                
            
