// exportArtboards.jsx
// Usage: Illustrator > File > Scripts > Other Script... → انتخاب این فایل
// Exports all artboards in the active document to JSON on Desktop
// JSON polyfill for older/malformed ExtendScript engine
if (typeof JSON !== "object") {
    JSON = {};
    JSON.stringify = function(obj) {
        var t = typeof obj;
        if (t != "object" || obj === null) {
            if (t == "string") obj = '"' + obj + '"';
            return String(obj);
        } else {
            var n, v, json = [], arr = (obj && obj.constructor == Array);
            for (n in obj) {
                v = obj[n]; t = typeof v;
                if (t == "string") v = '"' + v + '"';
                else if (t == "object" && v !== null) v = JSON.stringify(v);
                json.push((arr ? "" : '"' + n + '":') + String(v));
            }
            return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
        }
    };
    JSON.parse = function(str) { return eval("(" + str + ")"); };
}
(function(){
    try {
        if(app.documents.length === 0){
            alert("❌ No document open in Illustrator.");
            return;
        }

        var doc = app.activeDocument;

        // مسیر خروجی JSON روی Desktop
        var desktopFolder = Folder.desktop;
        var jsonFilePath = desktopFolder.fsName + "/ai_artboards.json"; // تغییر بده با username خودت

        var artboardsData = [];

        for(var i = 0; i < doc.artboards.length; i++){
            var ab = doc.artboards[i];
            var rect = ab.artboardRect; // [left, top, right, bottom]
            var width_pt = rect[2] - rect[0];
            var height_pt = rect[1] - rect[3];

            // تبدیل pt به mm: 1pt = 0.3527777778 mm
            var width_mm = width_pt * 0.3527777778;
            var height_mm = height_pt * 0.3527777778;

            var left_pt = rect[0];
            var top_pt = rect[1];
            var right_pt = rect[2];
            var bottom_pt = rect[3];

            // convert to mm
            var left_mm = left_pt * 0.3527777778;
            var top_mm = top_pt * 0.3527777778;
            var right_mm = right_pt * 0.3527777778;
            var bottom_mm = bottom_pt * 0.3527777778;

            artboardsData.push({
                "name": ab.name,
                "width_mm": width_mm,
                "height_mm": height_mm,
                "left_mm": left_mm,
                "top_mm": top_mm,
                "right_mm": right_mm,
                "bottom_mm": bottom_mm
            });
        }

        // write JSON to Desktop
        var file = new File(jsonFilePath);
        file.open("w");
        file.write(JSON.stringify(artboardsData, null, 2));
        file.close();

        alert("✅ Artboards exported to JSON:\n" + jsonFilePath);

    } catch(e){
        alert("Error: " + e);
    }
})();