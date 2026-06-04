# -*- coding: utf-8 -*-
# rhino_illustrator_direct_sync_panel.py
# Modeless Eto.Forms Panel for Rhino ⇄ Illustrator Live Sync (Direct via COM)
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

class RhinoDirectSyncPanel(forms.Form):
    def __init__(self):
        super().__init__()
        self.Title = "Rhino <-> Illustrator (Direct)"
        self.ClientSize = drawing.Size(300, 400)
        self.Padding = drawing.Padding(12)
        self.Resizable = False
        
        # Paths
        self.desktop_path = os.path.expanduser("~/Desktop")
        self.ai_artboards_file = os.path.join(self.desktop_path, "ai_artboards.json")
        self.rhino_curves_file = os.path.join(self.desktop_path, "rhino_curves.json")
        
        self.last_ai_mod_time = 0
        self.last_rhino_signature = {}
        self.annotation_group = False # Default to UnGroup based on Index = 1
        
        # --- Create Controls ---
        # Header
        self.header = forms.Label()
        self.header.Text = "RHINO ⇄ ILLUSTRATOR (DIRECT)"
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
        self.btn_import.Text = "📥 Read Illustrator Artboards"
        self.btn_import.Height = 28
        self.btn_import.Click += self.on_import_click
        
        self.chk_export_pics = forms.CheckBox()
        self.chk_export_pics.Text = "Export Pictures"
        self.chk_export_pics.Checked = False
        self.chk_export_pics.Height = 26
        self.chk_export_pics.Width = 150
        
        self.btn_export = forms.Button()
        self.btn_export.Text = "📤 Send Curves to Illustrator"
        self.btn_export.Height = 28
        self.btn_export.Click += self.on_export_click
        
        # Annotation Export Options
        self.lbl_annot_title = forms.Label()
        self.lbl_annot_title.Text = "Annotation Export:"
        self.lbl_annot_title.Font = drawing.Font("Arial", 9, drawing.FontStyle.Bold)

        self._annot_changing = False
        self.chk_annot_group = forms.RadioButtonList()
        self.chk_annot_group.DataStore = ["Group", "UnGroup"]
        self.chk_annot_group.Orientation = forms.Orientation.Horizontal
        self.chk_annot_group.SelectedIndex = 1
        self.chk_annot_group.SelectedValueChanged += self.on_annot_group_changed
        self.chk_annot_group.ToolTip = "Export each annotation as a grouped set of lines and text."
        
        # Hatch Export Options
        self.lbl_hatch_title = forms.Label()
        self.lbl_hatch_title.Text = "Hatch Export:"
        self.lbl_hatch_title.Font = drawing.Font("Arial", 9, drawing.FontStyle.Bold)
        
        self.chk_hatch_none = forms.CheckBox()
        self.chk_hatch_none.Text = "None"
        self.chk_hatch_none.Checked = False
        self.chk_hatch_none.CheckedChanged += self.on_none_changed
        
        self._hatch_changing = False
        self.rb_hatch_mode = forms.RadioButtonList()
        self.rb_hatch_mode.DataStore = [
            "Export hatches as solid fills",
            "Explode hatches (auto-detect solid)"
        ]
        self.rb_hatch_mode.Orientation = forms.Orientation.Vertical
        self.rb_hatch_mode.SelectedIndex = 1
        self.rb_hatch_mode.SelectedValueChanged += self.on_hatch_mode_changed
        
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
        layout.AddRow(self.chk_hatch_none)
        layout.AddRow(self.rb_hatch_mode)
        layout.AddRow(self.create_divider())

        # Annotation settings
        layout.AddRow(self.lbl_annot_title)
        layout.AddRow(self.chk_annot_group)
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
        all_objs = []
        all_objs += rs.ObjectsByType(4, select=False) or []      # Curve
        if not self.chk_hatch_none.Checked:
            all_objs += rs.ObjectsByType(65536, select=False) or []  # Hatch
        all_objs += rs.ObjectsByType(512, select=False) or []    # Annotation
        
        signature = {}
        for obj in all_objs:
            if rs.IsObjectLocked(obj):
                continue
                
            bbox = rs.BoundingBox(obj)
            bbox_coord = tuple((float(p.X), float(p.Y), float(p.Z)) for p in bbox) if bbox else None
            length = float(rs.CurveLength(obj)) if rs.IsCurve(obj) else 0.0
            color = rs.ObjectColor(obj)
            color_rgb = (int(color.R), int(color.G), int(color.B)) if color else (0,0,0)
            
            signature[str(obj)] = (rs.ObjectLayer(obj), bbox_coord, length, color_rgb)
        return signature

    def get_illustrator_app(self):
        """
        Connect to a running Adobe Illustrator instance via COM.
        Tries multiple strategies because Marshal.GetActiveObject was removed
        in .NET Core / .NET 5+ (which Rhino 8 uses).
        """
        # --- Strategy 1: Marshal.GetActiveObject (works in .NET Framework / IronPython) ---
        try:
            import clr
            clr.AddReference("System")
            from System.Runtime.InteropServices import Marshal as SysMarshal
            try:
                ai = SysMarshal.GetActiveObject("Illustrator.Application")
                if ai is not None:
                    return ai
            except Exception:
                pass
        except Exception:
            pass

        # --- Strategy 2: Activator.CreateInstance via GetTypeFromProgID ---
        #     For single-instance COM servers (like Illustrator) this connects
        #     to the already-running process rather than launching a new one.
        try:
            import clr
            clr.AddReference("System")
            from System import Type, Activator
            tp = Type.GetTypeFromProgID("Illustrator.Application")
            if tp is not None:
                ai = Activator.CreateInstance(tp)
                if ai is not None:
                    return ai
        except Exception:
            pass

        # --- Strategy 3: Direct Win32 COM API via ctypes ---
        #     Calls oleaut32!GetActiveObject and ole32!CLSIDFromProgID directly.
        try:
            import ctypes
            import ctypes.wintypes

            ole32 = ctypes.windll.ole32
            oleaut32 = ctypes.windll.oleaut32

            clsid = (ctypes.c_byte * 16)()
            hr = ole32.CLSIDFromProgID("Illustrator.Application", ctypes.byref(clsid))
            if hr != 0:
                return None

            punk = ctypes.c_void_p()
            hr = oleaut32.GetActiveObject(ctypes.byref(clsid), None, ctypes.byref(punk))
            if hr != 0 or not punk:
                return None

            # Convert the raw IUnknown pointer to a .NET COM object
            import clr
            clr.AddReference("System")
            from System import IntPtr
            from System.Runtime.InteropServices import Marshal as SysMarshal
            net_ptr = IntPtr(punk.value)
            ai = SysMarshal.GetObjectForIUnknown(net_ptr)
            return ai
        except Exception:
            pass

        return None

    def _com_invoke(self, com_obj, method_name, *args):
        """
        Call a method on a COM object using late binding via Type.InvokeMember.
        Required in .NET Core where COM objects don't expose methods as attributes.
        """
        import clr
        clr.AddReference("System")
        from System.Reflection import BindingFlags
        from System import Array, Object
        com_type = com_obj.GetType()
        flags = BindingFlags.InvokeMethod
        arg_array = Array[Object](list(args)) if args else Array[Object]([])
        return com_type.InvokeMember(method_name, flags, None, com_obj, arg_array)

    def on_import_click(self, sender, e):
        import System
        Rhino.RhinoApp.InvokeOnUiThread(System.Action(lambda: self.import_artboards(silent=False)))

    def on_export_click(self, sender, e):
        import System
        Rhino.RhinoApp.InvokeOnUiThread(System.Action(lambda: self.export_curves(silent=False)))
    
    def on_none_changed(self, sender, e):
        is_none = bool(self.chk_hatch_none.Checked)
        self.rb_hatch_mode.Enabled = not is_none
    
    def on_hatch_mode_changed(self, sender, e):
        if self.rb_hatch_mode.SelectedIndex == 0:
            self.hatch_export_mode = "solid"
        else:
            self.hatch_export_mode = "explode"
            
    def on_annot_group_changed(self, sender, e):
        selected = self.chk_annot_group.SelectedValue
        if selected == "Group":
            self.annotation_group = True
        else:
            self.annotation_group = False

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
        if "rhino_illustrator_direct_sync_panel" in scriptcontext.sticky:
            del scriptcontext.sticky["rhino_illustrator_direct_sync_panel"]

    def import_artboards(self, silent=False):
        ai = self.get_illustrator_app()
        artboards = None
        error_msg = None

        if ai:
            js_code = """
            (function() {
                try {
                    if (app.documents.length === 0) return "ERROR:No document is open in Illustrator.";
                    var doc = app.activeDocument;
                    var list = [];
                    var PT2MM = 0.3527777778;
                    for (var i = 0; i < doc.artboards.length; i++) {
                        var ab = doc.artboards[i];
                        var rect = ab.artboardRect;
                        list.push({
                            "name": ab.name,
                            "width_mm": (rect[2] - rect[0]) * PT2MM,
                            "height_mm": (rect[1] - rect[3]) * PT2MM,
                            "left_mm": rect[0] * PT2MM,
                            "top_mm": rect[1] * PT2MM,
                            "right_mm": rect[2] * PT2MM,
                            "bottom_mm": rect[3] * PT2MM
                        });
                    }
                    var jsonStr = "[";
                    for (var k = 0; k < list.length; k++) {
                        var obj = list[k];
                        jsonStr += "{";
                        jsonStr += '"name":"' + obj.name.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"') + '",';
                        jsonStr += '"width_mm":' + obj.width_mm + ',';
                        jsonStr += '"height_mm":' + obj.height_mm + ',';
                        jsonStr += '"left_mm":' + obj.left_mm + ',';
                        jsonStr += '"top_mm":' + obj.top_mm + ',';
                        jsonStr += '"right_mm":' + obj.right_mm + ',';
                        jsonStr += '"bottom_mm":' + obj.bottom_mm;
                        jsonStr += "}";
                        if (k < list.length - 1) jsonStr += ",";
                    }
                    jsonStr += "]";
                    return jsonStr;
                } catch(e) {
                    return "ERROR:" + e.toString();
                }
            })()
            """
            try:
                result = self._com_invoke(ai, "DoJavaScript", js_code)
                if result.startswith("ERROR:"):
                    error_msg = result[6:]
                else:
                    try:
                        artboards = json.loads(result)
                        # Save a backup to Desktop JSON
                        try:
                            with open(self.ai_artboards_file, "w") as f:
                                json.dump(artboards, f, indent=2)
                        except Exception:
                            pass
                    except Exception as parse_ex:
                        error_msg = "Failed to parse Illustrator response: " + str(parse_ex)
            except Exception as com_ex:
                error_msg = "COM communication failed: " + str(com_ex)
        else:
            error_msg = "Could not connect to Illustrator. Make sure Adobe Illustrator is running and a document is open."

        if not artboards:
            # Fallback to Desktop JSON
            fallback = False
            if os.path.exists(self.ai_artboards_file):
                title = "Illustrator Connection Failed"
                msg = "{}\n\nWould you like to import the last exported artboards from Desktop JSON instead?".format(error_msg)
                res = rs.MessageBox(msg, 4 + 32, title)
                if res == 6:  # Yes
                    fallback = True
            
            if fallback:
                try:
                    with open(self.ai_artboards_file, "r") as f:
                        artboards = json.load(f)
                    self.lbl_status.Text = "Status: Imported from backup JSON"
                except Exception as ex:
                    if not silent:
                        Rhino.UI.Dialogs.ShowMessageBox("❌ Error reading backup JSON:\n" + str(ex), "Error")
                    self.lbl_status.Text = "Status: JSON read error"
                    return
            else:
                if not silent:
                    Rhino.UI.Dialogs.ShowMessageBox("❌ " + error_msg, "Connection Error")
                self.lbl_status.Text = "Status: Connect failed"
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

        if os.path.exists(self.ai_artboards_file):
            self.last_ai_mod_time = os.path.getmtime(self.ai_artboards_file)
        self.lbl_import_status.Text = "📥 Last Imported: " + time.strftime("%H:%M:%S")
        self.lbl_status.Text = "Status: Artboards imported!"
        
        if not silent:
            Rhino.UI.Dialogs.ShowMessageBox("✅ Imported {} artboards successfully!".format(len(artboards)), "Success")

    def _is_picture_frame(self, obj):
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
        try:
            pattern_idx = rs.HatchPattern(obj)
            if pattern_idx is None:
                return True
            pattern_name = rs.HatchPatternName(pattern_idx)
            if pattern_name:
                if "solid" in pattern_name.lower():
                    return True
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
        loops = []
        try:
            rhino_obj = scriptcontext.doc.Objects.Find(obj)
            if not rhino_obj:
                return loops
            hatch_geo = rhino_obj.Geometry
            if not hasattr(hatch_geo, "Get3dCurves"):
                return loops

            outer_curves = hatch_geo.Get3dCurves(True)
            if not outer_curves:
                return loops

            for crv in outer_curves:
                result, polyline = crv.TryGetPolyline()
                if result and polyline and polyline.Count >= 2:
                    loops.append([[float(pt.X), float(pt.Y)] for pt in polyline])
                else:
                    params = crv.DivideByCount(64, True)
                    if params:
                        pts = [crv.PointAt(t) for t in params]
                        if len(pts) >= 2:
                            loops.append([[float(pt.X), float(pt.Y)] for pt in pts])
        except Exception:
            pass
        return loops

    def _get_hatch_boundary_loops(self, obj):
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
        try:
            obj_type = rs.ObjectType(obj)
            if obj_type != 512:
                return False
            if rs.IsText(obj):
                return False
            return True
        except Exception:
            return False

    def _explode_annotation(self, obj):
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

            if hasattr(geo, "UpdateDimensionText"):
                try:
                    dim_style = geo.GetDimensionStyle(scriptcontext.doc.DimStyles)
                    geo.UpdateDimensionText(dim_style, False)
                except Exception:
                    try:
                        geo.UpdateDimensionText()
                    except Exception:
                        pass

            exploded = None
            if hasattr(geo, "Explode"):
                try:
                    exploded = geo.Explode()
                except Exception:
                    pass

            if exploded and len(exploded) > 0:
                final_geos = self._flatten_annotation_geos(exploded)
                idx = 0
                for eg in final_geos:
                    shape = self._annotation_geo_to_shape(
                        eg, obj_id, idx, parent_layer, color_rgb, geo
                    )
                    if shape:
                        results.append(shape)
                        idx += 1

            if not results:
                results = self._explode_annotation_cmd(obj, parent_layer, color_rgb, obj_id)

            if not results:
                results = self._annotation_direct_extract(obj, parent_layer, color_rgb, obj_id, geo)

        except Exception:
            pass

        return results

    def _flatten_annotation_geos(self, geos, depth=0):
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
            
            shape = {
                "id":            "{}_{}_text".format(obj_id, idx),
                "layer":         parent_layer,
                "type":          "text",
                "text":          text,
                "point":         [float(pt.X), float(-pt.Y)],
                "height":        height,
                "font":          font,
                "color":         color_rgb,
                "justification": justification
            }
            if self.annotation_group:
                shape["group_id"] = obj_id
                shape["group_name"] = "Annotation"
            return shape

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
                params = geo.DivideByCount(32, True)
                if params:
                    pts = [[float(geo.PointAt(t).X), float(-geo.PointAt(t).Y)] for t in params]
            if len(pts) >= 2:
                shape = {
                    "id":         "{}_{}_crv".format(obj_id, idx),
                    "layer":      parent_layer,
                    "type":       "polyline",
                    "closed":     bool(geo.IsClosed),
                    "points":     pts,
                    "color":      color_rgb,
                    "width":      1.0,
                    "linetype":   "Continuous"
                }
                if self.annotation_group:
                    shape["group_id"] = obj_id
                    shape["group_name"] = "Annotation"
                return shape

        return None

    def _explode_annotation_cmd(self, obj, parent_layer, color_rgb, obj_id):
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
                                if self.annotation_group:
                                    s["group_id"] = obj_id
                                    s["group_name"] = "Annotation"
                                else:
                                    s.pop("group_id", None)
                                    s.pop("group_name", None)
                                results.append(s)
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
                    
                    shape = {
                        "id":            obj_id + "_text",
                        "layer":         parent_layer,
                        "type":          "text",
                        "text":          text,
                        "point":         [float(cx), float(-cy)],
                        "height":        text_height,
                        "font":          font_name,
                        "color":         color_rgb,
                        "justification": "center"
                    }
                    if self.annotation_group:
                        shape["group_id"] = obj_id
                        shape["group_name"] = "Annotation"
                    results.append(shape)
        except Exception:
            pass
        return results

    def _get_object_export_data(self, obj):
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

            justification = "left"
            try:
                robj = scriptcontext.doc.Objects.Find(obj)
                if robj:
                    geo_j = robj.Geometry
                    if hasattr(geo_j, "TextHorizontalAlignment"):
                        h_align = int(geo_j.TextHorizontalAlignment)
                        if h_align == 1:
                            justification = "center"
                        elif h_align == 2:
                            justification = "right"
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
            hatch_as_solid = (self.rb_hatch_mode.SelectedIndex == 0)
            hatch_explode  = (self.rb_hatch_mode.SelectedIndex == 1)
            
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
                
                # For annotations, use center-point check
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
                    
                obj_shapes = self._get_object_export_data(obj)
                if obj_shapes:
                    for shape in obj_shapes:
                        shapes.append(shape)

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
        self.btn_export.Text = "Update Curves to Illustrator"

        # Now, try to push to Illustrator directly via COM
        ai = self.get_illustrator_app()
        updated_directly = False
        error_msg = None

        if ai:
            # Write the import script to a temp .jsx file, then execute it.
            # This avoids DoJavaScript inline string length/escaping issues.
            curves_path_js = self.rhino_curves_file.replace("\\", "/")
            result_file = os.path.join(self.desktop_path, "_rhino_sync_result.txt")
            result_path_js = result_file.replace("\\", "/")

            jsx_content = """
// _rhino_sync_update.jsx  (auto-generated by Rhino Direct Sync)
(function() {
    var resultFile = new File("__RESULT_PATH__");
    try {
        var inPath = "__CURVES_PATH__";
        var file = new File(inPath);
        if (!file.exists) { writeResult(resultFile, "ERROR:Curves file not found at " + inPath); return; }
        file.encoding = "UTF-8";
        file.open("r");
        var raw = file.read();
        file.close();

        if (!raw || raw.length === 0) { writeResult(resultFile, "ERROR:Curves JSON empty."); return; }

        var data;
        try {
            data = eval("(" + raw + ")");
        } catch(err) {
            writeResult(resultFile, "ERROR:Failed to parse JSON: " + err.toString());
            return;
        }

        if (!data || data.length === 0) { writeResult(resultFile, "ERROR:No curve data found."); return; }

        var doc = (app.documents.length > 0) ? app.activeDocument : app.documents.add();

        function ensureLayer(pathName) {
            var layer = doc;
            var names = pathName.split("::");
            for (var i = 0; i < names.length; i++) {
                try { layer = layer.layers.getByName(names[i]); }
                catch (e) { layer = layer.layers.add(); layer.name = names[i]; }
            }
            return layer;
        }
        function mmToPt(mm) { return mm * 2.8346456693; }
        function applyStroke(item, color, width, linetype) {
            if (!item) return;
            item.stroked = true;
            item.filled  = false;
            if (color && color.length === 3) {
                var c = new RGBColor();
                c.red = color[0]; c.green = color[1]; c.blue = color[2];
                item.strokeColor = c;
            }
            item.strokeWidth = (typeof width === "number") ? width : 1.0;
            var lt = linetype ? linetype.toLowerCase() : "";
            if      (lt === "dashed")                      { item.strokeDashes = [6, 3]; }
            else if (lt === "dots")                        { item.strokeDashes = [1, 3]; }
            else if (lt === "hidden")                      { item.strokeDashes = [2, 2]; }
            else if (lt === "dashdot" || lt === "center")  { item.strokeDashes = [6, 3, 0, 3]; }
            else                                           { item.strokeDashes = []; }
        }

        var totalCurves = 0;

        for (var i = 0; i < data.length; i++) {
            var abData = data[i];
            var curves = abData.curves;
            if (!curves) continue;

            for (var j = 0; j < curves.length; j++) {
                var curve = curves[j];
                if (!curve.layer) continue;
                var targetLayer = ensureLayer(curve.layer);

                var group = null;
                if (curve.group_id) {
                    try {
                        group = doc.pageItems.getByName(curve.group_id);
                        if (group.typename !== "GroupItem") group = null;
                    } catch(e) {
                        group = targetLayer.groupItems.add();
                        group.name = curve.group_id;
                    }
                }
                var parentContainer = group || targetLayer;

                // --- Text ---
                if (curve.type === "text") {
                    try {
                        if (curve.id) {
                            try { var et = doc.pageItems.getByName(curve.id); if (et) et.remove(); } catch(e) {}
                        }
                        var textRef = parentContainer.textFrames.add();
                        textRef.contents = curve.text;
                        var fontSize = curve.height ? mmToPt(curve.height) : 12;
                        textRef.textRange.characterAttributes.size = fontSize;
                        if (curve.color && curve.color.length === 3) {
                            var tc = new RGBColor();
                            tc.red = curve.color[0]; tc.green = curve.color[1]; tc.blue = curve.color[2];
                            textRef.textRange.characterAttributes.fillColor = tc;
                        }
                        if (curve.font) {
                            try { textRef.textRange.characterAttributes.textFont = app.textFonts.getByName(curve.font); } catch(e) {}
                        }
                        if (curve.justification) {
                            var just = curve.justification.toLowerCase();
                            if (just === "center") textRef.textRange.paragraphAttributes.justification = Justification.CENTER;
                            else if (just === "right") textRef.textRange.paragraphAttributes.justification = Justification.RIGHT;
                            else textRef.textRange.paragraphAttributes.justification = Justification.LEFT;
                        }
                        var tx = mmToPt(curve.point[0]);
                        var baselineY = -mmToPt(curve.point[1]);
                        textRef.position = [0, 0];
                        var dx = 0, dy = 0;
                        try { var anch = textRef.anchor; dx = -anch[0]; dy = -anch[1]; }
                        catch(ae) { dy = fontSize * 0.8; }
                        textRef.position = [tx + dx, baselineY + dy];
                        if (curve.id) textRef.name = curve.id;
                    } catch (e) {}
                    totalCurves++;
                    continue;
                }

                // --- Picture ---
                if (curve.type === "picture" && curve.image) {
                    try {
                        var imgFile = new File(curve.image);
                        if (imgFile.exists) {
                            if (curve.id) { try { var ep = doc.pageItems.getByName(curve.id); if (ep) ep.remove(); } catch(e) {} }
                            var placed = parentContainer.placedItems.add();
                            placed.file = imgFile;
                            placed.position = [mmToPt(curve.left), -mmToPt(curve.top)];
                            placed.width = mmToPt(curve.width);
                            placed.height = mmToPt(curve.height);
                            if (curve.id) placed.name = curve.id;
                            placed.move(parentContainer, ElementPlacement.PLACEATEND);
                        }
                    } catch (e) {}
                    totalCurves++;
                    continue;
                }

                // --- Path items ---
                if (!curve.points || curve.points.length === 0) continue;

                var pts = [];
                for (var k = 0; k < curve.points.length; k++) {
                    pts.push([mmToPt(curve.points[k][0]), -mmToPt(curve.points[k][1])]);
                }

                var existingPath = null;
                if (curve.id) {
                    try { existingPath = doc.pageItems.getByName(curve.id); } catch(e) {}
                }

                if (existingPath && existingPath.typename === "PathItem") {
                    if (curve.type === "circle" || curve.type === "ellipse") {
                        var cx2 = pts[0][0], cy2 = pts[0][1];
                        var r2 = (curve.radius !== undefined) ? mmToPt(curve.radius) : mmToPt(1);
                        var nc = parentContainer.pathItems.ellipse(cy2+r2, cx2-r2, r2*2, r2*2);
                        nc.name = curve.id; nc.closed = true;
                        nc.filled = existingPath.filled;
                        if (existingPath.filled) nc.fillColor = existingPath.fillColor;
                        nc.stroked = existingPath.stroked;
                        if (existingPath.stroked) { nc.strokeColor = existingPath.strokeColor; nc.strokeWidth = existingPath.strokeWidth; nc.strokeDashes = existingPath.strokeDashes; }
                        existingPath.remove();
                    } else {
                        if (parentContainer && existingPath.parent !== parentContainer) { try { existingPath.move(parentContainer, ElementPlacement.PLACEATEND); } catch(e) {} }
                        var pp = existingPath.pathPoints;
                        while (pp.length > pts.length) { pp[pp.length-1].remove(); }
                        for (var m = 0; m < pp.length; m++) { pp[m].anchor = pts[m]; pp[m].leftDirection = pts[m]; pp[m].rightDirection = pts[m]; }
                        for (var m = pp.length; m < pts.length; m++) { var npt = pp.add(); npt.anchor = pts[m]; npt.leftDirection = pts[m]; npt.rightDirection = pts[m]; npt.pointType = PointType.CORNER; }
                        existingPath.closed = (curve.closed === true);
                    }
                    totalCurves++;
                    continue;
                }

                if ((curve.type === "circle" || curve.type === "ellipse") && pts.length >= 1) {
                    var cx3 = pts[0][0], cy3 = pts[0][1];
                    var r3 = (curve.radius !== undefined) ? mmToPt(curve.radius) : mmToPt(1);
                    var circ = parentContainer.pathItems.ellipse(cy3+r3, cx3-r3, r3*2, r3*2);
                    if (curve.id) circ.name = curve.id;
                    circ.closed = true;
                    applyStroke(circ, curve.color, curve.width, curve.linetype);
                } else if (pts.length >= 2) {
                    var poly = parentContainer.pathItems.add();
                    if (curve.id) poly.name = curve.id;
                    try {
                        for (var m = 0; m < pts.length; m++) {
                            var npt = poly.pathPoints.add();
                            npt.anchor = [pts[m][0], pts[m][1]];
                            npt.leftDirection = npt.anchor;
                            npt.rightDirection = npt.anchor;
                            npt.pointType = PointType.CORNER;
                        }
                        var isFill = (curve.type === "hatch_solid" || curve.type === "hatch");
                        if (isFill) {
                            poly.closed = true; poly.filled = true; poly.stroked = false;
                            var fc = curve.fill_color || curve.color;
                            if (fc && fc.length === 3) { var fr = new RGBColor(); fr.red = fc[0]; fr.green = fc[1]; fr.blue = fc[2]; poly.fillColor = fr; }
                        } else {
                            poly.filled = false; poly.stroked = true;
                            poly.closed = (curve.closed === true);
                            applyStroke(poly, curve.color, curve.width, curve.linetype);
                        }
                    } catch(e) {}
                }
                totalCurves++;
            }
        }
        app.redraw();
        writeResult(resultFile, "SUCCESS:" + totalCurves);
    } catch(e) {
        writeResult(resultFile, "ERROR:" + e.toString());
    }
})();

function writeResult(f, msg) {
    f.encoding = "UTF-8";
    f.open("w");
    f.write(msg);
    f.close();
}
"""
            jsx_content = jsx_content.replace("__CURVES_PATH__", curves_path_js)
            jsx_content = jsx_content.replace("__RESULT_PATH__", result_path_js)

            jsx_path = os.path.join(self.desktop_path, "_rhino_sync_update.jsx")
            try:
                with open(jsx_path, "w", encoding="utf-8") as f:
                    f.write(jsx_content)
            except Exception as write_ex:
                error_msg = "Failed to write temp JSX file: " + str(write_ex)

            if not error_msg:
                # Remove old result file
                if os.path.exists(result_file):
                    try:
                        os.remove(result_file)
                    except Exception:
                        pass

                # Execute the JSX file via DoJavaScript
                jsx_path_js = jsx_path.replace("\\", "/")
                exec_code = 'var f = new File("{}"); $.evalFile(f);'.format(jsx_path_js)
                try:
                    self._com_invoke(ai, "DoJavaScript", exec_code)
                except Exception as com_ex:
                    error_msg = "COM communication failed: " + str(com_ex)

                # Read result from the result file
                if not error_msg:
                    # Give Illustrator a moment to finish writing
                    time.sleep(0.5)
                    if os.path.exists(result_file):
                        try:
                            with open(result_file, "r", encoding="utf-8") as rf:
                                result_text = rf.read().strip()
                            if result_text.startswith("SUCCESS:"):
                                updated_directly = True
                                total_updated = result_text[8:]
                            elif result_text.startswith("ERROR:"):
                                error_msg = result_text[6:]
                            else:
                                error_msg = "Unexpected result: " + result_text
                        except Exception as read_ex:
                            error_msg = "Could not read result file: " + str(read_ex)
                    else:
                        error_msg = "Illustrator did not produce a result file. The script may have failed silently."
        else:
            error_msg = "Could not connect to Illustrator to update automatically. Make sure Adobe Illustrator is running and a document is open."

        if updated_directly:
            self.lbl_status.Text = "Status: Curves sent & synced!"
            if not silent:
                Rhino.UI.Dialogs.ShowMessageBox("✅ Sent and updated {} shapes in Illustrator successfully!".format(total_updated), "Success")
        else:
            self.lbl_status.Text = "Status: Exported to JSON only"
            if not silent:
                msg = "✅ Curves exported to Desktop JSON.\n\n⚠️ Could not update Illustrator automatically:\n{}".format(error_msg)
                Rhino.UI.Dialogs.ShowMessageBox(msg, "Export Successful")


# Main Execution flow
if __name__ in ("__main__", "Rhino3D_System"):
    # Close any existing instance
    if "rhino_illustrator_direct_sync_panel" in scriptcontext.sticky:
        try:
            scriptcontext.sticky["rhino_illustrator_direct_sync_panel"].Close()
        except:
            pass
            
    # Open new instance as modeless floating panel
    form = RhinoDirectSyncPanel()
    scriptcontext.sticky["rhino_illustrator_direct_sync_panel"] = form
    form.Owner = Rhino.UI.RhinoEtoApp.MainWindow
    form.Show()
