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

    # جمع‌آوری همه منحنی‌ها و پلی‌لاین‌ها
    all_objs = []
    all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
    all_objs += rs.ObjectsByType(8192, select=False) or []   # Polyline
    all_objs += rs.ObjectsByType(8, select=False) or []      # TextCurve

    for sub_layer in sublayers:
        rects = rs.ObjectsByLayer(sub_layer)
        if not rects:
            continue

        # تشخیص مستطیل آرتبورد
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

                # تعیین نوع آبجکت
                obj_type = "curve"
                if rs.IsCircle(obj):
                    obj_type = "circle"
                elif rs.IsEllipse(obj):
                    obj_type = "ellipse"
                elif rs.IsPolyline(obj):
                    obj_type = "polyline"

                pts_list = []
                if rs.IsCurve(obj):
                    deg = rs.CurveDegree(obj)
                    if deg == 1:
                        # خط یا مستطیل: width, height ذخیره کن
                        pts = rs.CurvePoints(obj)
                        pts_list = [[pt.X, pt.Y] for pt in pts]
                        obj_type = "polyline"
                    else:
                        # NURBS / Interpolate Curve
                        num_pts = 50
                        pts = rs.DivideCurve(obj, num_pts)
                        pts_list = [[pt.X, pt.Y] for pt in pts]
                        obj_type = "curve"
                elif rs.IsCircle(obj):
                    center = rs.CircleCenterPoint(obj)
                    radius = rs.CircleRadius(obj)
                    pts_list = [[center.X, center.Y], [center.X+radius, center.Y]]
                    obj_type = "circle"
                elif rs.IsRectangle(obj):
                    # rectangle width/height
                    bbox = rs.BoundingBox(obj)
                    pts_list = [[p.X, p.Y] for p in bbox]
                    obj_type = "rectangle"

                # Mirror روی محور X
                if mirror:
                    pts_list = [[x, -y] for x, y in pts_list]

                shapes.append({
                    "layer": rs.ObjectLayer(obj),
                    "type": obj_type,
                    "points": pts_list
                })

        result.append({
            "artboard": sub_layer,
            "curves": shapes
        })

    with open(desktop_path, "w") as f:
        json.dump(result, f, indent=2)

    total_shapes = sum(len(a['curves']) for a in result)
    print(f"✅ Exported {len(result)} artboards with {total_shapes} shapes -> {desktop_path}")

# اجرا با mirror=True اگر می‌خوای افقی شود
export_shapes_per_artboard(mirror=True)