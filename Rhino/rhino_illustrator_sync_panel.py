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
        self.ClientSize = drawing.Size(300, 340)
        self.Padding = drawing.Padding(12)
        self.Resizable = True
        
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
        
        # Annotation Export Options
        self.lbl_annot_title = forms.Label()
        self.lbl_annot_title.Text = "Annotation Export:"
        self.lbl_annot_title.Font = drawing.Font("Arial", 9, drawing.FontStyle.Bold)

        self._annot_changing = False

        self.chk_annot_group = forms.CheckBox()
        self.chk_annot_group.Text = "Group"
        self.chk_annot_group.Checked = True
        self.chk_annot_group.CheckedChanged += self.on_annot_group_changed
        self.chk_annot_group.ToolTip = "Export each annotation as a grouped set of lines and text."

        self.chk_annot_ungroup = forms.CheckBox()
        self.chk_annot_ungroup.Text = "Ungroup"
        self.chk_annot_ungroup.Checked = False
        self.chk_annot_ungroup.CheckedChanged += self.on_annot_ungroup_changed
        self.chk_annot_ungroup.ToolTip = "Export each annotation's lines and text as separate, ungrouped items."

        # Hatch Export Options
        self.lbl_hatch_title = forms.Label()
        self.lbl_hatch_title.Text = "Hatch Export:"
        self.lbl_hatch_title.Font = drawing.Font("Arial", 9, drawing.FontStyle.Bold)
        
        self.chk_hatch_none = forms.CheckBox()
        self.chk_hatch_none.Text = "None"
        self.chk_hatch_none.Checked = False
        self.chk_hatch_none.CheckedChanged += self.on_none_changed
        
        self._hatch_changing = False

        self.chk_hatch_solid = forms.CheckBox()
        self.chk_hatch_solid.Text = "Export hatches as solid fills"
        self.chk_hatch_solid.Checked = True
        self.chk_hatch_solid.CheckedChanged += self.on_solid_changed
        self.chk_hatch_solid.ToolTip = (
            "Export all hatches as closed filled polygons using the hatch object's colour. "
            "Matches Rhino's 'Hatches exported as solid fills' option."
        )

        self.chk_hatch_explode = forms.CheckBox()
        self.chk_hatch_explode.Text = "Explode hatches (auto-detect solid)"
        self.chk_hatch_explode.Checked = False
        self.chk_hatch_explode.CheckedChanged += self.on_explode_changed
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

        # Hatch settings
        layout.AddRow(self.lbl_hatch_title)
        layout.AddRow(self.chk_hatch_solid)
        layout.AddRow(self.chk_hatch_explode)
        layout.AddRow(self.chk_hatch_none)
        layout.AddRow(self.create_divider())

        # Annotation settings
        layout.AddRow(self.lbl_annot_title)
        layout.AddRow(self.chk_annot_group, self.chk_annot_ungroup)
        layout.AddRow(self.create_divider())
        
        layout.AddRow(self.lbl_status)
        
        self.Content = layout
        
        # Trigger initial UI state for hatch settings
        self.on_none_changed(None, None)
        
        # Bind close event
        self.Closed += self.on_form_closed

    def create_divider(self):
        divider = forms.Panel()
        divider.Height = 1
        divider.BackgroundColor = drawing.Color.FromArgb(180, 180, 180)
        return divider

    def get_rhino_curves_signature(self):
        # Calculate a signature of all unlocked curves in the document based on physical attributes
        all_objs = []
        all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
        if not self.chk_hatch_none.Checked:
            all_objs += rs.ObjectsByType(65536, select=False) or []  # Hatch
        all_objs += rs.ObjectsByType(512, select=False) or []    # Annotation
        
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

    def on_none_changed(self, sender, e):
        is_none = bool(self.chk_hatch_none.Checked)
        self.chk_hatch_solid.Enabled = not is_none
        self.chk_hatch_explode.Enabled = not is_none

    def on_solid_changed(self, sender, e):
        if self._hatch_changing: return
        if self.chk_hatch_solid.Checked:
            self._hatch_changing = True
            self.chk_hatch_explode.Checked = False
            self._hatch_changing = False
        elif not self.chk_hatch_explode.Checked:
            self._hatch_changing = True
            self.chk_hatch_solid.Checked = True
            self._hatch_changing = False

    def on_explode_changed(self, sender, e):
        if self._hatch_changing: return
        if self.chk_hatch_explode.Checked:
            self._hatch_changing = True
            self.chk_hatch_solid.Checked = False
            self._hatch_changing = False
        elif not self.chk_hatch_solid.Checked:
            self._hatch_changing = True
            self.chk_hatch_explode.Checked = True
            self._hatch_changing = False

    def on_annot_group_changed(self, sender, e):
        if self._annot_changing:
            return
        if self.chk_annot_group.Checked:
            self._annot_changing = True
            self.chk_annot_ungroup.Checked = False
            self._annot_changing = False
        elif not self.chk_annot_ungroup.Checked:
            self._annot_changing = True
            self.chk_annot_group.Checked = True
            self._annot_changing = False

    def on_annot_ungroup_changed(self, sender, e):
        if self._annot_changing:
            return
        if self.chk_annot_ungroup.Checked:
            self._annot_changing = True
            self.chk_annot_group.Checked = False
            self._annot_changing = False
        elif not self.chk_annot_group.Checked:
            self._annot_changing = True
            self.chk_annot_ungroup.Checked = True
            self._annot_changing = False

    def on_form_closed(self, sender, e):
        if "rhino_illustrator_sync_panel" in scriptcontext.sticky:
            del scriptcontext.sticky["rhino_illustrator_sync_panel"]

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

    def _is_annotation_not_text(self, obj):
        """
        Check if object is a dimension/leader annotation (not plain text).
        Uses rs.ObjectType (512 = all annotations) then excludes plain text.
        """
        try:
            obj_type = rs.ObjectType(obj)
            if obj_type != 512:
                return False
            # ObjectType 512 includes text, dimensions, and leaders.
            # Exclude plain text objects.
            if rs.IsText(obj):
                return False
            return True
        except Exception:
            return False

    def _explode_annotation(self, obj):
        """
        Explode annotation (dimension or leader) into curves and text
        using RhinoCommon's Dimension.Explode() API.
        Must call UpdateDimensionText() first because dimensions
        compute their text lazily.
        """
        parent_layer = str(rs.ObjectLayer(obj))
        if parent_layer.startswith("Artboards::"):
            parent_layer = parent_layer.replace("Artboards::", "", 1)

        color = rs.ObjectColor(obj)
        color_rgb = [int(color.R), int(color.G), int(color.B)] if color else [0, 0, 0]
        obj_id = str(obj)
        results = []

        try:
            rhino_obj = scriptcontext.doc.Objects.Find(obj)
            if not rhino_obj:
                return results
            geo = rhino_obj.Geometry

            # Force text/geometry computation before exploding
            if hasattr(geo, "UpdateDimensionText"):
                try:
                    dim_style = geo.GetDimensionStyle(scriptcontext.doc.DimStyles)
                    geo.UpdateDimensionText(dim_style, False)
                except Exception:
                    try:
                        geo.UpdateDimensionText()
                    except Exception:
                        pass

            # Explode using RhinoCommon (returns GeometryBase[])
            exploded = None
            if hasattr(geo, "Explode"):
                try:
                    exploded = geo.Explode()
                except Exception:
                    pass

            if exploded and len(exploded) > 0:
                # Recursively flatten any sub-annotations
                final_geos = self._flatten_annotation_geos(exploded)
                idx = 0
                for eg in final_geos:
                    shape = self._annotation_geo_to_shape(
                        eg, obj_id, idx, parent_layer, color_rgb, geo
                    )
                    if shape:
                        results.append(shape)
                        idx += 1

            # If RhinoCommon Explode produced nothing, try command fallback
            if not results:
                results = self._explode_annotation_cmd(obj, parent_layer, color_rgb, obj_id)

            # If command also failed, extract text + lines directly
            if not results:
                results = self._annotation_direct_extract(obj, parent_layer, color_rgb, obj_id, geo)

        except Exception:
            pass

        return results

    def _flatten_annotation_geos(self, geos, depth=0):
        """Recursively explode any sub-annotations in the result list."""
        if depth > 3:
            return list(geos)
        result = []
        for g in geos:
            if isinstance(g, Rhino.Geometry.AnnotationBase) and not isinstance(g, Rhino.Geometry.TextEntity):
                if hasattr(g, "UpdateDimensionText"):
                    try:
                        ds = g.GetDimensionStyle(scriptcontext.doc.DimStyles)
                        g.UpdateDimensionText(ds, False)
                    except Exception:
                        pass
                if hasattr(g, "Explode"):
                    try:
                        sub = g.Explode()
                        if sub and len(sub) > 0:
                            result.extend(self._flatten_annotation_geos(sub, depth + 1))
                            continue
                    except Exception:
                        pass
                result.append(g)
            else:
                result.append(g)
        return result

    def _annotation_geo_to_shape(self, geo, obj_id, idx, parent_layer, color_rgb, parent_geo):
        """Convert a single RhinoCommon geometry from Explode() into a shape dict."""
        # --- TextEntity ---
        if isinstance(geo, Rhino.Geometry.TextEntity):
            text = ""
            if hasattr(geo, "PlainText"):
                text = geo.PlainText
            if not text and hasattr(geo, "Text"):
                text = geo.Text
            if not text:
                return None
            pt = geo.Plane.Origin if hasattr(geo, "Plane") else None
            if not pt:
                return None
            height = 1.0
            font = ""
            justification = "center"
            try:
                ds = geo.GetDimensionStyle(scriptcontext.doc.DimStyles)
                if ds:
                    height = float(ds.TextHeight)
                    if ds.Font:
                        font = str(getattr(ds.Font, "LogfontName", getattr(ds.Font, "FamilyName", "")))
            except Exception:
                try:
                    height = float(getattr(geo, "TextHeight", 1.0))
                except Exception:
                    pass
            try:
                ha = int(getattr(geo, "TextHorizontalAlignment", 1))
                if ha == 0:
                    justification = "left"
                elif ha == 2:
                    justification = "right"
            except Exception:
                pass
            return {
                "id":            "{}_{}_text".format(obj_id, idx),
                "layer":         parent_layer,
                "type":          "text",
                "text":          text,
                "point":         [float(pt.X), float(-pt.Y)],
                "height":        height,
                "font":          font,
                "color":         color_rgb,
                "justification": justification,
                "group_id":      obj_id,
                "group_name":    "Annotation"
            }

        # --- Curve (LineCurve, PolylineCurve, ArcCurve, NurbsCurve) ---
        if isinstance(geo, Rhino.Geometry.Curve):
            pts = []
            ok, polyline = geo.TryGetPolyline()
            if ok and polyline and polyline.Count >= 2:
                pts = [[float(p.X), float(-p.Y)] for p in polyline]
            elif geo.IsLinear():
                pts = [
                    [float(geo.PointAtStart.X), float(-geo.PointAtStart.Y)],
                    [float(geo.PointAtEnd.X), float(-geo.PointAtEnd.Y)]
                ]
            else:
                # Approximate curved arrowheads / arcs
                params = geo.DivideByCount(32, True)
                if params:
                    pts = [[float(geo.PointAt(t).X), float(-geo.PointAt(t).Y)] for t in params]
            if len(pts) >= 2:
                return {
                    "id":         "{}_{}_crv".format(obj_id, idx),
                    "layer":      parent_layer,
                    "type":       "polyline",
                    "closed":     bool(geo.IsClosed),
                    "points":     pts,
                    "color":      color_rgb,
                    "width":      1.0,
                    "linetype":   "Continuous",
                    "group_id":   obj_id,
                    "group_name": "Annotation"
                }

        return None

    def _explode_annotation_cmd(self, obj, parent_layer, color_rgb, obj_id):
        """Fallback: use _Explode command if RhinoCommon Explode() is unavailable."""
        results = []
        rs.EnableRedraw(False)
        try:
            duplicated = rs.CopyObject(obj)
            if duplicated:
                rs.UnselectAllObjects()
                rs.SelectObject(duplicated)
                rs.Command("_Explode", False)
                sel = rs.SelectedObjects()
                rs.UnselectAllObjects()
                parts = list(sel) if sel else []
                for part in parts:
                    if rs.IsObject(part):
                        shapes = self._get_object_export_data(part)
                        if shapes:
                            for s in shapes:
                                s["layer"] = parent_layer
                                s["group_id"] = obj_id
                                s["group_name"] = "Annotation"
                                results.append(s)
                # Cleanup
                for part in parts:
                    try:
                        if rs.IsObject(part):
                            rs.DeleteObject(part)
                    except Exception:
                        pass
                try:
                    if rs.IsObject(duplicated):
                        rs.DeleteObject(duplicated)
                except Exception:
                    pass
        except Exception:
            pass
        rs.EnableRedraw(True)
        return results

    def _annotation_direct_extract(self, obj, parent_layer, color_rgb, obj_id, geo):
        """Last resort: extract text and bounding box lines from annotation."""
        results = []
        try:
            text = ""
            if hasattr(geo, "PlainText"):
                text = geo.PlainText
            elif hasattr(geo, "Text"):
                text = geo.Text

            text_height = 1.0
            font_name = ""
            try:
                ds = geo.GetDimensionStyle(scriptcontext.doc.DimStyles)
                if ds:
                    text_height = float(ds.TextHeight)
                    if ds.Font:
                        font_name = str(getattr(ds.Font, "LogfontName", ""))
            except Exception:
                pass

            if text:
                bbox = rs.BoundingBox(obj)
                if bbox:
                    bx = [float(p.X) for p in bbox]
                    by = [float(p.Y) for p in bbox]
                    cx = (min(bx) + max(bx)) / 2.0
                    cy = (min(by) + max(by)) / 2.0
                    results.append({
                        "id":            obj_id + "_text",
                        "layer":         parent_layer,
                        "type":          "text",
                        "text":          text,
                        "point":         [float(cx), float(-cy)],
                        "height":        text_height,
                        "font":          font_name,
                        "color":         color_rgb,
                        "justification": "center",
                        "group_id":      obj_id,
                        "group_name":    "Annotation"
                    })
        except Exception:
            pass
        return results

    def _get_object_export_data(self, obj):
        """
        Gets the list of shape dictionaries for a single object.
        Supports Curve, Hatch, Picture frame, and Text objects.
        """
        shapes = []
        obj_id_str = str(obj)
        layer_name = str(rs.ObjectLayer(obj))
        if layer_name.startswith("Artboards::"):
            layer_name = layer_name.replace("Artboards::", "", 1)
            
        color = rs.ObjectColor(obj)
        width = rs.ObjectPrintWidth(obj)
        linetype = rs.ObjectLinetype(obj)
        color_rgb = [int(color.R), int(color.G), int(color.B)] if color else [0, 0, 0]
        width_val = float(width) if width else 1.0
        linetype_v = str(linetype) if linetype else "Continuous"
        
        # --- 1. Text handling ---
        if rs.IsText(obj):
            text_content = None
            pt = None
            height = 1.0
            font = ""
            
            try:
                text_content = rs.TextObjectText(obj)
                pt = rs.TextObjectPoint(obj)
                height = rs.TextObjectHeight(obj)
                font = rs.TextObjectFont(obj)
            except Exception:
                pass
                
            # Fallback to RhinoCommon if properties missing (extremely robust for exploded annotation text entities)
            if not text_content or not pt:
                try:
                    rhino_obj = scriptcontext.doc.Objects.Find(obj)
                    if rhino_obj:
                        geo = rhino_obj.Geometry
                        if hasattr(geo, "PlainText"):
                            text_content = geo.PlainText
                        elif hasattr(geo, "Text"):
                            text_content = geo.Text
                            
                        if hasattr(geo, "Plane"):
                            pt = geo.Plane.Origin
                        elif hasattr(geo, "Location"):
                            pt = geo.Location
                            
                        if hasattr(geo, "TextHeight"):
                            height = geo.TextHeight
                        elif hasattr(geo, "Height"):
                            height = geo.Height
                            
                        if hasattr(geo, "Font"):
                            if hasattr(geo.Font, "LogfontName"):
                                font = geo.Font.LogfontName
                            elif hasattr(geo.Font, "FamilyName"):
                                font = geo.Font.FamilyName
                except Exception:
                    pass

            # Extract text justification/alignment
            justification = "left"
            try:
                robj = scriptcontext.doc.Objects.Find(obj)
                if robj:
                    geo_j = robj.Geometry
                    # Rhino 7+: TextHorizontalAlignment enum (0=Left, 1=Center, 2=Right)
                    if hasattr(geo_j, "TextHorizontalAlignment"):
                        h_align = int(geo_j.TextHorizontalAlignment)
                        if h_align == 1:
                            justification = "center"
                        elif h_align == 2:
                            justification = "right"
                    # Fallback: Justification bitmask (1=Left, 2=Center, 4=Right)
                    elif hasattr(geo_j, "Justification"):
                        j_val = int(geo_j.Justification)
                        h_bits = j_val & 0x7
                        if h_bits == 2:
                            justification = "center"
                        elif h_bits == 4:
                            justification = "right"
            except Exception:
                pass
                    
            if text_content and pt:
                shapes.append({
                    "id":            obj_id_str,
                    "layer":         layer_name,
                    "type":          "text",
                    "text":          text_content,
                    "point":         [float(pt.X), float(-pt.Y)],
                    "height":        float(height) if height else 1.0,
                    "font":          str(font) if font else "",
                    "color":         color_rgb,
                    "justification": justification
                })
            return shapes

        # --- 2. Picture handling ---
        if self.chk_export_pics.Checked and self._is_picture_frame(obj):
            img_path = self._get_picture_image_path(obj)
            if img_path:
                pic_bbox = rs.BoundingBox(obj)
                if pic_bbox:
                    bx = [float(p.X) for p in pic_bbox]
                    by = [float(p.Y) for p in pic_bbox]
                    pic_left = min(bx)
                    pic_right = max(bx)
                    pic_bottom = min(by)
                    pic_top = max(by)
                    shapes.append({
                        "id":      obj_id_str,
                        "layer":   layer_name,
                        "type":    "picture",
                        "left":    pic_left,
                        "top":     float(-pic_top),
                        "width":   pic_right - pic_left,
                        "height":  pic_top - pic_bottom,
                        "image":   img_path
                    })
            return shapes

        # --- 3. Hatch handling ---
        if rs.IsHatch(obj):
            hatch_as_solid = bool(self.chk_hatch_solid.Checked)
            hatch_explode = bool(self.chk_hatch_explode.Checked)
            
            if hatch_as_solid:
                loops = self._get_hatch_outer_boundary(obj)
                if loops:
                    for idx, loop in enumerate(loops):
                        if len(loop) < 2: continue
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
                            "linetype":   linetype_v,
                            "group_id":   obj_id_str,
                            "group_name": "Hatch"
                        })
                return shapes

            if hatch_explode:
                is_solid = self._is_solid_hatch(obj)
                if is_solid:
                    loops = self._get_hatch_outer_boundary(obj)
                else:
                    loops = self._get_hatch_boundary_loops(obj)
                    
                if not loops:
                    loops = self._get_hatch_outer_boundary(obj)
                    is_solid = True
                    
                if loops:
                    for idx, loop in enumerate(loops):
                        if len(loop) < 2: continue
                        mirrored = [[float(x), float(-y)] for x, y in loop]
                        if is_solid:
                            shapes.append({
                                "id":         "{}_{}".format(obj_id_str, idx),
                                "layer":      layer_name,
                                "type":       "hatch_solid",
                                "closed":     True,
                                "points":     mirrored,
                                "color":      color_rgb,
                                "fill_color": color_rgb,
                                "width":      width_val,
                                "linetype":   linetype_v,
                                "group_id":   obj_id_str,
                                "group_name": "Hatch"
                            })
                        else:
                            shapes.append({
                                "id":         "{}_{}".format(obj_id_str, idx),
                                "layer":      layer_name,
                                "type":       "polyline",
                                "closed":     True,
                                "points":     mirrored,
                                "color":      color_rgb,
                                "width":      width_val,
                                "linetype":   linetype_v,
                                "group_id":   obj_id_str,
                                "group_name": "Hatch"
                            })
                return shapes
            return shapes

        # --- 4. Curve handling ---
        if rs.IsCurve(obj):
            obj_type = "polyline"
            pts_list = []
            radius_val = None

            if rs.IsCircle(obj):
                center = rs.CircleCenterPoint(obj)
                radius_val = float(rs.CircleRadius(obj))
                pts_list = [[float(center.X), float(center.Y)], [float(center.X) + radius_val, float(center.Y)]]
                obj_type = "circle"

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
                    num_pts = max(100, rs.CurvePointCount(obj) * 5)
                    pts = rs.DivideCurve(obj, num_pts)
                    if pts:
                        pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                    obj_type = "nurbs"

            elif rs.CurveDegree(obj) > 1:
                num_pts = max(100, rs.CurvePointCount(obj) * 5)
                pts = rs.DivideCurve(obj, num_pts)
                if pts:
                    pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                obj_type = "nurbs"

            elif rs.CurveDegree(obj) == 1:
                pts = rs.CurvePoints(obj)
                if pts:
                    pts_list = [[float(pt.X), float(pt.Y)] for pt in pts]
                obj_type = "polyline"

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
            return shapes

        return shapes

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

        result = []
        all_objs = []
        all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
        all_objs += rs.ObjectsByType(8, select=False) or []      # Surface (PictureFrames)
        if not self.chk_hatch_none.Checked:
            all_objs += rs.ObjectsByType(65536, select=False) or []  # Hatch
        all_objs += rs.ObjectsByType(512, select=False) or []    # Annotation (Text, Dimensions, Leaders, etc.)

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
            debug_lines = []
            for obj in all_objs:
                if obj == artboard_rect:
                    continue
                
                obj_bbox = rs.BoundingBox(obj)
                if not obj_bbox:
                    continue
                cx = [p.X for p in obj_bbox]
                cy = [p.Y for p in obj_bbox]
                
                # For annotations, use center-point check (extension lines may go outside)
                is_annot = self._is_annotation_not_text(obj)
                if is_annot:
                    center_x = (min(cx) + max(cx)) / 2.0
                    center_y = (min(cy) + max(cy)) / 2.0
                    inside = (center_x >= min_x and center_x <= max_x and
                              center_y >= min_y and center_y <= max_y)
                    debug_lines.append("ANNOT id={} type={} inside={} center=({:.1f},{:.1f})".format(
                        str(obj), rs.ObjectType(obj), inside, center_x, center_y))
                    if inside:
                        exploded_shapes = self._explode_annotation(obj)
                        debug_lines.append("  -> exploded into {} shapes".format(len(exploded_shapes)))
                        for shape in exploded_shapes:
                            shapes.append(shape)
                    continue
                
                # Only keep objects fully inside the artboard
                if not (min(cx) >= min_x and max(cx) <= max_x and min(cy) >= min_y and max(cy) <= max_y):
                    continue
                    
                # --- General object handling ---
                obj_shapes = self._get_object_export_data(obj)
                if obj_shapes:
                    for shape in obj_shapes:
                        shapes.append(shape)

            # Write annotation debug log
            if debug_lines:
                try:
                    debug_path = os.path.join(self.desktop_path, "annotation_debug.txt")
                    with open(debug_path, "w") as df:
                        df.write("Annotation Debug Log\n")
                        df.write("Artboard: {}\n".format(sub_layer))
                        df.write("All type-512 objects: {}\n".format(
                            len([o for o in all_objs if rs.ObjectType(o) == 512])))
                        df.write("Non-text annotations: {}\n".format(
                            len([o for o in all_objs if self._is_annotation_not_text(o)])))
                        for line in debug_lines:
                            df.write(line + "\n")
                except Exception:
                    pass

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
