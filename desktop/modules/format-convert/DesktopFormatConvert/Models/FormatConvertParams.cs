using System.Text.Json.Serialization;

namespace TTTools.FormatConvert.Models;

/// <summary>
/// 格式转换参数（C# 侧，对应 Python FormatConvertParams dataclass）
/// 序列化时字段名保持 snake_case 以匹配 Python 侧 JSON 协议。
/// 格式转换是本地免费功能，无需套餐权限校验，不消耗云端 AI 额度。
/// </summary>
public class FormatConvertParams
{
    /// <summary>目标输出格式: original / png / jpeg / bmp / tiff / webp / gif / ico</summary>
    [JsonPropertyName("target_format")]
    public string TargetFormat { get; set; } = "original";

    /// <summary>JPEG/WEBP 输出质量（1-100），默认 85</summary>
    [JsonPropertyName("quality")]
    public int Quality { get; set; } = 85;

    /// <summary>PNG 压缩级别（0-9），默认 6</summary>
    [JsonPropertyName("png_compress")]
    public int PngCompress { get; set; } = 6;

    /// <summary>WEBP 输出质量（1-100），默认 85</summary>
    [JsonPropertyName("webp_quality")]
    public int WebpQuality { get; set; } = 85;

    /// <summary>是否保留透明通道</summary>
    [JsonPropertyName("preserve_alpha")]
    public bool PreserveAlpha { get; set; } = true;
}

/// <summary>
/// 压缩参数（C# 侧，对应 Python CompressParams dataclass）
/// </summary>
public class CompressParams
{
    /// <summary>输出质量（1-100），适用于 JPEG 和 WEBP 有损压缩，默认 75</summary>
    [JsonPropertyName("quality")]
    public int Quality { get; set; } = 75;

    /// <summary>压缩后的输出格式: original / png / jpeg / webp</summary>
    [JsonPropertyName("target_format")]
    public string TargetFormat { get; set; } = "original";

    /// <summary>PNG 压缩级别（0-9），默认 9（最高压缩）</summary>
    [JsonPropertyName("png_compress")]
    public int PngCompress { get; set; } = 9;

    /// <summary>目标最大文件大小（字节），仅 JPEG/WEBP 有效</summary>
    [JsonPropertyName("max_size_bytes")]
    public long? MaxSizeBytes { get; set; }
}

/// <summary>
/// 裁剪参数（C# 侧，对应 Python CropParams dataclass）
/// 支持两种模式：坐标裁剪（指定 left/top/width/height）和锚点裁剪（指定 width/height + anchor）
/// </summary>
public class CropParams
{
    /// <summary>裁剪左边界（像素），坐标模式使用</summary>
    [JsonPropertyName("left")]
    public int Left { get; set; }

    /// <summary>裁剪上边界（像素），坐标模式使用</summary>
    [JsonPropertyName("top")]
    public int Top { get; set; }

    /// <summary>裁剪宽度（像素）</summary>
    [JsonPropertyName("width")]
    public int Width { get; set; }

    /// <summary>裁剪高度（像素）</summary>
    [JsonPropertyName("height")]
    public int Height { get; set; }

    /// <summary>锚点对齐方式: center / top_left / top_right / bottom_left / bottom_right</summary>
    [JsonPropertyName("anchor")]
    public string? Anchor { get; set; }
}

/// <summary>
/// 旋转参数（C# 侧，对应 Python RotateParams dataclass）
/// </summary>
public class RotateParams
{
    /// <summary>旋转角度（正数为顺时针），支持 90/180/270 直角旋转和任意角度</summary>
    [JsonPropertyName("angle")]
    public double Angle { get; set; } = 90.0;

    /// <summary>是否扩展画布以容纳完整图像</summary>
    [JsonPropertyName("expand")]
    public bool Expand { get; set; } = true;

    /// <summary>空白区域填充颜色 R 分量（0-255），默认 255（白色）</summary>
    [JsonPropertyName("fillcolor_r")]
    public int FillColorR { get; set; } = 255;

    /// <summary>空白区域填充颜色 G 分量（0-255），默认 255（白色）</summary>
    [JsonPropertyName("fillcolor_g")]
    public int FillColorG { get; set; } = 255;

    /// <summary>空白区域填充颜色 B 分量（0-255），默认 255（白色）</summary>
    [JsonPropertyName("fillcolor_b")]
    public int FillColorB { get; set; } = 255;
}
