using System.Globalization;
using System.Windows.Data;

namespace TTTools.AuthDevice.Converters;

/// <summary>
/// 取字符串最后 N 位，超出部分用 "…" 省略。
/// 用法：{Binding DeviceId, Converter={StaticResource LastCharsConverter}, ConverterParameter=8}
/// </summary>
public class LastCharsConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        var str = value as string;
        if (string.IsNullOrEmpty(str)) return string.Empty;

        int count = 8;
        if (parameter is int n)
            count = n;
        else if (parameter is string s && int.TryParse(s, out var parsed))
            count = parsed;

        return str.Length <= count ? str : "…" + str.Substring(str.Length - count);
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
