"""
local-worker/shared/file_io — 文件 IO 工具

提供本地 worker 通用的文件读写、目录管理和文件信息查询。
所有路径操作使用 pathlib，确保 Windows 和 POSIX 兼容性。
"""

import glob as glob_module
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# 支持的文件类型后缀
SUPPORTED_IMAGE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif",
    ".webp", ".gif", ".ico",
}
SUPPORTED_PDF_SUFFIX = ".pdf"
SUPPORTED_DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx"}

# 默认文件大小上限：100MB
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024


@dataclass
class FileInfo:
    """文件信息。"""

    path: str  # 完整路径
    name: str  # 不含路径的文件名
    suffix: str  # 扩展名（小写），如 ".png"
    size_bytes: int  # 文件大小（字节）
    is_image: bool = False  # 是否为图片
    is_pdf: bool = False  # 是否为 PDF


# ---- 基础文件操作 ----


def read_file_bytes(file_path: str) -> bytes:
    """读取文件全部内容的二进制数据。

    读取失败时抛出 AppError(LOCAL_FILE_READ_ERROR)。
    """
    from .errors import AppError, ErrorCode

    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        raise AppError(
            ErrorCode.FILE_NOT_FOUND,
            f"文件未找到: {file_path}",
            details={"path": file_path},
        )
    except PermissionError:
        raise AppError(
            ErrorCode.FILE_READ_ERROR,
            f"文件权限不足: {file_path}",
            details={"path": file_path},
        )
    except Exception as e:
        raise AppError(
            ErrorCode.FILE_READ_ERROR,
            f"文件读取失败: {e}",
            details={"path": file_path, "error": str(e)},
        )


def write_file_bytes(
    file_path: str,
    data: bytes,
    overwrite: bool = False,
    ensure_dir: bool = True,
) -> str:
    """将二进制数据写入文件。

    参数：
        file_path: 目标路径
        data: 要写入的数据
        overwrite: 是否覆盖已存在文件（默认否）
        ensure_dir: 是否自动创建父目录（默认是）
    返回：写入后的文件绝对路径。
    """
    from .errors import AppError, ErrorCode

    path = Path(file_path)

    # 自动创建父目录
    if ensure_dir:
        path.parent.mkdir(parents=True, exist_ok=True)

    # 文件已存在且不允许覆盖
    if path.exists() and not overwrite:
        raise AppError(
            ErrorCode.FILE_WRITE_ERROR,
            f"文件已存在且 overwrite=False: {file_path}",
            details={"path": file_path},
        )

    try:
        path.write_bytes(data)
    except PermissionError:
        raise AppError(
            ErrorCode.FILE_WRITE_ERROR,
            f"文件写入权限不足: {file_path}",
            details={"path": file_path},
        )
    except Exception as e:
        raise AppError(
            ErrorCode.FILE_WRITE_ERROR,
            f"文件写入失败: {e}",
            details={"path": file_path, "error": str(e)},
        )

    return str(path.resolve())


# ---- 文件信息 ----

def get_file_info(file_path: str) -> FileInfo:
    """获取文件的基本信息。

    如果文件不存在，抛出 AppError(LOCAL_FILE_NOT_FOUND)。
    """
    from .errors import AppError, ErrorCode

    path = Path(file_path)
    if not path.is_file():
        raise AppError(
            ErrorCode.FILE_NOT_FOUND,
            f"文件未找到或不是常规文件: {file_path}",
            details={"path": file_path},
        )

    suffix = path.suffix.lower()
    stat = path.stat()

    return FileInfo(
        path=str(path.resolve()),
        name=path.name,
        suffix=suffix,
        size_bytes=stat.st_size,
        is_image=suffix in SUPPORTED_IMAGE_SUFFIXES,
        is_pdf=suffix == SUPPORTED_PDF_SUFFIX,
    )


def validate_file(
    file_path: str,
    allowed_suffixes: Optional[List[str]] = None,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE,
) -> FileInfo:
    """校验文件是否存在、格式是否支持、大小是否超限。

    校验通过返回 FileInfo，否则抛出对应 AppError。
    """
    from .errors import AppError, ErrorCode

    info = get_file_info(file_path)

    # 校验文件大小
    if info.size_bytes > max_size_bytes:
        raise AppError(
            ErrorCode.FILE_TOO_LARGE,
            f"文件过大: {info.size_bytes} > {max_size_bytes} bytes",
            details={
                "path": file_path,
                "size_bytes": info.size_bytes,
                "max_size_bytes": max_size_bytes,
            },
        )

    # 校验文件格式
    if allowed_suffixes and info.suffix not in allowed_suffixes:
        raise AppError(
            ErrorCode.FILE_UNSUPPORTED_FORMAT,
            f"不支持的文件格式: {info.suffix}",
            details={
                "path": file_path,
                "suffix": info.suffix,
                "allowed_suffixes": allowed_suffixes,
            },
        )

    return info


# ---- 目录操作 ----

def ensure_directory(dir_path: str) -> str:
    """确保目录存在，不存在则创建。

    返回目录的绝对路径。
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return str(path.resolve())


def list_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = False,
    max_count: Optional[int] = None,
) -> List[str]:
    """列出目录下匹配的文件。

    参数：
        directory: 目标目录
        pattern: glob 匹配模式，默认 "*"
        recursive: 是否递归子目录
        max_count: 最大返回数量，None 表示不限制
    返回：文件路径列表（按名称排序）。
    """
    from .errors import AppError, ErrorCode

    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise AppError(
            ErrorCode.FILE_NOT_FOUND,
            f"目录未找到: {directory}",
            details={"directory": directory},
        )

    # 构造 glob 表达式
    if recursive:
        glob_expr = f"**/{pattern}"
    else:
        glob_expr = pattern

    files = []
    for entry in sorted(dir_path.glob(glob_expr)):
        if entry.is_file():
            files.append(str(entry.resolve()))
        if max_count and len(files) >= max_count:
            break

    return files


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """检查 target_path 是否在 base_dir 内（防止路径穿越攻击）。

    本地 worker 接收外部文件路径时应使用此函数做安全检查。
    """
    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False
