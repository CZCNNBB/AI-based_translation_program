from contextlib import asynccontextmanager
import logging
import os
import requests
import yaml
from fastapi import FastAPI

logger = logging.getLogger("server.lifespan")

# 检查 Ollama 服务是否可用
def check_ollama():
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    config_path = os.path.join(backend_dir, "config.yaml")
    config_data = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
    ollama_config = config_data.get("ollama", {}) if isinstance(config_data, dict) else {}
    host = str(ollama_config.get("host", "localhost"))
    port = str(ollama_config.get("port", 11434))
    base_url = f"http://{host}:{port}"
    url = f"{base_url}/api/tags"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logger.info("✅ Ollama 连接成功")
    except Exception as e:
        logger.error(f"❌ Ollama 连接失败: {str(e)}")

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 系统正在启动...")
    check_ollama()
    yield
    logger.info("🛑 系统正在关闭...")
