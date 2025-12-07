from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services import connect_neo4j, read_schema_snapshot
from services.database import init_db
from services.chatbot_service import ChatbotService
from .user_routes import router as user_router
from .chatbot_routes import router as chatbot_router
from .graph_routes import router as graph_router, admin_router as graph_admin_router

TAGS_METADATA = [
    {"name": "users", "description": "Đăng ký, đăng nhập và quản lý người dùng"},
    {"name": "chatbot", "description": "Hỏi đáp tư vấn du học/visa (Gemini + Neo4j)"},
    {"name": "graph", "description": "Thống kê và sơ đồ Neo4j"},
    {"name": "system", "description": "Kiểm tra sức khỏe hệ thống và xem schema Neo4j"},
]

APP_DESCRIPTION = (
    "API cho hệ thống tư vấn VISA: bao gồm đăng ký/đăng nhập người dùng và chatbot Neo4j."
    " Xem ngay các endpoint tại trang Swagger (/docs)."
)

app = FastAPI(
    title="Visa Chatbot API",
    version="1.0.0",
    description=APP_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include user routes
app.include_router(user_router)
app.include_router(chatbot_router)
app.include_router(graph_router)
app.include_router(graph_admin_router)

@app.on_event("startup")
def _startup() -> None:
    # Initialize database tables
    init_db()
    
    # Initialize chatbot service (Gemini + Neo4j)
    try:
        driver = connect_neo4j()
        app.state.chatbot_service = ChatbotService(driver=driver)
        app.state.schema_text = read_schema_snapshot(driver)
        app.state.driver = driver
    except Exception as exc:  # pragma: no cover - depends on env
        # Keep server running even if chatbot init fails (e.g., missing keys)
        app.state.chatbot_service = None
        print(f"[startup] Chatbot service not initialized: {exc!r}")

    # Provide safe defaults so /schema remains available even if init fails
    app.state.schema_text = getattr(app.state, "schema_text", None) or "Schema unavailable"
    app.state.driver = getattr(app.state, "driver", None) or connect_neo4j()

@app.on_event("shutdown")
def _shutdown() -> None:
    driver = getattr(app.state, "driver", None)
    if driver:
        driver.close()

@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Landing endpoint directing users to Swagger docs."""
    return {"status": "ok", "docs": "/docs", "health": "/health"}

@app.get("/health", tags=["system"])
def health():
    """Lightweight health check to verify the API is running."""
    return {"status": "ok"}

@app.get("/schema", tags=["system"])
def schema():
    """Trả về snapshot schema Neo4j đã nạp lúc khởi động."""
    return {"schema": app.state.schema_text}
