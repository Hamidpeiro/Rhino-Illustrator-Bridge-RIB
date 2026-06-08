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

1. Copy `mac/RhinoIllustratorBridge.rhp` to a permanent location
   (e.g. `~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/`)
2. Open Rhino 8
3. Type `_PlugInManager` in the command line
4. Click **Install…** and browse to the `.rhp` file
5. Restart Rhino
6. Type `RhinoIllustratorBridge` in the command line to open the panel

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
