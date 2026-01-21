# 基于 Ollama 的多语言智能翻译引擎

基于 Python 的翻译引擎脚本，利用本地部署的 Ollama 大语言模型 API，实现多语言文本到中文的智能翻译。支持专业领域术语定制，以标准 JSON 格式输出结果。

## 功能特性

- ✅ 支持多语言翻译（默认翻译为中文）
- ✅ 支持专业领域定制（医疗、法律、计算机、文学等）
- ✅ 支持专业词汇表强制使用（Key=Value 或 JSON 格式）
- ✅ 可选生成翻译摘要
- ✅ 标准 JSON 格式输出，便于 Java 程序解析
- ✅ 完善的错误处理机制
- ✅ 支持重试和超时控制
- ✅ 支持批量文件翻译
- ✅ 支持批量配置文件
- ✅ 自动语言检测（使用 LLM）
- ✅ 超长文本自动分段翻译

## 环境要求

- Python 3.7+
- 本地已安装并运行 Ollama 服务
- 依赖库：`requests`, `pyyaml`

## 安装步骤

### 1. 安装 Ollama

访问 [Ollama 官网](https://ollama.ai/) 下载并安装 Ollama。

### 2. 拉取模型

```bash
# 拉取 llama3 模型（推荐）
ollama pull llama3

# 或拉取其他模型
ollama pull qwen
ollama pull mistral
```

### 3. 启动 Ollama 服务

```bash
# 默认情况下，Ollama 服务会在后台自动运行
# 服务地址：http://localhost:11434
```

### 4. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

## 项目结构

```
.
├── translator_main.py    # 主程序脚本
├── config.yaml           # 配置文件（包含文件管理配置）
├── batch_config.yaml     # 批量翻译配置文件（可选）
├── requirements.txt      # Python 依赖
├── input/               # 待翻译文件目录
├── completed/           # 翻译完成文件目录
├── archive/             # 原始文件归档文件夹
└── README.md            # 使用说明
```

## 配置说明

编辑 [`config.yaml`](config.yaml:1) 文件配置 Ollama 服务参数：

```yaml
ollama:
  host: "localhost"        # Ollama 服务地址
  port: 11434              # Ollama 服务端口
  model: "llama3"          # 默认使用的模型名称
  timeout: 60              # API 超时时间（秒）
  max_retries: 3           # 最大重试次数

translation:
  default_target_lang: "Chinese"  # 默认目标语言
  max_tokens: 2000                # 最大生成长度
  temperature: 0.3                # 温度参数（越低越确定）
  top_p: 0.9                      # Top-p 采样参数
  chunk_translation:               # 分段翻译配置
    enabled: true                  # 启用分段翻译
    max_chunk_size: 2000           # 单段最大字符数（超过此长度将自动分段）
    chunk_overlap: 100              # 分段重叠字符数（保持上下文连续性）

file_management:
  input_dir: "./input"            # 待翻译文件目录
  completed_dir: "./completed"    # 完成任务文件夹（存放翻译结果）
  archive_dir: "./archive"          # 原始文件归档文件夹（存放已翻译的原始文件）
  file_pattern: "*.txt"           # 文件匹配模式
  delete_after_translation: false   # 翻译完成后是否删除原文件（false：移动到归档文件夹，true：直接删除）
```

### 文件管理说明

- **待翻译文件目录**（`input_dir`）：脚本会自动读取该目录中的文件进行翻译
- **完成任务文件夹**（`completed_dir`）：翻译结果将保存到该目录
- **原始文件归档文件夹**（`archive_dir`）：存放已翻译的原始文件
- **文件匹配模式**（`file_pattern`）：支持通配符，如 `*.txt`、`*.md` 等
- **删除原文件**（`delete_after_translation`）：
  - `true`：翻译成功后直接删除原文件
  - `false`：翻译成功后将原文件移动到归档文件夹

## 使用方法

### 基本用法

```bash
python translator_main.py --text "Hello, world!"
```

输出示例：
```json
{
  "detected_language": "英语",
  "translated_text": "你好，世界！",
  "summary": ""
}
```

### 指定目标语言

```bash
python translator_main.py --text "Hello, world!" --target_lang "Japanese"
```

### 指定专业领域

```bash
python translator_main.py --text "The patient has hypertension and diabetes." --domain "医疗"
```

### 使用专业词汇表

#### 方式 1：Key=Value 格式

```bash
python translator_main.py --text "The API endpoint returns JSON data." --glossary "API=应用程序接口,endpoint=端点,JSON=JavaScript对象表示法"
```

#### 方式 2：JSON 格式

```bash
python translator_main.py --text "The API endpoint returns JSON data." --glossary '{"API":"应用程序接口","endpoint":"端点","JSON":"JavaScript对象表示法"}'
```

### 生成摘要

```bash
python translator_main.py --text "Artificial intelligence is transforming industries worldwide, from healthcare to finance, enabling new capabilities and efficiencies." --summary
```

输出示例：
```json
{
  "detected_language": "英语",
  "translated_text": "人工智能正在全球范围内改变各行各业，从医疗保健到金融，实现了新的能力和效率。",
  "summary": "人工智能正在全球范围内改变各行各业，提升能力和效率。"
}
```

### 组合使用

```bash
python translator_main.py \
  --text "The RESTful API uses HTTP methods like GET, POST, PUT, and DELETE to perform CRUD operations." \
  --target_lang "Chinese" \
  --domain "计算机" \
  --glossary "RESTful=表现层状态转换,API=应用程序接口,CRUD=创建、读取、更新、删除" \
  --summary
```

## 批量翻译

### 方式 1：最小化功能模式（推荐）

```bash
# 无参数直接运行，默认使用批量翻译模式，所有路径从 config.yaml 读取
python translator_main.py

# 指定专业领域
python translator_main.py --domain "计算机"
```

### 方式 2：从配置文件读取路径

```bash
# 使用 --batch，所有路径从 config.yaml 读取
python translator_main.py --batch

# 指定专业领域
python translator_main.py --batch --domain "计算机"
```

### 方式 2：使用命令行参数指定路径

```bash
python translator_main.py --batch --input_dir ./input --output_dir ./completed
```

### 方式 3：使用批量配置文件

```bash
python translator_main.py --batch --batch_config batch_config.yaml
```

### 文件删除控制

```bash
# 翻译完成后删除原文件（从配置文件读取）
python translator_main.py --batch

# 强制删除原文件
python translator_main.py --batch --delete_after

# 强制不删除原文件
python translator_main.py --batch --no_delete
```

### 批量翻译配置文件

创建 [`batch_config.yaml`](batch_config.yaml:1) 文件：

```yaml
# 输入目录：包含待翻译的文本文件
input_dir: "./input"

# 输出目录：翻译结果将保存为 JSON 文件
output_dir: "./completed"

# 目标语言（可选，默认为中文）
target_lang: "Chinese"

# 专业领域（可选）
domain: "计算机"

# 专业词汇表（可选）
glossary: "AI=人工智能,Machine Learning=机器学习"

# 是否生成摘要（可选，默认为 false）
summary: false

# 文件匹配模式（可选，默认为 *.txt）
file_pattern: "*.txt"
```

### 批量翻译输出格式

批量翻译会为每个输入文件生成一个对应的 JSON 文件，文件名格式为 `{原文件名}_translated.{原扩展名}`。

批量翻译的汇总输出：

```json
{
  "total_files": 2,
  "success_count": 2,
  "failed_count": 0,
  "results": [
    {
      "input_file": "input/sample1.txt",
      "output_file": "completed/sample1_translated.txt",
      "status": "success",
      "error": "",
      "deleted": false,
      "archived": true,
      "archive_path": "archive/sample1.txt",
      "translation": {
        "detected_language": "英语",
        "translated_text": "翻译后的内容...",
        "summary": ""
      }
    },
    {
      "input_file": "input/sample2.txt",
      "output_file": "completed/sample2_translated.txt",
      "status": "success",
      "error": "",
      "deleted": false,
      "archived": true,
      "archive_path": "archive/sample2.txt",
      "translation": {
        "detected_language": "英语",
        "translated_text": "翻译后的内容...",
        "summary": ""
      }
    }
  ],
  "message": "批量翻译完成：成功 2 个，失败 0 个"
}
```

### 批量翻译示例

1. 创建输入目录并放置待翻译文件：

```bash
mkdir -p input completed
echo "Hello, world!" > input/sample1.txt
echo "Machine learning is awesome." > input/sample2.txt
```

2. 执行批量翻译（从配置文件读取路径）：

```bash
python translator_main.py --batch --domain "计算机"
```

3. 查看翻译结果：

```bash
ls completed/
# completed/sample1_translated.txt
# completed/sample2_translated.txt

# 原文件已被移动到归档文件夹（如果配置了 delete_after_translation: false）
ls archive/
# archive/sample1.txt
# archive/sample2.txt

# 或者原文件已被删除（如果配置了 delete_after_translation: true）
ls input/
# （空目录）
```

## 命令行参数

### 单文本翻译模式

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--text` | str | 是* | - | 需要翻译的原文内容 |
| `--target_lang` | str | 否 | Chinese | 目标翻译语言 |
| `--domain` | str | 否 | - | 翻译的专业领域 |
| `--glossary` | str | 否 | - | 专业词汇表（Key=Value 或 JSON） |
| `--summary` | bool | 否 | False | 是否生成摘要 |
| `--config` | str | 否 | config.yaml | 配置文件路径 |

### 批量翻译模式

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--batch` | flag | 否* | True | 启用批量翻译模式（无参数时默认启用） |
| `--input_dir` | str | 否 | 从配置文件读取 | 输入文件目录 |
| `--output_dir` | str | 否 | 从配置文件读取 | 输出文件目录 |
| `--file_pattern` | str | 否 | 从配置文件读取 | 文件匹配模式 |
| `--delete_after` | flag | 否 | 从配置文件读取 | 翻译完成后删除原文件 |
| `--no_delete` | flag | 否 | - | 翻译完成后不删除原文件（优先于 --delete_after） |
| `--batch_config` | str | 否 | - | 批量配置文件路径 |
| `--target_lang` | str | 否 | Chinese | 目标翻译语言 |
| `--domain` | str | 否 | - | 翻译的专业领域 |
| `--glossary` | str | 否 | - | 专业词汇表（Key=Value 或 JSON） |
| `--summary` | bool | 否 | False | 是否生成摘要 |
| `--config` | str | 否 | config.yaml | 配置文件路径 |

* 如果不指定 `--text` 或 `--batch`，默认使用批量翻译模式
** 使用 `--batch_config` 时不需要指定 `--input_dir`、`--output_dir` 等参数

## Java 集成示例

### 单文本翻译

#### 使用 ProcessBuilder

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import org.json.JSONObject;

public class TranslationClient {
    public static String translate(String text, String targetLang, String domain, String glossary, boolean summary) {
        try {
            // 构建命令
            ProcessBuilder pb = new ProcessBuilder("python", "translator_main.py");
            
            // 添加参数
            pb.command().add("--text");
            pb.command().add(text);
            
            if (targetLang != null) {
                pb.command().add("--target_lang");
                pb.command().add(targetLang);
            }
            
            if (domain != null) {
                pb.command().add("--domain");
                pb.command().add(domain);
            }
            
            if (glossary != null) {
                pb.command().add("--glossary");
                pb.command().add(glossary);
            }
            
            if (summary) {
                pb.command().add("--summary");
            }
            
            // 启动进程
            Process process = pb.start();
            
            // 读取输出
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line);
            }
            
            // 等待进程结束
            int exitCode = process.waitFor();
            
            if (exitCode != 0) {
                throw new RuntimeException("翻译失败，退出码: " + exitCode);
            }
            
            return output.toString();
            
        } catch (Exception e) {
            throw new RuntimeException("翻译过程中发生错误", e);
        }
    }
    
    public static void main(String[] args) {
        String result = translate("Hello, world!", "Chinese", null, null, false);
        JSONObject json = new JSONObject(result);
        
        System.out.println("检测到的语言: " + json.getString("detected_language"));
        System.out.println("翻译结果: " + json.getString("translated_text"));
        System.out.println("摘要: " + json.getString("summary"));
    }
}
```

### 批量文件翻译

```java
import java.io.BufferedReader;
import java.io.InputStreamReader;
import org.json.JSONObject;
import org.json.JSONArray;

public class BatchTranslationClient {
    public static String batchTranslate(String inputDir, String outputDir, String domain) {
        try {
            // 构建命令
            ProcessBuilder pb = new ProcessBuilder("python", "translator_main.py");
            pb.command().add("--batch");
            pb.command().add("--input_dir");
            pb.command().add(inputDir);
            pb.command().add("--output_dir");
            pb.command().add(outputDir);
            
            if (domain != null) {
                pb.command().add("--domain");
                pb.command().add(domain);
            }
            
            // 启动进程
            Process process = pb.start();
            
            // 读取输出
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line);
            }
            
            // 等待进程结束
            int exitCode = process.waitFor();
            
            if (exitCode != 0) {
                throw new RuntimeException("批量翻译失败，退出码: " + exitCode);
            }
            
            return output.toString();
            
        } catch (Exception e) {
            throw new RuntimeException("批量翻译过程中发生错误", e);
        }
    }
    
    public static void main(String[] args) {
        String result = batchTranslate("./input", "./output", "计算机");
        JSONObject json = new JSONObject(result);
        
        System.out.println("总文件数: " + json.getInt("total_files"));
        System.out.println("成功数: " + json.getInt("success_count"));
        System.out.println("失败数: " + json.getInt("failed_count"));
        System.out.println("消息: " + json.getString("message"));
        
        // 遍历每个文件的结果
        JSONArray results = json.getJSONArray("results");
        for (int i = 0; i < results.length(); i++) {
            JSONObject fileResult = results.getJSONObject(i);
            System.out.println("\n文件: " + fileResult.getString("input_file"));
            System.out.println("状态: " + fileResult.getString("status"));
            
            if (fileResult.getString("status").equals("success")) {
                JSONObject translation = fileResult.getJSONObject("translation");
                System.out.println("检测到的语言: " + translation.getString("detected_language"));
                System.out.println("翻译结果: " + translation.getString("translated_text"));
            } else {
                System.out.println("错误: " + fileResult.getString("error"));
            }
        }
    }
}
```

## 输出格式

### 成功响应

```json
{
  "detected_language": "English",
  "translated_text": "翻译后的中文内容...",
  "summary": "摘要内容（如果未开启则为空字符串）"
}
```

### 错误响应

```json
{
  "error": "错误描述信息",
  "detected_language": "未知",
  "translated_text": "",
  "summary": ""
}
```

## 错误处理

脚本包含完善的错误处理机制：

1. **配置文件错误**：配置文件不存在或格式错误时，返回包含 error 字段的 JSON
2. **API 连接错误**：无法连接到 Ollama 服务时，返回明确的错误信息
3. **API 超时**：支持自动重试，超过最大重试次数后返回错误
4. **参数错误**：缺少必填参数时，提示正确的使用方法

## 常见问题

### Q: 如何修改使用的模型？

A: 编辑 [`config.yaml`](config.yaml:1) 文件，修改 `ollama.model` 字段为您已安装的模型名称（如 `qwen`、`mistral` 等）。

### Q: 如何提高翻译质量？

A: 可以通过以下方式优化：
- 使用更大参数量的模型
- 调整 `temperature` 参数（降低可提高确定性）
- 提供专业领域和词汇表
- 使用 `--summary` 参数可以生成摘要帮助理解

### Q: 支持哪些语言？

A: 支持的语言取决于使用的 Ollama 模型。常见的模型如 llama3、qwen 等都支持多语言翻译。

### Q: 如何处理超长文本？

A: 脚本支持自动分段翻译功能：
- 在 `config.yaml` 中配置 `chunk_translation` 参数
- 当文本长度超过 `max_chunk_size` 时，会自动分段翻译
- 分段时会保持上下文连续性（通过 `chunk_overlap` 参数控制重叠字符数）
- 翻译完成后会自动合并各段结果，并智能去除重复内容

示例配置：
```yaml
translation:
  chunk_translation:
    enabled: true            # 启用分段翻译
    max_chunk_size: 2000     # 单段最大字符数
    chunk_overlap: 100       # 分段重叠字符数
```

### Q: 语言检测准确吗？

A: 脚本使用 LLM 进行自动语言检测，具有以下特点：
- 支持多种常见语言（英语、中文、日语、韩语、法语、德语、西班牙语、俄语等）
- 对于超长文本，只取前 500 字符进行检测，提高效率
- 语言名称自动标准化为中文标注
- 检测结果会在日志中详细输出，方便调试

### Q: 如何提高语言检测准确性？

A: 可以通过以下方式优化：
- 确保输入文本具有明显的语言特征
- 使用更大参数量的模型
- 在 `config.yaml` 中调整语言检测的采样文本长度（修改代码中的 `sample_text = text[:500]`）

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
