"""
local-worker/shared/runtime — CPU/GPU 能力检测和进程协议

CPU/GPU 检测用于判断当前机器是否具备运行 ONNX/GPU 模型的条件，
并提供 CPU fallback 信息。进程协议预留子进程通信的基础结构。
"""

import json
import os
import platform
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CpuInfo:
    """CPU 信息。"""

    arch: str  # 架构，例如 x86_64、AMD64
    cores_physical: int  # 物理核心数
    cores_logical: int  # 逻辑核心数
    max_frequency_mhz: Optional[int] = None  # 最大频率，未知时为 None
    brand: Optional[str] = None  # 品牌名，如 "Intel(R) Core(TM) i7-10750H"
    supports_avx2: bool = False  # 是否支持 AVX2（ONNX 常用指令集）


@dataclass
class GpuInfo:
    """GPU 信息。"""

    available: bool  # 是否有可用 GPU
    name: Optional[str] = None  # GPU 名称
    vendor: Optional[str] = None  # 厂商：NVIDIA / AMD / Intel
    memory_mb: Optional[int] = None  # 显存大小（MB），未知时为 None
    cuda_available: bool = False  # CUDA 是否可用
    dml_available: bool = False  # DirectML 是否可用（Windows ONNX Runtime）


@dataclass
class RuntimeInfo:
    """综合运行时信息。"""

    platform: str  # 操作系统
    python_version: str  # Python 版本
    cpu: CpuInfo
    gpu: GpuInfo


# ---- CPU 检测 ----

def _get_cpu_count_windows() -> tuple:
    """Windows 下获取 CPU 物理和逻辑核心数（通过 wmic）。"""
    try:
        # 获取物理核心数
        result = subprocess.run(
            ["wmic", "cpu", "get", "NumberOfCores"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        physical = 0
        if len(lines) >= 2:
            # 第一行是表头 "NumberOfCores"，第二行是值
            try:
                physical = int(lines[1])
            except (ValueError, IndexError):
                pass

        # 获取逻辑核心数
        result2 = subprocess.run(
            ["wmic", "cpu", "get", "NumberOfLogicalProcessors"],
            capture_output=True, text=True, timeout=10,
        )
        lines2 = [l.strip() for l in result2.stdout.splitlines() if l.strip()]
        logical = 0
        if len(lines2) >= 2:
            try:
                logical = int(lines2[1])
            except (ValueError, IndexError):
                pass

        # 获取 CPU 名称
        result3 = subprocess.run(
            ["wmic", "cpu", "get", "Name"],
            capture_output=True, text=True, timeout=10,
        )
        lines3 = [l.strip() for l in result3.stdout.splitlines() if l.strip()]
        brand = None
        if len(lines3) >= 2:
            brand = lines3[1] or None

        return physical, logical, brand
    except Exception:
        return 0, 0, None


def _check_avx2() -> bool:
    """检查当前 CPU 是否支持 AVX2 指令集。

    Windows 下通过检查环境变量或尝试导入 CPU 特性检测库。
    简单方式：在 x86_64 且较新的 CPU 上假定支持。
    更精确的检测在使用 ONNX 模型加载模块时会做。
    """
    # Windows 下大多数 2013 年后的 x86_64 CPU 都支持 AVX2
    # 更精确的检测可引入 cpuinfo 库，但共享层不强制依赖
    if platform.machine().lower() in ("x86_64", "amd64", "i386"):
        # 尝试通过 PowerShell 检测
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-CimInstance Win32_Processor).Caption"],
                capture_output=True, text=True, timeout=10,
            )
            cpu_name = result.stdout.strip()
            # AVX2 在 Intel Haswell (2013) 和 AMD Excavator (2015) 后引入
            # 简单启发式：排除很老的 CPU 型号
            old_patterns = ["Core 2", "Pentium", "Celeron", "Atom", "Xeon 3", "Xeon 5"]
            if any(p in cpu_name for p in old_patterns):
                return False
            return True
        except Exception:
            pass
        return True  # 如果能到这里，大概率支持
    return False


def detect_cpu_info() -> CpuInfo:
    """检测当前 CPU 信息。

    返回 CpuInfo，包含核心数、架构、AVX2 支持等。
    CPU fallback 始终可用——所有本地 worker 模块必须支持。
    """
    arch = platform.machine() or "unknown"
    cores_physical = 0
    cores_logical = 0
    brand = None

    if sys.platform == "win32":
        # Windows：使用 wmic 获取精确核心数
        cores_physical, cores_logical, brand = _get_cpu_count_windows()
    else:
        cores_logical = os.cpu_count() or 0
        cores_physical = cores_logical  # 非 Windows 无法精确区分时对齐

    # 兜底使用 os.cpu_count()
    if cores_logical <= 0:
        cores_logical = os.cpu_count() or 0
    if cores_physical <= 0:
        cores_physical = max(1, cores_logical // 2)

    # AVX2 支持检测
    supports_avx2 = _check_avx2()

    return CpuInfo(
        arch=arch,
        cores_physical=max(1, cores_physical),
        cores_logical=max(1, cores_logical),
        max_frequency_mhz=None,  # Windows 下可通过额外 wmic 获取，暂不实现
        brand=brand,
        supports_avx2=supports_avx2,
    )


# ---- GPU 检测 ----

def _check_cuda_available() -> bool:
    """检查 CUDA 是否可用（通过 nvidia-smi）。"""
    try:
        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_nvidia_gpu_name() -> Optional[str]:
    """通过 nvidia-smi 获取 GPU 名称。"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


def _get_nvidia_memory_mb() -> Optional[int]:
    """通过 nvidia-smi 获取 GPU 显存大小（MB）。"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            mem_str = result.stdout.strip().split("\n")[0].strip()
            return int(float(mem_str))
    except Exception:
        pass
    return None


def _check_dml_available() -> bool:
    """检查 DirectML 是否可用（仅 Windows）。

    DirectML 是 Windows 上的 ONNX Runtime GPU 后端，
    支持 AMD/Intel/NVIDIA 显卡，无需 CUDA。
    简单检测方式：检查是否在 Windows 上且有 GPU 设备。
    """
    if sys.platform != "win32":
        return False
    # 通过 WMI 或 PowerShell 检测是否有 GPU
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_VideoController).Name"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except Exception:
        pass
    return False


def detect_gpu_info() -> GpuInfo:
    """检测当前 GPU 信息。

    返回 GpuInfo，包含 CUDA/DirectML 可用性、GPU 名称和显存。
    注意：本模块只检测，不强制要求 GPU——所有模块必须支持 CPU fallback。
    """
    cuda_available = _check_cuda_available()
    dml_available = _check_dml_available()
    gpu_name = None
    memory_mb = None

    if cuda_available:
        gpu_name = _get_nvidia_gpu_name()
        memory_mb = _get_nvidia_memory_mb()
        vendor = "NVIDIA"
    elif dml_available:
        # DirectML 可用但 CUDA 不可用，可能是 AMD 或 Intel 显卡
        vendor = "AMD/Intel"
    else:
        vendor = None

    available = cuda_available or dml_available

    return GpuInfo(
        available=available,
        name=gpu_name,
        vendor=vendor,
        memory_mb=memory_mb,
        cuda_available=cuda_available,
        dml_available=dml_available,
    )


# ---- 综合检测 ----

def get_runtime_info() -> RuntimeInfo:
    """获取完整的运行时信息（CPU + GPU + 平台）。

    这是推荐的外部调用入口，返回 RuntimeInfo 供各模块判断执行策略。
    """
    return RuntimeInfo(
        platform=sys.platform,
        python_version=sys.version,
        cpu=detect_cpu_info(),
        gpu=detect_gpu_info(),
    )


# ---- 进程协议基础（预留） ----

@dataclass
class ProcessMessage:
    """子进程间通信的消息结构。

    本地 worker 按设备绑定方式可能以子进程运行，
    ProcessMessage 定义统一的 IPC 消息格式，预留后续扩展。
    """

    message_type: str  # 消息类型：task、status、result、cancel、health
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    task_id: Optional[str] = None

    def to_bytes(self) -> bytes:
        """序列化为 bytes，用于管道或 socket 传输。

        消息长度前缀使用 4 字节大端无符号整数。
        """
        body = json.dumps({
            "type": self.message_type,
            "payload": self.payload,
            "request_id": self.request_id,
            "task_id": self.task_id,
        }, ensure_ascii=False).encode("utf-8")
        # 4 字节长度前缀 + 消息体
        return struct.pack("!I", len(body)) + body

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProcessMessage":
        """从 bytes 反序列化。"""
        # 解析 4 字节长度前缀
        if len(data) < 4:
            raise ValueError("消息数据不足 4 字节，无法读取长度前缀")
        body_len = struct.unpack("!I", data[:4])[0]
        body = json.loads(data[4:4 + body_len].decode("utf-8"))
        return cls(
            message_type=body.get("type", ""),
            payload=body.get("payload", {}),
            request_id=body.get("request_id"),
            task_id=body.get("task_id"),
        )


# ---- 健康检查入口 ----

def healthcheck() -> RuntimeInfo:
    """本地 worker 健康检查入口。

    返回 RuntimeInfo 即表示 worker 环境正常。
    如果无法返回有效的 RuntimeInfo 则抛出 AppError。
    """
    from .errors import AppError, ErrorCode

    info = get_runtime_info()
    if info.cpu.cores_logical <= 0:
        raise AppError(
            ErrorCode.RUNTIME_CPU_UNSUPPORTED,
            "无法检测到有效 CPU 核心数",
        )
    return info
