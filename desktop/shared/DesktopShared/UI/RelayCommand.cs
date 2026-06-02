using System.Windows.Input;

namespace TTShared.UI;

/// <summary>
/// 通用命令实现
/// 用于 WPF 数据绑定，替代代码后置中的事件处理。
/// </summary>
public class RelayCommand : ICommand
{
    private readonly Action _execute;
    private readonly Func<bool>? _canExecute;

    /// <summary>
    /// 创建 RelayCommand
    /// </summary>
    /// <param name="execute">执行动作</param>
    /// <param name="canExecute">可执行条件（可选）</param>
    public RelayCommand(Action execute, Func<bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    /// <summary>可执行状态变更事件</summary>
    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }

    /// <summary>判断当前是否可以执行</summary>
    public bool CanExecute(object? parameter)
        => _canExecute?.Invoke() ?? true;

    /// <summary>执行命令</summary>
    public void Execute(object? parameter)
        => _execute();

    /// <summary>手动触发 CanExecute 重新评估</summary>
    public void RaiseCanExecuteChanged()
        => CommandManager.InvalidateRequerySuggested();
}

/// <summary>
/// 带参数的通用命令实现
/// </summary>
/// <typeparam name="T">参数类型</typeparam>
public class RelayCommand<T> : ICommand
{
    private readonly Action<T?> _execute;
    private readonly Func<T?, bool>? _canExecute;

    /// <summary>
    /// 创建 RelayCommand
    /// </summary>
    /// <param name="execute">执行动作</param>
    /// <param name="canExecute">可执行条件（可选）</param>
    public RelayCommand(Action<T?> execute, Func<T?, bool>? canExecute = null)
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
        => _canExecute?.Invoke((T?)parameter) ?? true;

    public void Execute(object? parameter)
        => _execute((T?)parameter);

    public void RaiseCanExecuteChanged()
        => CommandManager.InvalidateRequerySuggested();
}
