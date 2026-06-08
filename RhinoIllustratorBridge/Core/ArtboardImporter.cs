using System;
using System.Collections.Generic;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoIllustratorBridge.Core
{
    public static class ArtboardImporter
    {
        public static void ImportArtboards(RhinoDoc doc, List<ArtboardData> artboards)
        {
            string parentLayerName = "Artboards";

            // Find or create parent layer
            int parentLayerIdx = doc.Layers.FindByFullPath(parentLayerName, -1);
            if (parentLayerIdx < 0)
            {
                var newParent = new Layer { Name = parentLayerName };
                parentLayerIdx = doc.Layers.Add(newParent);
            }
            var parentLayer = doc.Layers[parentLayerIdx];

            // Clear previous artboard objects in parent layer
            var allArtboardsObjects = doc.Objects.FindByLayer(parentLayer);
            if (allArtboardsObjects != null)
            {
                foreach (var obj in allArtboardsObjects)
                {
                    doc.Objects.Delete(obj.Id, true);
                }
            }

            // Clear previous objects in all sublayers under "Artboards"
            var children = parentLayer.GetChildren();
            if (children != null)
            {
                foreach (var child in children)
                {
                    var childObjects = doc.Objects.FindByLayer(child);
                    if (childObjects != null)
                    {
                        foreach (var obj in childObjects)
                        {
                            doc.Objects.Delete(obj.Id, true);
                        }
                    }
                }
            }

            // Draw new artboards
            foreach (var ab in artboards)
            {
                string name = string.IsNullOrEmpty(ab.Name) ? "Artboard" : ab.Name;
                double width = ab.WidthMm;
                double height = ab.HeightMm;
                double left = ab.LeftMm;
                double top = ab.TopMm;

                // Find or create sublayer
                string sublayerName = name;
                int subLayerIdx = doc.Layers.FindByFullPath(parentLayerName + "::" + sublayerName, -1);
                if (subLayerIdx < 0)
                {
                    var newSub = new Layer
                    {
                        Name = sublayerName,
                        ParentLayerId = parentLayer.Id
                    };
                    subLayerIdx = doc.Layers.Add(newSub);
                }
                var subLayer = doc.Layers[subLayerIdx];

                // Create rectangle geometry
                Point3d pt1 = new Point3d(left, -top, 0);
                Point3d pt2 = new Point3d(left + width, -top, 0);
                Point3d pt3 = new Point3d(left + width, -top + height, 0);
                Point3d pt4 = new Point3d(left, -top + height, 0);

                Polyline poly = new Polyline(new Point3d[] { pt1, pt2, pt3, pt4, pt1 });
                Curve rectCrv = poly.ToNurbsCurve();

                // Apply mirror along the X-axis (Y negation) via ZX plane
                Transform mirrorX = Transform.Mirror(Plane.WorldZX);
                rectCrv.Transform(mirrorX);

                // Add to document with attributes
                var attributes = new ObjectAttributes
                {
                    LayerIndex = subLayer.Index,
                    Name = name
                };

                Guid rectId = doc.Objects.AddCurve(rectCrv, attributes);
                if (rectId != Guid.Empty)
                {
                    doc.Objects.Lock(rectId, true);
                }
            }

            doc.Views.Redraw();
        }
    }
}
