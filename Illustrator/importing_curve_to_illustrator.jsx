// importShapes.jsx – Standalone curve importer for Illustrator
// Usage: File > Scripts > Other Script… → select this file
// Requires rhino_curves.json on the Desktop (exported from Rhino)

// JSON polyfill for older ExtendScript engines
if (typeof JSON !== "object") {
    JSON = {};
    JSON.stringify = function(obj) {
        var t = typeof obj;
        if (t != "object" || obj === null) {
            if (t == "string") obj = '"' + obj + '"';
            return String(obj);
        }
        var n, v, json = [], arr = (obj && obj.constructor == Array);
        for (n in obj) {
            v = obj[n]; t = typeof v;
            if (t == "string") v = '"' + v + '"';
            else if (t == "object" && v !== null) v = JSON.stringify(v);
            json.push((arr ? "" : '"' + n + '":') + String(v));
        }
        return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
    };
    JSON.parse = function(str) { return eval("(" + str + ")"); };
}

(function() {
    // JSON file on Desktop
    var desktopFolder = Folder.desktop;
    var jsonFilePath = desktopFolder.fsName + "/rhino_curves.json";

    var file = new File(jsonFilePath);
    if (!file.exists) {
        alert("❌ JSON file not found:\n" + jsonFilePath + "\n\nPlease export curves from Rhino first.");
        return;
    }

    file.encoding = "UTF-8";
    file.open("r");
    var raw = file.read();
    file.close();

    if (!raw || raw.length === 0) {
        alert("❌ JSON file is empty:\n" + jsonFilePath);
        return;
    }

    var data;
    try {
        data = JSON.parse(raw);
    } catch(e) {
        alert("❌ Failed to parse JSON:\n" + e);
        return;
    }

    if (!data || data.length === 0) {
        alert("❌ No curve data found in JSON file.");
        return;
    }

    var doc;
    if (app.documents.length === 0) {
        doc = app.documents.add();
    } else {
        doc = app.activeDocument;
    }

    // --- Helpers ---
    function ensureLayer(pathName) {
        var parts = pathName.split("::");
        var parent = doc.layers;
        var layer;
        for (var i = 0; i < parts.length; i++) {
            var name = parts[i];
            try {
                layer = parent.getByName(name);
            } catch(e) {
                layer = parent.add();
                layer.name = name;
            }
            parent = layer.layers;
        }
        return layer;
    }

    function mmToPt(mm) { return mm * 2.8346456693; }

    function applyStroke(item, color, width, linetype) {
        if (!item) return;
        item.stroked = true;
        item.filled = false;

        // Apply color
        if (color && color.length === 3) {
            var c = new RGBColor();
            c.red = color[0];
            c.green = color[1];
            c.blue = color[2];
            item.strokeColor = c;
        }

        // Apply width
        item.strokeWidth = (typeof width === "number") ? width : 1.0;

        // Map Rhino linetypes to Illustrator dash patterns
        if (linetype) {
            var lt = linetype.toLowerCase();
            switch(lt) {
                case "continuous":
                    item.strokeDashes = [];
                    break;
                case "border":
                    item.strokeDashes = [6, 3, 3, 3];
                    item.strokeCap = StrokeCap.ROUNDENDCAP;
                    item.strokeJoin = StrokeJoin.ROUNDENDJOIN;
                    break;
                case "center":
                case "dashdot":
                    item.strokeDashes = [6, 3, 0, 3];
                    item.strokeCap = StrokeCap.ROUNDENDCAP;
                    item.strokeJoin = StrokeJoin.ROUNDENDJOIN;
                    break;
                case "dashed":
                    item.strokeDashes = [6, 3];
                    item.strokeCap = StrokeCap.ROUNDENDCAP;
                    item.strokeJoin = StrokeJoin.ROUNDENDJOIN;
                    break;
                case "dots":
                    item.strokeDashes = [1, 3];
                    item.strokeCap = StrokeCap.ROUNDENDCAP;
                    item.strokeJoin = StrokeJoin.ROUNDENDJOIN;
                    break;
                case "hidden":
                    item.strokeDashes = [2, 2];
                    item.strokeCap = StrokeCap.ROUNDENDCAP;
                    item.strokeJoin = StrokeJoin.ROUNDENDJOIN;
                    break;
                default:
                    item.strokeDashes = [];
            }
        } else {
            item.strokeDashes = [];
        }
    }

    // --- Main Loop ---
    var totalCurves = 0;

    for (var i = 0; i < data.length; i++) {
        var artboardData = data[i];
        var curves = artboardData.curves;
        if (!curves) continue;

        for (var j = 0; j < curves.length; j++) {
            var curve = curves[j];
            if (!curve.points || curve.points.length === 0) continue;
            if (!curve.layer) continue;

            var targetLayer = ensureLayer(curve.layer);

            // Convert points mm -> pt and invert Y
            var pts = [];
            for (var k = 0; k < curve.points.length; k++) {
                pts.push([mmToPt(curve.points[k][0]), -mmToPt(curve.points[k][1])]);
            }

            // Create shape
            if (curve.type === "circle" && pts.length >= 1) {
                var centerX = pts[0][0];
                var centerY = pts[0][1];
                var radius = (curve.radius !== undefined) ? mmToPt(curve.radius) :
                            (pts.length >= 2) ? Math.sqrt(Math.pow(pts[1][0] - centerX, 2) + Math.pow(pts[1][1] - centerY, 2)) :
                            mmToPt(1);
                var circ = targetLayer.pathItems.ellipse(centerY + radius, centerX - radius, radius * 2, radius * 2);
                circ.closed = true;
                applyStroke(circ, curve.color, curve.width, curve.linetype);

            } else if (pts.length >= 2) {
                var poly = targetLayer.pathItems.add();
                try {
                    poly.filled = false;
                    poly.stroked = true;
                    poly.closed = (curve.type === "rectangle" || curve.closed === true);

                    for (var m = 0; m < pts.length; m++) {
                        var pt = poly.pathPoints.add();
                        pt.anchor = [pts[m][0], pts[m][1]];
                        pt.leftDirection = pt.anchor;
                        pt.rightDirection = pt.anchor;
                        pt.pointType = PointType.CORNER;
                    }

                    applyStroke(poly, curve.color, curve.width, curve.linetype);

                } catch(e) {
                    // Skip individual bad paths silently
                }
            }
            totalCurves++;
        }
    }

    alert("✅ Imported " + totalCurves + " shapes with types, color, width, and line type applied!");

})();