
bl_info = {
    "name": "MMDToolKit",
    "description": "MMD工具",
    "author": "psd",
    "version": (1,0),
    "blender": (4, 1, 0),
    "location": "VIEW3D > Sidebar",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "User" }
    
from . import registration

def register():
    registration.register()

def unregister():
    registration.unregister()

if __name__ == "__main__":
    register()


