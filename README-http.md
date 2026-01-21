python main.py

依赖导出:
pip freeze > requirements.txt
安装依赖:
pip install -r requirements.txt

## 该系统是一个基于大模型的翻译平台，后端基于FastApi + Ollama，前端使用Vue3 + TS + ElementPlus。

## 后端启动方式(windows)：
一、在根目录下：
1. 创建虚拟环境：`python -m venv venv`
2. 激活环境：`venv\Scripts\activate`

二、进入server目录：`cd backend`
4. 安装依赖：`pip install -r requirements.txt`
5. 启动服务：`python server\main.py`

## 前端启动方式(windows)：

1. 进入frontend目录：`cd frontend`
2. 安装依赖：`npm install`
3. 启动服务：`npm run dev`
