from pydantic import BaseModel
from typing import Optional

# 单翻译请求模型
class TranslationRequest(BaseModel):
    text: str
    target_lang: Optional[str] = None   # 目标语言，默认值为 None，从 config.yaml 中读取
    domain: Optional[str] = None    # 领域，默认值为 None，从 config.yaml 中读取
    glossary: Optional[str] = None  # 术语表，默认值为 None，从 config.yaml 中读取
    summary: Optional[bool] = None  # 是否生成摘要，默认值为 None，从 config.yaml 中读取

# 批量翻译请求模型
class BatchTranslationRequest(BaseModel):
    input_dir: Optional[str] = None # 输入目录，默认值为 None，从 config.yaml 中读取
    output_dir: Optional[str] = None # 输出目录，默认值为 None，从 config.yaml 中读取
    target_lang: Optional[str] = None   # 目标语言，默认值为 None，从 config.yaml 中读取
    domain: Optional[str] = None    # 领域，默认值为 None，从 config.yaml 中读取
    glossary: Optional[str] = None  # 术语表，默认值为 None，从 config.yaml 中读取
    summary: Optional[bool] = None  # 是否生成摘要，默认值为 None，从 config.yaml 中读取
    file_pattern: Optional[str] = None  # 文件模式，默认值为 None，从 config.yaml 中读取
    delete_after: Optional[bool] = None # 是否删除输入文件，默认值为 None，从 config.yaml 中读取
    batch_config: Optional[str] = None  # 批量配置文件路径，默认值为 None，从 config.yaml 中读取

