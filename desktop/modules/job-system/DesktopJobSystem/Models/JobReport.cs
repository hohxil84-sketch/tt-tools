using TTShared.JobSystem;

namespace TTTools.JobSystem.Models;

/// <summary>
/// 任务统计报告
/// 提供对任务列表中各状态任务数量的汇总统计。
/// </summary>
public class JobReport
{
    /// <summary>任务总数</summary>
    public int Total { get; set; }

    /// <summary>排队中任务数</summary>
    public int Queued { get; set; }

    /// <summary>运行中任务数</summary>
    public int Running { get; set; }

    /// <summary>成功完成任务数</summary>
    public int Succeeded { get; set; }

    /// <summary>失败任务数</summary>
    public int Failed { get; set; }

    /// <summary>已取消任务数</summary>
    public int Cancelled { get; set; }

    /// <summary>成功率（百分比，0-100）</summary>
    public double SuccessRate =>
        Total > 0 ? Math.Round((double)Succeeded / Total * 100, 1) : 0;

    /// <summary>
    /// 从任务列表生成统计报告
    /// </summary>
    public static JobReport FromJobs(IEnumerable<JobRecord> jobs)
    {
        var report = new JobReport();
        foreach (var job in jobs)
        {
            report.Total++;
            switch (job.Status)
            {
                case JobStatus.Queued:
                    report.Queued++;
                    break;
                case JobStatus.Running:
                    report.Running++;
                    break;
                case JobStatus.Succeeded:
                    report.Succeeded++;
                    break;
                case JobStatus.Failed:
                    report.Failed++;
                    break;
                case JobStatus.Cancelled:
                    report.Cancelled++;
                    break;
            }
        }
        return report;
    }
}
