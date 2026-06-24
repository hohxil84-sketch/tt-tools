using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;

namespace TTTools.AuthDevice.Views;

public partial class LoginView : UserControl
{
    public LoginView()
    {
        InitializeComponent();
    }
}

/// <summary>
/// 布尔值取反转换器：用于 IsLoggingIn → IsEnabled 的反向绑定
/// </summary>
public class BoolInvertConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b ? !b : value;
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b ? !b : value;
}

/// <summary>
/// 布尔到登录按钮文字转换器
/// </summary>
public class BoolToLoginTextConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b && b ? "登录中..." : "登 录";
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
