using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Windows;

namespace TTTools.OCR.Models;

/// <summary>
/// OCR 文字行数据模型
/// 用于展示单行识别结果，包含文字内容、置信度和坐标信息。
/// </summary>
public class OcrTextLine
{
    /// <summary>识别的文本内容</summary>
    public string Text { get; set; } = string.Empty;

    /// <summary>识别置信度 (0.0 ~ 1.0)</summary>
    public double Score { get; set; }

    /// <summary>四点坐标 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]</summary>
    public List<List<double>> Box { get; set; } = new();

    /// <summary>置信度百分比（用于 UI 展示）</summary>
    public string ScorePercent => $"{Score * 100:F1}%";

    /// <summary>高置信度（>= 0.9）</summary>
    public bool IsHighConfidence => Score >= 0.9;

    /// <summary>左边界 x 坐标（四点中最小 x），用于计算文字缩进</summary>
    public double LeftX => Box.Count > 0
        ? Box.Select(p => p[0]).Min()
        : 0.0;

    /// <summary>文字框中心 x 坐标</summary>
    public double CenterX => Box.Count >= 4
        ? Box.Take(4).Average(p => p[0])
        : 0.0;

    /// <summary>文字框中心 y 坐标</summary>
    public double CenterY => Box.Count >= 4
        ? Box.Take(4).Average(p => p[1])
        : 0.0;

    /// <summary>文字框近似高度</summary>
    public double BoxHeight
    {
        get
        {
            if (Box.Count < 4) return 20.0;
            var leftH = Math.Abs(Box[3][1] - Box[0][1]);
            var rightH = Math.Abs(Box[2][1] - Box[1][1]);
            return (leftH + rightH) / 2.0;
        }
    }

    /// <summary>按给定阈值判断是否为低置信度</summary>
    public bool IsLowConfidenceByThreshold(double threshold) => Score < threshold;
}

/// <summary>
/// OCR 展示行模型
/// 用于右侧详情面板的格式化展示：正常行显示原文，低置信度行显示红色 □ 占位。
/// LeftMargin 基于原图坐标计算，还原图片中文字的真实排版。
/// </summary>
public class OcrDisplayLine
{
    /// <summary>展示文本（原文或 * 占位符）</summary>
    public string DisplayText { get; set; } = string.Empty;

    /// <summary>是否为低置信度行（被遮罩）</summary>
    public bool IsMasked { get; set; }

    /// <summary>原始识别文本（调试/提示用）</summary>
    public string OriginalText { get; set; } = string.Empty;

    /// <summary>置信度</summary>
    public double Score { get; set; }

    /// <summary>左侧缩进距离（像素），基于原图坐标换算</summary>
    public double LeftMargin { get; set; }

    /// <summary>WPF Padding 用的 Thickness（仅左侧缩进）</summary>
    public Thickness IndentThickness => new(LeftMargin, 0, 0, 0);
}

/// <summary>
/// OCR 识别结果模型
/// 单张图片的完整 OCR 识别结果，包含所有文字行、耗时和引擎信息。
/// 从 local-worker OCR 引擎返回的 JSON 反序列化得到。
/// 支持按 UI 阈值动态更新低置信度遮罩。
/// </summary>
public class OcrJobResult : INotifyPropertyChanged
{
    private double _confidenceThreshold = 0.5;

    /// <summary>所有识别的文字行</summary>
    public List<OcrTextLine> TextLines { get; set; } = new();

    /// <summary>完整拼接文本（简单拼接）</summary>
    public string TotalText { get; set; } = string.Empty;

    /// <summary>按原图坐标排版的格式化文本（保留换行、空格、缩进）</summary>
    public string FormattedText { get; set; } = string.Empty;

    /// <summary>文字行数</summary>
    public int LineCount { get; set; }

    /// <summary>平均置信度</summary>
    public double AvgScore { get; set; }

    /// <summary>总耗时（秒）</summary>
    public double ElapsedTotal { get; set; }

    /// <summary>文字检测耗时（秒）</summary>
    public double ElapsedDet { get; set; }

    /// <summary>文字识别耗时（秒）</summary>
    public double ElapsedRec { get; set; }

    /// <summary>文字方向分类耗时（秒）</summary>
    public double? ElapsedCls { get; set; }

    /// <summary>引擎名称</summary>
    public string EngineName { get; set; } = string.Empty;

    /// <summary>引擎版本</summary>
    public string EngineVersion { get; set; } = string.Empty;

    /// <summary>原图宽度</summary>
    public int? ImageWidth { get; set; }

    /// <summary>原图高度</summary>
    public int? ImageHeight { get; set; }

    /// <summary>源文件路径</summary>
    public string? FilePath { get; set; }

    /// <summary>是否识别成功</summary>
    public bool IsSuccess { get; set; } = true;

    /// <summary>错误消息</summary>
    public string? ErrorMessage { get; set; }

    /// <summary>当前 UI 置信度阈值 (0.0 ~ 1.0)，用于计算低置信度数量和遮罩显示</summary>
    public double ConfidenceThreshold
    {
        get => _confidenceThreshold;
        set
        {
            if (Math.Abs(_confidenceThreshold - value) > 0.001)
            {
                _confidenceThreshold = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(LowConfidenceCount));
                OnPropertyChanged(nameof(HighConfidenceCount));
                OnPropertyChanged(nameof(DisplayLines));
            }
        }
    }

    /// <summary>高置信度文字行数（Score >= 0.9，不受阈值影响）</summary>
    public int HighConfidenceCount => TextLines.Count(t => t.IsHighConfidence);

    /// <summary>低于当前阈值的文字行数</summary>
    public int LowConfidenceCount => TextLines.Count(t => t.Score < ConfidenceThreshold);

    /// <summary>
    /// 将文本按阈值遮罩：低于阈值的字符替换为等长 □
    /// </summary>
    private static string MaskText(string text, double score, double threshold)
    {
        if (score < threshold)
            return new string('□', text.Length);
        return text;
    }

    /// <summary>
    /// 格式化展示行列表：低置信度行替换为等长 *。
    /// 根据 OCR 坐标计算缩进距离，还原图片中文字的排版（左对齐/居中/缩进）。
    /// 按原始图片坐标从上到下、从左到右排序。
    /// </summary>
    public List<OcrDisplayLine> DisplayLines
    {
        get
        {
            if (TextLines.Count == 0)
                return new List<OcrDisplayLine>();

            // 以所有行中最靠左的 x 坐标为基准 0 点
            var baseX = TextLines.Min(tl => tl.LeftX);

            // 按图片宽度比例将像素偏移换算为 UI 缩进
            var scale = ImageWidth > 0 ? 400.0 / ImageWidth.Value : 1.0;

            var threshold = ConfidenceThreshold;

            // 按坐标排序：先按 y 中心，再按 x 中心
            var sorted = TextLines
                .OrderBy(tl => tl.CenterY)
                .ThenBy(tl => tl.CenterX)
                .ToList();

            return sorted.Select(tl =>
            {
                var offsetX = Math.Max(0, tl.LeftX - baseX);
                var isBelowThreshold = tl.Score < threshold;
                return new OcrDisplayLine
                {
                    DisplayText = isBelowThreshold
                        ? new string('□', tl.Text.Length)
                        : tl.Text,
                    IsMasked = isBelowThreshold,
                    OriginalText = tl.Text,
                    Score = tl.Score,
                    LeftMargin = Math.Round(offsetX * scale, 0),
                };
            }).ToList();
        }
    }

    /// <summary>耗时摘要（用于 UI 展示）</summary>
    public string ElapsedSummary =>
        $"总耗时 {ElapsedTotal:F2}s (检测 {ElapsedDet:F3}s, 识别 {ElapsedRec:F3}s)";

    /// <summary>图片尺寸摘要（用于 UI 展示）</summary>
    public string ImageSizeSummary =>
        ImageWidth.HasValue && ImageHeight.HasValue
            ? $"{ImageWidth}×{ImageHeight}"
            : "未知";

    /// <summary>
    /// 从 local-worker OCR 引擎返回的原始 JSON 数据反序列化
    /// </summary>
    public static OcrJobResult FromRouterResponse(
        JsonElement data, string? filePath = null)
    {
        var result = new OcrJobResult
        {
            FilePath = filePath,
            LineCount = data.TryGetProperty("line_count", out var lc) ? lc.GetInt32() : 0,
            TotalText = data.TryGetProperty("total_text", out var tt) ? tt.GetString() ?? "" : "",
            FormattedText = data.TryGetProperty("formatted_text", out var ft) ? ft.GetString() ?? "" : "",
        };

        // 解析文字行
        if (data.TryGetProperty("text_lines", out var textLines) && textLines.ValueKind == JsonValueKind.Array)
        {
            foreach (var tl in textLines.EnumerateArray())
            {
                var line = new OcrTextLine
                {
                    Text = tl.TryGetProperty("text", out var t) ? t.GetString() ?? "" : "",
                    Score = tl.TryGetProperty("score", out var s) ? s.GetDouble() : 0.0,
                };

                // 解析坐标框
                if (tl.TryGetProperty("box", out var box) && box.ValueKind == JsonValueKind.Array)
                {
                    line.Box = new List<List<double>>();
                    foreach (var point in box.EnumerateArray())
                    {
                        if (point.ValueKind == JsonValueKind.Array)
                        {
                            var coords = new List<double>();
                            foreach (var c in point.EnumerateArray())
                                coords.Add(c.GetDouble());
                            line.Box.Add(coords);
                        }
                    }
                }

                result.TextLines.Add(line);
            }
        }

        // 解析耗时
        if (data.TryGetProperty("elapsed", out var elapsed))
        {
            result.ElapsedTotal = elapsed.TryGetProperty("total", out var et) ? et.GetDouble() : 0.0;
            result.ElapsedDet = elapsed.TryGetProperty("det", out var ed) ? ed.GetDouble() : 0.0;
            result.ElapsedRec = elapsed.TryGetProperty("rec", out var er) ? er.GetDouble() : 0.0;
            if (elapsed.TryGetProperty("cls", out var ecls) && ecls.ValueKind != JsonValueKind.Null)
                result.ElapsedCls = ecls.GetDouble();
        }

        // 解析引擎信息
        if (data.TryGetProperty("engine", out var engine))
        {
            result.EngineName = engine.TryGetProperty("name", out var en) ? en.GetString() ?? "" : "";
            result.EngineVersion = engine.TryGetProperty("version", out var ev) ? ev.GetString() ?? "" : "";
        }

        // 解析图片尺寸
        if (data.TryGetProperty("image", out var image))
        {
            if (image.TryGetProperty("width", out var iw) && iw.ValueKind != JsonValueKind.Null)
                result.ImageWidth = iw.GetInt32();
            if (image.TryGetProperty("height", out var ih) && ih.ValueKind != JsonValueKind.Null)
                result.ImageHeight = ih.GetInt32();
        }

        // 计算平均置信度
        if (result.TextLines.Count > 0)
            result.AvgScore = result.TextLines.Average(t => t.Score);
        else
            result.AvgScore = 0.0;

        return result;
    }

    // ---- INotifyPropertyChanged ----

    public event PropertyChangedEventHandler? PropertyChanged;

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
