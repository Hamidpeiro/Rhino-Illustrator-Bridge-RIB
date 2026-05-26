# Rhino–Illustrator Live Sync Plugin

A professional live-sync link between Rhino 3D and Adobe Illustrator that preserves layers, colors, stroke weights, and linetypes.

Instead of running separate import/export scripts manually, this plugin provides **persistent, modeless floating panels** in both applications with one-click operations and **smart auto-sync background watching**.

---

## Key Features

- **Persistent Floating Panels:** Launch the sync panel once in both programs; they stay open as you work.
- **Smart Auto-Sync / Live Mode:**
  - **Illustrator Auto-Import:** Automatically reads and updates imported curves from Rhino when you focus or hover over the Illustrator panel.
  - **Rhino Auto-Receive:** Automatically loads and mirrors artboards in real-time when Illustrator updates them.
  - **Rhino Auto-Send:** Continuously checks curves in the "Artboards" layers and automatically exports edits to Illustrator in the background.
- **Fidelity Preservation:** Full support for custom colors (RGB), layer hierarchy (`Parent::Child`), stroke widths, and mapped linetype dashes.

---

## Installation & Setup

### 1. Adobe Illustrator Sync Panel
Copy [rhino_illustrator_sync_panel.jsx](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Illustrator/rhino_illustrator_sync_panel.jsx) to Illustrator's scripts folder to make it accessible directly from the menu:
- **Windows:** `C:\Program Files\Adobe\Adobe Illustrator [Version]\Presets\[Language]\Scripts\`
- **macOS:** `/Applications/Adobe Illustrator [Version]/Presets/[Language]/Scripts/`

*Restart Illustrator to see it under `File > Scripts > rhino_illustrator_sync_panel`.*

### 2. Rhino Sync Panel
Run [rhino_illustrator_sync_panel.py](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Rhino/rhino_illustrator_sync_panel.py):
- Open Rhino's script editor by typing `EditPythonScript` in the command line, open the file, and run it.
- Alternatively, assign it to an alias or custom toolbar button using `-RunPythonScript "C:\path\to\rhino_illustrator_sync_panel.py"`.

---

## How to Use the Live Sync Workflow

1. **Launch Panels:** Open the sync panel in both Illustrator and Rhino.
2. **Setup Artboards:** 
   - Click **Export Artboards** in Illustrator.
   - Click **Import Artboards** in Rhino (or enable **Auto-Receive** in Rhino so it handles this instantly!).
3. **Draft & Sync Curves:**
   - Draw or modify curves in Rhino inside the generated "Artboards" sublayers.
   - Click **Export Curves** in Rhino, or enable **Auto-Send (Watch Rhino Curves)** to let Rhino handle it instantly in the background!
   - In Illustrator, click **Import Curves** or enable **Auto-Import on Focus** so it updates automatically when you switch back to Illustrator.

---

## Folder Structure

- [Illustrator/](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Illustrator/)
  - [rhino_illustrator_sync_panel.jsx](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Illustrator/rhino_illustrator_sync_panel.jsx) *(Unified Sync Panel)*
  - `exporting_artboards_from_illustrator.jsx` *(Legacy)*
  - `importing_curve_to_illustrator.jsx` *(Legacy)*
- [Rhino/](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Rhino/)
  - [rhino_illustrator_sync_panel.py](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Rhino/rhino_illustrator_sync_panel.py) *(Unified Modeless Eto Panel)*
  - `importing_artboards_into_rhino.py` *(Legacy)*
  - `exporting_curves_from_rhino.py` *(Legacy)*
- [Sample_JSON/](file:///c:/Users/hamid/Documents/GitHub/rhino-illustrator-sync/Sample_JSON/)
  - `ai_artboards.json` *(Artboards layout payload)*
  - `rhino_curves.json` *(Curves geometry payload)*
