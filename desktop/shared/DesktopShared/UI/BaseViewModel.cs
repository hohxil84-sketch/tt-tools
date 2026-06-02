using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace TTShared.UI;

/// <summary>
/// ViewModel 基类
/// 提供 INotifyPropertyChanged 的标准实现。
/// 所有业务模块的 ViewModel 应继承此类。
/// </summary>
public abstract class BaseViewModel : INotifyPropertyChanged
{
    /// <summary>属性变更通知</summary>
    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>
    /// 触发属性变更通知
    /// </summary>
    /// <param name="propertyName">属性名称（由 CallerMemberName 自动填充）</param>
    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));

    /// <summary>
    /// 设置属性值并在变更时自动通知
    /// </summary>
    /// <typeparam name="T">属性类型</typeparam>
    /// <param name="field">字段引用</param>
    /// <param name="value">新值</param>
    /// <param name="propertyName">属性名称</param>
    /// <returns>是否发生变更</returns>
    protected bool SetProperty<T>(ref T field, T value,
        [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }
}
