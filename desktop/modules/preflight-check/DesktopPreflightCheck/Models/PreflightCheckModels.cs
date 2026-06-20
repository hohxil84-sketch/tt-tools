using System.Collections.ObjectModel;
using System.Text.Json;

namespace TTTools.PreflightCheck.Models;

/// <summary>
/// 风险等级枚举
/// 与 local-worker report.py 中的 RiskLevel 对应。
/// </summary>
public enum RiskLevel
{
    /// <summary>通过，无风险</summary>
    Pass,
    /// <summary>警告，建议人工复核</summary>
    Warning,
    /// <summary>错误，不建议直接印刷</summary>
    Error
}

/// <summary>
/// 检查项标识枚举
/// 与 local-worker report.py 中的 CheckItem 对应。
/// </summary>
public enum CheckItemType
{
    /// <summary>文件格式</summary>
    FileFormat,
    /// <summary>图片尺寸</summary>
    Dimensions,
    /// <summary>DPI 分辨率</summary>
    Dpi,
    /// <summary>颜色模式</summary>
    ColorMode,
    /// <summary>透明通道</summary>
    Transparency,
    /// <summary>低清风险</summary>
    LowResolution,
    /// <summary>文件大小</summary>
    FileSize
}

/// <summary>
/// 单项检查结果
/// 对应 Python report.py 中的 PreflightCheckResult。
/// </summary>
public class PreflightCheckResultItem
{
    /// <summary>检查项类型</summary>
    public CheckItemType Item { get; set; }

    /// <summary>风险等级</summary>
    public RiskLevel RiskLevel { get; set; }

    /// <summary>中文描述信息</summary>
    public string Message { get; set; } = string.Empty;

    /// <summary>附加详情（如当前值、推荐值）</summary>
    public Dictionary<string, JsonElement> Details { get; set; } = new();

    // ==================== UI 展示属性 ====================

    /// <summary>检查项的中文名称</summary>
    public string ItemDisplayName => Item switch
    {
        CheckItemType.FileFormat => "文件格式",
        CheckItemType.Dimensions => "图片尺寸",
        CheckItemType.Dpi => "DPI 分辨率",
        CheckItemType.ColorMode => "颜色模式",
        CheckItemType.Transparency => "透明通道",
        CheckItemType.LowResolution => "低清风险",
        CheckItemType.FileSize => "文件大小",
        _ => Item.ToString()
    };

    /// <summary>风险等级的中文文本</summary>
    public string RiskLevelDisplay => RiskLevel switch
    {
        RiskLevel.Pass => "通过",
        RiskLevel.Warning => "警告",
        RiskLevel.Error => "错误",
        _ => RiskLevel.ToString()
    };

    /// <summary>风险等级对应的图标</summary>
    public string RiskIcon => RiskLevel switch
    {
        RiskLevel.Pass => "✅",
        RiskLevel.Warning => "⚠️",
        RiskLevel.Error => "❌",
        _ => "❓"
    };

    /// <summary>是否为通过状态</summary>
    public bool IsPass => RiskLevel == RiskLevel.Pass;

    /// <summary>是否为警告状态</summary>
    public bool IsWarning => RiskLevel == RiskLevel.Warning;

    /// <summary>是否为错误状态</summary>
    public bool IsError => RiskLevel == RiskLevel.Error;
}

/// <summary>
/// 印前检查综合报告
/// 对应 Python report.py 中的 PreflightReport。
/// </summary>
public class PreflightCheckReport
{
    /// <summary>被检查的文件路径</summary>
    public string FilePath { get; set; } = string.Empty;

    /// <summary>文件名</summary>
    public string FileName { get; set; } = string.Empty;

    /// <summary>文件扩展名</summary>
    public string FileFormat { get; set; } = string.Empty;

    /// <summary>文件大小（字节）</summary>
    public long FileSizeBytes { get; set; }

    /// <summary>图像宽度（像素），可能为空</summary>
    public int? Width { get; set; }

    /// <summary>图像高度（像素），可能为空</summary>
    public int? Height { get; set; }

    /// <summary>DPI（水平方向），可能为空</summary>
    public double? Dpi { get; set; }

    /// <summary>DPI 水平分量，可能为空</summary>
    public double? DpiH { get; set; }

    /// <summary>DPI 垂直分量，可能为空</summary>
    public double? DpiV { get; set; }

    /// <summary>颜色模式（RGB/CMYK/L 等），可能为空</summary>
    public string? ColorMode { get; set; }

    /// <summary>是否有透明通道</summary>
    public bool HasTransparency { get; set; }

    /// <summary>检查结果列表</summary>
    public List<PreflightCheckResultItem> Checks { get; set; } = new();

    /// <summary>整体风险等级</summary>
    public RiskLevel OverallRisk { get; set; }

    /// <summary>是否有 error 级别风险</summary>
    public bool HasErrors { get; set; }

    /// <summary>是否有 warning 级别风险</summary>
    public bool HasWarnings { get; set; }

    /// <summary>综合建议</summary>
    public string OverallMessage { get; set; } = string.Empty;

    // ==================== UI 展示属性 ====================

    /// <summary>文件大小（KB）用于友好展示</summary>
    public double FileSizeKB => Math.Round(FileSizeBytes / 1024.0, 1);

    /// <summary>文件大小的展示文本</summary>
    public string FileSizeDisplay => FileSizeKB < 1024
        ? $"{FileSizeKB} KB"
        : $"{FileSizeKB / 1024.0:F1} MB";

    /// <summary>图像尺寸展示</summary>
    public string ImageSizeDisplay =>
        Width.HasValue && Height.HasValue
            ? $"{Width}×{Height}"
            : "未知";

    /// <summary>DPI 展示</summary>
    public string DpiDisplay =>
        Dpi.HasValue
            ? Dpi.Value % 1 == 0
                ? $"{Dpi.Value:F0}"
                : $"{Dpi.Value:F1}"
            : "无";

    /// <summary>颜色模式展示</summary>
    public string ColorModeDisplay => ColorMode ?? "未知";

    /// <summary>风险等级的中文文本</summary>
    public string OverallRiskDisplay => OverallRisk switch
    {
        RiskLevel.Pass => "✅ 可以印刷",
        RiskLevel.Warning => "⚠️ 建议复核",
        RiskLevel.Error => "❌ 不建议印刷",
        _ => "未知"
    };

    /// <summary>总体风险对应的简短文本</summary>
    public string OverallRiskLabel => OverallRisk switch
    {
        RiskLevel.Pass => "通过",
        RiskLevel.Warning => "警告",
        RiskLevel.Error => "错误",
        _ => "未知"
    };

    /// <summary>Error 级别检查项数量</summary>
    public int ErrorCount => Checks.Count(c => c.IsError);

    /// <summary>Warning 级别检查项数量</summary>
    public int WarningCount => Checks.Count(c => c.IsWarning);

    /// <summary>Pass 级别检查项数量</summary>
    public int PassCount => Checks.Count(c => c.IsPass);

    /// <summary>检查项总数</summary>
    public int TotalCheckCount => Checks.Count;

    // ==================== 静态工厂方法 ====================

    /// <summary>
    /// 从 local-worker 返回的 JSON 原始数据创建 PreflightCheckReport。
    /// </summary>
    /// <param name="data">Python PreflightReport.to_dict() 返回的 JSON 数据</param>
    /// <returns>反序列化的 PreflightCheckReport</returns>
    public static PreflightCheckReport FromRouterResponse(JsonElement data)
    {
        var report = new PreflightCheckReport
        {
            FilePath = data.TryGetProperty("file_path", out var fp) ? fp.GetString() ?? "" : "",
            FileName = data.TryGetProperty("file_name", out var fn) ? fn.GetString() ?? "" : "",
            FileFormat = data.TryGetProperty("file_format", out var ff) ? ff.GetString() ?? "" : "",
            FileSizeBytes = data.TryGetProperty("file_size_bytes", out var fs) ? fs.GetInt64() : 0,
            Width = TryGetNullableInt(data, "width"),
            Height = TryGetNullableInt(data, "height"),
            Dpi = TryGetNullableDouble(data, "dpi"),
            DpiH = TryGetNullableDouble(data, "dpi_h"),
            DpiV = TryGetNullableDouble(data, "dpi_v"),
            ColorMode = data.TryGetProperty("color_mode", out var cm) && cm.ValueKind != JsonValueKind.Null ? cm.GetString() : null,
            HasTransparency = data.TryGetProperty("has_transparency", out var ht) && ht.GetBoolean(),
            OverallRisk = ParseRiskLevel(data, "overall_risk"),
            HasErrors = data.TryGetProperty("has_errors", out var he) && he.GetBoolean(),
            HasWarnings = data.TryGetProperty("has_warnings", out var hw) && hw.GetBoolean(),
            OverallMessage = data.TryGetProperty("overall_message", out var om) ? om.GetString() ?? "" : "",
        };

        // 解析 checks 数组
        if (data.TryGetProperty("checks", out var checks) && checks.ValueKind == JsonValueKind.Array)
        {
            foreach (var checkEl in checks.EnumerateArray())
            {
                var item = new PreflightCheckResultItem
                {
                    Item = ParseCheckItemType(checkEl, "item"),
                    RiskLevel = ParseRiskLevel(checkEl, "risk_level"),
                    Message = checkEl.TryGetProperty("message", out var msg) ? msg.GetString() ?? "" : "",
                };

                // 解析 details 字典
                if (checkEl.TryGetProperty("details", out var details) && details.ValueKind == JsonValueKind.Object)
                {
                    foreach (var prop in details.EnumerateObject())
                    {
                        item.Details[prop.Name] = prop.Value.Clone();
                    }
                }

                report.Checks.Add(item);
            }
        }

        return report;
    }

    /// <summary>
    /// 创建一个表示失败的报告（文件无法检查时）。
    /// </summary>
    /// <param name="filePath">文件路径</param>
    /// <param name="errorMessage">错误消息</param>
    public static PreflightCheckReport CreateFailedReport(string filePath, string errorMessage)
    {
        return new PreflightCheckReport
        {
            FilePath = filePath,
            FileName = System.IO.Path.GetFileName(filePath) ?? filePath,
            OverallRisk = RiskLevel.Error,
            HasErrors = true,
            OverallMessage = errorMessage,
            Checks = new List<PreflightCheckResultItem>
            {
                new()
                {
                    Item = CheckItemType.FileFormat,
                    RiskLevel = RiskLevel.Error,
                    Message = errorMessage,
                }
            }
        };
    }

    // ==================== 辅助方法 ====================

    private static int? TryGetNullableInt(JsonElement el, string prop)
    {
        if (el.TryGetProperty(prop, out var val) && val.ValueKind != JsonValueKind.Null)
            return val.GetInt32();
        return null;
    }

    private static double? TryGetNullableDouble(JsonElement el, string prop)
    {
        if (el.TryGetProperty(prop, out var val) && val.ValueKind != JsonValueKind.Null)
            return val.GetDouble();
        return null;
    }

    private static RiskLevel ParseRiskLevel(JsonElement el, string prop)
    {
        if (!el.TryGetProperty(prop, out var val)) return RiskLevel.Pass;
        var str = val.GetString() ?? "pass";
        return str switch
        {
            "error" => RiskLevel.Error,
            "warning" => RiskLevel.Warning,
            "pass" => RiskLevel.Pass,
            _ => RiskLevel.Pass,
        };
    }

    private static CheckItemType ParseCheckItemType(JsonElement el, string prop)
    {
        if (!el.TryGetProperty(prop, out var val)) return CheckItemType.FileFormat;
        var str = val.GetString() ?? "file_format";
        return str switch
        {
            "file_format" => CheckItemType.FileFormat,
            "dimensions" => CheckItemType.Dimensions,
            "dpi" => CheckItemType.Dpi,
            "color_mode" => CheckItemType.ColorMode,
            "transparency" => CheckItemType.Transparency,
            "low_resolution" => CheckItemType.LowResolution,
            "file_size" => CheckItemType.FileSize,
            _ => CheckItemType.FileFormat,
        };
    }
}
