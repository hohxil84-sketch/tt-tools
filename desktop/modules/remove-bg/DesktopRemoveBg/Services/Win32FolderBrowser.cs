using System.Runtime.InteropServices;

namespace TTTools.RemoveBg.Services;

/// <summary>
/// Win32 文件夹浏览对话框（SHBrowseForFolder）
/// WPF 原生项目不依赖 WinForms，使用 P/Invoke 实现文件夹选择。
/// </summary>
internal static class Win32FolderBrowser
{
    /// <summary>
    /// 打开文件夹浏览对话框，返回用户选择的路径（取消则返回 null）。
    /// </summary>
    /// <param name="title">对话框标题</param>
    /// <param name="initialPath">初始路径（可选）</param>
    public static string? Browse(string title, string? initialPath = null)
    {
        var owner = GetActiveWindow();
        var bi = new BROWSEINFO
        {
            hwndOwner = owner,
            lpszTitle = title,
            ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE | BIF_EDITBOX,
            lpfn = IntPtr.Zero,
            lParam = IntPtr.Zero,
        };

        if (!string.IsNullOrEmpty(initialPath))
            bi.lParam = Marshal.StringToHGlobalUni(initialPath);

        var pidl = SHBrowseForFolder(ref bi);

        if (bi.lParam != IntPtr.Zero)
            Marshal.FreeHGlobal(bi.lParam);

        if (pidl == IntPtr.Zero)
            return null;

        try
        {
            var path = new char[260];
            if (SHGetPathFromIDList(pidl, path))
                return new string(path).TrimEnd('\0');
            return null;
        }
        finally
        {
            Marshal.FreeCoTaskMem(pidl);
        }
    }

    // ---- Win32 API ----

    private const uint BIF_RETURNONLYFSDIRS = 0x0001;
    private const uint BIF_NEWDIALOGSTYLE = 0x0040;
    private const uint BIF_EDITBOX = 0x0010;

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    private struct BROWSEINFO
    {
        public IntPtr hwndOwner;
        public IntPtr pidlRoot;
        public IntPtr pszDisplayName;
        public string lpszTitle;
        public uint ulFlags;
        public IntPtr lpfn;
        public IntPtr lParam;
        public int iImage;
    }

    [DllImport("shell32.dll", CharSet = CharSet.Auto)]
    private static extern IntPtr SHBrowseForFolder(ref BROWSEINFO lpbi);

    [DllImport("shell32.dll", CharSet = CharSet.Auto)]
    private static extern bool SHGetPathFromIDList(IntPtr pidl, char[] pszPath);

    [DllImport("user32.dll")]
    private static extern IntPtr GetActiveWindow();
}
