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
        self.ClientSize = drawing.Size(300, 310)
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
        
        self.chk_export_pics = forms.CheckBox()
        self.chk_export_pics.Text = "Export Pictures"
        self.chk_export_pics.Checked = False
        self.chk_export_pics.Height = 26
        self.chk_export_pics.Width = 150
        
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

        # Hatch Export Options
        self.chk_hatch_solid = forms.CheckBox()
        self.chk_hatch_solid.Text = "Export hatches as solid fills"
        self.chk_hatch_solid.Checked = True
        self.chk_hatch_solid.ToolTip = (
            "Export all hatches as closed filled polygons using the hatch object's colour. "
            "Matches Rhino's 'Hatches exported as solid fills' option."
        )

        self.chk_hatch_explode = forms.CheckBox()
        self.chk_hatch_explode.Text = "Explode hatches (auto-detect solid)"
        self.chk_hatch_explode.Checked = False
        self.chk_hatch_explode.ToolTip = (
            "Explode each hatch into its boundary curves. "
            "If the hatch pattern is Solid, it is still exported as a filled polygon. "
            "Otherwise each boundary loop is exported as a separate open/closed curve."
        )
        
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
        layout.AddRow(self.chk_export_pics)
        layout.AddRow(self.create_divider())
        
        layout.AddRow(self.chk_auto_import)
        layout.AddRow(self.chk_auto_export)
        layout.AddRow(self.create_divider())

        layout.AddRow(self.chk_hatch_solid)
        layout.AddRow(self.chk_hatch_explode)
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
        all_objs += rs.ObjectsByType(65536, select=False) or []  # Hatch
        
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

    def _is_picture_frame(self, obj):
        """
        Check if an object is a picture frame using RhinoCommon.
        Picture frames are single-face Breps with a bitmap texture material.
        """
        try:
            rhino_obj = scriptcontext.doc.Objects.Find(obj)
            if not rhino_obj:
                return False
            geo = rhino_obj.Geometry
            if not isinstance(geo, Rhino.Geometry.Brep):
                return False
            if geo.Faces.Count != 1:
                return False
            attr = rhino_obj.Attributes
            mat_idx = attr.MaterialIndex
            if mat_idx < 0:
                return False
            mat = scriptcontext.doc.Materials[mat_idx]
            if mat is None:
                return False
            tex = mat.GetBitmapTexture()
            return tex is not None and tex.FileName is not None and len(tex.FileName) > 0
        except Exception:
            return False

    def _get_picture_image_path(self, obj):
        """
        Get the image file path from a picture frame using RhinoCommon.
        """
        try:
            rhino_obj = scriptcontext.doc.Objects.Find(obj)
            if not rhino_obj:
                return None
            attr = rhino_obj.Attributes
            mat_idx = attr.MaterialIndex
            if mat_idx < 0:
                return None
            mat = scriptcontext.doc.Materials[mat_idx]
            if mat is None:
                return None
            tex = mat.GetBitmapTexture()
            if tex and tex.FileName:
                return tex.FileName
            return None
        except Exception:
            return None

    def _is_solid_hatch(self, obj):
        """
        Determines if a hatch object has a Solid fill pattern.
        """
        try:
            # Solid hatches may have no pattern index (None) or a pattern named "Solid"
            pattern_idx = rs.HatchPattern(obj)
            if pattern_idx is None:
                return True
            pattern_name = rs.HatchPatternName(pattern_idx)
            if pattern_name:
                if "solid" in pattern_name.lower():
                    return True
                # Check fill type: 0 = solid
                try:
                    fill_type = rs.HatchPatternFillType(pattern_name)
                    if fill_type == 0:
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def _get_hatch_outer_boundary(self, obj):
        """
        Returns the OUTER boundary loop(s) of a hatch as lists of [x, y] pairs.
        Uses RhinoCommon Hatch.Get3dCurves(True) which returns the closed
        boundary curve(s), NOT the internal fill lines that rs.ExplodeHatch returns.
        """
        loops = []
        try:
            # Get the RhinoCommon geometry via scriptcontext
            rhino_obj = scriptcontext.doc.Objects.Find(obj)
            if not rhino_obj:
                return loops
            hatch_geo = rhino_obj.Geometry
            if not hasattr(hatch_geo, "Get3dCurves"):
                return loops

            # True = outer boundary curves
            outer_curves = hatch_geo.Get3dCurves(True)
            if not outer_curves:
                return loops

            for crv in outer_curves:
                # Try polyline first
                result, polyline = crv.TryGetPolyline()
                if result and polyline and polyline.Count >= 2:
                    loops.append([[float(pt.X), float(pt.Y)] for pt in polyline])
                else:
                    # Divide the curve into points
                    params = crv.DivideByCount(64, True)
                    if params:
                        pts = [crv.PointAt(t) for t in params]
                        if len(pts) >= 2:
                            loops.append([[float(pt.X), float(pt.Y)] for pt in pts])
        except Exception:
            pass
        return loops

    def _get_hatch_boundary_loops(self, obj):
        """
        Explode hatch into its fill lines (for explode-mode export).
        Returns a list of loops, each a list of [x, y] pairs.
        """
        loops = []
        try:
            exploded = rs.ExplodeHatch(obj)
            if not exploded:
                return loops
            for c in exploded:
                if rs.IsCurve(c):
                    pts = rs.CurvePoints(c)
                    if pts and len(pts) >= 2:
                        loops.append([[float(p.X), float(p.Y)] for p in pts])
                    else:
                        num_pts = max(64, (rs.CurvePointCount(c) or 1) * 10)
                        div_pts = rs.DivideCurve(c, num_pts)
                        if div_pts and len(div_pts) >= 2:
                            loops.append([[float(p.X), float(p.Y)] for p in div_pts])
            rs.DeleteObjects(exploded)
        except Exception:
            pass
        return loops

    def export_curves(self, silent=False):
        try:
            self._export_curves_internal(silent)
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            Rhino.UI.Dialogs.ShowMessageBox("CRASH in export_curves:\n" + err_msg, "Fatal Error")
            self.lbl_status.Text = "Status: Export crashed"

    def _export_curves_internal(self, silent=False):
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

        hatch_as_solid = bool(self.chk_hatch_solid.Checked)
        hatch_explode = bool(self.chk_hatch_explode.Checked)

        result = []
        all_objs = []
        all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
        all_objs += rs.ObjectsByType(8, select=False) or []      # Surface (PictureFrames)
        all_objs += rs.ObjectsByType(65536, select=False) or []  # Hatch

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
                layer_name = str(rs.ObjectLayer(obj))
                if layer_name.startswith("Artboards::"):
                    layer_name = layer_name.replace("Artboards::", "", 1)
                
                if self.chk_export_pics.Checked and self._is_picture_frame(obj):
                    # Export picture frame as an image reference
                    img_path = self._get_picture_image_path(obj)
                    if img_path:
                        # Bounding box of the picture frame
                        pic_bbox = rs.BoundingBox(obj)
                        if pic_bbox:
                            # Compute min/max from all bbox points
                            bx = [float(p.X) for p in pic_bbox]
                            by = [float(p.Y) for p in pic_bbox]
                            pic_left = min(bx)
                            pic_right = max(bx)
                            pic_bottom = min(by)
                            pic_top = max(by)
                            pic_width = pic_right - pic_left
                            pic_height = pic_top - pic_bottom
                            # Mirror Y for Illustrator: top becomes -top
                            shape = {
                                "id": str(obj),
                                "layer": layer_name,
                                "type": "picture",
                                "left": pic_left,
                                "top": float(-pic_top),
                                "width": pic_width,
                                "height": pic_height,
                                "image": img_path
                            }
                            shapes.append(shape)
                    continue

                # Only keep objects fully inside the artboard
                if (min(cx) >= min_x and max(cx) <= max_x and min(cy) >= min_y and max(cy) <= max_y):
                    color = rs.ObjectColor(obj)
                    width = rs.ObjectPrintWidth(obj)
                    linetype = rs.ObjectLinetype(obj)
                    color_rgb = [int(color.R), int(color.G), int(color.B)] if color else [0, 0, 0]
                    width_val = float(width) if width else 1.0
                    linetype_v = str(linetype) if linetype else "Continuous"
                    layer_name = str(rs.ObjectLayer(obj))
                    if layer_name.startswith("Artboards::"):
                        layer_name = layer_name.replace("Artboards::", "", 1)
                    obj_id_str = str(obj)

                    # ---------- HATCH handling ----------
                    if rs.IsHatch(obj):
                        # Option 1: Export as solid fills (use outer boundary, not fill lines)
                        if hatch_as_solid:
                            loops = self._get_hatch_outer_boundary(obj)
                            if not loops:
                                continue
                            for idx, loop in enumerate(loops):
                                if len(loop) < 2:
                                    continue
                                # Mirror Y for Illustrator
                                mirrored = [[float(x), float(-y)] for x, y in loop]
                                shapes.append({
                                    "id":         "{}_{}".format(obj_id_str, idx),
                                    "layer":      layer_name,
                                    "type":       "hatch_solid",
                                    "closed":     True,
                                    "points":     mirrored,
                                    "color":      color_rgb,
                                    "fill_color": color_rgb,
                                    "width":      width_val,
                                    "linetype":   linetype_v
                                })
                            continue

                        # Option 2: Explode hatches (auto-detect solid)
                        if hatch_explode:
                            is_solid = self._is_solid_hatch(obj)
                            # Try to get appropriate loops
                            if is_solid:
                                # Solid hatch - use outer boundary
                                loops = self._get_hatch_outer_boundary(obj)
                            else:
                                # Non-solid hatch - explode into pattern lines
                                loops = self._get_hatch_boundary_loops(obj)
                            # Fallback: if no loops were retrieved, try outer boundary anyway
                            if not loops:
                                loops = self._get_hatch_outer_boundary(obj)
                                is_solid = True  # If explode failed, it is a solid hatch
                            if not loops:
                                continue
                            for idx, loop in enumerate(loops):
                                if len(loop) < 2:
                                    continue
                                mirrored = [[float(x), float(-y)] for x, y in loop]
                                if is_solid:
                                    # Solid hatch - filled polygon
                                    shapes.append({
                                        "id":         "{}_{}".format(obj_id_str, idx),
                                        "layer":    layer_name,
                                        "type":     "hatch_solid",
                                        "closed":   True,
                                        "points":   mirrored,
                                        "color":    color_rgb,
                                        "fill_color": color_rgb,
                                        "width":    width_val,
                                        "linetype": linetype_v
                                    })
                                else:
                                    # Non-solid hatch - boundary curves (stroked)
                                    shapes.append({
                                        "id":         "{}_{}".format(obj_id_str, idx),
                                        "layer":    layer_name,
                                        "type":     "polyline",
                                        "closed":   True,
                                        "points":   mirrored,
                                        "color":    color_rgb,
                                        "width":    width_val,
                                        "linetype": linetype_v
                                    })
                            continue

                    # ---------- CURVE handling ----------
                    elif rs.IsCurve(obj):
                        obj_type = "polyline"
                        pts_list = []
                        radius_val = None

                        # Circles
                        if rs.IsCircle(obj):
                            center = rs.CircleCenterPoint(obj)
                            radius_val = float(rs.CircleRadius(obj))
                            pts_list = [[float(center.X), float(center.Y)], [float(center.X) + radius_val, float(center.Y)]]
                            obj_type = "circle"

                        # Ellipses
                        elif rs.IsEllipse(obj):
                            try:
                                curve_obj = rs.coercecurve(obj)
                                result_val, ellipse = curve_obj.TryGetEllipse()
                                if result_val:
                                    center = ellipse.Plane.Origin
                                    radius_val = float(ellipse.Radius1)
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
                        elif rs.CurveDegree(obj) > 1:
                            num_pts = max(100, rs.CurvePointCount(obj) * 5)
                            pts = rs.DivideCurve(obj, num_pts)
                            if pts:
                                pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                            obj_type = "nurbs"

                        # Straight polylines / lines
                        elif rs.CurveDegree(obj) == 1:
                            pts = rs.CurvePoints(obj)
                            if pts:
                                pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                            obj_type = "polyline"

                        # Mirror curves for Illustrator
                        pts_list = [[float(x), float(-y)] for x, y in pts_list]
                        try:
                            closed_val = bool(rs.IsCurveClosed(obj))
                        except:
                            closed_val = False

                        shape_data = {
                            "id":       obj_id_str,
                            "layer":    layer_name,
                            "type":     str(obj_type),
                            "closed":   closed_val,
                            "points":   pts_list,
                            "color":    color_rgb,
                            "width":    width_val,
                            "linetype": linetype_v
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
        self.btn_export.Text = "Update Curves to Illustrator"
        
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
