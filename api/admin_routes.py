"""Admin/graph utilities for visualization."""
from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/graph", response_model=Dict[str, Any])
def get_graph_snapshot() -> Dict[str, Any]:
    """Trả về danh sách node/edge (giới hạn) để FE hiển thị đồ thị."""
    data = AdminService.get_neo4j_graph_data()
    if not data:
        raise HTTPException(status_code=503, detail="Graph data unavailable")
    return data


@router.get("/graph/stats", response_model=Dict[str, Any])
def get_graph_stats() -> Dict[str, Any]:
    """Trả về thống kê số lượng node theo label và quan hệ theo type."""
    data = AdminService.get_neo4j_stats()
    if not data:
        raise HTTPException(status_code=503, detail="Graph stats unavailable")
    return data
