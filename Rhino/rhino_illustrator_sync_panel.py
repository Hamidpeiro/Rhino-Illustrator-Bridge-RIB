# -*- coding: utf-8 -*-
# rhino_illustrator_sync_panel.py
# Modeless Eto.Forms Panel for Rhino ⇄ Illustrator Live Sync
# Run this script inside Rhino to open a persistent floating interface.

import Rhino
import Rhino.UI
import rhinoscriptsyntax as rs
import Eto.Forms as forms
import Eto.Drawing as drawing
import scriptcontext
import os
import json
import time


class RhinoSyncPanel(forms.Form):
    def __init__(self):
        super().__init__()
        self.Title = "Rhino <-> Illustrator"
        self.ClientSize = drawing.Size(300, 240)
        self.Padding = drawing.Padding(12)
        self.Resizable = False
        
        # Paths
        self.desktop_path = os.path.expanduser("~/Desktop")
        self.ai_artboards_file = os.path.join(self.desktop_path, "ai_artboards.json")
        self.rhino_curves_file = os.path.join(self.desktop_path, "rhino_curves.json")
        
        self.last_ai_mod_time = 0
        self.last_rhino_signature = {}
        
        # --- Create Controls ---
        # Header
        self.header = forms.Label()
        self.header.Text = "RHINO ⇄ ILLUSTRATOR"
        self.header.Font = drawing.Font("Arial", 11, drawing.FontStyle.Bold)
        self.header.TextAlignment = forms.TextAlignment.Center
        
        # Stats Labels
        self.lbl_import_status = forms.Label()
        self.lbl_import_status.Text = "📥 Last Imported: Never"
        self.lbl_import_status.Font = drawing.Font("Arial", 9)
        
        self.lbl_export_status = forms.Label()
        self.lbl_export_status.Text = "📤 Last Exported: Never"
        self.lbl_export_status.Font = drawing.Font("Arial", 9)
        
        # Buttons
        self.btn_import = forms.Button()
        self.btn_import.Text = "📥 Import Artboards"
        self.btn_import.Height = 28
        self.btn_import.Click += self.on_import_click
        
        self.btn_export = forms.Button()
        self.btn_export.Text = "📤 Export Curves"
        self.btn_export.Height = 28
        self.btn_export.Click += self.on_export_click
        
        # Options Checkboxes
        self.chk_auto_import = forms.CheckBox()
        self.chk_auto_import.Text = "Auto-Receive (Watch Artboards)"
        self.chk_auto_import.ToolTip = "Automatically import artboards when Illustrator updates them."
        
        self.chk_auto_export = forms.CheckBox()
        self.chk_auto_export.Text = "Auto-Send (Watch Rhino Curves)"
        self.chk_auto_export.ToolTip = "Automatically export curves when changes are detected in the Artboards sublayers."
        
        # Footer / Status
        self.lbl_status = forms.Label()
        self.lbl_status.Text = "Status: Ready"
        self.lbl_status.Font = drawing.Font("Arial", 8.5)
        self.lbl_status.Enabled = False
        
        # Assemble Layout
        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(6, 6)
        
        layout.AddRow(self.header)
        layout.AddRow(self.create_divider())
        
        layout.AddRow(self.lbl_import_status)
        layout.AddRow(self.lbl_export_status)
        layout.AddRow(self.create_divider())
        
        layout.AddRow(self.btn_import)
        layout.AddRow(self.btn_export)
        layout.AddRow(self.create_divider())
        
        layout.AddRow(self.chk_auto_import)
        layout.AddRow(self.chk_auto_export)
        layout.AddRow(self.create_divider())
        
        layout.AddRow(self.lbl_status)
        
        self.Content = layout
        
        # Set up a timer for background Auto-Sync (runs every 1000ms)
        self.timer = forms.UITimer()
        self.timer.Interval = 1.0 # 1 second
        self.timer.Elapsed += self.on_timer_tick
        self.timer.Start()
        
        # Bind close event to cleanly stop timer
        self.Closed += self.on_form_closed
        
        # Initialize watch parameters
        if os.path.exists(self.ai_artboards_file):
            self.last_ai_mod_time = os.path.getmtime(self.ai_artboards_file)
        self.last_rhino_signature = self.get_rhino_curves_signature()

    def create_divider(self):
        divider = forms.Panel()
        divider.Height = 1
        divider.BackgroundColor = drawing.Color.FromArgb(180, 180, 180)
        return divider

    def get_rhino_curves_signature(self):
        # Calculate a signature of all unlocked curves in the document based on physical attributes
        all_objs = []
        all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
        all_objs += rs.ObjectsByType(8192, select=False) or []   # Polyline
        all_objs += rs.ObjectsByType(8, select=False) or []      # TextCurve
        
        signature = {}
        for obj in all_objs:
            # Exclude locked objects (which includes the artboard boundary rectangles themselves)
            # to avoid false modifications when artboards are locked.
            if rs.IsObjectLocked(obj):
                continue
                
            # Gather attributes to detect changes (position, length, color, layer)
            bbox = rs.BoundingBox(obj)
            bbox_coord = tuple((float(p.X), float(p.Y), float(p.Z)) for p in bbox) if bbox else None
            length = float(rs.CurveLength(obj)) if rs.IsCurve(obj) else 0.0
            color = rs.ObjectColor(obj)
            color_rgb = (int(color.R), int(color.G), int(color.B)) if color else (0,0,0)
            
            # Capture unique signature for this object state
            signature[str(obj)] = (rs.ObjectLayer(obj), bbox_coord, length, color_rgb)
        return signature

    def on_import_click(self, sender, e):
        import System
        Rhino.RhinoApp.InvokeOnUiThread(System.Action(lambda: self.import_artboards(silent=False)))

    def on_export_click(self, sender, e):
        import System
        Rhino.RhinoApp.InvokeOnUiThread(System.Action(lambda: self.export_curves(silent=False)))

    def on_form_closed(self, sender, e):
        if self.timer:
            self.timer.Stop()
        if "rhino_illustrator_sync_panel" in scriptcontext.sticky:
            del scriptcontext.sticky["rhino_illustrator_sync_panel"]

    def on_timer_tick(self, sender, e):
        # Dispatch to Rhino's UI thread to ensure document operations are 100% thread-safe
        import System
        Rhino.RhinoApp.InvokeOnUiThread(System.Action(self.safe_timer_tick))

    def safe_timer_tick(self):
        # 1. Auto Import
        if self.chk_auto_import.Checked:
            if os.path.exists(self.ai_artboards_file):
                current_mod_time = os.path.getmtime(self.ai_artboards_file)
                if current_mod_time > self.last_ai_mod_time:
                    self.lbl_status.Text = "Status: AI artboards updated, importing..."
                    self.import_artboards(silent=True)
                    self.last_ai_mod_time = current_mod_time
        
        # 2. Auto Export
        if self.chk_auto_export.Checked:
            current_signature = self.get_rhino_curves_signature()
            if current_signature != self.last_rhino_signature:
                self.lbl_status.Text = "Status: Curves modified, exporting..."
                self.export_curves(silent=True)
                self.last_rhino_signature = current_signature

    def import_artboards(self, silent=False):
        if not os.path.exists(self.ai_artboards_file):
            if not silent:
                Rhino.UI.Dialogs.ShowMessageBox("❌ JSON file not found:\n" + self.ai_artboards_file, "Error")
            self.lbl_status.Text = "Status: File not found"
            return
            
        try:
            with open(self.ai_artboards_file, "r") as f:
                artboards = json.load(f)
        except Exception as ex:
            if not silent:
                Rhino.UI.Dialogs.ShowMessageBox("❌ Error reading JSON:\n" + str(ex), "Error")
            self.lbl_status.Text = "Status: JSON read error"
            return

        parent_layer = "Artboards"
        if not rs.IsLayer(parent_layer):
            rs.AddLayer(parent_layer)

        # Clear previous artboard objects in parent layer
        for obj in rs.ObjectsByLayer(parent_layer):
            rs.DeleteObject(obj)
            
        # Draw new artboards
        for ab in artboards:
            name = ab.get("name", "Artboard")
            width = ab.get("width_mm", 0)
            height = ab.get("height_mm", 0)
            left = ab.get("left_mm", 0)
            top = ab.get("top_mm", 0)

            # Create sublayer
            sub_layer = "{}::{}".format(parent_layer, name)
            if not rs.IsLayer(sub_layer):
                rs.AddLayer(sub_layer, parent_layer)

            pt1 = (left, -top, 0)
            rect = rs.AddRectangle(pt1, width, height)
            if rect:
                rs.ObjectName(rect, name)
                rs.ObjectLayer(rect, sub_layer)
                rs.LockObject(rect)

                # Mirror along X-axis
                base_pt = (0, 0, 0)
                mirror_pt = (1, 0, 0)
                rs.MirrorObject(rect, base_pt, mirror_pt)

        self.last_ai_mod_time = os.path.getmtime(self.ai_artboards_file)
        self.lbl_import_status.Text = "📥 Last Imported: " + time.strftime("%H:%M:%S")
        self.lbl_status.Text = "Status: Artboards imported!"
        
        if not silent:
            Rhino.UI.Dialogs.ShowMessageBox("✅ Imported {} artboards successfully!".format(len(artboards)), "Success")

    def export_curves(self, silent=False):
        parent_layer = "Artboards"
        if not rs.IsLayer(parent_layer):
            if not silent:
                Rhino.UI.Dialogs.ShowMessageBox("❌ Parent layer 'Artboards' not found.", "Error")
            self.lbl_status.Text = "Status: Layer not found"
            return

        sublayers = rs.LayerChildren(parent_layer)
        if not sublayers:
            if not silent:
                Rhino.UI.Dialogs.ShowMessageBox("❌ No artboard sublayers found.", "Error")
            self.lbl_status.Text = "Status: No artboards"
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
                if obj == artboard_rect:
                    continue
                
                obj_bbox = rs.BoundingBox(obj)
                if not obj_bbox:
                    continue
                cx = [p.X for p in obj_bbox]
                cy = [p.Y for p in obj_bbox]

                # Check if object is inside the artboard bounding box
                if (min(cx) >= min_x and max(cx) <= max_x and
                    min(cy) >= min_y and max(cy) <= max_y):

                    obj_type = "curve"
                    pts_list = []
                    radius_val = None

                    # Circles — check BEFORE NURBS (circles are degree-2 NURBS in Rhino)
                    if rs.IsCircle(obj):
                        center = rs.CircleCenterPoint(obj)
                        radius_val = float(rs.CircleRadius(obj))
                        pts_list = [[float(center.X), float(center.Y)], [float(center.X) + radius_val, float(center.Y)]]
                        obj_type = "circle"

                    # Ellipses — check BEFORE NURBS
                    elif rs.IsEllipse(obj):
                        plane, rx, ry = rs.SurfaceEvaluate(obj, [0, 0], 0) if False else (None, 0, 0)
                        try:
                            import Rhino.Geometry as rg
                            curve_obj = rs.coercecurve(obj)
                            result, ellipse = curve_obj.TryGetEllipse()
                            if result:
                                center = ellipse.Plane.Origin
                                radius_val = float(ellipse.Radius1)
                                r2 = float(ellipse.Radius2)
                                pts_list = [[float(center.X), float(center.Y)], [float(center.X) + radius_val, float(center.Y)]]
                                obj_type = "ellipse"
                        except:
                            # Fallback: treat as NURBS
                            num_pts = max(100, rs.CurvePointCount(obj) * 5)
                            pts = rs.DivideCurve(obj, num_pts)
                            if pts:
                                pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                            obj_type = "nurbs"

                    # Smooth NURBS / splines
                    elif rs.IsCurve(obj) and rs.CurveDegree(obj) > 1:
                        num_pts = max(100, rs.CurvePointCount(obj) * 5)
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

                    # Mirror curves for Illustrator
                    pts_list = [[float(x), float(-y)] for x, y in pts_list]

                    color = rs.ObjectColor(obj)
                    width = rs.ObjectPrintWidth(obj)
                    linetype = rs.ObjectLinetype(obj)

                    color_rgb = [int(color.R), int(color.G), int(color.B)] if color else [0, 0, 0]
                    width_val = float(width) if width else 1.0
                    linetype_val = str(linetype) if linetype else "Continuous"

                    shape_data = {
                        "layer": str(rs.ObjectLayer(obj)),
                        "type": str(obj_type),
                        "closed": bool(rs.IsCurveClosed(obj)),
                        "points": pts_list,
                        "color": color_rgb,
                        "width": width_val,
                        "linetype": linetype_val
                    }
                    if radius_val is not None:
                        shape_data["radius"] = radius_val
                    shapes.append(shape_data)

            result.append({
                "artboard": sub_layer.split("::")[-1],
                "curves": shapes
            })

        try:
            with open(self.rhino_curves_file, "w") as f:
                json.dump(result, f, indent=2)
        except Exception as ex:
            if not silent:
                Rhino.UI.Dialogs.ShowMessageBox("❌ Error writing JSON:\n" + str(ex), "Error")
            self.lbl_status.Text = "Status: Export error"
            return

        total_shapes = sum(len(a['curves']) for a in result)
        self.last_rhino_signature = self.get_rhino_curves_signature()
        self.lbl_export_status.Text = "📤 Last Exported: " + time.strftime("%H:%M:%S")
        self.lbl_status.Text = "Status: Curves exported!"
        
        if not silent:
            Rhino.UI.Dialogs.ShowMessageBox("✅ Exported {} artboards with {} shapes successfully!".format(len(result), total_shapes), "Success")

# Main Execution flow
if __name__ in ("__main__", "Rhino3D_System"):
    # Close any existing instance
    if "rhino_illustrator_sync_panel" in scriptcontext.sticky:
        try:
            scriptcontext.sticky["rhino_illustrator_sync_panel"].Close()
        except:
            pass
            
    # Open new instance as modeless floating panel
    form = RhinoSyncPanel()
    scriptcontext.sticky["rhino_illustrator_sync_panel"] = form
    form.Owner = Rhino.UI.RhinoEtoApp.MainWindow
    form.Show()
