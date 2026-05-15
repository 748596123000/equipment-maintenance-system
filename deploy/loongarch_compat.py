"""
LoongArch架构兼容性检测工具
用于在银河麒麟+LoongArch环境下检测系统兼容性
"""

import os
import sys
import platform
import subprocess


def check_architecture():
    """检测CPU架构"""
    arch = platform.machine()
    print(f"CPU架构: {arch}")

    if arch == "loongarch64":
        print("  ✓ LoongArch64架构 - 符合赛题要求")
        return True
    else:
        print(f"  ⚠ 当前架构为{arch}，非LoongArch64")
        print("  提示: 开发阶段可在x86_64上运行，部署时需适配LoongArch")
        return False


def check_os():
    """检测操作系统"""
    print(f"操作系统: {platform.platform()}")

    try:
        with open("/etc/os-release", "r") as f:
            content = f.read()
            if "Kylin" in content:
                print("  ✓ 检测到银河麒麟(Kylin)操作系统")
                return True
            else:
                print("  ⚠ 未检测到银河麒麟操作系统")
                return False
    except FileNotFoundError:
        print("  ⚠ 无法读取系统信息")
        return False


def check_python():
    """检测Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 10:
        print("  ✓ Python版本满足要求(>=3.10)")
        return True
    else:
        print("  ✗ Python版本过低，需要3.10+")
        return False


def check_dependencies():
    """检测关键依赖"""
    print("\n关键依赖检测:")

    dependencies = {
        "streamlit": "Streamlit前端框架",
        "fastapi": "FastAPI后端框架",
        "uvicorn": "ASGI服务器",
        "chromadb": "向量数据库",
        "fitz": "PyMuPDF(PDF解析)",
        "dashscope": "通义千问SDK",
        "langchain": "LangChain框架",
    }

    all_ok = True
    for package, desc in dependencies.items():
        try:
            __import__(package)
            print(f"  ✓ {desc} ({package})")
        except ImportError:
            print(f"  ✗ {desc} ({package}) - 未安装")
            all_ok = False

    return all_ok


def check_chroma_compat():
    """检测ChromaDB兼容性"""
    print("\nChromaDB兼容性检测:")

    db_impl = os.environ.get("CHROMA_DB_IMPL", "default")
    print(f"  当前后端: {db_impl}")

    if platform.machine() == "loongarch64":
        if db_impl == "duckdb+parquet":
            print("  ✓ 已配置LoongArch兼容后端")
            return True
        else:
            print("  ⚠ 建议设置 CHROMA_DB_IMPL=duckdb+parquet")
            return False

    print("  ✓ 非LoongArch架构，使用默认后端")
    return True


def check_network():
    """检测网络连通性（通义千问API）"""
    print("\n网络连通性检测:")

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        print("  ⚠ DASHSCOPE_API_KEY未配置")
        return False

    try:
        import httpx
        resp = httpx.get("https://dashscope.aliyuncs.com", timeout=5)
        if resp.status_code < 500:
            print("  ✓ 通义千问API可达")
            return True
        else:
            print("  ⚠ 通义千问API响应异常")
            return False
    except Exception as e:
        print(f"  ⚠ 网络检测失败: {e}")
        return False


def run_all_checks():
    """运行所有检测"""
    print("=" * 50)
    print("  LoongArch兼容性检测工具")
    print("  设备检修知识检索与作业系统")
    print("=" * 50)
    print()

    results = {
        "架构检测": check_architecture(),
        "系统检测": check_os(),
        "Python检测": check_python(),
        "依赖检测": check_dependencies(),
        "ChromaDB兼容性": check_chroma_compat(),
        "网络检测": check_network(),
    }

    print("\n" + "=" * 50)
    print("  检测结果汇总")
    print("=" * 50)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 未通过"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print()
    if all_passed:
        print("  🎉 所有检测通过，系统可正常运行")
    else:
        print("  ⚠ 部分检测未通过，请参考上方提示修复")

    return all_passed


if __name__ == "__main__":
    run_all_checks()
