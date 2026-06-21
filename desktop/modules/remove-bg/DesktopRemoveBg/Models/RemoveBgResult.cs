namespace TTTools.RemoveBg.Models;

/// <summary>
/// 抠图模型信息
/// 用于在 UI 中展示可选模型的名称和描述。
/// </summary>
public class RemoveBgModelInfo
{
    /// <summary>模型名称，如 "u2net"、"u2netp"</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>模型描述（中文），如 "默认模型，质量最佳，约 168 MB"</summary>
    public string Description { get; set; } = string.Empty;

    /// <summary>是否为默认模型</summary>
    public bool IsDefault { get; set; }

    /// <summary>UI 展示文本</summary>
    public string DisplayText => IsDefault
        ? $"{Name}（默认）- {Description}"
        : $"{Name} - {Description}";

    /// <summary>
    /// 从 Python router 返回的 JSON 反序列化
    /// </summary>
    public static RemoveBgModelInfo FromJsonElement(JsonElement element, string defaultModel = "")
    {
        var name = element.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
        return new RemoveBgModelInfo
        {
            Name = name,
            Description = element.TryGetProperty("description", out var d) ? d.GetString() ?? "" : "",
            IsDefault = name == defaultModel,
        };
    }
}

/// <summary>
/// 智能抠图处理结果模型
/// 单张图片的完整抠图处理结果，包含输出路径、图像尺寸、模型和元信息。
/// 从 local-worker remove-bg 引擎返回的 JSON 反序列化得到。
/// </summary>
public class RemoveBgResult
{
    /// <summary>输出文件路径</summary>
    public string OutputPath { get; set; } = string.Empty;

    /// <summary>输入文件路径</summary>
    public string InputPath { get; set; } = string.Empty;

    /// <summary>输出图像像素宽度</summary>
    public int OutputWidth { get; set; }

    /// <summary>输出图像像素高度</summary>
    public int OutputHeight { get; set; }

    /// <summary>输入图像像素宽度</summary>
    public int InputWidth { get; set; }

    /// <summary>输入图像像素高度</summary>
    public int InputHeight { get; set; }

    /// <summary>使用的模型名称</summary>
    public string Model { get; set; } = string.Empty;

    /// <summary>是否启用了 Alpha Matting 精细化边缘</summary>
    public bool AlphaMatting { get; set; }

    /// <summary>是否输出 RGBA 格式</summary>
    public bool OutputRgba { get; set; }

    /// <summary>合成的纯色背景 RGB（null 表示不合成）</summary>
    public List<int>? CompositeColor { get; set; }

    /// <summary>是否包含 Alpha 遮罩</summary>
    public bool HasAlphaMask { get; set; }

    /// <summary>前景占比（0.0 ~ 1.0），用于 UI 预览展示</summary>
    public double? ForegroundRatio { get; set; }

    /// <summary>处理是否成功</summary>
    public bool IsSuccess { get; set; } = true;

    /// <summary>错误消息</summary>
    public string? ErrorMessage { get; set; }

    /// <summary>处理元信息（模型、alpha_matting 等）</summary>
    public Dictionary<string, object>? Metadata { get; set; }

    /// <summary>源文件名（用于显示）</summary>
    public string InputFileName => string.IsNullOrEmpty(InputPath)
        ? "未知文件"
        : Path.GetFileName(InputPath);

    /// <summary>输出文件名（用于显示）</summary>
    public string OutputFileName => string.IsNullOrEmpty(OutputPath)
        ? "未知文件"
        : Path.GetFileName(OutputPath);

    /// <summary>像素尺寸摘要（用于 UI 展示）</summary>
    public string SizeSummary =>
        InputWidth > 0 && InputHeight > 0
            ? $"{InputWidth}×{InputHeight} → {OutputWidth}×{OutputHeight}"
            : $"{OutputWidth}×{OutputHeight}";

    /// <summary>输入尺寸摘要</summary>
    public string InputSizeSummary =>
        InputWidth > 0 && InputHeight > 0
            ? $"{InputWidth}×{InputHeight}"
            : "未知";

    /// <summary>输出尺寸摘要</summary>
    public string OutputSizeSummary => $"{OutputWidth}×{OutputHeight} px";

    /// <summary>模型名称显示（含 Alpha Matting 标记）</summary>
    public string ModelSummary =>
        AlphaMatting ? $"{Model} (Alpha Matting)" : Model;

    /// <summary>输出格式说明</summary>
    public string OutputFormatSummary => OutputRgba ? "透明 PNG (RGBA)" : "不透明 JPG/合成";

    /// <summary>前景占比摘要（百分比）</summary>
    public string ForegroundRatioSummary =>
        ForegroundRatio.HasValue
            ? $"{ForegroundRatio.Value * 100:F1}%"
            : "N/A";

    /// <summary>
    /// 从 Python router 返回的原始 JSON 数据反序列化
    /// </summary>
    /// <param name="data">Worker 返回的 data JSON 元素</param>
    /// <param name="inputPath">输入文件路径</param>
    /// <returns>反序列化的结果对象</returns>
    public static RemoveBgResult FromRouterResponse(JsonElement data, string? inputPath = null)
    {
        var result = new RemoveBgResult
        {
            OutputPath = data.TryGetProperty("output_path", out var op) ? op.GetString() ?? "" : "",
            InputPath = inputPath ?? (data.TryGetProperty("input_path", out var ip) ? ip.GetString() ?? "" : ""),
            OutputWidth = data.TryGetProperty("output_width", out var ow) ? ow.GetInt32() : 0,
            OutputHeight = data.TryGetProperty("output_height", out var oh) ? oh.GetInt32() : 0,
            InputWidth = data.TryGetProperty("input_width", out var iw) ? iw.GetInt32() : 0,
            InputHeight = data.TryGetProperty("input_height", out var ih) ? ih.GetInt32() : 0,
            Model = data.TryGetProperty("model", out var m) ? m.GetString() ?? "" : "",
            AlphaMatting = data.TryGetProperty("alpha_matting", out var am) && am.GetBoolean(),
            OutputRgba = data.TryGetProperty("output_rgba", out var or) && or.GetBoolean(),
            HasAlphaMask = data.TryGetProperty("has_alpha_mask", out var hm) && hm.GetBoolean(),
        };

        // 解析前景占比
        if (data.TryGetProperty("foreground_ratio", out var fr) && fr.ValueKind != JsonValueKind.Null)
            result.ForegroundRatio = fr.GetDouble();

        // 解析合成颜色
        if (data.TryGetProperty("composite_color", out var cc) && cc.ValueKind == JsonValueKind.Array)
        {
            result.CompositeColor = new List<int>();
            foreach (var v in cc.EnumerateArray())
                result.CompositeColor.Add(v.GetInt32());
        }

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
