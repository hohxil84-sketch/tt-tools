using TTTools.ExportSettings.Models;
using TTShared.FileSystem;

namespace TTTools.ExportSettings.Services;

/// <summary>
/// 导出服务
/// 负责将文件导出到指定目录，支持格式转换和目标目录管理。
/// 当前阶段实现文件复制导出；格式转换依赖后续 local-worker 模块。
/// </summary>
public class ExportService
{
    private readonly FileSystemService _fileSystem;

    public ExportService(FileSystemService fileSystem)
    {
        _fileSystem = fileSystem ?? throw new ArgumentNullException(nameof(fileSystem));
    }

    /// <summary>
    /// 导出文件列表
    /// 将源文件按配置导出到目标目录。
    /// </summary>
    /// <param name="sourceFiles">源文件路径列表</param>
    /// <param name="config">导出配置</param>
    /// <param name="progressCallback">进度回调（已处理数 / 总数）</param>
    /// <param name="cancellationToken">取消令牌</param>
    /// <returns>导出结果</returns>
    public async Task<ExportResult> ExportAsync(
        List<string> sourceFiles,
        ExportConfig config,
        IProgress<(int current, int total)>? progressCallback = null,
        CancellationToken cancellationToken = default)
    {
        if (sourceFiles == null || sourceFiles.Count == 0)
            return new ExportResult { Success = true };

        var startTime = Environment.TickCount64;
        var outputPaths = new List<string>();
        var errors = new List<ExportError>();
        var successCount = 0;

        // 确保输出目录存在
        try
        {
            if (!Directory.Exists(config.OutputDirectory))
                Directory.CreateDirectory(config.OutputDirectory);
        }
        catch (Exception ex)
        {
            // 输出目录创建失败，所有导出必定失败
            return ExportResult.WithFailures(0, outputPaths,
                sourceFiles.Select(f => new ExportError
                {
                    SourcePath = f,
                    Message = $"输出目录创建失败：{ex.Message}",
                    ExceptionType = ex.GetType().Name
                }).ToList(),
                ElapsedSince(startTime));
        }

        for (int i = 0; i < sourceFiles.Count; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var sourcePath = sourceFiles[i];
            try
            {
                var outputPath = await ExportSingleFileAsync(sourcePath, config);
                outputPaths.Add(outputPath);
                successCount++;
            }
            catch (Exception ex)
            {
                errors.Add(new ExportError
                {
                    SourcePath = sourcePath,
                    Message = ex.Message,
                    ExceptionType = ex.GetType().Name
                });
            }

            // 报告进度
            progressCallback?.Report((i + 1, sourceFiles.Count));
        }

        return ExportResult.WithFailures(successCount, outputPaths, errors,
            ElapsedSince(startTime));
    }

    /// <summary>
    /// 导出单个文件
    /// </summary>
    private async Task<string> ExportSingleFileAsync(string sourcePath, ExportConfig config)
    {
        // 检查源文件存在
        if (!File.Exists(sourcePath))
            throw new FileNotFoundException("源文件不存在", sourcePath);

        // 确定输出文件名
        var sourceFileName = Path.GetFileName(sourcePath);
        var targetFileName = string.IsNullOrEmpty(config.FileNamePrefix)
            ? sourceFileName
            : $"{config.FileNamePrefix}{sourceFileName}";

        // 处理格式转换的文件名
        if (config.Format != "original")
        {
            var baseName = Path.GetFileNameWithoutExtension(sourceFileName);
            targetFileName = string.IsNullOrEmpty(config.FileNamePrefix)
                ? $"{baseName}.{config.Format}"
                : $"{config.FileNamePrefix}{baseName}.{config.Format}";
        }

        // 确定输出路径
        string outputPath;
        if (config.PreserveDirectoryStructure)
        {
            // 保留相对目录结构（这里简化处理）
            outputPath = Path.Combine(config.OutputDirectory, targetFileName);
        }
        else
        {
            outputPath = Path.Combine(config.OutputDirectory, targetFileName);
        }

        // 处理文件名冲突
        if (!config.OverwriteExisting && File.Exists(outputPath))
        {
            var dir = Path.GetDirectoryName(outputPath) ?? config.OutputDirectory;
            var nameWithoutExt = Path.GetFileNameWithoutExtension(targetFileName);
            var ext = Path.GetExtension(targetFileName);
            var counter = 1;
            do
            {
                outputPath = Path.Combine(dir, $"{nameWithoutExt}_{counter}{ext}");
                counter++;
            } while (File.Exists(outputPath) && counter < 1000);
        }

        // 执行导出（当前阶段：复制文件）
        // 后续阶段可通过 local-worker 实现格式转换
        await Task.Run(() => File.Copy(sourcePath, outputPath, config.OverwriteExisting));

        return outputPath;
    }

    /// <summary>
    /// 计算从起始时间到当前经过的毫秒数
    /// </summary>
    private static long ElapsedSince(long startTick)
        => Environment.TickCount64 - startTick;
}
