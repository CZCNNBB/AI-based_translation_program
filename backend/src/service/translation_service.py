import os
import sys
from typing import Any, Dict, Optional

# 定义根目录、后端目录和翻译引擎
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# 定义后端目录
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

# 将根目录添加到系统路径中，确保可以导入项目模块
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from translator_main import TranslationEngine


class translation_Service:
    # 初始化翻译服务，加载配置文件
    def __init__(self, config_path: Optional[str] = None):
        self.root_dir = ROOT_DIR
        if config_path is None:
            config_path = os.path.join(BACKEND_DIR, "config.yaml")
        self.engine = TranslationEngine(config_path=config_path)

    # 单文本翻译方法
    def translate_text(
        self,
        text: str,
        target_lang: Optional[str],
        domain: Optional[str],
        glossary: Optional[str],
        summary: Optional[bool],
    ) -> Dict[str, Any]:
        return self.engine.translate(
            text=text,
            target_lang=target_lang,
            domain=domain,
            glossary=glossary,
            summary=summary,
        )

    # 批量翻译方法
    def batch_translate(
        self,
        input_dir: Optional[str],
        output_dir: Optional[str],
        target_lang: Optional[str],
        domain: Optional[str],
        glossary: Optional[str],
        summary: Optional[bool],
        file_pattern: Optional[str],
        delete_after: Optional[bool],
        batch_config: Optional[str],
    ) -> Dict[str, Any]:

        if batch_config:
            resolved_config = self._resolve_batch_config(batch_config)
            return self.engine.batch_translate_from_config(resolved_config)

        resolved_input_dir = self._resolve_path(input_dir)
        resolved_output_dir = self._resolve_path(output_dir)

        return self.engine.batch_translate_files(
            input_dir=resolved_input_dir,
            output_dir=resolved_output_dir,
            target_lang=target_lang,
            domain=domain,
            glossary=glossary,
            summary=summary,
            file_pattern=file_pattern,
            delete_after=delete_after,
        )

    # 清除语言缓存方法
    def clear_cache(self) -> int:
        return self.engine.clear_language_cache()

    # 获取缓存统计信息方法
    def cache_stats(self) -> Dict[str, Any]:
        return self.engine.get_cache_stats()

    # 解析路径方法，支持相对路径转换为绝对路径
    def _resolve_path(self, path_value: Optional[str]) -> Optional[str]:
        if not path_value:
            return path_value
        if os.path.isabs(path_value):
            return path_value
        return os.path.join(self.root_dir, path_value)

    # 解析批量配置文件路径，支持相对路径转换为绝对路径
    def _resolve_batch_config(self, path_value: str) -> str:
        if os.path.isabs(path_value):
            return path_value
        return os.path.join(BACKEND_DIR, path_value)
