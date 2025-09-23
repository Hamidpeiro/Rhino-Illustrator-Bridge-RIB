// importShapes.jsx
// JSON polyfill for older ExtendScript
if (typeof JSON !== "object") {
    JSON = {};
    JSON.stringify = function(obj) { /* polyfill */ };
    JSON.parse = function(str) { return eval("(" + str + ")"); };
}

// JSON file on Desktop
var desktopFolder = Folder.desktop;
var jsonFilePath = desktopFolder.fsName + "/rhino_curves.json";

var file = new File(jsonFilePath);
if (!file.exists) {
    alert("❌ JSON file not found: " + jsonFilePath);
}

file.open("r");
var raw = file.read();
file.close();

var data = JSON.parse(raw);

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

function mmToPt(mm){ return mm * 2.8346456693; }

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
                item.strokeDashes = [6, 3, 0, 3]; // dash-dot
                item.strokeCap = StrokeCap.ROUNDENDCAP;
                item.strokeJoin = StrokeJoin.ROUNDENDJOIN;
                break;
            case "dashed":
                item.strokeDashes = [6, 3];        // dashed
                break;
            case "dots":
                item.strokeDashes = [1, 3];        // dotted
                break;
            case "hidden":
                item.strokeDashes = [2, 2];        // short dash
                break;
            default:
                item.strokeDashes = [];
        }
    } else {
        item.strokeDashes = [];
    }
}

// --- Main Loop ---
for (var i=0; i<data.length; i++){
    var artboardData = data[i];
    var curves = artboardData.curves;

    for (var j=0; j<curves.length; j++){
        var curve = curves[j];
        if (!curve.points || !curve.layer) continue;

        var targetLayer = ensureLayer(curve.layer);

        // Convert points mm -> pt and invert Y
        var pts = [];
        for (var k=0; k<curve.points.length; k++){
            pts.push([mmToPt(curve.points[k][0]), -mmToPt(curve.points[k][1])]);
        }

        // Create shape
        if (curve.type === "circle" && pts.length >= 2){
            var centerX = pts[0][0];
            var centerY = pts[0][1];
            var radius = (curve.radius !== undefined) ? mmToPt(curve.radius) :
                         Math.sqrt(Math.pow(pts[1][0]-centerX,2)+Math.pow(pts[1][1]-centerY,2));
            var circ = targetLayer.pathItems.ellipse(centerY + radius, centerX - radius, radius*2, radius*2);
            circ.closed = true;
            applyStroke(circ, curve.color, curve.width, curve.linetype);

        } else {
            var poly = targetLayer.pathItems.add();
            try {
                poly.filled = false;
                poly.stroked = true;
                poly.closed = (curve.type === "rectangle");

                for (var m=0; m<pts.length; m++){
                    var pt = poly.pathPoints.add();
                    pt.anchor = [pts[m][0], pts[m][1]];
                    pt.leftDirection = pt.anchor;
                    pt.rightDirection = pt.anchor;
                    pt.pointType = PointType.CORNER;
                }

                applyStroke(poly, curve.color, curve.width, curve.linetype);

            } catch(e){
                alert("⚠️ Failed to add polyline points for layer: " + curve.layer);
            }
        }
    }
}

alert("✅ Imported shapes with types, color, width, and line type applied!");