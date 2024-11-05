
bl_info = {
    "name": "MMDToolKit",
    "description": "MMD工具",
    "author": "好想破坏",
    "version": (1,0),
    "blender": (4, 1, 0),
    "location": "VIEW3D > Sidebar",
    "wiki_url": "",
    "category": "User" }
    
from . import registration

def register():
    registration.register()

def unregister():
    registration.unregister()

if __name__ == "__main__":
    register()
