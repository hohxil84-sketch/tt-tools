using System.Text.Json;

namespace TTTools.ResizeImage.Models;

/// <summary>
/// 预设尺寸信息（从 Python worker list_presets 获取，用于 UI 下拉展示）
/// </summary>
public class PresetInfo
{
    /// <summary>预设键名，如 "id_1inch"、"print_a4_300dpi"</summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>预设目标宽度（像素）</summary>
    public int Width { get; set; }

    /// <summary>预设目标高度（像素）</summary>
    public int Height { get; set; }

    /// <summary>中文描述，如 "一寸证件照 (25x35mm @300DPI)"</summary>
    public string Description { get; set; } = string.Empty;

    /// <summary>UI 展示文本 "一寸证件照 (25x35mm @300DPI) (295x413)"</summary>
    public string DisplayText =>
        $"{Description} ({Width}x{Height})";

    /// <summary>
    /// 从 Python worker 返回的 JSON 元素反序列化构建 PresetInfo。
    /// </summary>
    public static PresetInfo FromJsonElement(JsonElement element)
    {
        return new PresetInfo
        {
            Name = element.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "",
            Width = element.TryGetProperty("width", out var w) ? w.GetInt32() : 0,
            Height = element.TryGetProperty("height", out var h) ? h.GetInt32() : 0,
            Description = element.TryGetProperty("description", out var d) ? d.GetString() ?? "" : "",
        };
    }
}
