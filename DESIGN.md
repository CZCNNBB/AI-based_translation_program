# 多语言智能翻译引擎 - 设计文档

## 1. 项目概述

### 1.1 项目简介
这是一个基于 Ollama 本地大模型的多语言智能翻译引擎,支持专业领域术语定制,输出标准 JSON 格式结果。

### 1.2 核心特性
- 自动语言检测(支持 30+ 种语言)
- 智能分段翻译(处理长文本)
- 专业领域定制
- 术语对照表支持
- 翻译结果摘要生成
- 批量文件处理
- 语言检测缓存机制
- 完善的错误处理和重试机制

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                     CLI 命令行接口                        │
│              (argparse 参数解析)                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  TranslationEngine                       │
│                   (翻译引擎核心类)                         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│ 配置管理     │ │ API 调用  │ │ 文本处理     │
│ Config.yaml │ │ Ollama   │ │ 分段/合并    │
└─────────────┘ └──────────┘ └──────────────┘
```

### 2.2 核心模块

#### 2.2.1 TranslationEngine 类
翻译引擎的核心类,封装所有翻译逻辑。

**职责:**
- 配置文件加载与管理
- 语言检测(带缓存)
- 文本分段与合并
- 翻译 Prompt 构建
- Ollama API 调用
- 结果解析与输出

#### 2.2.2 配置管理模块
- 从 YAML 文件加载配置
- 支持 Ollama 服务配置
- 翻译参数配置
- 文件管理配置

#### 2.2.3 语言检测模块
- 基于 LLM 的语言识别
- MD5 哈希缓存机制
- 支持 30+ 种语言映射

#### 2.2.4 文本处理模块
- 智能分段(按句子边界)
- 重叠处理(避免上下文丢失)
- 段落合并算法

---

## 3. 详细设计

### 3.1 常量定义

```python
LANGUAGE_DETECTION_SAMPLE_SIZE = 500   # 语言检测采样长度
SUMMARY_GENERATION_SAMPLE_SIZE = 1000  # 摘要生成采样长度
RETRY_WAIT_TIME_BASE = 2               # 重试等待时间基数(指数退避)
SENTENCE_END_MARKERS = [...]           # 句子结束标记
WHITESPACE_MARKERS = [...]             # 空白字符标记
```

### 3.2 TranslationEngine 类设计

#### 3.2.1 初始化方法
```python
def __init__(self, config_path: str = "config.yaml")
```

**流程:**
1. 加载 YAML 配置文件
2. 初始化 Ollama 服务地址
3. 配置日志输出
4. 初始化语言检测缓存字典

#### 3.2.2 核心翻译方法

##### translate() - 单文本翻译
```python
def translate(self, text: str, target_lang: Optional[str] = None,
             domain: Optional[str] = None, glossary: Optional[str] = None,
             summary: Optional[bool] = None) -> Dict[str, Any]
```

**翻译流程:**
```
1. 参数验证与默认值设置
   ├─ 设置目标语言
   ├─ 解析词汇表
   └─ 确定摘要生成策略

2. 语言检测
   └─ _detect_language_with_llm_cached()
      ├─ 计算文本 MD5
      ├─ 检查缓存
      └─ 调用 LLM 检测(如缓存未命中)

3. 文本分段
   └─ _split_text_into_chunks()
      ├─ 检查是否需要分段
      ├─ 按句子边界分割
      └─ 处理重叠区域

4. 翻译执行
   ├─ 单段: _translate_single_chunk()
   └─ 多段: _translate_multiple_chunks()
      ├─ 逐段翻译
      ├─ 合并段落
      └─ 生成摘要

5. 返回结果
   └─ {
       "detected_language": str,
       "translated_text": str,
       "summary": str
      }
```

##### batch_translate_files() - 批量文件翻译
```python
def batch_translate_files(self, input_dir: Optional[str] = None,
                         output_dir: Optional[str] = None,
                         ...) -> Dict[str, Any]
```

**批量处理流程:**
```
1. 目录准备
   ├─ 验证输入目录
   ├─ 创建输出目录
   └─ 创建归档目录

2. 文件查找
   └─ 使用 glob 模式匹配文件

3. 逐文件处理
   for each file:
   ├─ 读取文件内容
   ├─ 调用 translate()
   ├─ 保存 JSON 结果
   └─ 处理原文件(删除/归档)

4. 返回统计结果
   └─ {
       "total_files": int,
       "success_count": int,
       "failed_count": int,
       "results": [...]
      }
```

### 3.3 辅助方法设计

#### 3.3.1 Prompt 构建
```python
def _build_prompt(self, text: str, source_lang: str, target_lang: str,
                 domain: Optional[str] = None,
                 glossary: Optional[Dict[str, str]] = None,
                 summary: bool = False) -> tuple
```

**System Prompt 结构:**
- 角色定义:专业翻译助手
- 任务说明:源语言 → 目标语言
- 翻译要求:准确、流畅、保持风格
- 专业领域(可选)
- 术语对照表(可选)

**User Prompt 结构:**
- 待翻译文本
- 输出要求
- 摘要生成指令(可选)

#### 3.3.2 API 调用
```python
def _call_ollama_api(self, system_prompt: str, user_prompt: str) -> str
```

**重试机制:**
- 最大重试次数:3次(可配置)
- 指数退避策略:2^attempt 秒
- 超时处理:配置可调
- 错误类型处理:
  - Timeout:重试
  - ConnectionError:终止
  - HTTPError:终止
  - 其他异常:终止

#### 3.3.3 语言检测
```python
def _detect_language_with_llm(self, text: str) -> str
def _detect_language_with_llm_cached(self, text: str) -> str
```

**缓存策略:**
- 缓存键:文本 MD5 哈希
- 缓存值:检测结果
- 可通过配置启用/禁用

**支持语言:**
英语、中文、日语、韩语、法语、德语、西班牙语、俄语、阿拉伯语、葡萄牙语、意大利语、荷兰语、波兰语、土耳其语、泰语、越南语、印尼语、马来语、希腊语、捷克语、瑞典语、丹麦语、挪威语、芬兰语、匈牙利语、罗马尼亚语、保加利亚语、乌克兰语、希伯来语、印地语、孟加拉语、乌尔都语、波斯语

#### 3.3.4 文本分段
```python
def _split_text_into_chunks(self, text: str) -> List[str]
```

**分段策略:**
1. 触发条件:文本长度 > max_chunk_size
2. 分割点优先级:
   - 句子结束标记(。!?等)
   - 空白字符
3. 重叠处理:chunk_overlap 字符
4. 避免在句子中间分割

#### 3.3.5 结果解析
```python
def _parse_response(self, response: str, summary: bool) -> tuple
```

**解析逻辑:**
1. 查找【翻译结果】标记
2. 查找【摘要】标记
3. 兼容无标记格式
4. 清理转义字符

---

## 4. 数据流图

### 4.1 单文本翻译数据流

```
用户输入
  │
  ▼
参数解析
  │
  ▼
┌──────────────┐
│ 语言检测     │ ← 缓存查询
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 文本分段     │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────┐
│ Prompt 构建  │ ──→ │ Ollama API  │
└──────────────┘     └──────┬──────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ 结果解析     │
                    └──────┬───────┘
                           │
                           ▼
                      JSON 输出
```

### 4.2 批量翻译数据流

```
输入目录
  │
  ▼
文件扫描(Glob)
  │
  ▼
┌──────────────────────────┐
│  for each file           │
│  ├─ 读取文件             │
│  ├─ 调用 translate()     │
│  ├─ 保存 JSON            │
│  └─ 处理原文件           │
└──────────┬───────────────┘
           │
           ▼
      统计结果输出
```

---

## 5. 配置文件设计

### 5.1 config.yaml 结构

```yaml
ollama:
  host: localhost          # Ollama 服务地址
  port: 11434             # Ollama 服务端口
  model: llama3           # 使用的模型
  timeout: 60             # API 超时时间(秒)
  max_retries: 3          # 最大重试次数

translation:
  default_target_lang: Chinese    # 默认目标语言
  temperature: 0.3               # 生成温度
  top_p: 0.9                     # Top-p 采样
  max_tokens: 2000               # 最大生成 token 数

  language_detection:
    cache_enabled: true          # 是否启用语言检测缓存

  chunk_translation:
    enabled: true                # 是否启用分段翻译
    max_chunk_size: 2000         # 单段最大字符数
    chunk_overlap: 100           # 段落重叠字符数

  summary_generation:
    enabled: true                # 是否启用摘要生成
    max_length: 100              # 摘要最大长度
    prompt_template: ""          # 自定义摘要 Prompt 模板

file_management:
  input_dir: ./input            # 输入文件目录
  completed_dir: ./completed    # 翻译完成目录
  archive_dir: ./archive        # 原文件归档目录
  file_pattern: "*.txt"         # 文件匹配模式
  delete_after_translation: false  # 翻译后是否删除原文件
```

---

## 6. 命令行接口设计

### 6.1 单文本模式

```bash
# 基础翻译
python translator_main.py --text "Hello, world!"

# 指定目标语言
python translator_main.py --text "Hello" --target_lang "Japanese"

# 专业领域翻译
python translator_main.py --text "AI is transforming healthcare" \
  --domain "医疗" \
  --glossary "AI=人工智能,healthcare=医疗保健"

# 控制摘要生成
python translator_main.py --text "..." --summary
python translator_main.py --text "..." --no_summary

# 缓存管理
python translator_main.py --clear_cache
python translator_main.py --cache_stats
```

### 6.2 批量翻译模式

```bash
# 使用默认配置
python translator_main.py --batch

# 指定目录
python translator_main.py --batch \
  --input_dir ./input \
  --output_dir ./output

# 指定文件模式
python translator_main.py --batch --file_pattern "*.md"

# 翻译后删除原文件
python translator_main.py --batch --delete_after

# 使用批量配置文件
python translator_main.py --batch --batch_config batch_config.yaml

# 自定义配置文件
python translator_main.py --batch --config my_config.yaml
```

---

## 7. 错误处理机制

### 7.1 异常处理层级

```
┌─────────────────────────────────┐
│    CLI 参数解析错误             │
│    (argparse 自动处理)          │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│    配置文件错误                 │
│    ├─ FileNotFoundError         │
│    └─ YAMLError                 │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│    API 调用错误                 │
│    ├─ Timeout (重试)            │
│    ├─ ConnectionError (终止)    │
│    ├─ HTTPError (终止)          │
│    └─ 其他异常 (终止)           │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│    文件操作错误                 │
│    ├─ 目录不存在                │
│    ├─ 文件读取失败              │
│    └─ 文件写入失败              │
└─────────────────────────────────┘
```

### 7.2 错误输出格式

所有错误均以标准 JSON 格式输出:

```json
{
  "error": "错误描述信息"
}
```

批量模式错误输出:
```json
{
  "error": "错误描述",
  "total_files": 0,
  "success_count": 0,
  "failed_count": 0,
  "results": []
}
```

单文本模式错误输出:
```json
{
  "error": "错误描述",
  "detected_language": "未知",
  "translated_text": "",
  "summary": ""
}
```

---

## 8. 性能优化

### 8.1 语言检测缓存
- 使用 MD5 哈希作为缓存键
- 避免重复的 LLM 调用
- 可通过配置启用/禁用

### 8.2 分段翻译优化
- 智能分割点选择(句子边界)
- 重叠区域处理保持上下文
- 避免在句子中间分割

### 8.3 API 重试策略
- 指数退避算法
- 避免频繁重试导致服务压力
- 可配置重试次数和超时

### 8.4 长文本采样
- 语言检测:仅采样前 500 字符
- 摘要生成:仅采样前 1000 字符
- 减少 token 消耗

---

## 9. 扩展性设计

### 9.1 可配置项
- 所有关键参数均通过 YAML 配置
- 支持命令行参数覆盖配置
- 模块化的配置结构

### 9.2 Prompt 模板化
- 摘要生成 Prompt 支持自定义模板
- 易于调整翻译风格

### 9.3 语言扩展
- 语言映射表集中管理
- 添加新语言只需更新映射表

### 9.4 文件处理扩展
- 支持多种文件模式
- 可扩展支持更多文件格式

---

## 10. 依赖项

```
requests:     HTTP 请求库
yaml:         YAML 配置文件解析
logging:      日志记录
argparse:     命令行参数解析
hashlib:      MD5 哈希计算
pathlib:      路径处理
shutil:       文件操作(移动/归档)
```

---

## 11. 日志设计

### 11.1 日志级别
- INFO:正常流程信息
- WARNING:警告信息(如文件为空)
- ERROR:错误信息

### 11.2 日志格式
```
%(asctime)s - %(levelname)s - %(message)s
```

### 11.3 关键日志节点
- 引擎初始化
- 语言检测开始/完成
- 文本分段
- API 调用(含重试信息)
- 翻译结果
- 文件处理
- 缓存操作

---

## 12. 使用示例

### 12.1 场景一:翻译英文技术文档
```bash
python translator_main.py --text "Machine learning is a subset of AI" \
  --domain "计算机科学" \
  --glossary "Machine learning=机器学习,AI=人工智能"
```

### 12.2 场景二:批量翻译合同文件
```bash
python translator_main.py --batch \
  --input_dir ./contracts \
  --output_dir ./contracts_translated \
  --domain "法律" \
  --file_pattern "*.txt"
```

### 12.3 场景三:翻译医疗论文
```bash
python translator_main.py --text "Clinical trials show..." \
  --target_lang "Chinese" \
  --domain "医疗" \
  --glossary "Clinical trials=临床试验,patients=患者"
```

---

## 13. 限制与注意事项

### 13.1 当前限制
1. 仅支持文本文件(.txt 等)
2. 依赖本地 Ollama 服务
3. 长文本翻译时间较长
4. 语言检测准确度依赖模型质量

### 13.2 注意事项
1. 确保 Ollama 服务已启动
2. 配置文件必须存在且格式正确
3. 输入/输出目录需有正确权限
4. 批量翻译建议先测试单文件

---

## 14. 未来改进方向

### 14.1 功能增强
- [ ] 支持更多文件格式(PDF, DOCX 等)
- [ ] 翻译质量评估
- [ ] 并发翻译加速
- [ ] 翻译记忆库
- [ ] API 服务模式

### 14.2 性能优化
- [ ] 多线程/异步处理
- [ ] 增量翻译(仅翻译变更部分)
- [ ] 更智能的分段算法

### 14.3 用户体验
- [ ] 进度条显示
- [ ] Web UI 界面
- [ ] 翻译预览功能
- [ ] 术语库管理工具

---

## 附录:文件结构

```
demo4/
├── translator_main.py       # 主程序
├── config.yaml              # 配置文件
├── batch_config.yaml        # 批量配置文件(可选)
├── input/                   # 输入文件目录
├── completed/               # 翻译完成目录
├── archive/                 # 原文件归档目录
└── DESIGN.md                # 本设计文档
```

---

**文档版本:** 1.0
**最后更新:** 2025-12-30
**项目:** 基于 Ollama 的多语言智能翻译引擎
