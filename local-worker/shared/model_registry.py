r"""
local-worker/shared/model_registry — 模型注册表和加载

管理本地 worker 各模块使用的 ONNX/ML 模型，提供：
  - 模型注册和查询
  - 模型文件完整性校验（SHA256）
  - 按名称获取模型路径
  - 模型下载状态管理

模型文件必须存放在 D:\localPath\models 下，不得提交 Git。
"""

import hashlib
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# 模型默认存放根目录（优先使用 D:\localPath\models）
DEFAULT_MODEL_ROOT = os.environ.get(
    "TT_MODEL_ROOT",
    r"D:\localPath\models",
)


@dataclass
class ModelInfo:
    """单个模型的描述信息。

    对齐 environment/MODEL_REGISTRY.md 的登记字段。
    """

    name: str  # 模型名称，如 "rapidocr_det"
    display_name: str  # 中文显示名，如 "RapidOCR 检测模型"
    version: str  # 版本号
    file_name: str  # 文件名，如 "ch_PP-OCRv4_det.onnx"
    source: str  # 来源，如 "RapidOCR"
    url: Optional[str] = None  # 下载地址
    license_info: Optional[str] = None  # 许可证信息
    sha256: Optional[str] = None  # SHA256 校验值
    size_bytes: Optional[int] = None  # 文件大小（字节）
    requires_gpu: bool = False  # 是否必须 GPU（大多数模型都应支持 CPU fallback）
    status: str = "pending"  # pending / downloaded / verified / failed


class ModelRegistry:
    """模型注册表。

    每个本地 worker 模块在初始化时注册自己需要的模型。
    注册表负责：
      - 维护模型清单
      - 验证模型文件完整性
      - 提供模型路径查询

    用法：
        registry = ModelRegistry()
        registry.register(
            name="rapidocr_det",
            display_name="RapidOCR 检测模型",
            version="v4",
            file_name="ch_PP-OCRv4_det.onnx",
            source="RapidOCR",
            sha256="abc123...",
        )
        model_path = registry.get_model_path("rapidocr_det")
    """

    def __init__(self, model_root: Optional[str] = None) -> None:
        # 模型根目录，默认 D:\localPath\models
        self._model_root = model_root or DEFAULT_MODEL_ROOT
        # 注册表字典：name -> ModelInfo
        self._models: Dict[str, ModelInfo] = {}
        # 确保根目录存在
        os.makedirs(self._model_root, exist_ok=True)

    @property
    def model_root(self) -> str:
        """模型根目录路径。"""
        return self._model_root

    def register(self, **kwargs) -> ModelInfo:
        """注册一个模型。

        必须参数：name, display_name, version, file_name, source
        可选参数：url, license_info, sha256, size_bytes, requires_gpu
        """
        info = ModelInfo(**kwargs)
        self._models[info.name] = info
        return info

    def is_registered(self, name: str) -> bool:
        """检查模型是否已注册。"""
        return name in self._models

    def get_model_info(self, name: str) -> ModelInfo:
        """获取模型描述信息。"""
        from .errors import AppError, ErrorCode

        if name not in self._models:
            raise AppError(
                ErrorCode.MODEL_NOT_REGISTERED,
                f"模型未注册: {name}",
                details={"name": name},
            )
        return self._models[name]

    def get_model_path(self, name: str) -> str:
        """获取模型文件的完整路径。

        不保证文件存在——调用方在使用前需自行检查。
        """
        info = self.get_model_info(name)
        return os.path.join(self._model_root, info.file_name)

    def is_model_file_present(self, name: str) -> bool:
        """检查模型文件是否存在。"""
        info = self.get_model_info(name)
        path = os.path.join(self._model_root, info.file_name)
        return os.path.isfile(path)

    def verify_model(self, name: str) -> bool:
        """校验模型文件完整性（SHA256）。

        如果 ModelInfo 中登记了 sha256，则校验文件哈希。
        如果未登记 sha256，只检查文件是否存在。
        """
        from .errors import AppError, ErrorCode

        info = self.get_model_info(name)
        path = os.path.join(self._model_root, info.file_name)

        if not os.path.isfile(path):
            info.status = "failed"
            return False

        # 如果登记了 SHA256，进行哈希校验
        if info.sha256:
            actual_hash = _compute_sha256(path)
            if actual_hash.lower() != info.sha256.lower():
                info.status = "failed"
                raise AppError(
                    ErrorCode.MODEL_LOAD_FAILED,
                    f"模型文件 SHA256 校验失败: {info.file_name}",
                    details={
                        "name": name,
                        "expected_sha256": info.sha256,
                        "actual_sha256": actual_hash,
                    },
                )

        info.status = "verified"
        return True

    def list_models(self) -> List[ModelInfo]:
        """列出所有已注册模型。"""
        return list(self._models.values())

    def list_pending_models(self) -> List[ModelInfo]:
        """列出尚未下载的模型。"""
        return [
            info for info in self._models.values()
            if not self.is_model_file_present(info.name)
        ]

    def list_ready_models(self) -> List[ModelInfo]:
        """列出文件存在且校验通过的模型。"""
        ready = []
        for name in self._models:
            try:
                if self.verify_model(name):
                    ready.append(self._models[name])
            except Exception:
                pass
        return ready

    def __len__(self) -> int:
        return len(self._models)

    def __contains__(self, name: str) -> bool:
        return name in self._models


def _compute_sha256(file_path: str, chunk_size: int = 8192) -> str:
    """计算文件的 SHA256 哈希值。

    使用分块读取，避免大文件一次性加载到内存。
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()
