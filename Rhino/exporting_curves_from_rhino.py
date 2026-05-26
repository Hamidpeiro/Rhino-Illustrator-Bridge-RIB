import rhinoscriptsyntax as rs
import json
import os

def export_shapes_per_artboard(mirror=False):
    desktop_path = os.path.expanduser("~/Desktop/rhino_curves.json")
    parent_layer = "Artboards"

    if not rs.IsLayer(parent_layer):
        print("❌ Parent layer 'Artboards' not found.")
        return

    sublayers = rs.LayerChildren(parent_layer)
    if not sublayers:
        print("❌ No artboard sublayers found.")
        return

    result = []

    all_objs = []
    all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
    all_objs += rs.ObjectsByType(8192, select=False) or []   # Polyline
    all_objs += rs.ObjectsByType(8, select=False) or []      # TextCurve

    for sub_layer in sublayers:
        rects = rs.ObjectsByLayer(sub_layer)
        if not rects:
            continue

        # Detect artboard rectangle
        artboard_rect = None
        for obj in rects:
            if rs.IsCurve(obj) and rs.IsCurveClosed(obj):
                if rs.CurveDegree(obj) == 1 and rs.CurvePointCount(obj) == 5:
                    artboard_rect = obj
                    break
        if not artboard_rect:
            artboard_rect = rects[0]  # fallback

        bbox = rs.BoundingBox(artboard_rect)
        if not bbox:
            continue

        min_x = min([p.X for p in bbox])
        max_x = max([p.X for p in bbox])
        min_y = min([p.Y for p in bbox])
        max_y = max([p.Y for p in bbox])

        shapes = []
        for obj in all_objs:
            obj_bbox = rs.BoundingBox(obj)
            if not obj_bbox:
                continue
            cx = [p.X for p in obj_bbox]
            cy = [p.Y for p in obj_bbox]

            if (min(cx) >= min_x and max(cx) <= max_x and
                min(cy) >= min_y and max(cy) <= max_y):

                obj_type = "curve"
                pts_list = []

                # Smooth NURBS / splines
                if rs.IsCurve(obj) and rs.CurveDegree(obj) > 1:
                    num_pts = max(100, rs.CurvePointCount(obj)*5)  # more points for smoothness
                    pts = rs.DivideCurve(obj, num_pts)
                    if pts:
                        pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                    obj_type = "nurbs"

                # Straight polylines / lines
                elif rs.IsCurve(obj) and rs.CurveDegree(obj) == 1:
                    pts = rs.CurvePoints(obj)
                    if pts:
                        pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                    obj_type = "polyline"

                # Circles
                elif rs.IsCircle(obj):
                    center = rs.CircleCenterPoint(obj)
                    radius = float(rs.CircleRadius(obj))
                    pts_list = [[float(center.X), float(center.Y)], [float(center.X) + radius, float(center.Y)]]
                    obj_type = "circle"

                # Ellipses
                elif rs.IsEllipse(obj):
                    center = rs.EllipseCenterPoint(obj)
                    radius1 = float(rs.EllipseRadius1(obj))
                    radius2 = float(rs.EllipseRadius2(obj))
                    pts_list = [[float(center.X), float(center.Y)], [float(center.X) + radius1, float(center.Y)]]
                    obj_type = "ellipse"

                # Mirror if needed
                if mirror:
                    pts_list = [[float(x), -float(y)] for x, y in pts_list]

                # Export line properties
                color = rs.ObjectColor(obj)
                width = rs.ObjectPrintWidth(obj)
                linetype = rs.ObjectLinetype(obj)

                color_rgb = [int(color.R), int(color.G), int(color.B)] if color else [0, 0, 0]
                width_val = float(width) if width else 1.0
                linetype_val = str(linetype) if linetype else "Continuous"

                shapes.append({
                    "layer": str(rs.ObjectLayer(obj)),
                    "type": str(obj_type),
                    "closed": bool(rs.IsCurveClosed(obj)),
                    "points": pts_list,
                    "color": color_rgb,
                    "width": width_val,
                    "linetype": linetype_val
                })

        result.append({
            "artboard": sub_layer,
            "curves": shapes
        })

    with open(desktop_path, "w") as f:
        json.dump(result, f, indent=2)

    total_shapes = sum(len(a['curves']) for a in result)
    print("✅ Exported {} artboards with {} shapes -> {}".format(len(result), total_shapes, desktop_path))

# Run with mirror=True if needed
export_shapes_per_artboard(mirror=True)