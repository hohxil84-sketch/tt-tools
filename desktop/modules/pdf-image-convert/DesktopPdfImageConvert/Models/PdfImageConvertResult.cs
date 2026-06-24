using System.Text.Json;

namespace TTTools.PdfImageConvert.Models;

/// <summary>
/// PDF/图片互转处理结果模型
/// 包含转换元数据、输出信息和套餐权限信息。
/// 从 Python worker 返回的 JSON 和云端的套餐权限检查结果中反序列化构建。
/// </summary>
public class PdfImageConvertResult
{
    // === 来源信息 ===

    /// <summary>输入文件路径（PDF→图片时为 PDF 文件路径，图片→PDF 时为第一张图片路径）</summary>
    public string InputPath { get; set; } = string.Empty;

    /// <summary>输出文件路径（PDF→图片时为输出目录，图片→PDF 时为输出 PDF 文件路径）</summary>
    public string OutputPath { get; set; } = string.Empty;

    /// <summary>输入文件名</summary>
    public string InputFileName =>
        string.IsNullOrEmpty(InputPath) ? "未知文件" : Path.GetFileName(InputPath);

    /// <summary>输出文件名或目录名</summary>
    public string OutputFileName =>
        string.IsNullOrEmpty(OutputPath) ? "未知" : Path.GetFileName(OutputPath);

    // === 转换信息 ===

    /// <summary>转换方向: pdf_to_images / images_to_pdf</summary>
    public string Direction { get; set; } = string.Empty;

    /// <summary>输入格式（如 "pdf"、"images"）</summary>
    public string SourceFormat { get; set; } = string.Empty;

    /// <summary>总页数（PDF→图片）或总输入图片数（图片→PDF）</summary>
    public int TotalPages { get; set; }

    /// <summary>输出页数/图片数量</summary>
    public int OutputPages { get; set; }

    /// <summary>每页/每图转换结果列表</summary>
    public List<PageResult> Pages { get; set; } = new();

    /// <summary>输出格式</summary>
    public string OutputFormat { get; set; } = string.Empty;

    /// <summary>输出文件字节大小</summary>
    public long OutputSize { get; set; }

    // === 处理元信息 ===

    /// <summary>非致命警告信息列表</summary>
    public List<string> Warnings { get; set; } = new();

    /// <summary>处理耗时（毫秒）</summary>
    public double ElapsedMs { get; set; }

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

    /// <summary>转换方向中文显示</summary>
    public string DirectionDisplay =>
        Direction == "pdf_to_images" ? "PDF → 图片"
        : Direction == "images_to_pdf" ? "图片 → PDF"
        : Direction;

    /// <summary>输出格式大写显示</summary>
    public string OutputFormatDisplay => OutputFormat.ToUpperInvariant();

    /// <summary>输出大小可读显示 "1.2 MB"</summary>
    public string OutputSizeDisplay =>
        OutputSize >= 1048576 ? $"{OutputSize / 1048576.0:F1} MB"
        : OutputSize >= 1024 ? $"{OutputSize / 1024.0:F1} KB"
        : $"{OutputSize} B";

    /// <summary>耗时显示 "1234.5 ms"</summary>
    public string ElapsedMsDisplay => $"{ElapsedMs:F1} ms";

    /// <summary>页数摘要 "输出 5 页 (共 10 页)"</summary>
    public string PagesSummary =>
        TotalPages > 0
            ? $"输出 {OutputPages} 页 (共 {TotalPages} 页)"
            : $"输出 {OutputPages} 页";

    /// <summary>是否有警告</summary>
    public bool HasWarnings => Warnings.Count > 0;

    /// <summary>是否有权限</summary>
    public bool HasPermission => EntitlementAllowed;

    /// <summary>
    /// 从 Python worker 返回的 JSON data 反序列化构建结果。
    /// 不含二进制 output_data——图片/PDF 已通过文件保存，C# 侧读取文件路径即可。
    /// </summary>
    /// <param name="data">Python bridge 返回的 data 字段</param>
    /// <param name="inputPath">原始输入文件路径</param>
    /// <returns>构建好的 PdfImageConvertResult</returns>
    public static PdfImageConvertResult FromRouterResponse(JsonElement data, string inputPath)
    {
        var result = new PdfImageConvertResult
        {
            InputPath = inputPath,
            OutputPath = data.TryGetProperty("output_path", out var op)
                ? op.GetString() ?? ""
                : data.TryGetProperty("output_dir", out var od)
                    ? od.GetString() ?? ""
                    : "",
            Direction = data.TryGetProperty("direction", out var dir)
                ? dir.GetString() ?? "" : "",
            SourceFormat = data.TryGetProperty("source_format", out var sf)
                ? sf.GetString() ?? "" : "",
            TotalPages = data.TryGetProperty("total_pages", out var tp) ? tp.GetInt32() : 0,
            OutputPages = data.TryGetProperty("output_pages", out var opc) ? opc.GetInt32() : 0,
            OutputFormat = data.TryGetProperty("output_format", out var of)
                ? of.GetString() ?? "" : "",
            OutputSize = data.TryGetProperty("output_size", out var os) ? os.GetInt64() : 0,
            ElapsedMs = data.TryGetProperty("elapsed_ms", out var em) ? em.GetDouble() : 0,
            IsSuccess = true,
        };

        // Pages 列表
        if (data.TryGetProperty("pages", out var pagesArr) &&
            pagesArr.ValueKind == JsonValueKind.Array)
        {
            result.Pages = pagesArr.EnumerateArray()
                .Select(p => new PageResult
                {
                    PageNumber = p.TryGetProperty("page_number", out var pn) ? pn.GetInt32() : 0,
                    Width = p.TryGetProperty("width", out var pw) ? pw.GetInt32() : 0,
                    Height = p.TryGetProperty("height", out var ph) ? ph.GetInt32() : 0,
                    Format = p.TryGetProperty("format", out var pf) ? pf.GetString() ?? "" : "",
                    SizeBytes = p.TryGetProperty("size_bytes", out var ps) ? ps.GetInt32() : 0,
                })
                .ToList();
        }

        // Warnings
        if (data.TryGetProperty("warnings", out var warns) &&
            warns.ValueKind == JsonValueKind.Array)
        {
            result.Warnings = warns.EnumerateArray()
                .Select(w => w.GetString() ?? "").ToList();
        }

        return result;
    }
}
