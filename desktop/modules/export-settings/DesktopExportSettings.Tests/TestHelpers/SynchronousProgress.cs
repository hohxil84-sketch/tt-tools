namespace TTTools.ExportSettings.Tests.TestHelpers;

/// <summary>
/// 同步 IProgress 实现，用于测试中可靠捕获进度回调。
/// Progress&lt;T&gt; 默认异步投递回调，测试中可能遗漏。
/// </summary>
public class SynchronousProgress<T> : IProgress<T>
{
    private readonly Action<T>? _handler;

    /// <summary>已报告的值列表</summary>
    public List<T> ReportedValues { get; } = new();

    public SynchronousProgress(Action<T>? handler = null)
    {
        _handler = handler;
    }

    public void Report(T value)
    {
        ReportedValues.Add(value);
        _handler?.Invoke(value);
    }
}
