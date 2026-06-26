# PROGRESS.md - desktop-id-photo

## 当前状态

`DEVELOPED`

## 分支

`feature/desktop-id-photo`

## 已完成

- 已创建模块文档骨架。
- 已创建 DesktopIdPhoto.csproj（net8.0-windows WPF Library，引用 TTShared）。
- 已创建 Python router 脚本 (id_photo_router.py)，支持 ping / process_id_photo / list_specs / list_background_colors / shutdown 5 个动作。
- 已创建 C# Models: IdPhotoResult、PhotoSpecItem、BackgroundColorItem。
- 已创建 IdPhotoService（封装 LocalRuntimeClient 通信，支持处理、规格查询、底色查询、任务跟踪）。
- 已创建 IdPhotoViewModel（MVVM ViewModel，管理输入文件选择、底色/规格选择、处理触发、结果展示、导出）。
- 已创建 IdPhotoView（WPF UserControl，包含拖拽输入区、规格下拉框、底色色块选择器、处理选项、结果预览、历史列表、导出按钮）。
- 已创建 20 项单元测试（Models 和 ViewModels 全覆盖），全部通过。
- Python router 4 项运行测试全部通过（ping / list_specs / list_background_colors / shutdown）。
- 关键逻辑已添加中文注释。

## 未完成

- 待集成到 app-shell 主窗口导航。
- 待执行与 local-worker 的完整联调测试。

## 测试记录

```
日期：2026-06-21
测试命令：dotnet test（DesktopIdPhoto.Tests）
结果：通过
详情：20 项测试全部通过，0 失败，0 警告
中文备注：覆盖 IdPhotoResult 反序列化、显示属性、PhotoSpecItem 显示属性、BackgroundColorItem 显示属性、IdPhotoViewModel 初始状态/Dpi/输入文件/规格/底色/结果/清除/失败计数/运行状态/默认构造函数/服务状态/选项属性
```

```
日期：2026-06-21
测试命令：echo '{...}' | python id_photo_router.py（stdin/stdout 协议测试）
结果：通过
详情：4 个动作（ping、list_specs、list_background_colors、shutdown）全部返回 success=true
中文备注：Python router 通过 stdin/stdout JSON 协议正确响应，规格返回 7 项，底色返回 6 项
```

## Bug 记录

### 2026-06-26: 证件照换底色功能完全不可用 — 下拉框空白 + 底色色块空白 + 无缩略图

**现象：**
- 规格下拉框为空，无法选择证件照规格
- 底色色块列表为空，无法选择目标底色
- 输入图片区域只显示文字文件名，无缩略图预览

**根因：**
1. `IdPhotoService` 默认构造函数未创建 `_runtimeClient`，导致服务永远不可用
2. `IdPhotoViewModel` 默认构造函数传入 `_idPhotoService = null`，`InitializeAsync()` 直接返回
3. `IdPhotoView` 缺少 `Loaded` 事件处理，`InitializeAsync()` 从未被调用

**修复点：**
1. `IdPhotoService.cs`: 默认构造函数中创建 `_runtimeClient` 并绑定事件
2. `IdPhotoViewModel.cs`: 默认构造函数改为创建 `IdPhotoService`；新增硬编码默认规格（7项）和底色（6项）确保 UI 永不为空；新增 `InputImageThumbnail` / `InputFileFormat` 属性和缩略图加载逻辑
3. `IdPhotoView.xaml.cs`: 添加 `Loaded` 事件，调用 `InitializeAsync()`
4. `IdPhotoView.xaml`: 输入区域改为缩略图 + 文件名 + 格式展示
5. `InitializeAsync`: 将 `useCache: false` 改为 `useCache: true` 避免重复调 worker；新增 `Count > 0` 保护防止 worker 返回空列表时清空硬编码默认值

**测试命令：** `dotnet test`
**测试结果：** 23 项测试全部通过，0 失败

### 2026-06-26: 换底色不准确 — 背景检测 + 遮罩精度 + 色值不一致

**现象：**
- 换底色后人物边缘有原背景色残留或过度切割
- UI 显示的色块颜色与实际替换颜色不一致

**根因：**
1. `processor.py`: 背景色检测用均值（`np.mean`）易被边缘人物像素污染
2. `processor.py`: 颜色距离阈值硬编码 45，不适应不同照片的背景均匀度
3. `processor.py`: 形态学开运算核 5×5 太大，头发等细节被抹掉
4. `IdPhotoViewModel.cs`: 硬编码 RGB 值与 Python `specifications.py` 不一致

**修复点：**
1. `processor.py` - `detect_background_color()`: 用 `np.median` 替代 `np.mean`
2. `processor.py` - `_create_color_mask()`: 自适应阈值（基于边缘距离标准差动态调整）；开运算核从 5×5 缩到 3×3
3. `processor.py` - `_refine_mask_edge()`: 羽化核根据图像分辨率自适应（3~11px）
4. `processor.py` - `_create_grabcut_mask()`: 形态学核从 5×5 缩到 3×3
5. `processor.py` - `create_foreground_mask()`: 质量检查上限从 90% 降到 85%
6. `IdPhotoViewModel.cs`: 对齐色值为 Python 实际值（红色 #DB0000, 蓝色 #438EDB, 浅蓝 #64AAEB, 新增深红 #B40000）

**测试命令：** `python -m pytest tests/ -v` + `dotnet test`
**测试结果：** Python 58/58 + C# 23/23，全部通过

### 2026-06-26: JPEG/BMP 导出失败 — router 未传 output_format 导致格式回退为 PNG

**现象：**
- 用户在格式下拉框选择 JPEG 或 BMP 后点击导出，导出的文件格式不正确或导出失败

**根因：**
`id_photo_router.py` 的 `handle_process_id_photo()` 解析了 `output_format` 参数并正确修改了输出路径扩展名（`.jpeg`→`.jpg`），但调用 `process_id_photo_from_path()` 时没有传入 `output_format` 参数。函数默认 `output_format="png"`，导致内部再次将扩展名改回 `.png`，`cv2.imwrite` 实际写入的是 PNG 格式数据。

**修复点：**
在 `id_photo_router.py` 第 209 行，向 `process_id_photo_from_path()` 传入 `output_format=safe_ext`，确保格式参数全链路贯通。

**测试命令：** `python -c "..."` 端到端格式测试
**测试结果：** JPEG 输出验证有效（header `FF D8 FF`），BMP 输出验证有效（header `BM`）

### 2026-06-26: 证件照规格默认选 1寸 + 底色默认选白色

**现象：**
- 用户打开页面后规格下拉框和底色色块无默认选中项，需要手动选择

**根因：**
`IdPhotoViewModel` 构造函数中虽调用 `InitializeDefaultSpecs()` 和 `InitializeDefaultColors()` 填充了列表，但未设置 `SelectedSpec` 和 `SelectedBackgroundColor`。

**修复点：**
1. `IdPhotoViewModel.cs`: 构造函数中 `InitializeDefaultSpecs()` 后添加 `SelectedSpec = AvailableSpecs.FirstOrDefault()` 和 `SelectedBackgroundColor = AvailableBackgroundColors.FirstOrDefault()`
2. 添加 `using System.Linq;` 以支持 `FirstOrDefault()`
3. `IdPhotoViewModelTests.cs`: 更新 3 项测试断言，适配默认选中行为

**测试命令：** `dotnet test`
**测试结果：** 23/23 全部通过

## 提交记录

```
2026-06-21: feat(desktop-id-photo): 完成证件照换底色桌面模块
  分支: feature/desktop-id-photo
  提交哈希: 1ca1c68
  已推送到 origin
  测试结果: 20 项 C# 单元测试 + 4 项 Python router 协议测试全部通过
  说明: 完成证件照换底色桌面入口、底色选择、规格选择、导出全流程
```

## 下一步

提交并推送到 origin，等待用户指定是否合并到 dev/full-product。
