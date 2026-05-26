#target illustrator

// rhino_illustrator_sync_panel.jsx
//
// HOW TO USE:
//   Run via File > Scripts > Other Script…
//   The dialog will open — use the buttons to Export/Import, then close when done.
//   Compatible with Illustrator 2026 (v30+).
//

(function() {

    // JSON polyfill for older ExtendScript engines
    if (typeof JSON !== "object") {
        JSON = {};
        JSON.stringify = function(obj) {
            var t = typeof obj;
            if (t != "object" || obj === null) {
                if (t == "string") obj = '"' + obj.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
                return String(obj);
            }
            var n, v, json = [], arr = (obj && obj.constructor == Array);
            for (n in obj) {
                if (!obj.hasOwnProperty(n)) continue;
                v = obj[n]; t = typeof v;
                if (t == "string") v = '"' + v.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
                else if (t == "object" && v !== null) v = JSON.stringify(v);
                json.push((arr ? "" : '"' + n + '":') + String(v));
            }
            return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
        };
        JSON.parse = function(str) { return eval("(" + str + ")"); };
    }

    var desktopFolder    = Folder.desktop;
    var artboardsJsonPath = desktopFolder.fsName + "/ai_artboards.json";
    var curvesJsonPath    = desktopFolder.fsName + "/rhino_curves.json";

    // Use "dialog" mode for Illustrator 2026 compatibility.
    // Palette mode with #targetengine "session" loses document access in v30+.
    var win = new Window("dialog", "Rhino \u2194 Illustrator Sync", undefined);
    win.orientation   = "column";
    win.alignChildren = ["fill", "top"];
    win.spacing       = 12;
    win.margins       = 16;
    win.preferredSize = [300, 420];

    // --- Title ---
    var titleGrp = win.add("group");
    titleGrp.orientation = "row";
    titleGrp.alignment   = "center";
    var titleTxt = titleGrp.add("statictext", undefined, "RHINO \u2194 ILLUSTRATOR SYNC");
    titleTxt.font = ScriptUI.newFont("Tahoma", "BOLD", 12);

    // --- File paths display ---
    var pathGrp = win.add("panel", undefined, "File Paths");
    pathGrp.orientation   = "column";
    pathGrp.alignChildren = "left";
    pathGrp.spacing       = 4;
    pathGrp.margins       = 8;

    var lblAI = pathGrp.add("statictext", undefined, "Artboards JSON:", {multiline: false});
    lblAI.font = ScriptUI.newFont("Tahoma", "BOLD", 9);
    var txtAI = pathGrp.add("statictext", undefined, artboardsJsonPath, {multiline: true, truncate: "middle"});
    txtAI.font = ScriptUI.newFont("Tahoma", "REGULAR", 8);
    txtAI.preferredSize.width = 260;

    var lblRH = pathGrp.add("statictext", undefined, "Curves JSON:", {multiline: false});
    lblRH.font = ScriptUI.newFont("Tahoma", "BOLD", 9);
    var txtRH = pathGrp.add("statictext", undefined, curvesJsonPath, {multiline: true, truncate: "middle"});
    txtRH.font = ScriptUI.newFont("Tahoma", "REGULAR", 8);
    txtRH.preferredSize.width = 260;

    // Browse buttons
    var browseGrp = pathGrp.add("group");
    browseGrp.orientation   = "row";
    browseGrp.alignChildren = ["fill", "center"];
    browseGrp.spacing       = 6;

    var btnBrowseAI = browseGrp.add("button", undefined, "Change AI path\u2026");
    btnBrowseAI.font = ScriptUI.newFont("Tahoma", "REGULAR", 9);

    var btnBrowseRH = browseGrp.add("button", undefined, "Change Rhino path\u2026");
    btnBrowseRH.font = ScriptUI.newFont("Tahoma", "REGULAR", 9);

    // --- Status Panel ---
    var statusPanel = win.add("panel", undefined, "Sync Status");
    statusPanel.orientation   = "column";
    statusPanel.alignChildren = "left";
    statusPanel.spacing       = 4;
    statusPanel.margins       = 8;

    var importStatus = statusPanel.add("statictext", undefined, "Last Imported: Never");
    importStatus.font = ScriptUI.newFont("Tahoma", "REGULAR", 10);

    var exportStatus = statusPanel.add("statictext", undefined, "Last Exported: Never");
    exportStatus.font = ScriptUI.newFont("Tahoma", "REGULAR", 10);

    // --- Action Buttons ---
    var actPanel = win.add("panel", undefined, "Actions");
    actPanel.orientation   = "column";
    actPanel.alignChildren = ["fill", "top"];
    actPanel.spacing       = 8;
    actPanel.margins       = 8;

    var btnExport = actPanel.add("button", undefined, "Export Artboards to Rhino");
    btnExport.preferredSize.height = 32;
    btnExport.font = ScriptUI.newFont("Tahoma", "BOLD", 11);

    var btnImport = actPanel.add("button", undefined, "Import Curves from Rhino");
    btnImport.preferredSize.height = 32;
    btnImport.font = ScriptUI.newFont("Tahoma", "BOLD", 11);

    var btnBoth = actPanel.add("button", undefined, "Sync Both (Export then Import)");
    btnBoth.preferredSize.height = 28;
    btnBoth.font = ScriptUI.newFont("Tahoma", "REGULAR", 10);

    // --- Footer ---
    var footer = win.add("statictext", undefined, "Status: Ready");
    footer.font      = ScriptUI.newFont("Tahoma", "REGULAR", 9);
    footer.alignment = "center";

    // Close button
    var btnClose = win.add("button", undefined, "Close");
    btnClose.alignment = "right";

    // =============================================
    // HELPER FUNCTIONS
    // =============================================

    function nowStr() {
        var d = new Date();
        var h = String(d.getHours());   if (h.length < 2) h = "0" + h;
        var m = String(d.getMinutes()); if (m.length < 2) m = "0" + m;
        var s = String(d.getSeconds()); if (s.length < 2) s = "0" + s;
        return h + ":" + m + ":" + s;
    }

    function setStatus(msg) {
        footer.text = "Status: " + msg;
        win.update();
    }

    function getDoc() {
        // Safely get the active document, or null
        try {
            if (app.documents.length > 0) {
                return app.activeDocument;
            }
        } catch(e) {}
        return null;
    }

    // =============================================
    // EXPORT ARTBOARDS
    // =============================================
    function doExport(silent) {
        try {
            var doc = getDoc();
            if (!doc) {
                if (!silent) alert("No document is open in Illustrator.\nPlease open or create a document first.");
                setStatus("No document open");
                return false;
            }

            var list = [];
            var PT2MM = 0.3527777778;

            for (var i = 0; i < doc.artboards.length; i++) {
                var ab   = doc.artboards[i];
                var rect = ab.artboardRect;
                list.push({
                    "name":      ab.name,
                    "width_mm":  (rect[2] - rect[0]) * PT2MM,
                    "height_mm": (rect[1] - rect[3]) * PT2MM,
                    "left_mm":   rect[0]  * PT2MM,
                    "top_mm":    rect[1]  * PT2MM,
                    "right_mm":  rect[2]  * PT2MM,
                    "bottom_mm": rect[3]  * PT2MM
                });
            }

            var file = new File(artboardsJsonPath);
            file.encoding = "UTF-8";
            file.open("w");
            file.write(JSON.stringify(list, null, 2));
            file.close();

            exportStatus.text = "Last Exported: " + nowStr();
            setStatus("Artboards exported OK");
            if (!silent) {
                alert("Artboards exported!\n\nSaved to:\n" + artboardsJsonPath + "\n\nNow press 'Import Artboards' in Rhino.");
            }
            return true;
        } catch(e) {
            setStatus("Export ERROR: " + e);
            if (!silent) alert("Export error:\n" + e);
            return false;
        }
    }

    // =============================================
    // IMPORT CURVES
    // =============================================
    function doImport(silent) {
        try {
            var file = new File(curvesJsonPath);
            if (!file.exists) {
                if (!silent) alert("Curves file not found at:\n" + curvesJsonPath + "\n\nPlease run 'Export Curves' from Rhino first.");
                return false;
            }

            file.encoding = "UTF-8";
            file.open("r");
            var raw = file.read();
            file.close();

            if (!raw || raw.length === 0) {
                if (!silent) alert("Curves JSON file is empty.\nPlease export curves from Rhino first.");
                return false;
            }

            var data = JSON.parse(raw);
            if (!data || data.length === 0) {
                if (!silent) alert("No curve data found in JSON file.");
                return false;
            }

            var doc = getDoc();
            if (!doc) {
                doc = app.documents.add();
            }

            function ensureLayer(pathName) {
                var parts  = pathName.split("::");
                var parent = doc.layers;
                var layer;
                for (var i = 0; i < parts.length; i++) {
                    try {
                        layer = parent.getByName(parts[i]);
                    } catch(e) {
                        layer = parent.add();
                        layer.name = parts[i];
                    }
                    parent = layer.layers;
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
                if      (lt === "dashed")                       { item.strokeDashes = [6, 3]; }
                else if (lt === "dots")                         { item.strokeDashes = [1, 3]; }
                else if (lt === "hidden")                       { item.strokeDashes = [2, 2]; }
                else if (lt === "dashdot" || lt === "center")  { item.strokeDashes = [6, 3, 0, 3]; }
                else                                            { item.strokeDashes = []; }
            }

            var totalCurves = 0;
            var clearedLayers = {};

            for (var i = 0; i < data.length; i++) {
                var abData = data[i];
                var curves = abData.curves;
                if (!curves) continue;

                for (var j = 0; j < curves.length; j++) {
                    var curve = curves[j];
                    if (!curve.points || curve.points.length === 0) continue;
                    if (!curve.layer) continue;

                    var targetLayer = ensureLayer(curve.layer);

                    // Clear the target sublayer once per session
                    var layerPath = targetLayer.name;
                    if (!clearedLayers[layerPath]) {
                        for (var p = targetLayer.pageItems.length - 1; p >= 0; p--) {
                            targetLayer.pageItems[p].remove();
                        }
                        clearedLayers[layerPath] = true;
                    }

                    var pts = [];
                    for (var k = 0; k < curve.points.length; k++) {
                        pts.push([mmToPt(curve.points[k][0]), -mmToPt(curve.points[k][1])]);
                    }

                    if (curve.type === "circle" && pts.length >= 1) {
                        var cx = pts[0][0], cy = pts[0][1];
                        var r  = (curve.radius !== undefined) ? mmToPt(curve.radius) : mmToPt(1);
                        var circ = targetLayer.pathItems.ellipse(cy + r, cx - r, r * 2, r * 2);
                        circ.closed = true;
                        applyStroke(circ, curve.color, curve.width, curve.linetype);
                    } else if (pts.length >= 2) {
                        var poly = targetLayer.pathItems.add();
                        try {
                            poly.filled  = false;
                            poly.stroked = true;
                            poly.closed  = (curve.closed === true);
                            for (var m = 0; m < pts.length; m++) {
                                var pt = poly.pathPoints.add();
                                pt.anchor = [pts[m][0], pts[m][1]];
                                pt.leftDirection  = pt.anchor;
                                pt.rightDirection = pt.anchor;
                                pt.pointType = PointType.CORNER;
                            }
                            applyStroke(poly, curve.color, curve.width, curve.linetype);
                        } catch(e) { /* skip bad paths */ }
                    }
                    totalCurves++;
                }
            }

            importStatus.text = "Last Imported: " + nowStr();
            setStatus("Imported " + totalCurves + " curves OK");
            if (!silent) {
                alert("Import complete!\n" + totalCurves + " curves imported from Rhino.");
            }
            return true;
        } catch(e) {
            setStatus("Import ERROR: " + e);
            if (!silent) alert("Import error:\n" + e);
            return false;
        }
    }

    // =============================================
    // WIRE UP EVENTS
    // =============================================

    btnBrowseAI.onClick = function() {
        var f = File.saveDialog("Choose where to save artboards JSON", "*.json");
        if (f) {
            artboardsJsonPath = f.fsName;
            txtAI.text        = artboardsJsonPath;
        }
    };

    btnBrowseRH.onClick = function() {
        var f = File.openDialog("Choose the Rhino curves JSON file", "*.json");
        if (f) {
            curvesJsonPath = f.fsName;
            txtRH.text     = curvesJsonPath;
        }
    };

    btnExport.onClick = function() { doExport(false); };
    btnImport.onClick = function() { doImport(false); };
    btnBoth.onClick   = function() {
        setStatus("Running sync...");
        doExport(false);
        doImport(false);
    };

    btnClose.onClick = function() { win.close(); };

    // =============================================
    // SHOW WINDOW
    // =============================================
    win.center();
    win.show();

})();
