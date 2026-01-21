# 翻译引擎 HTTP 接口文档

基础地址：`http://{FASTAPI_HOST}:{FASTAPI_PORT}`  
默认：`http://127.0.0.1:8090`

统一响应结构：
```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

## 1. 健康入口

**GET /**

返回：
```json
{
  "message": "统一入口"
}
```

## 2. 单文本翻译

**POST /translation/text**

请求体：
```json
{
  "text": "Hello",
  "target_lang": "Chinese",
  "domain": "计算机",
  "glossary": "AI=人工智能",
  "summary": true
}
```

字段说明：
- text：必填
- target_lang/domain/glossary/summary：可选
- summary = null 时走 config.yaml 默认值

成功返回示例：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "translated_text": "...",
    "summary": "...",
    "detected_language": "..."
  }
}
```

## 3. 批量翻译

**POST /translation/batch**

请求体：
```json
{
  "input_dir": "./input",
  "output_dir": "./completed",
  "target_lang": "Chinese",
  "domain": "计算机",
  "glossary": "AI=人工智能",
  "summary": false,
  "file_pattern": "*.txt",
  "delete_after": false,
  "batch_config": "batch_config.yaml"
}
```

字段说明：
- input_dir/output_dir/file_pattern/delete_after：可选
- batch_config：可选，存在时忽略其他批量参数
- 相对路径默认相对 backend 目录

成功返回示例：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "total_files": 10,
    "success_count": 9,
    "failed_count": 1,
    "results": []
  }
}
```

## 4. 清理语言检测缓存

**POST /translation/cache/clear**

成功返回示例：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "cleared": 123
  }
}
```

## 5. 获取缓存统计

**GET /translation/cache/stats**

成功返回示例：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "cache_size": 123
  }
}
```

## 6. curl 示例

单文本：
```bash
curl -X POST http://127.0.0.1:8090/translation/text -H "Content-Type: application/json" -d "{\"text\":\"Hello\"}"
```

批量：
```bash
curl -X POST http://127.0.0.1:8090/translation/batch -H "Content-Type: application/json" -d "{\"input_dir\":\"./input\",\"output_dir\":\"./completed\"}"
```
