using System.Globalization;
using System.Windows.Data;
using System.Windows.Media.Imaging;

namespace TTTools.AiRenderClient.Views;

/// <summary>
/// 将图片 URL 字符串转换为 WPF BitmapImage，用于 Image.Source 绑定。
/// 结合 Binding.IsAsync=true 可避免阻塞 UI 线程。
/// </summary>
public class UrlToBitmapConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is string url && !string.IsNullOrWhiteSpace(url))
        {
            try
            {
                var bitmap = new BitmapImage();
                bitmap.BeginInit();
                bitmap.UriSource = new Uri(url);
                bitmap.CacheOption = BitmapCacheOption.OnLoad;
                bitmap.EndInit();
                return bitmap;
            }
            catch
            {
                return null;
            }
        }
        return null;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotImplementedException();
}
