import rhinoscriptsyntax as rs
import json
import os

def import_artboards_from_json():
    desktop_path = os.path.expanduser("~/Desktop/ai_artboards.json")
    
    if not os.path.exists(desktop_path):
        print("❌ JSON file not found:", desktop_path)
        return

    with open(desktop_path, "r") as f:
        try:
            artboards = json.load(f)
        except Exception as e:
            print("❌ Error reading JSON:", e)
            return

    # Create parent layer "Artboards" if it doesn't exist
    parent_layer = "Artboards"
    if not rs.IsLayer(parent_layer):
        rs.AddLayer(parent_layer)

    # Optional: clear previous artboards
    for obj in rs.ObjectsByLayer(parent_layer):
        rs.DeleteObject(obj)
    
    # Create rectangles for each artboard
    for ab in artboards:
        name = ab.get("name", "Artboard")
        width = ab.get("width_mm", 0)
        height = ab.get("height_mm", 0)
        left = ab.get("left_mm", 0)
        top = ab.get("top_mm", 0)

        # Create sublayer for this artboard
        sub_layer = "{}::{}".format(parent_layer, name)
        if not rs.IsLayer(sub_layer):
            rs.AddLayer(sub_layer, parent_layer)

        # Create rectangle in sublayer
        pt1 = (left, -top, 0)  # invert Y to match Illustrator
        rect = rs.AddRectangle(pt1, width, height)
        if rect:
            rs.ObjectName(rect, name)
            rs.ObjectLayer(rect, sub_layer)
            rs.LockObject(rect)

            # Mirror along X-axis (vertical axis through origin)
            base_pt = (0, 0, 0)
            mirror_pt = (1, 0, 0)
            rs.MirrorObject(rect, base_pt, mirror_pt)

    print("✅ Imported {} artboards with sublayers and X-axis mirrored.".format(len(artboards)))

# Run the function
import_artboards_from_json()