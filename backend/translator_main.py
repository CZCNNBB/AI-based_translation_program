#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Ollama 的多语言智能翻译引擎
支持专业领域术语定制，输出标准 JSON 格式结果
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

import requests
import yaml


# 常量定义
LANGUAGE_DETECTION_SAMPLE_SIZE = 500  # 语言检测采样长度
SUMMARY_GENERATION_SAMPLE_SIZE = 1000  # 摘要生成采样长度
RETRY_WAIT_TIME_BASE = 2  # 重试等待时间基数（指数退避）
SENTENCE_END_MARKERS = ['。', '！', '？', '.', '!', '?', '\n']  # 句子结束标记
WHITESPACE_MARKERS = [' ', '\t', '\n']  # 空白字符标记

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _resolve_summary_flag(has_summary: bool, has_no_summary: bool) -> Optional[bool]:
    """解析摘要参数
    
    Args:
        has_summary: 是否设置了 --summary 参数
        has_no_summary: 是否设置了 --no_summary 参数
    
    Returns:
        True: 强制启用摘要
        False: 强制禁用摘要
        None: 使用配置文件默认值
    """
    if has_no_summary:
        return False
    elif has_summary:
        return True
    return None


class TranslationEngine:
    """翻译引擎类，封装所有翻译逻辑"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化翻译引擎，加载配置文件
        
        Args:
            config_path: 配置文件路径
        """
        logger.info("========== 翻译引擎启动 ==========")
        logger.info(f"正在加载配置文件: {config_path}")

        self.config = self._load_config(config_path)
        self.ollama_config = self.config.get("ollama", {})
        self.translation_config = self.config.get("translation", {})
        self.file_management_config = self.config.get("file_management", {})
        self.summary_config = self.translation_config.get("summary_generation", {})
        self.base_url = f"http://{self.ollama_config.get('host', 'localhost')}:{self.ollama_config.get('port', 11434)}"
        
        # 初始化缓存字典
        self._lang_cache = {}  # 语言检测结果缓存
        lang_detection_config = self.translation_config.get("language_detection", {})
        self._cache_enabled = lang_detection_config.get('cache_enabled', True)  # 是否启用缓存
        
        logger.info(f"Ollama 服务地址: {self.base_url}")
        logger.info(f"使用模型: {self.ollama_config.get('model', 'llama3')}")
        logger.info(f"默认目标语言: {self.translation_config.get('default_target_lang', 'Chinese')}")
        logger.info(f"摘要生成: {'启用' if self.summary_config.get('enabled', True) else '禁用'}")
        logger.info(f"语言检测缓存: {'启用' if self._cache_enabled else '禁用'}")
        logger.info("========== 翻译引擎初始化完成 ==========")
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载 YAML 配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            logger.info(f"正在读取配置文件: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info("配置文件加载成功")
                return config

        except FileNotFoundError:
            logger.error(f"配置文件 {config_path} 不存在")
            print(json.dumps({"error": f"配置文件 {config_path} 不存在"}, ensure_ascii=False))
            sys.exit(1)

        except yaml.YAMLError as e:
            logger.error(f"配置文件解析错误: {str(e)}")
            print(json.dumps({"error": f"配置文件解析错误: {str(e)}"}, ensure_ascii=False))
            sys.exit(1)
    
    def _parse_glossary(self, glossary_str: Optional[str]) -> Dict[str, str]:
        """解析词汇表字符串
        
        Args:
            glossary_str: 词汇表字符串，支持 Key=Value 或 JSON 格式
            
        Returns:
            词汇字典
        """
        if not glossary_str:
            return {}
        
        # 尝试解析为 JSON
        if glossary_str.strip().startswith('{'):
            try:
                return json.loads(glossary_str)
            except json.JSONDecodeError:
                pass
        
        # 解析 Key=Value 格式
        glossary = {}
        for item in glossary_str.split(','):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                glossary[key.strip()] = value.strip()
        
        return glossary
    
    def _build_prompt(self, text: str, source_lang: str, target_lang: str,
                     domain: Optional[str] = None,
                     glossary: Optional[Dict[str, str]] = None, summary: bool = False) -> tuple:
        """构建 System Prompt 和 User Prompt
        
        Args:
            text: 待翻译文本
            source_lang: 源语言
            target_lang: 目标语言
            domain: 专业领域
            glossary: 词汇字典
            summary: 是否生成摘要
            
        Returns:
            (system_prompt, user_prompt) 元组
        """
        # 构建 System Prompt
        system_prompt = f"""你是一个专业的翻译助手，擅长多语言翻译。

任务：将以下{source_lang}文本翻译成{target_lang}

要求：
1. 准确、流畅地翻译
2. 保持原文的语气和风格
3. 只输出翻译后的{target_lang}文本，不要包含原文"""
        
        if domain:
            system_prompt += f"\n\n专业领域：{domain}。请使用该领域的专业术语和表达方式。"
        
        if glossary:
            glossary_text = "\n".join([f"- {key}: {value}" for key, value in glossary.items()])
            system_prompt += f"\n\n术语对照表（必须严格使用）：\n{glossary_text}"
        
        # 构建 User Prompt
        user_prompt = f"""待翻译文本：
{text}

请输出翻译结果。"""
        
        if summary:
            user_prompt += "\n\n翻译完成后，请用中文生成一个简短的摘要（不超过100字）。"
        
        return system_prompt, user_prompt
    
    def _call_ollama_api(self, system_prompt: str, user_prompt: str) -> str:
        """调用 Ollama API 进行翻译
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            API 响应文本
        """
        model = self.ollama_config.get('model', 'llama3')
        timeout = self.ollama_config.get('timeout', 60)
        max_retries = self.ollama_config.get('max_retries', 3)
        
        temperature = self.translation_config.get('temperature', 0.3)
        top_p = self.translation_config.get('top_p', 0.9)
        max_tokens = self.translation_config.get('max_tokens', 2000)
        
        logger.info(f"API 配置 - 模型: {model}, 超时: {timeout}s, 最大重试: {max_retries}")
        logger.info(f"生成参数 - Temperature: {temperature}, Top-p: {top_p}, 最大Token: {max_tokens}")
        
        url = f"{self.base_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens
            }
        }
        
        # 重试机制
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"发送 API 请求 (尝试 {attempt + 1}/{max_retries})...")
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                logger.info(f"API 响应状态码: {response.status_code}")
                
                result = response.json()
                if "message" in result and "content" in result["message"]:
                    logger.info(f"API 响应成功，返回内容长度: {len(result['message']['content'])} 字符")
                    return result["message"]["content"]
                else:
                    raise ValueError(f"API 返回格式异常: {result}")
                    
            except requests.exceptions.Timeout:
                last_error = f"API 请求超时（尝试 {attempt + 1}/{max_retries}）"
                logger.warning(last_error)
                if attempt < max_retries - 1:
                    wait_time = RETRY_WAIT_TIME_BASE ** attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)  # 指数退避
                    continue
            except requests.exceptions.ConnectionError:
                last_error = f"无法连接到 Ollama 服务（{self.base_url}），请确保服务已启动"
                logger.error(last_error)
                break
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP 错误: {e.response.status_code} - {e.response.text}"
                logger.error(last_error)
                break
            except Exception as e:
                last_error = f"API 调用失败: {str(e)}"
                logger.error(last_error)
                break
        
        raise Exception(last_error)
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """将长文本分割成多个段落
        
        Args:
            text: 待分割的文本
            
        Returns:
            文本段落列表
        """
        chunk_config = self.translation_config.get('chunk_translation', {})
        enabled = chunk_config.get('enabled', True)
        max_chunk_size = chunk_config.get('max_chunk_size', 2000)
        chunk_overlap = chunk_config.get('chunk_overlap', 100)
        
        # 如果未启用分段翻译或文本长度小于阈值，直接返回
        if not enabled or len(text) <= max_chunk_size:
            logger.info(f"文本长度 {len(text)} 字符，无需分段")
            return [text]
        
        logger.info(f"文本长度 {len(text)} 字符，启用分段翻译（单段最大 {max_chunk_size} 字符，重叠 {chunk_overlap} 字符）")
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # 计算当前段的结束位置
            end = start + max_chunk_size
            
            # 如果不是最后一段，尝试在句号、问号、感叹号等标点处分割
            if end < text_length:
                # 向后查找最近的句号、问号、感叹号
                for i in range(end, max(start, end - 200), -1):
                    if text[i] in SENTENCE_END_MARKERS:
                        end = i + 1
                        break
                else:
                    # 如果找不到合适的分割点，就在空格处分割
                    for i in range(end, max(start, end - 100), -1):
                        if text[i] in WHITESPACE_MARKERS:
                            end = i + 1
                            break
            
            # 提取当前段落
            chunk = text[start:end]
            chunks.append(chunk)
            
            logger.info(f"分段 [{len(chunks)}]: {start}-{end} ({len(chunk)} 字符)")
            
            # 计算下一段的起始位置（考虑重叠）
            start = end - chunk_overlap
            if start < 0:
                start = 0
        
        logger.info(f"文本已分割为 {len(chunks)} 个段落")
        return chunks
    
    def _detect_language_with_llm_cached(self, text: str) -> str:
        """使用 LLM 检测文本语言（带缓存）
        
        Args:
            text: 待检测的文本
            
        Returns:
            检测到的语言名称（中文标注）
        """
        # 如果缓存未启用，直接调用原始方法
        if not self._cache_enabled:
            return self._detect_language_with_llm(text)
        
        # 计算文本哈希作为缓存键
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # 检查缓存
        if text_hash in self._lang_cache:
            cached_lang = self._lang_cache[text_hash]
            logger.info(f"========== 步骤一：使用缓存的语言检测结果 ==========")
            logger.info(f"检测到的语言（缓存）: {cached_lang}")
            logger.info(f"缓存键: {text_hash}")
            return cached_lang
        
        # 缓存未命中，调用原始方法
        detected_lang = self._detect_language_with_llm(text)
        
        # 将结果存入缓存
        self._lang_cache[text_hash] = detected_lang
        logger.info(f"语言检测结果已缓存: {text_hash} → {detected_lang}")
        
        return detected_lang
    
    def clear_language_cache(self) -> int:
        """清除语言检测缓存
        
        Returns:
            清除的缓存条目数量
        """
        cache_size = len(self._lang_cache)
        self._lang_cache.clear()
        logger.info(f"语言检测缓存已清除，共清除 {cache_size} 条记录")
        return cache_size
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计字典
        """
        return {
            "cache_enabled": self._cache_enabled,
            "cache_size": len(self._lang_cache),
            "cache_keys": list(self._lang_cache.keys())
        }
    
    def _detect_language_with_llm(self, text: str) -> str:
        """使用 LLM 检测文本语言（内部方法）
        
        Args:
            text: 待检测的文本
            
        Returns:
            检测到的语言名称（中文标注）
        """
        logger.info("========== 步骤一：使用 LLM 检测语种 ==========")
        
        # 对于超长文本，只取前 LANGUAGE_DETECTION_SAMPLE_SIZE 字符用于语言检测
        sample_text = text[:LANGUAGE_DETECTION_SAMPLE_SIZE] if len(text) > LANGUAGE_DETECTION_SAMPLE_SIZE else text
        
        system_prompt = """你是一个语言识别专家，擅长识别各种语言的文本。

任务：识别文本的语言，并只输出语言名称（使用中文标注）。

常见语言映射：
- 英语/英文/English → 英语
- 中文/Chinese → 中文
- 日语/Japanese → 日语
- 韩语/Korean → 韩语
- 法语/French → 法语
- 德语/German → 德语
- 西班牙语/Spanish → 西班牙语
- 俄语/Russian → 俄语
- 阿拉伯语/Arabic → 阿拉伯语
- 葡萄牙语/Portuguese → 葡萄牙语
- 意大利语/Italian → 意大利语
- 荷兰语/Dutch → 荷兰语
- 波兰语/Polish → 波兰语
- 土耳其语/Turkish → 土耳其语
- 泰语/Thai → 泰语
- 越南语/Vietnamese → 越南语
- 印尼语/Indonesian → 印尼语
- 马来语/Malay → 马来语
- 希腊语/Greek → 希腊语
- 捷克语/Czech → 捷克语
- 瑞典语/Swedish → 瑞典语
- 丹麦语/Danish → 丹麦语
- 挪威语/Norwegian → 挪威语
- 芬兰语/Finnish → 芬兰语
- 匈牙利语/Hungarian → 匈牙利语
- 罗马尼亚语/Romanian → 罗马尼亚语
- 保加利亚语/Bulgarian → 保加利亚语
- 乌克兰语/Ukrainian → 乌克兰语
- 希伯来语/Hebrew → 希伯来语
- 印地语/Hindi → 印地语
- 孟加拉语/Bengali → 孟加拉语
- 乌尔都语/Urdu → 乌尔都语
- 波斯语/Persian → 波斯语

注意：
1. 只输出语言名称，不要输出任何其他内容
2. 使用中文标注
3. 如果无法确定语言，输出"其他"
"""
        
        user_prompt = f"""请识别以下文本的语言：

【待识别文本】
{sample_text}

只输出语言名称（中文标注）。"""
        
        logger.info("正在构建语言检测提示词...")
        logger.info("=" * 80)
        logger.info("【语言检测 System Prompt】")
        logger.info(system_prompt)
        logger.info("=" * 80)
        logger.info("【语言检测 User Prompt】")
        logger.info(user_prompt)
        logger.info("=" * 80)
        
        # 调用 API
        logger.info("正在调用 Ollama API 进行语言检测...")
        response_text = self._call_ollama_api(system_prompt, user_prompt)
        logger.info("语言检测 API 调用成功")
        
        # 解析响应
        logger.info("=" * 80)
        logger.info("【语言检测 API 响应】")
        logger.info(response_text)
        logger.info("=" * 80)
        
        # 清理响应，提取语言名称
        detected_lang = response_text.strip()
        # 移除可能的标点符号和多余字符
        detected_lang = detected_lang.replace("【", "").replace("】", "").replace("：", "").replace(":", "")
        detected_lang = detected_lang.replace("语言", "").replace("是", "").strip()
        
        # 语言名称标准化（包含所有 System Prompt 中提到的语言）
        lang_mapping = {
            "英语": "英语",
            "英文": "英语",
            "English": "英语",
            "中文": "中文",
            "Chinese": "中文",
            "日语": "日语",
            "Japanese": "日语",
            "韩语": "韩语",
            "Korean": "韩语",
            "法语": "法语",
            "French": "法语",
            "德语": "德语",
            "German": "德语",
            "西班牙语": "西班牙语",
            "Spanish": "西班牙语",
            "俄语": "俄语",
            "Russian": "俄语",
            "阿拉伯语": "阿拉伯语",
            "Arabic": "阿拉伯语",
            "葡萄牙语": "葡萄牙语",
            "Portuguese": "葡萄牙语",
            "意大利语": "意大利语",
            "Italian": "意大利语",
            "荷兰语": "荷兰语",
            "Dutch": "荷兰语",
            "波兰语": "波兰语",
            "Polish": "波兰语",
            "土耳其语": "土耳其语",
            "Turkish": "土耳其语",
            "泰语": "泰语",
            "Thai": "泰语",
            "越南语": "越南语",
            "Vietnamese": "越南语",
            "印尼语": "印尼语",
            "Indonesian": "印尼语",
            "马来语": "马来语",
            "Malay": "马来语",
            "希腊语": "希腊语",
            "Greek": "希腊语",
            "捷克语": "捷克语",
            "Czech": "捷克语",
            "瑞典语": "瑞典语",
            "Swedish": "瑞典语",
            "丹麦语": "丹麦语",
            "Danish": "丹麦语",
            "挪威语": "挪威语",
            "Norwegian": "挪威语",
            "芬兰语": "芬兰语",
            "Finnish": "芬兰语",
            "匈牙利语": "匈牙利语",
            "Hungarian": "匈牙利语",
            "罗马尼亚语": "罗马尼亚语",
            "Romanian": "罗马尼亚语",
            "保加利亚语": "保加利亚语",
            "Bulgarian": "保加利亚语",
            "乌克兰语": "乌克兰语",
            "Ukrainian": "乌克兰语",
            "希伯来语": "希伯来语",
            "Hebrew": "希伯来语",
            "印地语": "印地语",
            "Hindi": "印地语",
            "孟加拉语": "孟加拉语",
            "Bengali": "孟加拉语",
            "乌尔都语": "乌尔都语",
            "Urdu": "乌尔都语",
            "波斯语": "波斯语",
            "Persian": "波斯语",
            "其他": "其他"
        }
        
        # 标准化语言名称（如果不在映射表中，保持原样）
        detected_lang = lang_mapping.get(detected_lang, detected_lang)
        
        logger.info(f"LLM 检测到的语言: {detected_lang}")
        logger.info("========== 步骤一完成 ==========")
        
        return detected_lang
    
    def _parse_response(self, response: str, summary: bool) -> tuple:
        """解析 API 响应，提取翻译文本和摘要
        
        Args:
            response: API 响应文本
            summary: 是否包含摘要
            
        Returns:
            (translated_text, summary_text) 元组
        """
        # 清理响应中的转义字符
        response = response.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
        
        # 查找【翻译结果】标记
        if "【翻译结果】" in response:
            parts = response.split("【翻译结果】", 1)
            if len(parts) > 1:
                # 提取翻译结果部分
                remaining = parts[1]
                
                if "【摘要】" in remaining:
                    # 有摘要部分
                    trans_part, summary_part = remaining.split("【摘要】", 1)
                    translated_text = trans_part.strip()
                    summary_text = summary_part.strip()
                    
                    # 如果摘要为"无"且未启用摘要，则清空
                    if not summary and summary_text == "无":
                        summary_text = ""
                else:
                    # 没有摘要部分
                    translated_text = remaining.strip()
                    summary_text = ""
                
                return translated_text, summary_text
        
        # 如果没有找到格式化标记，使用旧逻辑
        if not summary:
            return response.strip(), ""
        
        # 尝试分离翻译和摘要
        # 常见的分隔符：摘要、摘要：、Summary 等
        separators = ["\n摘要：", "\n摘要:", "\n摘要", "\nSummary:", "\nSummary", "---"]
        
        for sep in separators:
            if sep in response:
                parts = response.split(sep, 1)
                translated_text = parts[0].strip()
                summary_text = parts[1].strip() if len(parts) > 1 else ""
                return translated_text, summary_text
        
        # 如果没有找到分隔符，尝试判断最后一行是否为摘要
        lines = response.strip().split('\n')
        if len(lines) > 1:
            # 假设最后一行是摘要
            translated_text = '\n'.join(lines[:-1]).strip()
            summary_text = lines[-1].strip()
            return translated_text, summary_text
        
        # 无法分离，全部作为翻译文本
        return response.strip(), ""
    
    def _translate_single_chunk(self, text: str, source_lang: str, target_lang: str,
                                domain: Optional[str] = None,
                                glossary: Optional[Dict[str, str]] = None,
                                summary: bool = False) -> tuple:
        """翻译单个文本段落
        
        Args:
            text: 待翻译文本
            source_lang: 源语言
            target_lang: 目标语言
            domain: 专业领域
            glossary: 词汇字典
            summary: 是否生成摘要
            
        Returns:
            (translated_text, summary_text) 元组
        """
        # 构建 Prompt
        logger.info("正在构建翻译提示词...")
        system_prompt, user_prompt = self._build_prompt(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            domain=domain,
            glossary=glossary,
            summary=summary
        )
        logger.info("提示词构建完成")
        logger.info("=" * 80)
        logger.info("【System Prompt】")
        logger.info(system_prompt)
        logger.info("=" * 80)
        logger.info("【User Prompt】")
        logger.info(user_prompt)
        logger.info("=" * 80)
        
        # 调用 API
        logger.info(f"正在调用 Ollama API (模型: {self.ollama_config.get('model', 'llama3')})...")
        response_text = self._call_ollama_api(system_prompt, user_prompt)
        logger.info("API 调用成功")
        
        # 解析响应
        logger.info("正在解析翻译结果...")
        logger.info("=" * 80)
        logger.info("【API 原始响应】")
        logger.info(response_text)
        logger.info("=" * 80)
        translated_text, summary_text = self._parse_response(response_text, summary)
        logger.info(f"翻译结果长度: {len(translated_text)} 字符")
        logger.info("=" * 80)
        logger.info("【解析后的翻译结果】")
        logger.info(translated_text)
        logger.info("=" * 80)
        if summary_text:
            logger.info(f"摘要长度: {len(summary_text)} 字符")
            logger.info("=" * 80)
            logger.info("【解析后的摘要】")
            logger.info(summary_text)
            logger.info("=" * 80)
        
        return translated_text, summary_text
    
    def _translate_multiple_chunks(self, chunks: List[str], source_lang: str, target_lang: str,
                                   domain: Optional[str] = None,
                                   glossary: Optional[Dict[str, str]] = None,
                                   summary: bool = False) -> tuple:
        """翻译多个文本段落
        
        Args:
            chunks: 文本段落列表
            source_lang: 源语言
            target_lang: 目标语言
            domain: 专业领域
            glossary: 词汇字典
            summary: 是否生成摘要
            
        Returns:
            (translated_text, summary_text) 元组
        """
        logger.info(f"开始分段翻译，共 {len(chunks)} 个段落")
        
        translated_chunks = []
        all_summaries = []
        
        for idx, chunk in enumerate(chunks, 1):
            logger.info(f"========== 翻译段落 [{idx}/{len(chunks)}] ==========")
            logger.info(f"段落长度: {len(chunk)} 字符")
            
            # 翻译当前段落（不生成摘要，只在最后生成一次）
            translated_chunk, _ = self._translate_single_chunk(
                text=chunk,
                source_lang=source_lang,
                target_lang=target_lang,
                domain=domain,
                glossary=glossary,
                summary=False
            )
            
            translated_chunks.append(translated_chunk)
            logger.info(f"段落 [{idx}/{len(chunks)}] 翻译完成")
        
        # 合并所有翻译段落
        # 移除重叠部分的重复内容
        chunk_config = self.translation_config.get('chunk_translation', {})
        chunk_overlap = chunk_config.get('chunk_overlap', 100)
        
        merged_text = ""
        for idx, chunk in enumerate(translated_chunks):
            if idx == 0:
                merged_text = chunk
            else:
                # 对于后续段落，跳过重叠部分
                # 简单策略：从重叠位置开始查找第一个句子边界
                if len(chunk) > chunk_overlap:
                    # 在重叠部分查找句子边界
                    overlap_text = chunk[:chunk_overlap]
                    # 从后往前找句子结束标记
                    sentence_end_pos = -1
                    for i in range(len(overlap_text) - 1, -1, -1):
                        if overlap_text[i] in SENTENCE_END_MARKERS:
                            sentence_end_pos = i + 1
                            break
                    
                    if sentence_end_pos > 0:
                        merged_text += chunk[sentence_end_pos:]
                    else:
                        # 如果找不到句子边界，使用重叠长度的一半作为分割点
                        merged_text += chunk[chunk_overlap // 2:]
                else:
                    merged_text += chunk
        
        logger.info(f"合并后的翻译文本长度: {len(merged_text)} 字符")
        
        # 如果需要生成摘要，对合并后的文本生成摘要
        summary_text = ""
        if summary:
            logger.info("========== 生成全文摘要 ==========")
            # 使用合并后的文本生成摘要
            summary_text = self._generate_summary(merged_text, target_lang)
            logger.info(f"摘要长度: {len(summary_text)} 字符")
        
        return merged_text, summary_text
    
    def _generate_summary(self, text: str, target_lang: str) -> str:
        """为翻译后的文本生成摘要
        
        Args:
            text: 翻译后的文本
            target_lang: 目标语言
            
        Returns:
            摘要文本
        """
        # 从配置获取摘要参数
        max_length = self.summary_config.get('max_length', 100)
        prompt_template = self.summary_config.get('prompt_template', '')
        
        # 对于超长文本，只取前 SUMMARY_GENERATION_SAMPLE_SIZE 字符用于生成摘要
        sample_text = text[:SUMMARY_GENERATION_SAMPLE_SIZE] if len(text) > SUMMARY_GENERATION_SAMPLE_SIZE else text
        
        # 使用配置文件中的提示词模板
        if prompt_template:
            system_prompt = prompt_template.format(
                target_lang=target_lang,
                max_length=max_length
            )
        else:
            # 如果没有配置提示词，使用默认提示词
            system_prompt = f"""你是一个文本摘要专家，擅长为{target_lang}文本生成简洁的摘要。

任务：为以下{target_lang}文本生成一个简短的摘要（不超过{max_length}字）。

要求：
1. 准确概括文本的主要内容
2. 语言简洁明了
3. 只输出摘要内容，不要输出任何其他内容
"""
        
        user_prompt = f"""请为以下文本生成摘要：

【待摘要文本】
{sample_text}

只输出摘要内容（不超过{max_length}字）。"""
        
        logger.info("正在调用 API 生成摘要...")
        response_text = self._call_ollama_api(system_prompt, user_prompt)
        logger.info("摘要生成完成")
        
        # 清理摘要文本
        summary = response_text.strip()
        # 限制摘要长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    def translate(self, text: str, target_lang: Optional[str] = None,
                 domain: Optional[str] = None, glossary: Optional[str] = None,
                 summary: Optional[bool] = None) -> Dict[str, Any]:
        """执行翻译
        
        Args:
            text: 待翻译文本
            target_lang: 目标语言（默认为配置中的默认值）
            domain: 专业领域
            glossary: 词汇表字符串
            summary: 是否生成摘要（默认从配置文件读取）
            
        Returns:
            包含翻译结果的字典
        """
        logger.info("========== 开始翻译任务 ==========")
        logger.info(f"待翻译文本长度: {len(text)} 字符")
        
        # 设置默认目标语言
        if not target_lang:
            target_lang = self.translation_config.get('default_target_lang', 'Chinese')
        
        # 设置默认摘要生成（从配置文件读取）
        if summary is None:
            summary = self.summary_config.get('enabled', True)
        
        # 解析词汇表
        glossary_dict = self._parse_glossary(glossary)
        if glossary_dict:
            logger.info(f"加载词汇表，包含 {len(glossary_dict)} 个术语")
        
        # 步骤一：使用 LLM 检测源语言（带缓存）
        source_lang = self._detect_language_with_llm_cached(text)
        logger.info(f"翻译目标语言: {target_lang}")
        
        # 步骤二：翻译并输出
        logger.info("========== 步骤二：翻译并输出 ==========")
        
        if domain:
            logger.info(f"专业领域: {domain}")
        
        if summary:
            logger.info("摘要生成: 已启用")
        
        # 检查是否需要分段翻译
        chunks = self._split_text_into_chunks(text)
        
        if len(chunks) == 1:
            # 单段翻译
            logger.info("========== 单段翻译模式 ==========")
            translated_text, summary_text = self._translate_single_chunk(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                domain=domain,
                glossary=glossary_dict,
                summary=summary
            )
        else:
            # 分段翻译
            logger.info("========== 分段翻译模式 ==========")
            translated_text, summary_text = self._translate_multiple_chunks(
                chunks=chunks,
                source_lang=source_lang,
                target_lang=target_lang,
                domain=domain,
                glossary=glossary_dict,
                summary=summary
            )
        
        logger.info("========== 翻译任务完成 ==========")
        
        return {
            "detected_language": source_lang,
            "translated_text": translated_text,
            "summary": summary_text
        }
    
    def batch_translate_files(self, input_dir: Optional[str] = None, output_dir: Optional[str] = None,
                             target_lang: Optional[str] = None,
                             domain: Optional[str] = None,
                             glossary: Optional[str] = None,
                             summary: Optional[bool] = None,
                             file_pattern: Optional[str] = None,
                             delete_after: Optional[bool] = None) -> Dict[str, Any]:
        """批量翻译指定目录中的文本文件
        
        Args:
            input_dir: 输入文件目录（如果为 None，则从配置文件读取）
            output_dir: 输出文件目录（如果为 None，则从配置文件读取）
            target_lang: 目标语言（默认为配置中的默认值）
            domain: 专业领域
            glossary: 词汇表字符串
            summary: 是否生成摘要（默认从配置文件读取）
            file_pattern: 文件匹配模式（如果为 None，则从配置文件读取）
            delete_after: 翻译完成后是否删除原文件（如果为 None，则从配置文件读取）
            
        Returns:
            包含批量翻译结果的字典
        """
        logger.info("========== 开始批量翻译任务 ==========")
        
        # 从配置文件读取默认值
        if input_dir is None:
            input_dir = self.file_management_config.get('input_dir', './input')
        if output_dir is None:
            output_dir = self.file_management_config.get('completed_dir', './completed')
        if file_pattern is None:
            file_pattern = self.file_management_config.get('file_pattern', '*.txt')
        if delete_after is None:
            delete_after = self.file_management_config.get('delete_after_translation', False)
        archive_dir = self.file_management_config.get('archive_dir', './archive')
        
        logger.info(f"输入目录: {input_dir}")
        logger.info(f"输出目录: {output_dir}")
        logger.info(f"文件匹配模式: {file_pattern}")
        logger.info(f"归档目录: {archive_dir}")
        logger.info(f"翻译后处理: {'删除原文件' if delete_after else '归档原文件'}")
        
        # 设置默认摘要生成（从配置文件读取）
        if summary is None:
            summary = self.summary_config.get('enabled', True)
        
        if target_lang:
            logger.info(f"目标语言: {target_lang}")
        if domain:
            logger.info(f"专业领域: {domain}")
        if glossary:
            logger.info("使用自定义词汇表")
        if summary:
            logger.info("摘要生成: 已启用")
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # 检查输入目录是否存在
        if not input_path.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        if not input_path.is_dir():
            logger.error(f"输入路径不是目录: {input_dir}")
            raise NotADirectoryError(f"输入路径不是目录: {input_dir}")
        
        # 创建输出目录和归档目录
        output_path.mkdir(parents=True, exist_ok=True)
        archive_path = Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        logger.info("输出目录和归档目录已就绪")
        
        # 查找匹配的文件
        files = list(input_path.glob(file_pattern))
        
        if not files:
            logger.warning(f"在目录 {input_dir} 中未找到匹配 {file_pattern} 的文件")
            return {
                "total_files": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "message": f"在目录 {input_dir} 中未找到匹配 {file_pattern} 的文件"
            }
        
        logger.info(f"找到 {len(files)} 个待翻译文件")
        results = []
        success_count = 0
        failed_count = 0
        
        for idx, file_path in enumerate(sorted(files), 1):
            logger.info(f"========== 处理文件 [{idx}/{len(files)}]: {file_path.name} ==========")
            file_result = {
                "input_file": str(file_path),
                "output_file": "",
                "status": "",
                "error": "",
                "translation": None,
                "deleted": False
            }
            
            try:
                # 读取文件内容
                logger.info(f"正在读取文件: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                logger.info(f"文件读取完成，内容长度: {len(text)} 字符")
                
                if not text:
                    logger.warning(f"文件内容为空，跳过: {file_path.name}")
                    file_result["status"] = "skipped"
                    file_result["error"] = "文件内容为空"
                    results.append(file_result)
                    continue
                
                # 执行翻译
                translation_result = self.translate(
                    text=text,
                    target_lang=target_lang,
                    domain=domain,
                    glossary=glossary,
                    summary=summary
                )
                
                # 生成输出文件名
                output_filename = f"{file_path.stem}_translated{file_path.suffix}"
                output_file_path = output_path / output_filename
                
                # 保存翻译结果到 JSON 文件
                logger.info(f"正在保存翻译结果到: {output_file_path}")
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(translation_result, f, ensure_ascii=False, indent=2)
                logger.info(f"翻译结果已保存")
                
                file_result["output_file"] = str(output_file_path)
                file_result["status"] = "success"
                file_result["translation"] = translation_result
                success_count += 1
                
                # 根据配置处理原文件
                if delete_after:
                    logger.info(f"正在删除原文件: {file_path}")
                    try:
                        os.remove(file_path)
                        logger.info(f"原文件已删除")
                        file_result["deleted"] = True
                        file_result["archived"] = False
                    except Exception as e:
                        logger.error(f"删除文件失败: {str(e)}")
                        file_result["delete_error"] = f"删除文件失败: {str(e)}"
                else:
                    # 移动到归档文件夹
                    logger.info(f"正在归档原文件到: {archive_path}")
                    try:
                        archive_file_path = archive_path / file_path.name
                        shutil.move(str(file_path), str(archive_file_path))
                        logger.info(f"原文件已归档到: {archive_file_path}")
                        file_result["deleted"] = False
                        file_result["archived"] = True
                        file_result["archive_path"] = str(archive_file_path)
                    except Exception as e:
                        logger.error(f"归档文件失败: {str(e)}")
                        file_result["archive_error"] = f"归档文件失败: {str(e)}"
                
                logger.info(f"文件 [{idx}/{len(files)}] 处理完成: {file_path.name}")
                
            except Exception as e:
                logger.error(f"文件处理失败 [{idx}/{len(files)}]: {file_path.name} - {str(e)}")
                file_result["status"] = "failed"
                file_result["error"] = str(e)
                failed_count += 1
            
            results.append(file_result)
        
        logger.info("========== 批量翻译任务完成 ==========")
        logger.info(f"总文件数: {len(files)}")
        logger.info(f"成功翻译: {success_count} 个")
        logger.info(f"翻译失败: {failed_count} 个")
        logger.info(f"成功率: {success_count/len(files)*100:.1f}%" if len(files) > 0 else "成功率: 0%")
        
        return {
            "total_files": len(files),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "message": f"批量翻译完成：成功 {success_count} 个，失败 {failed_count} 个"
        }
    
    def batch_translate_from_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """从配置文件批量翻译
        
        Args:
            config_path: 批量配置文件路径
            
        Returns:
            批量翻译结果
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "backend", "batch_config.yaml")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                batch_config = yaml.safe_load(f)
            
            return self.batch_translate_files(
                input_dir=batch_config.get('input_dir', ''),
                output_dir=batch_config.get('output_dir', ''),
                target_lang=batch_config.get('target_lang'),
                domain=batch_config.get('domain'),
                glossary=batch_config.get('glossary'),
                summary=batch_config.get('summary', False),
                file_pattern=batch_config.get('file_pattern', '*.txt')
            )
            
        except FileNotFoundError:
            raise FileNotFoundError(f"批量配置文件不存在: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"批量配置文件解析错误: {str(e)}")


def main():
    """主函数，处理命令行参数并执行翻译"""
    parser = argparse.ArgumentParser(
        description="基于 Ollama 的多语言智能翻译引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 单文本翻译
  python translator_main.py --text "Hello, world!"
  
  # 批量文件翻译（从配置文件读取路径）
  python translator_main.py --batch
  
  # 批量文件翻译（指定路径）
  python translator_main.py --batch --input_dir ./input --output_dir ./output
  
  # 使用批量配置文件
  python translator_main.py --batch --batch_config batch_config.yaml
  
  # 带专业领域和词汇表
  python translator_main.py --text "AI is transforming healthcare" --domain "医疗" --glossary "AI=人工智能,healthcare=医疗保健"
        """
    )
    
    # 模式选择（默认为批量翻译模式）
    mode_group = parser.add_mutually_exclusive_group(required=False)    # 添加互斥组，确保只能选择一种模式
    mode_group.add_argument(    # 单文本模式参数
        '--text',   
        type=str,   
        help='需要翻译的原文内容（单文本模式）'
    )
    mode_group.add_argument(    # 批量翻译模式参数
        '--batch',
        action='store_true',
        help='批量翻译模式（从配置文件读取路径或通过参数指定）'
    )
    

    single_group = parser.add_argument_group("单文本模式参数")
    single_group.add_argument(
        '--target_lang',
        type=str,
        default=None,
        help='目标翻译语言（默认为中文）'
    )
    
    single_group.add_argument(
        '--domain',
        type=str,
        default=None,
        help='翻译的专业领域（如：医疗、法律、计算机、文学等）'
    )
    
    single_group.add_argument(
        '--glossary',
        type=str,
        default=None,
        help='专业词汇表内容（格式为 Key=Value 或 JSON 字符串）'
    )
    
    single_group.add_argument(
        '--summary',
        action='store_true',
        default=None,
        help='是否需要对译文进行摘要生成（默认从配置文件读取）'
    )
    
    single_group.add_argument(
        '--no_summary',
        action='store_true',
        help='禁用摘要生成（优先于 --summary 参数）'
    )
    
    single_group.add_argument(
        '--clear_cache',
        action='store_true',
        help='清除语言检测缓存'
    )
    
    single_group.add_argument(
        '--cache_stats',
        action='store_true',
        help='显示缓存统计信息'
    )
    

    batch_group = parser.add_argument_group("批量模式参数")
    batch_group.add_argument(
        '--input_dir',
        type=str,
        default=None,
        help='输入文件目录（批量模式，不指定则从配置文件读取）'
    )
    
    batch_group.add_argument(
        '--output_dir',
        type=str,
        default=None,
        help='输出文件目录（批量模式，不指定则从配置文件读取）'
    )
    
    batch_group.add_argument(
        '--file_pattern',
        type=str,
        default=None,
        help='文件匹配模式（批量模式，不指定则从配置文件读取）'
    )
    
    batch_group.add_argument(
        '--delete_after',
        action='store_true',
        help='翻译完成后删除原文件（批量模式，不指定则从配置文件读取）'
    )
    
    batch_group.add_argument(
        '--no_delete',
        action='store_true',
        help='翻译完成后不删除原文件（批量模式，优先于 --delete_after）'
    )
    
    batch_group.add_argument(
        '--batch_config',
        type=str,
        default=None,
        help='批量配置文件路径（批量模式，如使用此参数则忽略其他批量参数）'
    )
    
    common_group = parser.add_argument_group("通用参数")
    common_group.add_argument(
        '--config',
        type=str,
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"),
    )
    
    args = parser.parse_args()
    
    # 如果没有指定任何模式，默认使用批量翻译模式
    if not args.text and not args.batch:
        args.batch = True
    
    try:
        # 创建翻译引擎
        engine = TranslationEngine(config_path=args.config)
        
        if args.batch:
            # 批量翻译模式
            logger.info("========== 批量翻译模式 ==========")
            if args.batch_config:
                # 使用批量配置文件
                logger.info(f"使用批量配置文件: {args.batch_config}")
                result = engine.batch_translate_from_config(args.batch_config)
            else:
                # 处理删除参数
                delete_after = None
                if args.no_delete:
                    delete_after = False
                elif args.delete_after:
                    delete_after = True
                
                # 处理摘要参数
                summary = _resolve_summary_flag(args.summary, args.no_summary)
                
                # 使用命令行参数（或从配置文件读取）
                result = engine.batch_translate_files(
                    input_dir=args.input_dir,
                    output_dir=args.output_dir,
                    target_lang=args.target_lang,
                    domain=args.domain,
                    glossary=args.glossary,
                    summary=summary,
                    file_pattern=args.file_pattern,
                    delete_after=delete_after
                )
        else:
            # 单文本翻译模式
            logger.info("========== 单文本翻译模式 ==========")
            
            # 处理摘要参数
            summary = _resolve_summary_flag(args.summary, args.no_summary)
            
            # 处理缓存相关参数
            if args.clear_cache:
                cache_size = engine.clear_language_cache()
                result = {
                    "message": f"语言检测缓存已清除，共清除 {cache_size} 条记录"
                }
            elif args.cache_stats:
                cache_stats = engine.get_cache_stats()
                result = cache_stats
            else:
                # 正常翻译
                result = engine.translate(
                    text=args.text,
                    target_lang=args.target_lang,
                    domain=args.domain,
                    glossary=args.glossary,
                    summary=summary
                )
        
        # 输出 JSON 结果
        logger.info("========== 输出翻译结果 ==========")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        logger.info("========== 程序执行完成 ==========")
        
    except Exception as e:
        # 错误处理：输出包含 error 字段的 JSON
        logger.error(f"程序执行出错: {str(e)}")
        if args.batch:
            error_result = {
                "error": str(e),
                "total_files": 0,
                "success_count": 0,
                "failed_count": 0,
                "results": []
            }
        else:
            error_result = {
                "error": str(e),
                "detected_language": "未知",
                "translated_text": "",
                "summary": ""
            }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        logger.error("========== 程序异常退出 ==========")
        sys.exit(1)


if __name__ == "__main__":
    main()
