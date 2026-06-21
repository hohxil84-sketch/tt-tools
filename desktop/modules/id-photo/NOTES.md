# NOTES.md - desktop-id-photo

## 设计备注

证件照换底色桌面入口、底色选择、规格选择、导出。

## 选型记录

桌面端技术栈：C# / .NET 8 / WPF（MVVM 模式），无额外第三方依赖。
本地处理引擎：复用 local-worker-id-photo（Python / OpenCV），通过 stdin/stdout JSON 协议通信。
桌面端公共层：依赖 desktop-shared（TTShared.dll）提供的 LocalRuntimeClient、JobManager、BaseViewModel、FileSystemService 等。

## 架构说明

```
IdPhotoView (XAML) → IdPhotoViewModel → IdPhotoService → LocalRuntimeClient
                                                                ↓ (stdin/stdout)
                                                         id_photo_router.py
                                                                ↓
                                                  local-worker/modules/id-photo/
                                                    (processor.py + specifications.py)
```

## 功能列表

- 图片输入：文件选择对话框 + 拖拽上传
- 证件照规格选择：下拉框展示 7 种规格（1寸、2寸、小1寸、小2寸、大一寸、大二寸、5寸）
- 底色选择：色块网格展示 6 种颜色（白、红、蓝、浅蓝、深红、灰），支持选中高亮
- 处理选项：DPI（72-600）、自动检测背景、边缘羽化
- 结果预览：处理详情展示（输入文件、输出尺寸、使用规格、目标底色、遮罩方法、输出路径）
- 历史列表：成功/失败计数、规格和底色摘要
- 导出：支持保存为 PNG/JPEG 到指定位置
- 状态栏：引擎状态指示灯、进度条、处理消息

## 已知限制

- 预览区暂不显示处理后的图片缩略图（依赖图片文件读取）。
- 导出功能依赖处理结果中的输出文件存在。
- Python router 的 local-worker 路径依赖（parents[4]）基于模块在项目中的固定位置。
