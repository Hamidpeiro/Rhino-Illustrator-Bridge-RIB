# Rhino ⇄ Illustrator Direct Sync

A professional, single-click synchronization plugin that connects **Rhinoceros 3D** directly to **Adobe Illustrator**. 

No more manually exporting `.ai` files, opening them, fixing scale, and reorganizing layers. With **Rhino Illustrator Bridge**, you simply click "Export" in Rhino, and your layout appears instantly inside Adobe Illustrator with **100% fidelity**.

![Rhino to Illustrator Sync](icon.png)

---

## 🔥 Key Features

- **Direct Communication:** The plugin directly talks to Adobe Illustrator via COM (Windows) or AppleScript (macOS). No need to run any scripts manually in Illustrator!
- **One-Click Sync:** Export thousands of lines, hatches, and texts directly into an open Illustrator document in seconds.
- **Bi-Directional Artboards:** Import Illustrator Artboards into Rhino as scaled bounding boxes, draw your lines inside them, and push them back. They will land exactly on the correct artboards in Illustrator.
- **Absolute Fidelity:**
  - **Layers & Sublayers:** Preserves your exact Rhino layer structure (e.g. `Layer::Sublayer`).
  - **Colors & Stroke Weights:** RGB colors are mapped perfectly.
  - **Linetypes:** Dashed, dotted, and custom linetypes in Rhino translate to Illustrator stroke dash arrays natively.
  - **Text & Annotations:** Rhino Text objects are converted to live editable Text Frames in Illustrator, matching font, size, color, and justification.
  - **Hatches (Solid & Pattern):** Solid hatches are mapped to Illustrator filled paths.
  - **Pictures / Images:** Picture frames in Rhino are placed as linked images in Illustrator.
- **High Performance:** Heavily optimized C++ & ExtendScript logic instantly processes tens of thousands of paths without hanging.

---

## 🚀 Installation

The plugin supports **Rhino 8** on both **Windows** and **macOS**. 

### Option A: Install via Package Manager (Recommended)
1. Download the latest `.yak` package from the `dist/` folder or the Releases page.
2. Open Rhino 8, type `PackageManager` in the command line.
3. Drag and drop the `.yak` file into the Package Manager window, or click the gear icon to install from a local file.
4. Restart Rhino.

### Option B: macOS Installer (.macrhi)
1. Go to the `dist/mac/` folder.
2. Double-click `RhinoIllustratorBridge.macrhi`.
3. Rhino will open and install the package. Restart Rhino.
*(Do not double-click the `.rhp` file directly on macOS).*

### Option C: Windows Manual Install (.rhp)
1. Go to the `dist/windows/` folder.
2. Right-click `RhinoIllustratorBridge.rhp` -> **Properties** -> Check **"Unblock"** -> **Apply**.
3. Drag and drop the `.rhp` file into the Rhino viewport.

---

## 🛠 How to Use

1. **Launch the Panel:** In Rhino, type `RhinoIllustratorBridge` to open the dockable sync panel.
2. **Import Artboards (Optional):** 
   - Open your Illustrator document with your desired artboards.
   - Click **"Import Artboards"** in the Rhino panel. The plugin will create a layer called `Artboards` containing rectangles matching your Illustrator artboards.
3. **Draw & Prepare:** 
   - Draw your lines, hatches, and text inside the imported artboard rectangles.
   - Organize them into layers.
4. **Push to Illustrator:** 
   - Make sure Adobe Illustrator is running and has a document open.
   - Click **"Export to Illustrator"** in the Rhino panel. 
   - Watch the magic happen! Your artwork will appear instantly in Illustrator, perfectly scaled, layered, and styled.

---

## 💻 Building from Source

To compile the C# plugin yourself:

- **Windows:** Run the `build-yak-package.ps1` script in PowerShell.
- **macOS:** Run the `build-mac.sh` script in your terminal.

Both scripts will automatically compile the plugin, stage the assets, create the Yak package, and generate the installers in the `dist/` directory.
