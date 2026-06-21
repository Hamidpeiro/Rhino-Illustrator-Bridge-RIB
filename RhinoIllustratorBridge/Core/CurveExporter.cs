using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoIllustratorBridge.Core
{
    public static class CurveExporter
    {
        [ThreadStatic]
        private static System.Collections.Generic.Dictionary<Guid, (bool isPic, string? path)>? _pictureCache;

        public static List<ExportGroup> BuildExportGroups(RhinoDoc doc, bool exportPictures, string hatchExportMode, bool annotationGroup)
        {
            _pictureCache = new System.Collections.Generic.Dictionary<Guid, (bool isPic, string? path)>();
            var result = new List<ExportGroup>();

            int parentIdx = doc.Layers.FindByFullPath("Artboards", -1);
            if (parentIdx < 0) return result;

            var parentLayer = doc.Layers[parentIdx];
            var sublayers = parentLayer.GetChildren();
            if (sublayers == null || sublayers.Length == 0) return result;

            // Gather all candidate objects from the document
            var allObjects = new List<RhinoObject>();
            foreach (var obj in doc.Objects)
            {
                if (obj.IsDeleted || obj.IsLocked) continue;

                var otype = obj.ObjectType;
                if (otype == ObjectType.Curve || otype == ObjectType.Hatch ||
                    otype == ObjectType.Annotation || otype == ObjectType.Brep ||
                    otype == ObjectType.Surface)
                {
                    allObjects.Add(obj);
                }
            }

            foreach (var subLayer in sublayers)
            {
                var rects = doc.Objects.FindByLayer(subLayer);
                if (rects == null || rects.Length == 0) continue;

                RhinoObject? artboardRectObj = null;
                foreach (var obj in rects)
                {
                    if (obj.Geometry is Curve c && c.IsClosed)
                    {
                        if (c.Degree == 1 && c.SpanCount == 4) // Rectangle check
                        {
                            artboardRectObj = obj;
                            break;
                        }
                    }
                }
                if (artboardRectObj == null)
                {
                    artboardRectObj = rects[0]; // fallback
                }

                var bbox = artboardRectObj.Geometry.GetBoundingBox(true);
                if (!bbox.IsValid) continue;

                double minX = bbox.Min.X;
                double maxX = bbox.Max.X;
                double minY = bbox.Min.Y;
                double maxY = bbox.Max.Y;

                var shapes = new List<ShapeData>();

                foreach (var obj in allObjects)
                {
                    if (obj.Id == artboardRectObj.Id) continue;

                    var objBbox = obj.Geometry.GetBoundingBox(true);
                    if (!objBbox.IsValid) continue;

                    bool isAnnot = obj.Geometry is AnnotationBase;

                    if (isAnnot)
                    {
                        // Annotations use center-point containment check
                        var center = objBbox.Center;
                        bool inside = (center.X >= minX && center.X <= maxX &&
                                       center.Y >= minY && center.Y <= maxY);
                        if (inside)
                        {
                            var exploded = ExplodeAnnotation(obj, annotationGroup);
                            shapes.AddRange(exploded);
                        }
                    }
                    else
                    {
                        // Curves/hatches/pictures use full bounding box containment check
                        bool inside = (objBbox.Min.X >= minX && objBbox.Max.X <= maxX &&
                                       objBbox.Min.Y >= minY && objBbox.Max.Y <= maxY);
                        if (inside)
                        {
                            var objShapes = GetObjectExportData(obj, exportPictures, hatchExportMode);
                            if (objShapes != null)
                            {
                                shapes.AddRange(objShapes);
                            }
                        }
                    }
                }

                result.Add(new ExportGroup
                {
                    Artboard = subLayer.Name,
                    Curves = shapes
                });
            }

            return result;
        }

        public static List<ShapeData> GetObjectExportData(RhinoObject obj, bool exportPictures, string hatchExportMode)
        {
            var shapes = new List<ShapeData>();
            string objIdStr = obj.Id.ToString();
            string layerName = obj.Document.Layers[obj.Attributes.LayerIndex].FullPath;

            bool isPic = false;
            string? cachedImgPath = null;
            if (exportPictures && obj.ObjectType == ObjectType.Brep)
            {
                isPic = IsPictureFrame(obj, out cachedImgPath);
            }

            if (obj.ObjectType == ObjectType.Curve || obj.ObjectType == ObjectType.Hatch || isPic)
            {
                if (layerName.StartsWith("Artboards::"))
                {
                    layerName = layerName.Substring("Artboards::".Length);
                }
            }

            var doc = obj.Document;
            var color = obj.Attributes.DrawColor(doc);
            int[] colorRgb = new int[] { color.R, color.G, color.B };

            double widthVal = 1.0;
            if (obj.Attributes.PlotWeightSource == ObjectPlotWeightSource.PlotWeightFromObject)
            {
                widthVal = obj.Attributes.PlotWeight;
            }

            string linetypeV = "Continuous";
            if (obj.Attributes.LinetypeSource == ObjectLinetypeSource.LinetypeFromObject)
            {
                var lt = doc.Linetypes[obj.Attributes.LinetypeIndex];
                if (lt != null) linetypeV = lt.Name;
            }

            // 1. Text handling
            if (obj is TextObject textObj)
            {
                var textEntity = textObj.Geometry as TextEntity;
                if (textEntity != null)
                {
                    string textContent = textEntity.PlainText;
                    var pt = textEntity.Plane.Origin;
                    double height = textEntity.TextHeight;
                    string font = textEntity.Font.FamilyName;

                    string justification = "left";
                    var ha = textEntity.TextHorizontalAlignment;
                    if (ha == TextHorizontalAlignment.Center) justification = "center";
                    else if (ha == TextHorizontalAlignment.Right) justification = "right";

                    shapes.Add(new ShapeData
                    {
                        Id = objIdStr,
                        Layer = layerName,
                        Type = "text",
                        Text = textContent,
                        Point = new double[] { pt.X, -pt.Y },
                        Height = height,
                        Font = font,
                        Color = colorRgb,
                        Justification = justification
                    });
                }
                return shapes;
            }

            // 2. Picture handling
            if (isPic && cachedImgPath != null)
            {
                var bbox = obj.Geometry.GetBoundingBox(true);
                if (bbox.IsValid)
                {
                    double picLeft = bbox.Min.X;
                    double picRight = bbox.Max.X;
                    double picBottom = bbox.Min.Y;
                    double picTop = bbox.Max.Y;

                    shapes.Add(new ShapeData
                    {
                        Id = objIdStr,
                        Layer = layerName,
                        Type = "picture",
                        Left = picLeft,
                        Top = -picTop,
                        Width = picRight - picLeft,
                        Height = picTop - picBottom,
                        Image = cachedImgPath
                    });
                }
                return shapes;
            }

            // 3. Hatch handling
            if (obj is HatchObject hatchObj)
            {
                bool hatchAsSolid = (hatchExportMode == "solid");
                bool hatchExplode = (hatchExportMode == "explode");

                if (hatchAsSolid)
                {
                    var loops = GetHatchOuterBoundary(hatchObj);
                    for (int idx = 0; idx < loops.Count; idx++)
                    {
                        var loop = loops[idx];
                        if (loop.Count < 2) continue;
                        var mirrored = loop.ConvertAll(pt => new double[] { pt[0], -pt[1] });
                        shapes.Add(new ShapeData
                        {
                            Id = $"{objIdStr}_{idx}",
                            Layer = layerName,
                            Type = "hatch_solid",
                            Closed = true,
                            Points = mirrored,
                            Color = colorRgb,
                            FillColor = colorRgb,
                            Width = widthVal,
                            Linetype = linetypeV,
                            GroupId = objIdStr,
                            GroupName = "Hatch"
                        });
                    }
                    return shapes;
                }

                if (hatchExplode)
                {
                    bool isSolid = IsSolidHatch(hatchObj);
                    
                    if (isSolid)
                    {
                        var loops = GetHatchOuterBoundary(hatchObj);
                        for (int idx = 0; idx < loops.Count; idx++)
                        {
                            var loop = loops[idx];
                            if (loop.Count < 2) continue;
                            var mirrored = loop.ConvertAll(pt => new double[] { pt[0], -pt[1] });
                            shapes.Add(new ShapeData
                            {
                                Id = $"{objIdStr}_{idx}",
                                Layer = layerName,
                                Type = "hatch_solid",
                                Closed = true,
                                Points = mirrored,
                                Color = colorRgb,
                                FillColor = colorRgb,
                                Width = widthVal,
                                Linetype = linetypeV,
                                GroupId = objIdStr,
                                GroupName = "Hatch"
                            });
                        }
                    }
                    else
                    {
                        var explodedGeos = hatchObj.HatchGeometry.Explode();
                        if (explodedGeos != null)
                        {
                            int idx = 0;
                            foreach (var geo in explodedGeos)
                            {
                                if (geo is Curve crv)
                                {
                                    var pts = GetCurvePoints(crv);
                                    if (pts.Count >= 2)
                                    {
                                        var mirrored = pts.ConvertAll(pt => new double[] { pt[0], -pt[1] });
                                        shapes.Add(new ShapeData
                                        {
                                            Id = $"{objIdStr}_{idx}",
                                            Layer = layerName,
                                            Type = "polyline",
                                            Closed = crv.IsClosed,
                                            Points = mirrored,
                                            Color = colorRgb,
                                            Width = widthVal,
                                            Linetype = linetypeV,
                                            GroupId = objIdStr,
                                            GroupName = "Hatch"
                                        });
                                        idx++;
                                    }
                                }
                            }
                        }
                        
                        // If no lines were exploded, fallback to outer boundary (solid)
                        if (shapes.Count == 0)
                        {
                            var loops = GetHatchOuterBoundary(hatchObj);
                            for (int idx = 0; idx < loops.Count; idx++)
                            {
                                var loop = loops[idx];
                                if (loop.Count < 2) continue;
                                var mirrored = loop.ConvertAll(pt => new double[] { pt[0], -pt[1] });
                                shapes.Add(new ShapeData
                                {
                                    Id = $"{objIdStr}_fb_{idx}",
                                    Layer = layerName,
                                    Type = "hatch_solid",
                                    Closed = true,
                                    Points = mirrored,
                                    Color = colorRgb,
                                    FillColor = colorRgb,
                                    Width = widthVal,
                                    Linetype = linetypeV,
                                    GroupId = objIdStr,
                                    GroupName = "Hatch"
                                });
                            }
                        }
                    }
                    return shapes;
                }
            }

            // 4. Curve handling
            if (obj.Geometry is Curve curveObj)
            {
                string objType = "polyline";
                var ptsList = new List<double[]>();
                double? radiusVal = null;

                if (curveObj.TryGetCircle(out var circle))
                {
                    var center = circle.Center;
                    radiusVal = circle.Radius;
                    ptsList.Add(new double[] { center.X, center.Y });
                    ptsList.Add(new double[] { center.X + radiusVal.Value, center.Y });
                    objType = "circle";
                }
                else if (curveObj.TryGetEllipse(out var ellipse))
                {
                    var center = ellipse.Plane.Origin;
                    radiusVal = ellipse.Radius1;
                    ptsList.Add(new double[] { center.X, center.Y });
                    ptsList.Add(new double[] { center.X + radiusVal.Value, center.Y });
                    objType = "ellipse";
                }
                else if (curveObj.Degree > 1)
                {
                    int numPts = Math.Max(100, curveObj.SpanCount * 5);
                    var parameters = curveObj.DivideByCount(numPts, true);
                    if (parameters != null)
                    {
                        foreach (var t in parameters)
                        {
                            var pt = curveObj.PointAt(t);
                            ptsList.Add(new double[] { pt.X, pt.Y });
                        }
                    }
                    objType = "nurbs";
                }
                else
                {
                    if (curveObj.TryGetPolyline(out var polyline))
                    {
                        foreach (var pt in polyline)
                        {
                            ptsList.Add(new double[] { pt.X, pt.Y });
                        }
                    }
                    else
                    {
                        ptsList.Add(new double[] { curveObj.PointAtStart.X, curveObj.PointAtStart.Y });
                        ptsList.Add(new double[] { curveObj.PointAtEnd.X, curveObj.PointAtEnd.Y });
                    }
                    objType = "polyline";
                }

                var mirroredPts = ptsList.ConvertAll(pt => new double[] { pt[0], -pt[1] });
                var shape = new ShapeData
                {
                    Id = objIdStr,
                    Layer = layerName,
                    Type = objType,
                    Closed = curveObj.IsClosed,
                    Points = mirroredPts,
                    Color = colorRgb,
                    Width = widthVal,
                    Linetype = linetypeV
                };
                if (radiusVal != null)
                {
                    shape.Radius = radiusVal.Value;
                }
                shapes.Add(shape);
                return shapes;
            }

            return shapes;
        }

        private static bool IsPictureFrame(RhinoObject rhinoObj, out string? imagePath)
        {
            imagePath = null;
            if (rhinoObj == null) return false;

            if (_pictureCache != null && _pictureCache.TryGetValue(rhinoObj.Id, out var cached))
            {
                imagePath = cached.path;
                return cached.isPic;
            }

            bool result = false;
            if (rhinoObj.Geometry is Brep brep && brep.Faces.Count == 1)
            {
                int matIdx = rhinoObj.Attributes.MaterialIndex;
                if (matIdx >= 0)
                {
                    var mat = rhinoObj.Document.Materials[matIdx];
                    if (mat != null)
                    {
                        var tex = mat.GetBitmapTexture();
                        if (tex != null && !string.IsNullOrEmpty(tex.FileName))
                        {
                            imagePath = tex.FileName;
                            result = true;
                        }
                    }
                }
            }

            if (_pictureCache != null)
            {
                _pictureCache[rhinoObj.Id] = (result, imagePath);
            }

            return result;
        }

        private static bool IsSolidHatch(HatchObject hatchObj)
        {
            if (hatchObj == null) return false;
            int patternIdx = hatchObj.HatchGeometry.PatternIndex;
            var pattern = hatchObj.Document.HatchPatterns[patternIdx];
            if (pattern == null) return false;
            if (pattern.Name.Contains("solid", StringComparison.OrdinalIgnoreCase)) return true;
            if (pattern.FillType == HatchPatternFillType.Solid) return true;
            return false;
        }

        private static List<List<double[]>> GetHatchOuterBoundary(HatchObject hatchObj)
        {
            var loops = new List<List<double[]>>();
            if (hatchObj == null) return loops;
            var outerCurves = hatchObj.HatchGeometry.Get3dCurves(true);
            if (outerCurves == null) return loops;
            foreach (var crv in outerCurves)
            {
                var loop = GetCurvePoints(crv);
                if (loop.Count >= 2) loops.Add(loop);
            }
            return loops;
        }

        private static List<List<double[]>> GetHatchBoundaryLoops(HatchObject hatchObj)
        {
            var loops = new List<List<double[]>>();
            if (hatchObj == null) return loops;
            var curves = hatchObj.HatchGeometry.Get3dCurves(false);
            if (curves == null) return loops;
            foreach (var crv in curves)
            {
                var loop = GetCurvePoints(crv);
                if (loop.Count >= 2) loops.Add(loop);
            }
            return loops;
        }

        private static List<double[]> GetCurvePoints(Curve crv)
        {
            var pts = new List<double[]>();
            if (crv.TryGetPolyline(out var polyline))
            {
                foreach (var pt in polyline)
                {
                    pts.Add(new double[] { pt.X, pt.Y });
                }
            }
            else if (crv.IsLinear())
            {
                pts.Add(new double[] { crv.PointAtStart.X, crv.PointAtStart.Y });
                pts.Add(new double[] { crv.PointAtEnd.X, crv.PointAtEnd.Y });
            }
            else
            {
                int count = 64;
                var parameters = crv.DivideByCount(count, true);
                if (parameters != null)
                {
                    foreach (var t in parameters)
                    {
                        var pt = crv.PointAt(t);
                        pts.Add(new double[] { pt.X, pt.Y });
                    }
                }
            }
            return pts;
        }

        private static List<ShapeData> ExplodeAnnotation(RhinoObject annotObj, bool annotationGroup)
        {
            var results = new List<ShapeData>();
            if (annotObj == null) return results;

            var annotGeo = annotObj.Geometry as AnnotationBase;
            if (annotGeo == null) return results;

            var doc = annotObj.Document;
            var dimStyle = doc.DimStyles.FindId(annotGeo.DimensionStyleId) ?? doc.DimStyles.Current;

            GeometryBase[]? exploded = null;
            try
            {
                if (annotGeo is Dimension dim)
                {
                    dim.UpdateDimensionText(dimStyle, doc.ModelUnitSystem);
                    exploded = dim.Explode();
                }
            }
            catch
            {
                // Fall through
            }

            string parentLayer = annotObj.Attributes.LayerIndex >= 0 ? doc.Layers[annotObj.Attributes.LayerIndex].FullPath : "";
            if (parentLayer.StartsWith("Artboards::"))
            {
                parentLayer = parentLayer.Substring("Artboards::".Length);
            }

            var color = annotObj.Attributes.DrawColor(doc);
            int[] colorRgb = new int[] { color.R, color.G, color.B };
            string objId = annotObj.Id.ToString();

            if (exploded != null && exploded.Length > 0)
            {
                var finalGeos = FlattenAnnotationGeos(exploded, doc);
                int idx = 0;
                foreach (var eg in finalGeos)
                {
                    var shape = AnnotationGeoToShape(eg, objId, idx, parentLayer, colorRgb, annotationGroup, dimStyle, doc);
                    if (shape != null)
                    {
                        results.Add(shape);
                        idx++;
                    }
                }
            }

            // Fallback 1: Run Explode command on copy
            if (results.Count == 0)
            {
                results = ExplodeAnnotationCmd(annotObj, parentLayer, colorRgb, objId, annotationGroup);
            }

            // Fallback 2: Direct extraction
            if (results.Count == 0)
            {
                results = AnnotationDirectExtract(annotObj, parentLayer, colorRgb, objId, annotationGroup, dimStyle);
            }

            return results;
        }

        private static List<GeometryBase> FlattenAnnotationGeos(IEnumerable<GeometryBase> geos, RhinoDoc doc, int depth = 0)
        {
            var result = new List<GeometryBase>();
            if (depth > 3)
            {
                result.AddRange(geos);
                return result;
            }

            foreach (var g in geos)
            {
                if (g is AnnotationBase subAnnot && g is not TextEntity)
                {
                    var subStyle = doc.DimStyles.FindId(subAnnot.DimensionStyleId) ?? doc.DimStyles.Current;
                    try
                    {
                        if (subAnnot is Dimension subDim)
                        {
                            subDim.UpdateDimensionText(subStyle, doc.ModelUnitSystem);
                            var subExploded = subDim.Explode();
                            if (subExploded != null && subExploded.Length > 0)
                            {
                                result.AddRange(FlattenAnnotationGeos(subExploded, doc, depth + 1));
                                continue;
                            }
                        }
                    }
                    catch
                    {
                        // Fall through
                    }
                }
                result.Add(g);
            }
            return result;
        }

        private static ShapeData? AnnotationGeoToShape(GeometryBase geo, string objId, int idx, string parentLayer, int[] colorRgb, bool annotationGroup, DimensionStyle dimStyle, RhinoDoc doc)
        {
            if (geo is TextEntity textEntity)
            {
                string text = textEntity.PlainText;
                if (string.IsNullOrEmpty(text)) text = textEntity.RichText;
                if (string.IsNullOrEmpty(text)) return null;

                var pt = textEntity.Plane.Origin;
                double height = textEntity.TextHeight;
                string fontName = textEntity.Font?.FamilyName ?? "";

                string justification = "center";
                var ha = textEntity.TextHorizontalAlignment;
                if (ha == TextHorizontalAlignment.Left) justification = "left";
                else if (ha == TextHorizontalAlignment.Right) justification = "right";

                var shape = new ShapeData
                {
                    Id = $"{objId}_{idx}_text",
                    Layer = parentLayer,
                    Type = "text",
                    Text = text,
                    Point = new double[] { pt.X, -pt.Y },
                    Height = height,
                    Font = fontName,
                    Color = colorRgb,
                    Justification = justification
                };
                if (annotationGroup)
                {
                    shape.GroupId = objId;
                    shape.GroupName = "Annotation";
                }
                return shape;
            }

            if (geo is Curve curve)
            {
                var pts = new List<double[]>();
                if (curve.TryGetPolyline(out var polyline))
                {
                    foreach (var p in polyline) pts.Add(new double[] { p.X, -p.Y });
                }
                else if (curve.IsLinear())
                {
                    pts.Add(new double[] { curve.PointAtStart.X, -curve.PointAtStart.Y });
                    pts.Add(new double[] { curve.PointAtEnd.X, -curve.PointAtEnd.Y });
                }
                else
                {
                    var parameters = curve.DivideByCount(32, true);
                    if (parameters != null)
                    {
                        foreach (var t in parameters)
                        {
                            var p = curve.PointAt(t);
                            pts.Add(new double[] { p.X, -p.Y });
                        }
                    }
                }

                if (pts.Count >= 2)
                {
                    var shape = new ShapeData
                    {
                        Id = $"{objId}_{idx}_crv",
                        Layer = parentLayer,
                        Type = "polyline",
                        Closed = curve.IsClosed,
                        Points = pts,
                        Color = colorRgb,
                        Width = 1.0,
                        Linetype = "Continuous"
                    };
                    if (annotationGroup)
                    {
                        shape.GroupId = objId;
                        shape.GroupName = "Annotation";
                    }
                    return shape;
                }
            }

            return null;
        }

        private static List<ShapeData> ExplodeAnnotationCmd(RhinoObject annotObj, string parentLayer, int[] colorRgb, string objId, bool annotationGroup)
        {
            var results = new List<ShapeData>();
            var doc = annotObj.Document;

            bool oldRedraw = doc.Views.RedrawEnabled;
            doc.Views.RedrawEnabled = false;

            try
            {
                var dup = annotObj.DuplicateGeometry();
                if (dup == null) return results;

                Guid dupId = doc.Objects.Add(dup, annotObj.Attributes);
                if (dupId == Guid.Empty) return results;

                var selectedBefore = doc.Objects.GetSelectedObjects(false, false);
                doc.Objects.UnselectAll();

                doc.Objects.Select(dupId);
                RhinoApp.RunScript("_Explode", false);

                var explodedParts = doc.Objects.GetSelectedObjects(false, false);
                doc.Objects.UnselectAll();

                foreach (var part in explodedParts)
                {
                    var shapes = GetObjectExportData(part, false, "solid");
                    if (shapes != null)
                    {
                        foreach (var s in shapes)
                        {
                            s.Layer = parentLayer;
                            if (annotationGroup)
                            {
                                s.GroupId = objId;
                                s.GroupName = "Annotation";
                            }
                            else
                            {
                                s.GroupId = null;
                                s.GroupName = null;
                            }
                            results.Add(s);
                        }
                    }
                    doc.Objects.Delete(part.Id, true);
                }

                doc.Objects.Delete(dupId, true);

                foreach (var sel in selectedBefore)
                {
                    doc.Objects.Select(sel.Id);
                }
            }
            catch
            {
                // Ignore
            }
            finally
            {
                doc.Views.RedrawEnabled = oldRedraw;
            }

            return results;
        }

        private static List<ShapeData> AnnotationDirectExtract(RhinoObject annotObj, string parentLayer, int[] colorRgb, string objId, bool annotationGroup, DimensionStyle dimStyle)
        {
            var results = new List<ShapeData>();
            var annotGeo = annotObj.Geometry as AnnotationBase;
            if (annotGeo == null) return results;

            string text = annotGeo.PlainText;
            if (string.IsNullOrEmpty(text)) text = annotGeo.RichText;
            if (string.IsNullOrEmpty(text)) return results;

            double textHeight = annotGeo.TextHeight;
            string fontName = annotGeo.Font?.FamilyName ?? "";

            var bbox = annotObj.Geometry.GetBoundingBox(true);
            if (bbox.IsValid)
            {
                var center = bbox.Center;
                var shape = new ShapeData
                {
                    Id = objId + "_text",
                    Layer = parentLayer,
                    Type = "text",
                    Text = text,
                    Point = new double[] { center.X, -center.Y },
                    Height = textHeight,
                    Font = fontName,
                    Color = colorRgb,
                    Justification = "center"
                };
                if (annotationGroup)
                {
                    shape.GroupId = objId;
                    shape.GroupName = "Annotation";
                }
                results.Add(shape);
            }

            return results;
        }
    }
}
