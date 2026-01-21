import sys
import os

# 获取当前文件 (main.py) 的父目录的父目录 (即项目根目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(BASE_DIR)
sys.path.append(ROOT_DIR)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routers import translation_router
# from server.routers import file_router
from src.utils.logging_config import setup_logging
from src.utils.lifespan import lifespan
import uvicorn

# 设置日志配置
setup_logging()

def create_app() -> FastAPI:
    """
    创建FastAPI实例
    """
    app = FastAPI(lifespan=lifespan)
    
    # 配置 CORS 中间件，允许所有来源访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # 注册路由
    app.include_router(translation_router.router, prefix="/translation", tags=["翻译模块"])
    # app.include_router(file_router.router, prefix="/file", tags=["文件模块"])
    
    @app.get("/")
    def root_endpoint():
        return {"message": "统一入口"}
    
    return app


if __name__ == "__main__":

    app = create_app()
    
    # 打印所有路由
    print("当前 FastAPI 已注册路由列表：")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"{route.path}")
        else:
            print(f"  {route} - {type(route)}")
   
    # 生产环境配置（多进程）
    uvicorn.run(
        "main:create_app",   # 用 factory 模式, 必须在 uvicorn.run 中指定 factory=True
        host="127.0.0.1",
        port=8090,
        loop="asyncio",     # 使用 asyncio 事件循环
        workers=1,          # 启动的进程个数
        reload=True,        # 自动重载代码变更，异步下需要设置为 True
        factory=True        # 启用 factory 模式，该模式下必须指定 "模块名:函数名"，作用是每个进程独立创建 FastAPI 实例
    )
