using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace RhinoIllustratorSync.Core
{
    public class ArtboardData
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("width_mm")]
        public double WidthMm { get; set; }

        [JsonPropertyName("height_mm")]
        public double HeightMm { get; set; }

        [JsonPropertyName("left_mm")]
        public double LeftMm { get; set; }

        [JsonPropertyName("top_mm")]
        public double TopMm { get; set; }

        [JsonPropertyName("right_mm")]
        public double RightMm { get; set; }

        [JsonPropertyName("bottom_mm")]
        public double BottomMm { get; set; }
    }

    public class ShapeData
    {
        [JsonPropertyName("id")]
        public string Id { get; set; } = string.Empty;

        [JsonPropertyName("layer")]
        public string Layer { get; set; } = string.Empty;

        [JsonPropertyName("type")]
        public string Type { get; set; } = string.Empty;

        [JsonPropertyName("text")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? Text { get; set; }

        [JsonPropertyName("point")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public double[]? Point { get; set; }

        [JsonPropertyName("height")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public double? Height { get; set; }

        [JsonPropertyName("font")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? Font { get; set; }

        [JsonPropertyName("color")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public int[]? Color { get; set; }

        [JsonPropertyName("justification")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? Justification { get; set; }

        [JsonPropertyName("closed")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public bool? Closed { get; set; }

        [JsonPropertyName("points")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public List<double[]>? Points { get; set; }

        [JsonPropertyName("width")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public double? Width { get; set; }

        [JsonPropertyName("linetype")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? Linetype { get; set; }

        [JsonPropertyName("radius")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public double? Radius { get; set; }

        [JsonPropertyName("image")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? Image { get; set; }

        [JsonPropertyName("left")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public double? Left { get; set; }

        [JsonPropertyName("top")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public double? Top { get; set; }

        [JsonPropertyName("group_id")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? GroupId { get; set; }

        [JsonPropertyName("group_name")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public string? GroupName { get; set; }

        [JsonPropertyName("fill_color")]
        [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        public int[]? FillColor { get; set; }
    }

    public class ExportGroup
    {
        [JsonPropertyName("artboard")]
        public string Artboard { get; set; } = string.Empty;

        [JsonPropertyName("curves")]
        public List<ShapeData> Curves { get; set; } = new List<ShapeData>();
    }
}
