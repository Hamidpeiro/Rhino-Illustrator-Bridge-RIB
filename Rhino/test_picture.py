import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def test_picture():
    objs = rs.GetObjects("Select pictures")
    if not objs: return
    for obj in objs:
        print("Object: {}".format(obj))
        # Check if it's a picture frame
        print("IsPictureFrame: {}".format(rs.IsPictureFrame(obj)))
        
        # Try to get the texture path
        rhobj = rs.coercerhinoobject(obj)
        if rhobj:
            print("Rhino Object Type: {}".format(rhobj.ObjectType))
            # A picture frame is usually a surface/brep with a render material
            mat = rhobj.GetMaterial(True)
            print("Material: {}".format(mat))
            if mat:
                print("Texture path: {}".format(mat.GetBitmapTexture().FileName if mat.GetBitmapTexture() else "No bitmap"))
                
test_picture()
