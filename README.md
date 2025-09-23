# Rhino–Illustrator Sync

Scripts to transfer design data between Rhino 3D and Adobe Illustrator, preserving layers, colors, line widths, and line types.

---

## Features

- Export Artboards from Illustrator → JSON
- Import Artboards into Rhino → maintain sizes & positions
- Export curves from Rhino → JSON with colors, line widths, line types
- Import curves back into Illustrator → preserves layers, stroke styles, and colors

---

## Folder Structure

python/
    importing_artboards_into_rhino.py
    exporting_curves_from_rhino.py

illustrator/
    exporting_artboards_from_illustrator.jsx
    importing_curve_to_illustrator.jsx

sample_json/
    rhino_curves.json

---

## How to Use

1. Export Artboards from Illustrator  
   - Run `exporting_artboards_from_illustrator.jsx` in Illustrator  

2. Import Artboards into Rhino  
   - Run `importing_artboards_into_rhino.py` in Rhino Python  

3. Export Curves from Rhino  
   - Run `exporting_curves_from_rhino.py` in Rhino  

4. Import Curves into Illustrator  
   - Run `importing_curve_to_illustrator.jsx` in Illustrator  

---

## Notes

- Ensure the JSON file is on your Desktop before importing  
- Compatible with Illustrator 2025 and Rhino 8 (Python 3.9)  
