# Rhino Illustrator Bridge (RIB)
## Installation Guide

### Requirements
- **Rhino 8** or later
- **Adobe Illustrator** (any recent version)

---

### Windows Installation

1. Copy `windows/RhinoIllustratorBridge.rhp` to a permanent location
   (e.g. `C:\Users\<YourName>\AppData\Roaming\McNeel\Rhinoceros\8.0\Plug-ins\`)
2. Open Rhino 8
3. Type `_PlugInManager` in the command line
4. Click **Install…** and browse to the `.rhp` file
5. Restart Rhino
6. Type `RhinoIllustratorBridge` in the command line to open the panel

### macOS Installation

You can install the plugin on macOS using one of the following methods:

#### Method 1: Using the Mac Installer (Recommended)
1. Go to the `dist/mac` folder.
2. Double-click the `RhinoIllustratorBridge.macrhi` file. (Alternatively, drag it onto the Rhino icon in your Dock).
3. Rhino will open and install the plugin automatically.
4. Restart Rhino to complete the installation.
5. Type `RhinoIllustratorBridge` in the command line to launch the panel.

> **Warning:** Do NOT double-click `RhinoIllustratorBridge.rhp` directly! Finder will try to open it as a CAD document, resulting in a **"File type not supported by Rhinoceros"** error. Only double-click the `.macrhi` installer file, or load the `.rhp` using the manual steps below.

#### Method 2: Manual Load via Plug-in Manager
1. Copy `dist/mac/RhinoIllustratorBridge.rhp` to a permanent folder on your drive (e.g. `~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/`).
2. Open Rhino 8.
3. Type `_PlugInManager` in the command line.
4. Click **Install...** (or **+** button) and select the `.rhp` file you copied.
5. Restart Rhino.
6. Type `RhinoIllustratorBridge` in the command line to launch the panel.

> **macOS Note:** The first time the plugin tries to communicate with
> Illustrator, macOS may ask you to grant Rhino permission to control
> Adobe Illustrator. Click **OK** to allow.

---

### Usage

| Button | Action |
|--------|--------|
| **📥 Read Illustrator Artboards** | Imports artboard rectangles from the active Illustrator document into Rhino as locked rectangles on an "Artboards" layer |
| **📤 Send Curves to Illustrator** | Exports all curves, hatches, annotations and text within each artboard boundary to Illustrator |

### Options

- **Export Pictures** – Include picture-frame objects in the export
- **Hatch Export** – Choose between solid fill or exploded boundary export
- **Annotation Export** – Group or ungroup dimension/annotation elements

---

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "Could not connect to Illustrator" | Make sure Adobe Illustrator is running and a document is open |
| Curves export but don't appear | Check that curves are inside an artboard boundary |
| macOS permission error | Grant Rhino automation access in System Settings → Privacy & Security → Automation |

---

**Version:** 1.0.0  
**Author:** Hamid Peiro  
**License:** MIT  
