using System.Text.Json;

namespace TTTools.ResizeImage.Models;

/// <summary>
/// 改尺寸处理结果模型
/// 包含源泉信息、输出尺寸、缩放比例、元数据和套装权限信息。
/// 从 Python worker 返回的 JSON 和云端的套餐权限检查结果中反序列化构建。
/// </summary>
public class ResizeImageResult
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

    // === 处理参数 ===

    /// <summary>使用的缩放模式</summary>
    public string Mode { get; set; } = string.Empty;

    /// <summary>实际缩放比例（输出宽 / 原图宽）</summary>
    public double ScaleRatio { get; set; } = 1.0;

    /// <summary>输出格式（如 "png", "jpeg"）</summary>
    public string OutputFormat { get; set; } = string.Empty;

    /// <summary>输出文件字节大小</summary>
    public long OutputSize { get; set; }

    // === DPI ===

    /// <summary>输出 DPI X 分量</summary>
    public double? DpiX { get; set; }

    /// <summary>输出 DPI Y 分量</summary>
    public double? DpiY { get; set; }

    // === 处理元信息 ===

    /// <summary>非致命警告信息列表</summary>
    public List<string> Warnings { get; set; } = new();

    /// <summary>处理耗时（毫秒）</summary>
    public double ElapsedMs { get; set; }

    /// <summary>使用的预设名称（如有）</summary>
    public string? Preset { get; set; }

    // === 状态 ===

    /// <summary>处理是否成功</summary>
    public bool IsSuccess { get; set; } = true;

    /// <summary>错误消息（失败时）</summary>
    public string? ErrorMessage { get; set; }

    // === 套餐权限（来自 /api/v1/entitlements/check） ===

    /// <summary>套餐权限是否已通过</summary>
    public bool EntitlementAllowed { get; set; } = true;

    /// <summary>权限不通过时的拒绝原因（中文）</summary>
    public string? EntitlementReason { get; set; }

    /// <summary>用户当前套餐编码</summary>
    public string? PlanCode { get; set; }

    /// <summary>免费套餐剩余配额</summary>
    public int? RemainingFreeQuota { get; set; }

    // === UI 辅助显示属性 ===

    /// <summary>源泉尺寸摘要 "800 x 600 px"</summary>
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

    /// <summary>缩放比例可读显示 "1:2.40 (缩小)" 或 "2.40:1 (放大)"</summary>
    public string ScaleRatioDisplay =>
        ScaleRatio == 1.0 ? "1:1 (原始)"
        : ScaleRatio > 1.0 ? $"{ScaleRatio:F2}:1 (放大)"
        : $"1:{1.0 / ScaleRatio:F2} (缩小)";

    /// <summary>输出格式 + 文件大小 "PNG (12.3 KB)"</summary>
    public string OutputFormatSummary =>
        $"{OutputFormat.ToUpperInvariant()} ({OutputSize / 1024.0:F1} KB)";

    /// <summary>DPI 显示 "300 x 300" 或 "保持原图"</summary>
    public string DpiSummary =>
        DpiX.HasValue && DpiY.HasValue
            ? $"{DpiX:F0} x {DpiY:F0}"
            : "保持原图";

    /// <summary>是否有警告</summary>
    public bool HasWarnings => Warnings.Count > 0;

    /// <summary>是否有权限</summary>
    public bool HasPermission => EntitlementAllowed;

    /// <summary>
    /// 从 Python worker 返回的 JSON data 反序列化构建结果。
    /// 不含二进制 output_data——图片已通过文件保存，C# 侧读取文件路径即可。
    /// </summary>
    /// <param name="data">Python bridge 返回的 data 字段</param>
    /// <param name="inputPath">原始输入文件路径</param>
    /// <returns>构建好的 ResizeImageResult</returns>
    public static ResizeImageResult FromRouterResponse(JsonElement data, string inputPath)
    {
        var result = new ResizeImageResult
        {
            InputPath = inputPath,
            OutputPath = data.TryGetProperty("output_path", out var op) ? op.GetString() ?? "" : "",
            SourceWidth = data.TryGetProperty("source_width", out var sw) ? sw.GetInt32() : 0,
            SourceHeight = data.TryGetProperty("source_height", out var sh) ? sh.GetInt32() : 0,
            OutputWidth = data.TryGetProperty("output_width", out var ow) ? ow.GetInt32() : 0,
            OutputHeight = data.TryGetProperty("output_height", out var oh) ? oh.GetInt32() : 0,
            Mode = data.TryGetProperty("mode", out var m) ? m.GetString() ?? "" : "",
            ScaleRatio = data.TryGetProperty("scale_ratio", out var sr) ? sr.GetDouble() : 1.0,
            OutputFormat = data.TryGetProperty("output_format", out var of) ? of.GetString() ?? "" : "",
            OutputSize = data.TryGetProperty("output_size", out var os) ? os.GetInt64() : 0,
            ElapsedMs = data.TryGetProperty("elapsed_ms", out var em) ? em.GetDouble() : 0,
            Preset = data.TryGetProperty("preset", out var pr) ? pr.GetString() : null,
            IsSuccess = true,
        };

        // DPI: Python 返回 [x, y] 格式
        if (data.TryGetProperty("dpi", out var dpi) && dpi.ValueKind == JsonValueKind.Array)
        {
            var dpiArr = dpi.EnumerateArray().ToArray();
            if (dpiArr.Length >= 2)
            {
                result.DpiX = dpiArr[0].GetDouble();
                result.DpiY = dpiArr[1].GetDouble();
            }
        }

        // Warnings
        if (data.TryGetProperty("warnings", out var warns) && warns.ValueKind == JsonValueKind.Array)
        {
            result.Warnings = warns.EnumerateArray()
                .Select(w => w.GetString() ?? "").ToList();
        }

        return result;
    }
}
