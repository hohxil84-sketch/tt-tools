using System.Windows.Input;

namespace TTTools.ExportSettings.ViewModels;

/// <summary>
/// 异步命令实现
/// 包装 async Task 方法为 WPF ICommand，支持异步执行和 IsExecuting 状态。
/// </summary>
public class AsyncRelayCommand : ICommand
{
    private readonly Func<Task> _execute;
    private readonly Func<bool>? _canExecute;
    private bool _isExecuting;

    /// <summary>
    /// 创建 AsyncRelayCommand
    /// </summary>
    /// <param name="execute">异步执行方法</param>
    /// <param name="canExecute">可执行条件（可选）</param>
    public AsyncRelayCommand(Func<Task> execute, Func<bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }

    public bool CanExecute(object? parameter)
    {
        return !_isExecuting && (_canExecute?.Invoke() ?? true);
    }

    public async void Execute(object? parameter)
    {
        if (_isExecuting) return;

        _isExecuting = true;
        RaiseCanExecuteChanged();

        try
        {
            await _execute();
        }
        finally
        {
            _isExecuting = false;
            RaiseCanExecuteChanged();
        }
    }

    /// <summary>
    /// 手动触发 CanExecute 重新评估
    /// </summary>
    public void RaiseCanExecuteChanged()
        => CommandManager.InvalidateRequerySuggested();
}

/// <summary>
/// 带参数的异步命令实现
/// </summary>
/// <typeparam name="T">命令参数类型</typeparam>
public class AsyncRelayCommand<T> : ICommand
{
    private readonly Func<T?, Task> _execute;
    private readonly Func<T?, bool>? _canExecute;
    private bool _isExecuting;

    /// <summary>
    /// 创建 AsyncRelayCommand
    /// </summary>
    /// <param name="execute">异步执行方法</param>
    /// <param name="canExecute">可执行条件（可选）</param>
    public AsyncRelayCommand(Func<T?, Task> execute, Func<T?, bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }

    public bool CanExecute(object? parameter)
    {
        return !_isExecuting && (_canExecute?.Invoke((T?)parameter) ?? true);
    }

    public async void Execute(object? parameter)
    {
        if (_isExecuting) return;

        _isExecuting = true;
        RaiseCanExecuteChanged();

        try
        {
            await _execute((T?)parameter);
        }
        finally
        {
            _isExecuting = false;
            RaiseCanExecuteChanged();
        }
    }

    /// <summary>
    /// 手动触发 CanExecute 重新评估
    /// </summary>
    public void RaiseCanExecuteChanged()
        => CommandManager.InvalidateRequerySuggested();
}
