using System.Collections.ObjectModel;

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

    /// <summary>低置信度（< 0.5）</summary>
    public bool IsLowConfidence => Score < 0.5;
}

/// <summary>
/// OCR 识别结果模型
/// 单张图片的完整 OCR 识别结果，包含所有文字行、耗时和引擎信息。
/// 从 local-worker OCR 引擎返回的 JSON 反序列化得到。
/// </summary>
public class OcrJobResult
{
    /// <summary>所有识别的文字行</summary>
    public List<OcrTextLine> TextLines { get; set; } = new();

    /// <summary>完整拼接文本</summary>
    public string TotalText { get; set; } = string.Empty;

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

    /// <summary>高置信度文字行数</summary>
    public int HighConfidenceCount => TextLines.Count(t => t.IsHighConfidence);

    /// <summary>低置信度文字行数</summary>
    public int LowConfidenceCount => TextLines.Count(t => t.IsLowConfidence);

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
}
