using System.Text.Json.Serialization;

namespace TTTools.ResizeImage.Models;

/// <summary>
/// 图片改尺寸参数（C# 侧，对应 Python ResizeParams dataclass）
/// 序列化时字段名保持 camelCase 以匹配 Python 侧 JSON 协议。
/// 桌面端不决定套装权限、额度扣费和模型选择。
/// </summary>
public class ResizeImageParams
{
    /// <summary>改尺寸模式: fit / exact / fill / scale / short_side / long_side / custom_dpi</summary>
    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "fit";

    /// <summary>目标宽度（像素），EXACT/FIT/FILL 模式使用</summary>
    [JsonPropertyName("width")]
    public int? Width { get; set; }

    /// <summary>目标高度（像素），EXACT/FIT/FILL 模式使用</summary>
    [JsonPropertyName("height")]
    public int? Height { get; set; }

    /// <summary>缩放百分比，SCALE 模式使用，100 表示原大</summary>
    [JsonPropertyName("scale_percent")]
    public double ScalePercent { get; set; } = 100.0;

    /// <summary>短边目标像素，SHORT_SIDE 模式使用</summary>
    [JsonPropertyName("short_side")]
    public int? ShortSide { get; set; }

    /// <summary>长边目标像素，LONG_SIDE 模式使用</summary>
    [JsonPropertyName("long_side")]
    public int? LongSide { get; set; }

    /// <summary>目标 DPI，CUSTOM_DPI 模式使用</summary>
    [JsonPropertyName("target_dpi")]
    public int? TargetDpi { get; set; }

    /// <summary>重采样滤镜: lanczos / bilinear / bicubic / nearest / box / hamming</summary>
    [JsonPropertyName("resample")]
    public string Resample { get; set; } = "lanczos";

    /// <summary>是否保持宽高比（EXACT 模式设为 true 会退化为 FIT）</summary>
    [JsonPropertyName("keep_aspect")]
    public bool KeepAspect { get; set; } = true;

    /// <summary>输出格式: original / png / jpeg / bmp / tiff / webp</summary>
    [JsonPropertyName("output_format")]
    public string OutputFormat { get; set; } = "original";

    /// <summary>JPEG 输出质量（1-100），默认 92</summary>
    [JsonPropertyName("jpeg_quality")]
    public int JpegQuality { get; set; } = 92;

    /// <summary>PNG 压缩级别（0-9），默认 6</summary>
    [JsonPropertyName("png_compress_level")]
    public int PngCompressLevel { get; set; } = 6;

    /// <summary>WEBP 输出质量（1-100），默认 85</summary>
    [JsonPropertyName("webp_quality")]
    public int WebpQuality { get; set; } = 85;

    /// <summary>自定义输出 DPI X 分量，null 表示保持原图 DPI</summary>
    [JsonPropertyName("dpi")]
    public List<double>? Dpi { get; set; }

    /// <summary>预设名称（如 "id_1inch"），不为空时优先于 mode + 尺寸参数</summary>
    [JsonPropertyName("preset")]
    public string? Preset { get; set; }
}
