using System.Text.Json;
using TTTools.IdPhoto.Models;

namespace TTTools.IdPhoto.Tests.Models;

/// <summary>
/// IdPhotoResult 模型单元测试
/// 覆盖从 JSON 反序列化、计算属性、显示文本等场景。
/// </summary>
public class IdPhotoResultTests
{
    /// <summary>从有效的 Router 响应数据反序列化 IdPhotoResult</summary>
    [Fact]
    public void FromRouterResponse_WithValidData_ShouldPopulateAllFields()
    {
        // 模拟 Python router 返回的 JSON data
        var json = """
        {
            "output_path": "C:\\temp\\photo_id_photo.jpg",
            "input_path": "C:\\temp\\photo.jpg",
            "width_px": 295,
            "height_px": 413,
            "spec": {
                "name": "1寸",
                "width_mm": 25,
                "height_mm": 35,
                "width_px": 295,
                "height_px": 413,
                "dpi": 300
            },
            "background_color": {
                "name": "红色",
                "r": 219,
                "g": 0,
                "b": 0,
                "hex": "#DB0000",
                "bgr": [0, 0, 219]
            },
            "detected_background": {
                "name": "检测背景色",
                "r": 200,
                "g": 210,
                "b": 220,
                "hex": "#C8D2DC",
                "bgr": [220, 210, 200]
            },
            "metadata": {
                "spec_name": "1寸",
                "target_background": "红色",
                "mask_method": "color_distance",
                "is_solid_background": true
            }
        }
        """;

        var element = JsonDocument.Parse(json).RootElement;
        var result = IdPhotoResult.FromRouterResponse(element);

        Assert.Equal("C:\\temp\\photo_id_photo.jpg", result.OutputPath);
        Assert.Equal("C:\\temp\\photo.jpg", result.InputPath);
        Assert.Equal(295, result.WidthPx);
        Assert.Equal(413, result.HeightPx);
        Assert.NotNull(result.Spec);
        Assert.Equal("1寸", result.Spec!.Name);
        Assert.Equal(25, result.Spec.WidthMm);
        Assert.Equal(35, result.Spec.HeightMm);
        Assert.Equal(295, result.Spec.WidthPx);
        Assert.Equal(413, result.Spec.HeightPx);
        Assert.Equal(300, result.Spec.Dpi);

        Assert.NotNull(result.BackgroundColor);
        Assert.Equal("红色", result.BackgroundColor!.Name);
        Assert.Equal(219, result.BackgroundColor.R);
        Assert.Equal(0, result.BackgroundColor.G);
        Assert.Equal(0, result.BackgroundColor.B);
        Assert.Equal("#DB0000", result.BackgroundColor.Hex);

        Assert.NotNull(result.DetectedBackground);
        Assert.Equal("检测背景色", result.DetectedBackground!.Name);
        Assert.Equal(200, result.DetectedBackground.R);

        Assert.NotNull(result.Metadata);
        Assert.True(result.Metadata!.ContainsKey("mask_method"));
        Assert.Equal("color_distance", result.Metadata["mask_method"]);
    }

    /// <summary>从空的 JSON 数据反序列化应返回默认值</summary>
    [Fact]
    public void FromRouterResponse_WithMinimalData_ShouldHaveDefaults()
    {
        var json = "{}";
        var element = JsonDocument.Parse(json).RootElement;
        var result = IdPhotoResult.FromRouterResponse(element);

        Assert.Equal("", result.OutputPath);
        Assert.Equal("", result.InputPath);
        Assert.Equal(0, result.WidthPx);
        Assert.Equal(0, result.HeightPx);
        Assert.Null(result.Spec);
        Assert.Null(result.BackgroundColor);
        Assert.Null(result.DetectedBackground);
        Assert.Null(result.Metadata);
    }

    /// <summary>显示属性应返回正确的文本摘要</summary>
    [Fact]
    public void DisplayProperties_ShouldReturnCorrectSummaries()
    {
        var json = """
        {
            "output_path": "C:\\temp\\photo_id_photo.jpg",
            "input_path": "C:\\temp\\test_photo.png",
            "width_px": 295,
            "height_px": 413,
            "spec": {
                "name": "2寸",
                "width_mm": 35,
                "height_mm": 49,
                "width_px": 413,
                "height_px": 579,
                "dpi": 300
            },
            "background_color": {
                "name": "蓝色",
                "r": 67,
                "g": 142,
                "b": 219,
                "hex": "#438EDB",
                "bgr": [219, 142, 67]
            },
            "metadata": {
                "mask_method": "grabcut"
            }
        }
        """;

        var element = JsonDocument.Parse(json).RootElement;
        var result = IdPhotoResult.FromRouterResponse(element);

        Assert.Equal("test_photo.png", result.InputFileName);
        Assert.Equal("295 × 413 px", result.SizeSummary);
        Assert.Contains("2寸", result.SpecSummary);
        Assert.Contains("35×49mm", result.SpecSummary);
        Assert.Contains("蓝色", result.BackgroundSummary);
        Assert.Contains("#438EDB", result.BackgroundSummary);
        Assert.Equal("GrabCut 分割", result.MaskMethodSummary);
    }

    /// <summary>输入路径为空时 InputFileName 应返回 "未知文件"</summary>
    [Fact]
    public void InputFileName_WithEmptyPath_ShouldReturnUnknownFile()
    {
        var result = new IdPhotoResult { InputPath = "" };
        Assert.Equal("未知文件", result.InputFileName);
    }

    /// <summary>遮罩方法为 color_distance 时应返回 "颜色距离法"</summary>
    [Fact]
    public void MaskMethodSummary_ColorDistance_ShouldReturnChinese()
    {
        var result = new IdPhotoResult
        {
            Metadata = new Dictionary<string, object> { ["mask_method"] = "color_distance" }
        };
        Assert.Equal("颜色距离法", result.MaskMethodSummary);
    }

    /// <summary>没有元数据时 MaskMethodSummary 应返回 "未知"</summary>
    [Fact]
    public void MaskMethodSummary_NullMetadata_ShouldReturnUnknown()
    {
        var result = new IdPhotoResult { Metadata = null };
        Assert.Equal("未知", result.MaskMethodSummary);
    }
}
