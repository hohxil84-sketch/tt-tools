namespace TTTools.IdPhoto.Models;

/// <summary>
/// 证件照规格显示模型
/// 用于在 UI 中展示可选规格的详细信息。
/// </summary>
public class PhotoSpecItem
{
    /// <summary>规格名称（中文），如 "1寸"、"2寸"</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>物理宽度（毫米）</summary>
    public int WidthMm { get; set; }

    /// <summary>物理高度（毫米）</summary>
    public int HeightMm { get; set; }

    /// <summary>像素宽度（基于 DPI）</summary>
    public int WidthPx { get; set; }

    /// <summary>像素高度（基于 DPI）</summary>
    public int HeightPx { get; set; }

    /// <summary>目标 DPI</summary>
    public int Dpi { get; set; } = 300;

    /// <summary>规格描述（用于 UI 展示）</summary>
    public string DisplayText => $"{Name} ({WidthMm}×{HeightMm}mm, {WidthPx}×{HeightPx}px)";

    /// <summary>物理尺寸摘要</summary>
    public string SizeMmText => $"{WidthMm} × {HeightMm} mm";

    /// <summary>像素尺寸摘要</summary>
    public string SizePxText => $"{WidthPx} × {HeightPx} px";

    /// <summary>
    /// 从 Python router 返回的 JSON 反序列化
    /// </summary>
    public static PhotoSpecItem FromJsonElement(JsonElement element)
    {
        return new PhotoSpecItem
        {
            Name = element.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "",
            WidthMm = element.TryGetProperty("width_mm", out var wm) ? wm.GetInt32() : 0,
            HeightMm = element.TryGetProperty("height_mm", out var hm) ? hm.GetInt32() : 0,
            WidthPx = element.TryGetProperty("width_px", out var wp) ? wp.GetInt32() : 0,
            HeightPx = element.TryGetProperty("height_px", out var hp) ? hp.GetInt32() : 0,
            Dpi = element.TryGetProperty("dpi", out var d) ? d.GetInt32() : 300,
        };
    }
}

/// <summary>
/// 背景色显示模型
/// 用于在 UI 中展示可选背景色及其颜色预览。
/// </summary>
public class BackgroundColorItem
{
    /// <summary>颜色名称（中文），如 "白色"、"红色"、"蓝色"</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>颜色标识键，如 "white"、"red"、"blue"</summary>
    public string Key { get; set; } = string.Empty;

    /// <summary>红色分量 (0-255)</summary>
    public int R { get; set; }

    /// <summary>绿色分量 (0-255)</summary>
    public int G { get; set; }

    /// <summary>蓝色分量 (0-255)</summary>
    public int B { get; set; }

    /// <summary>十六进制颜色字符串，如 "#FF0000"</summary>
    public string Hex { get; set; } = "#FFFFFF";

    /// <summary>BGR 分量列表 [B, G, R]</summary>
    public List<int> Bgr { get; set; } = new();

    /// <summary>颜色名称 + 色值展示文本</summary>
    public string DisplayText => $"{Name} ({Hex})";

    /// <summary>
    /// 从 Python router 返回的 JSON 反序列化
    /// </summary>
    /// <param name="element">JSON 元素</param>
    /// <param name="key">颜色标识键（从字典 key 传入）</param>
    public static BackgroundColorItem FromJsonElement(JsonElement element, string key = "")
    {
        var name = element.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
        // 如果 key 为空，尝试用中文名匹配 key
        if (string.IsNullOrEmpty(key))
            key = name;

        var bgr = new List<int>();
        if (element.TryGetProperty("bgr", out var bgrArray) && bgrArray.ValueKind == JsonValueKind.Array)
        {
            foreach (var v in bgrArray.EnumerateArray())
                bgr.Add(v.GetInt32());
        }

        return new BackgroundColorItem
        {
            Name = name,
            Key = key,
            R = element.TryGetProperty("r", out var r) ? r.GetInt32() : 255,
            G = element.TryGetProperty("g", out var g) ? g.GetInt32() : 255,
            B = element.TryGetProperty("b", out var b) ? b.GetInt32() : 255,
            Hex = element.TryGetProperty("hex", out var h) ? h.GetString() ?? "#FFFFFF" : "#FFFFFF",
            Bgr = bgr,
        };
    }

    /// <summary>
    /// 获取 WPF 可用的 System.Windows.Media.Color
    /// </summary>
    public System.Windows.Media.Color ToMediaColor() =>
        System.Windows.Media.Color.FromRgb((byte)R, (byte)G, (byte)B);

    /// <summary>
    /// 获取 WPF 可用的 SolidColorBrush
    /// </summary>
    public System.Windows.Media.SolidColorBrush ToBrush() =>
        new(ToMediaColor());
}

/// <summary>
/// 证件照换底色处理结果模型
/// 单张图片的完整处理结果，包含输出路径、尺寸、规格和底色信息。
/// 从 local-worker id-photo 引擎返回的 JSON 反序列化得到。
/// </summary>
public class IdPhotoResult
{
    /// <summary>输出文件路径</summary>
    public string OutputPath { get; set; } = string.Empty;

    /// <summary>输入文件路径</summary>
    public string InputPath { get; set; } = string.Empty;

    /// <summary>输出图像像素宽度</summary>
    public int WidthPx { get; set; }

    /// <summary>输出图像像素高度</summary>
    public int HeightPx { get; set; }

    /// <summary>使用的证件照规格</summary>
    public PhotoSpecItem? Spec { get; set; }

    /// <summary>目标背景色</summary>
    public BackgroundColorItem? BackgroundColor { get; set; }

    /// <summary>检测到的原始背景色（可能为 null）</summary>
    public BackgroundColorItem? DetectedBackground { get; set; }

    /// <summary>处理是否成功</summary>
    public bool IsSuccess { get; set; } = true;

    /// <summary>错误消息</summary>
    public string? ErrorMessage { get; set; }

    /// <summary>处理元信息（遮罩方法、是否纯色背景等）</summary>
    public Dictionary<string, object>? Metadata { get; set; }

    /// <summary>源文件名（用于显示）</summary>
    public string InputFileName => string.IsNullOrEmpty(InputPath)
        ? "未知文件"
        : Path.GetFileName(InputPath);

    /// <summary>像素尺寸摘要（用于 UI 展示）</summary>
    public string SizeSummary => $"{WidthPx} × {HeightPx} px";

    /// <summary>规格摘要（用于 UI 展示）</summary>
    public string SpecSummary => Spec?.DisplayText ?? "未指定";

    /// <summary>底色摘要（用于 UI 展示）</summary>
    public string BackgroundSummary => BackgroundColor?.DisplayText ?? "未指定";

    /// <summary>遮罩方法摘要（用于 UI 展示）</summary>
    public string MaskMethodSummary
    {
        get
        {
            if (Metadata == null) return "未知";
            if (Metadata.TryGetValue("mask_method", out var method))
                return method?.ToString() == "color_distance" ? "颜色距离法" : "GrabCut 分割";
            return "未知";
        }
    }

    /// <summary>
    /// 从 Python router 返回的原始 JSON 数据反序列化
    /// </summary>
    /// <param name="data">Worker 返回的 data JSON 元素</param>
    /// <returns>反序列化的结果对象</returns>
    public static IdPhotoResult FromRouterResponse(JsonElement data)
    {
        var result = new IdPhotoResult
        {
            OutputPath = data.TryGetProperty("output_path", out var op) ? op.GetString() ?? "" : "",
            InputPath = data.TryGetProperty("input_path", out var ip) ? ip.GetString() ?? "" : "",
            WidthPx = data.TryGetProperty("width_px", out var wp) ? wp.GetInt32() : 0,
            HeightPx = data.TryGetProperty("height_px", out var hp) ? hp.GetInt32() : 0,
        };

        // 解析规格
        if (data.TryGetProperty("spec", out var spec) && spec.ValueKind == JsonValueKind.Object)
            result.Spec = PhotoSpecItem.FromJsonElement(spec);

        // 解析目标背景色
        if (data.TryGetProperty("background_color", out var bg) && bg.ValueKind == JsonValueKind.Object)
            result.BackgroundColor = BackgroundColorItem.FromJsonElement(bg);

        // 解析检测到的背景色
        if (data.TryGetProperty("detected_background", out var dbg) &&
            dbg.ValueKind == JsonValueKind.Object)
            result.DetectedBackground = BackgroundColorItem.FromJsonElement(dbg);

        // 解析元数据
        if (data.TryGetProperty("metadata", out var meta) && meta.ValueKind == JsonValueKind.Object)
        {
            result.Metadata = new Dictionary<string, object>();
            foreach (var prop in meta.EnumerateObject())
            {
                result.Metadata[prop.Name] = prop.Value.ValueKind switch
                {
                    JsonValueKind.String => (object)(prop.Value.GetString() ?? ""),
                    JsonValueKind.Number => prop.Value.GetDouble(),
                    JsonValueKind.True => true,
                    JsonValueKind.False => false,
                    _ => prop.Value.ToString()
                };
            }
        }

        return result;
    }
}
