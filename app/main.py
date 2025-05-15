"""
应用入口模块
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.router import api_router
from app.core.logging import logger
from app.config import HOST, PORT

# 创建FastAPI应用
app = FastAPI(title="实时语音转写")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="templates")

# 注册API路由
app.include_router(api_router)

# 主页路由
@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    """
    渲染主页
    
    Args:
        request: 请求对象
    
    Returns:
        HTML响应
    """
    return templates.TemplateResponse("index.html", {"request": request})

# 应用启动入口
if __name__ == '__main__':
    try:
        logger.info("启动应用服务器")
        uvicorn.run(app, host=HOST, port=PORT)
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")