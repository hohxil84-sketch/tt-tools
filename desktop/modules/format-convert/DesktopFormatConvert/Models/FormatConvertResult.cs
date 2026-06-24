using System.Text.Json;

namespace TTTools.FormatConvert.Models;

/// <summary>
/// 格式转换处理结果模型
/// 包含源图信息、输出尺寸、输出格式、压缩比、元数据。
/// 从 Python worker 返回的 JSON data 中反序列化构建。
/// 格式转换是本地免费功能，不含套餐权限信息。
/// </summary>
public class FormatConvertResult
{
    // === 来源信息 ===

    /// <summary>输入文件路径</summary>
    public string InputPath { get; set; } = string.Empty;

    /// <summary>输出文件路径</summary>
    public string OutputPath { get; set; } = string.Empty;

    /// <summary>输入文件名</summary>
    public string InputFileName =>
        string.IsNullOrEmpty(InputPath) ? "未知文件" : Path.GetFileName(InputPath);

    /// <summary>输出文件名</summary>
    public string OutputFileName =>
        string.IsNullOrEmpty(OutputPath) ? "未知文件" : Path.GetFileName(OutputPath);

    // === 尺寸信息 ===

    /// <summary>原图宽度（像素）</summary>
    public int SourceWidth { get; set; }

    /// <summary>原图高度（像素）</summary>
    public int SourceHeight { get; set; }

    /// <summary>输出宽度（像素）</summary>
    public int OutputWidth { get; set; }

    /// <summary>输出高度（像素）</summary>
    public int OutputHeight { get; set; }

    // === 输出信息 ===

    /// <summary>输出格式（如 "png"、"jpeg"）</summary>
    public string OutputFormat { get; set; } = string.Empty;

    /// <summary>输出文件字节大小</summary>
    public long OutputSize { get; set; }

    /// <summary>压缩比（输出大小 / 输入大小），仅压缩操作有意义</summary>
    public double CompressionRatio { get; set; } = 1.0;

    // === 处理元信息 ===

    /// <summary>非致命警告信息列表</summary>
    public List<string> Warnings { get; set; } = new();

    /// <summary>处理耗时（毫秒）</summary>
    public double ElapsedMs { get; set; }

    // === 操作类型 ===

    /// <summary>本次执行的操作类型: convert_format / compress / crop / rotate</summary>
    public string OperationType { get; set; } = string.Empty;

    // === 状态 ===

    /// <summary>处理是否成功</summary>
    public bool IsSuccess { get; set; } = true;

    /// <summary>错误消息（失败时）</summary>
    public string? ErrorMessage { get; set; }

    // === UI 辅助显示属性 ===

    /// <summary>源图尺寸摘要 "800 x 600 px"</summary>
    public string SourceSizeSummary =>
        SourceWidth > 0 && SourceHeight > 0
            ? $"{SourceWidth} x {SourceHeight} px"
            : "未知";

    /// <summary>输出尺寸摘要 "400 x 300 px"</summary>
    public string OutputSizeSummary =>
        OutputWidth > 0 && OutputHeight > 0
            ? $"{OutputWidth} x {OutputHeight} px"
            : "未知";

    /// <summary>尺寸变化摘要 "800x600 -> 400x300"</summary>
    public string SizeSummary =>
        $"{SourceSizeSummary} -> {OutputSizeSummary}";

    /// <summary>输出格式 + 文件大小 "PNG (12.3 KB)"</summary>
    public string OutputFormatSummary =>
        $"{OutputFormat.ToUpperInvariant()} ({OutputSize / 1024.0:F1} KB)";

    /// <summary>压缩比可读显示 "45.2%" 或 "1.0x"</summary>
    public string CompressionRatioDisplay =>
        CompressionRatio == 1.0 ? "未压缩"
        : CompressionRatio < 1.0 ? $"压缩率: {CompressionRatio * 100:F1}%"
        : $"放大: {CompressionRatio:F1}x";

    /// <summary>处理耗时显示 "1234.5 ms"</summary>
    public string ElapsedDisplay => $"{ElapsedMs:F1} ms";

    /// <summary>是否有警告</summary>
    public bool HasWarnings => Warnings.Count > 0;

    /// <summary>是否有错误</summary>
    public bool HasError => !IsSuccess && !string.IsNullOrEmpty(ErrorMessage);

    /// <summary>
    /// 从 Python worker 返回的 JSON data 反序列化构建结果。
    /// 不含二进制 output_data——图片已通过文件保存，C# 侧读取文件路径即可。
    /// </summary>
    /// <param name="data">Python bridge 返回的 data 字段</param>
    /// <param name="inputPath">原始输入文件路径</param>
    /// <param name="operationType">操作类型: convert_format / compress / crop / rotate</param>
    /// <returns>构建好的 FormatConvertResult</returns>
    public static FormatConvertResult FromRouterResponse(JsonElement data, string inputPath, string operationType)
    {
        var result = new FormatConvertResult
        {
            InputPath = inputPath,
            OutputPath = data.TryGetProperty("output_path", out var op) ? op.GetString() ?? "" : "",
            SourceWidth = data.TryGetProperty("source_width", out var sw) ? sw.GetInt32() : 0,
            SourceHeight = data.TryGetProperty("source_height", out var sh) ? sh.GetInt32() : 0,
            OutputWidth = data.TryGetProperty("output_width", out var ow) ? ow.GetInt32() : 0,
            OutputHeight = data.TryGetProperty("output_height", out var oh) ? oh.GetInt32() : 0,
            OutputFormat = data.TryGetProperty("output_format", out var of) ? of.GetString() ?? "" : "",
            OutputSize = data.TryGetProperty("output_size", out var os) ? os.GetInt64() : 0,
            CompressionRatio = data.TryGetProperty("compression_ratio", out var cr) ? cr.GetDouble() : 1.0,
            ElapsedMs = data.TryGetProperty("elapsed_ms", out var em) ? em.GetDouble() : 0,
            OperationType = operationType,
            IsSuccess = true,
        };

        // Warnings
        if (data.TryGetProperty("warnings", out var warns) && warns.ValueKind == JsonValueKind.Array)
        {
            result.Warnings = warns.EnumerateArray()
                .Select(w => w.GetString() ?? "").ToList();
        }

        return result;
    }
}
