#target illustrator
#targetengine "session"

// rhino_illustrator_sync_panel.jsx
//
// HOW TO USE:
//   Run via File > Scripts > Other Script…
//   The panel will open and stay on screen (palette mode).
//   Compatible with Illustrator 2026 (v30+).
//

(function() {

    var desktopFolder    = Folder.desktop;
    var artboardsJsonPath = desktopFolder.fsName + "/ai_artboards.json";
    var curvesJsonPath    = desktopFolder.fsName + "/rhino_curves.json";

    // Use "palette" mode for non-blocking panel
    var win = new Window("palette", "Rhino \u2194 Illustrator Sync", undefined);
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

    // =============================================
    // BRIDGETALK: MAIN ENGINE EXECUTION
    // =============================================
    // In Illustrator 2026, running DOM commands (app.activeDocument) from a palette UI
    // inside the session engine throws "there is no document". We bypass this by sending
    // the heavy lifting to the "main" engine via BridgeTalk.

    var jsonPolyfillStr = "";

    function runInMainEngine(func, argPath, onSuccess, onError) {
        var bt = new BridgeTalk();
        bt.target = "illustrator";
        var scriptStr = "var argPath = '" + argPath.replace(/\\/g, "\\\\") + "';\n" +
                        "(" + func.toString() + ")(argPath);";
        bt.body = scriptStr;
        bt.onResult = function(res) {
            var msg = res.body;
            if (msg.indexOf("ERROR:") === 0) {
                if (onError) onError(msg.substring(6));
            } else {
                if (onSuccess) onSuccess(msg);
            }
        };
        bt.onError = function(err) {
            if (onError) onError(err.body);
        };
        bt.send();
    }

    // =============================================
    // EXPORT ARTBOARDS (runs in Main Engine)
    // =============================================
    function doExportMain(outPath) {
        try {
            if (app.documents.length === 0) return "ERROR:No document is open in Illustrator.\nPlease open or create a document first.";
            var doc = app.activeDocument;
            
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

            var file = new File(outPath);
            file.encoding = "UTF-8";
            file.open("w");

            var jsonStr = "[";
            for (var k = 0; k < list.length; k++) {
                var obj = list[k];
                jsonStr += "{";
                jsonStr += '"name":"' + obj.name.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '",';
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

            file.write(jsonStr);
            file.close();

            app.redraw();
            return "SUCCESS";
        } catch(e) {
            return "ERROR:" + e.toString();
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

    btnExport.onClick = function() {
        setStatus("Exporting...");
        runInMainEngine(doExportMain, artboardsJsonPath, 
            function(msg) {
                exportStatus.text = "Last Exported: " + nowStr();
                setStatus("Artboards exported OK");
                alert("Artboards exported!\n\nSaved to:\n" + artboardsJsonPath + "\n\nNow press 'Import Artboards' in Rhino.");
            },
            function(err) {
                setStatus("Export ERROR");
                alert("Export error:\n" + err);
            }
        );
    };

    btnImport.onClick = function() {
        setStatus(btnImport.text.indexOf("Update") >= 0 ? "Updating..." : "Importing...");
        runInMainEngine(doUpdateMain, curvesJsonPath, 
            function(msg) {
                importStatus.text = "Last Synced: " + nowStr();
                setStatus("Sync OK (" + msg + " curves)");
                btnImport.text = "Update Curves from Rhino";
                alert("Success!\n" + msg + " curves synced from Rhino.\nIllustrator styling and manual edits were preserved.");
            },
            function(err) {
                setStatus("Import ERROR");
                alert("Import error:\n" + err);
            }
        );
    };

    // =============================================
    // UPDATE CURVES (runs in Main Engine)
    // =============================================
    function doUpdateMain(inPath) {
        try {
            var file = new File(inPath);
            if (!file.exists) return "ERROR:Curves file not found.";
            file.encoding = "UTF-8";
            file.open("r");
            var raw = file.read();
            file.close();

            if (!raw || raw.length === 0) return "ERROR:Curves JSON empty.";
            
            var data;
            try {
                if (typeof JSON === "object" && JSON.parse) {
                    data = JSON.parse(raw);
                } else {
                    data = eval("(" + raw + ")");
                }
            } catch(err) {
                return "ERROR:Failed to parse JSON.";
            }
            
            if (!data || data.length === 0) return "ERROR:No curve data found.";

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
                if      (lt === "dashed")                       { item.strokeDashes = [6, 3]; }
                else if (lt === "dots")                         { item.strokeDashes = [1, 3]; }
                else if (lt === "hidden")                       { item.strokeDashes = [2, 2]; }
                else if (lt === "dashdot" || lt === "center")  { item.strokeDashes = [6, 3, 0, 3]; }
                else                                            { item.strokeDashes = []; }
            }

            var totalCurves = 0;
            var incomingIds = {};

            for (var i = 0; i < data.length; i++) {
                if (!data[i].curves) continue;
                for (var j = 0; j < data[i].curves.length; j++) {
                    if (data[i].curves[j].id) incomingIds[data[i].curves[j].id] = true;
                }
            }

            for (var i = 0; i < data.length; i++) {
                var abData = data[i];
                var curves = abData.curves;
                if (!curves) continue;

                for (var j = 0; j < curves.length; j++) {
                    var curve = curves[j];
                    if (!curve.layer) continue;
                    var targetLayer = ensureLayer(curve.layer);

                    // Check for group
                    var group = null;
                    if (curve.group_id) {
                        try {
                            group = doc.pageItems.getByName(curve.group_id);
                            if (group.typename !== "GroupItem") {
                                group = null;
                            }
                        } catch(e) {
                            group = targetLayer.groupItems.add();
                            group.name = curve.group_id;
                        }
                    }
                    var parentContainer = group || targetLayer;

                    // Text frame handling – baseline positioning matching Rhino's native AI export
                    if (curve.type === "text") {
                        try {
                            if (curve.id) {
                                try {
                                    var existingText = doc.pageItems.getByName(curve.id);
                                    if (existingText) existingText.remove();
                                } catch(e) {}
                            }
                            var textRef = parentContainer.textFrames.add();
                            textRef.contents = curve.text;

                            // Set text size
                            var fontSize = curve.height ? mmToPt(curve.height) : 12;
                            textRef.textRange.characterAttributes.size = fontSize;

                            // Set text color
                            if (curve.color && curve.color.length === 3) {
                                var c = new RGBColor();
                                c.red = curve.color[0]; c.green = curve.color[1]; c.blue = curve.color[2];
                                textRef.textRange.characterAttributes.fillColor = c;
                            }
                            // Set font
                            if (curve.font) {
                                try {
                                    textRef.textRange.characterAttributes.textFont = app.textFonts.getByName(curve.font);
                                } catch(e) {}
                            }
                            // Set paragraph justification (alignment)
                            if (curve.justification) {
                                var just = curve.justification.toLowerCase();
                                if (just === "center") {
                                    textRef.textRange.paragraphAttributes.justification = Justification.CENTER;
                                } else if (just === "right") {
                                    textRef.textRange.paragraphAttributes.justification = Justification.RIGHT;
                                } else {
                                    textRef.textRange.paragraphAttributes.justification = Justification.LEFT;
                                }
                            }

                            // Baseline position from Rhino: point = [x, -y]
                            // Negate Y again (same double-negation as curve points)
                            var tx = mmToPt(curve.point[0]);
                            var baselineY = -mmToPt(curve.point[1]);

                            // .position = [left, top] of bounding box, NOT the baseline.
                            // .anchor = baseline insertion point (for point text).
                            // Strategy: place at origin, read anchor offset, then move to target.
                            textRef.position = [0, 0];
                            var dx = 0, dy = 0;
                            try {
                                var anch = textRef.anchor;
                                dx = -anch[0];
                                dy = -anch[1];
                            } catch(anchorErr) {
                                // Fallback: ascent ≈ 80% of font size
                                dy = fontSize * 0.8;
                            }
                            textRef.position = [tx + dx, baselineY + dy];

                            if (curve.id) textRef.name = curve.id;
                        } catch (e) {}
                        totalCurves++;
                        continue;
                    }

                    // Picture handling: place image (no points needed)
                    if (curve.type === "picture" && curve.image) {
                        try {
                            var imgFile = new File(curve.image);
                            if (imgFile.exists) {
                                // Remove existing placed item with same id
                                if (curve.id) {
                                    try {
                                        var existingPic = doc.pageItems.getByName(curve.id);
                                        if (existingPic) existingPic.remove();
                                    } catch(e) {}
                                }
                                var placed = parentContainer.placedItems.add();
                                placed.file = imgFile;
                                var picLeft = mmToPt(curve.left);
                                var picTop = -mmToPt(curve.top);
                                var picWidth = mmToPt(curve.width);
                                var picHeight = mmToPt(curve.height);
                                placed.position = [picLeft, picTop];
                                placed.width = picWidth;
                                placed.height = picHeight;
                                if (curve.id) placed.name = curve.id;
                                placed.move(parentContainer, ElementPlacement.PLACEATEND);
                            }
                        } catch (e) {}
                        totalCurves++;
                        continue;
                    }

                    if (!curve.points || curve.points.length === 0) continue;

                    var pts = [];
                    for (var k = 0; k < curve.points.length; k++) {
                        pts.push([mmToPt(curve.points[k][0]), -mmToPt(curve.points[k][1])]);
                    }
                    
                    var existingPath = null;
                    if (curve.id) {
                        try { existingPath = doc.pageItems.getByName(curve.id); } 
                        catch(e) {}
                    }
                    
                    if (existingPath && existingPath.typename === "PathItem") {
                        if (curve.type === "circle" || curve.type === "ellipse") {
                            var cx = pts[0][0], cy = pts[0][1];
                            var r  = (curve.radius !== undefined) ? mmToPt(curve.radius) : mmToPt(1);
                            var newCirc = parentContainer.pathItems.ellipse(cy + r, cx - r, r * 2, r * 2);
                            newCirc.name = curve.id;
                            newCirc.closed = true;
                            
                            newCirc.filled = existingPath.filled;
                            if (existingPath.filled) newCirc.fillColor = existingPath.fillColor;
                            
                            newCirc.stroked = existingPath.stroked;
                            if (existingPath.stroked) {
                                newCirc.strokeColor = existingPath.strokeColor;
                                newCirc.strokeWidth = existingPath.strokeWidth;
                                newCirc.strokeDashes = existingPath.strokeDashes;
                            }
                            existingPath.remove();
                            totalCurves++;
                            continue;
                        } else {
                            if (parentContainer && existingPath.parent !== parentContainer) {
                                try {
                                    existingPath.move(parentContainer, ElementPlacement.PLACEATEND);
                                } catch(e) {}
                            }
                            var pp = existingPath.pathPoints;
                            while (pp.length > pts.length) { pp[pp.length - 1].remove(); }
                            for (var m = 0; m < pp.length; m++) {
                                pp[m].anchor = pts[m];
                                pp[m].leftDirection = pts[m];
                                pp[m].rightDirection = pts[m];
                            }
                            for (var m = pp.length; m < pts.length; m++) {
                                var pt = pp.add();
                                pt.anchor = pts[m];
                                pt.leftDirection = pts[m];
                                pt.rightDirection = pts[m];
                                pt.pointType = PointType.CORNER;
                            }
                            existingPath.closed = (curve.closed === true);
                            totalCurves++;
                            continue;
                        }
                    }
                    
                    if ((curve.type === "circle" || curve.type === "ellipse") && pts.length >= 1) {
                        var cx = pts[0][0], cy = pts[0][1];
                        var r  = (curve.radius !== undefined) ? mmToPt(curve.radius) : mmToPt(1);
                        var circ = parentContainer.pathItems.ellipse(cy + r, cx - r, r * 2, r * 2);
                        if (curve.id) circ.name = curve.id;
                        circ.closed = true;
                        applyStroke(circ, curve.color, curve.width, curve.linetype);
                    } else if (pts.length >= 2) {
                        var poly = parentContainer.pathItems.add();
                        if (curve.id) poly.name = curve.id;
                        try {
                            for (var m = 0; m < pts.length; m++) {
                                var pt = poly.pathPoints.add();
                                pt.anchor         = [pts[m][0], pts[m][1]];
                                pt.leftDirection  = pt.anchor;
                                pt.rightDirection = pt.anchor;
                                pt.pointType      = PointType.CORNER;
                            }
                            var isFill = (curve.type === "hatch_solid" || curve.type === "hatch");
                            if (isFill) {
                                poly.closed  = true;
                                poly.filled  = true;
                                poly.stroked = false;
                                var fc = curve.fill_color || curve.color;
                                if (fc && fc.length === 3) {
                                    var fillRgb = new RGBColor();
                                    fillRgb.red = fc[0]; fillRgb.green = fc[1]; fillRgb.blue = fc[2];
                                    poly.fillColor = fillRgb;
                                }
                            } else {
                                poly.filled  = false;
                                poly.stroked = true;
                                poly.closed  = (curve.closed === true);
                                applyStroke(poly, curve.color, curve.width, curve.linetype);
                            }
                        } catch(e) {}
                    }
                    totalCurves++;
                }
            }
            app.redraw();
            return totalCurves.toString();
        } catch(e) { return "ERROR:" + e.toString(); }
    }

    btnBoth.onClick = function() {
        setStatus("Running sync...");
        runInMainEngine(doExportMain, artboardsJsonPath, 
            function(msg1) {
                exportStatus.text = "Last Exported: " + nowStr();
                runInMainEngine(doUpdateMain, curvesJsonPath, 
                    function(msg2) {
                        importStatus.text = "Last Synced: " + nowStr();
                        btnImport.text = "Update Curves from Rhino";
                        setStatus("Sync OK (" + msg2 + " curves)");
                    },
                    function(err2) {
                        setStatus("Import ERROR during sync");
                        alert("Import error:\n" + err2);
                    }
                );
            },
            function(err1) {
                setStatus("Export ERROR during sync");
                alert("Export error:\n" + err1);
            }
        );
    };

    btnClose.onClick = function() { win.close(); };

    // =============================================
    // SHOW WINDOW
    // =============================================
    win.center();
    win.show();

})();
