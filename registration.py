import bpy
from . import op,panel

classes = []


modules= (
    #layout
    op, panel, 
)

for module in modules:
    if hasattr(module,"classes"):
        classes = classes + module.classes



from bpy.utils import register_classes_factory

_register, _unregister = register_classes_factory(classes)


def register():
    initID(classes)
    _register()
    

def unregister():
    _unregister()


bl_idname_prefix = "toolkit"

def initID(classes):
    for cls in classes:
        if hasattr(cls, "bl_idname"):
            if issubclass(cls,bpy.types.Operator):
                cls.bl_idname = bl_idname_prefix + "." + cls.__name__
                cls.bl_idname = cls.bl_idname.lower()   
            else:
                 cls.bl_idname = cls.__name__
                
            
