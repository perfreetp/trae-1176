from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.routers import family, letter, person, attachment, permission, exhibition, search, export

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="家书收藏平台 API",
    description="面向纪念馆网站、家庭小程序和数字展厅的信件管理服务，提供家庭空间、信件档案、人物关系、影像附件、权限分享、展陈专题、检索统计、导出交接八组接口",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(family.router)
app.include_router(letter.router)
app.include_router(person.router)
app.include_router(attachment.router)
app.include_router(permission.router)
app.include_router(exhibition.router)
app.include_router(search.router)
app.include_router(export.router)


@app.get("/", summary="服务状态")
def root():
    return {
        "service": "家书收藏平台 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
