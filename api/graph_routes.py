"""Neo4j graph insights endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from services.neo4j_exec import connect_neo4j

router = APIRouter(prefix="/api/graph", tags=["graph"])
# Alias router for admin namespace (same handlers)
admin_router = APIRouter(prefix="/api/admin/graph", tags=["graph"])


class LabelStat(BaseModel):
    label: str
    count: int


class GraphPreviewNode(BaseModel):
    id: int
    labels: List[str]


class GraphPreviewRelationship(BaseModel):
    source_id: int
    target_id: int
    type: str


class GraphPreview(BaseModel):
    nodes: List[GraphPreviewNode]
    relationships: List[GraphPreviewRelationship]


class GraphSummaryResponse(BaseModel):
    node_count: int
    relationship_count: int
    relationship_types: List[str]
    labels: List[LabelStat]
    sample: Optional[GraphPreview] = None


SUMMARY_QUERY = """
MATCH (n)
WITH count(n) AS node_count
MATCH ()-[r]->()
WITH node_count, count(r) AS relationship_count, collect(DISTINCT type(r)) AS relationship_types
RETURN node_count, relationship_count, relationship_types
"""

LABEL_STATS_QUERY = """
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS count
ORDER BY count DESC
LIMIT 25
"""

SAMPLE_GRAPH_QUERY = """
MATCH (n)-[r]->(m)
RETURN id(n) AS source_id, labels(n) AS source_labels,
       id(m) AS target_id, labels(m) AS target_labels,
       type(r) AS type
LIMIT 50
"""


def _get_driver(request: Request):
    driver = getattr(request.app.state, "driver", None)
    if driver:
        return driver
    driver = connect_neo4j()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is not configured",
        )
    request.app.state.driver = driver
    return driver


def _run_query(driver, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    params = params or {}
    with driver.session() as session:
        result = session.run(cypher, params)
        return [record.data() for record in result]


def _build_sample(records: List[Dict[str, Any]]) -> Optional[GraphPreview]:
    if not records:
        return None
    nodes: Dict[int, GraphPreviewNode] = {}
    relationships: List[GraphPreviewRelationship] = []

    for row in records:
        src_id = row["source_id"]
        tgt_id = row["target_id"]
        nodes[src_id] = GraphPreviewNode(id=src_id, labels=row.get("source_labels", []))
        nodes[tgt_id] = GraphPreviewNode(id=tgt_id, labels=row.get("target_labels", []))
        relationships.append(
            GraphPreviewRelationship(
                source_id=src_id,
                target_id=tgt_id,
                type=row.get("type", ""),
            )
        )

    return GraphPreview(nodes=list(nodes.values()), relationships=relationships)


@router.get("/summary", response_model=GraphSummaryResponse)
def graph_summary(request: Request) -> GraphSummaryResponse:
    """Thống kê nhanh Neo4j: số node, số edge, loại quan hệ, nhãn phổ biến và mẫu subgraph nhỏ."""
    driver = _get_driver(request)

    try:
        summary_rows = _run_query(driver, SUMMARY_QUERY)
        if not summary_rows:
            raise HTTPException(status_code=503, detail="Cannot retrieve graph summary")
        summary = summary_rows[0]

        label_rows = _run_query(driver, LABEL_STATS_QUERY)
        labels = [LabelStat(label=row["label"], count=row["count"]) for row in label_rows]

        sample_rows = _run_query(driver, SAMPLE_GRAPH_QUERY)
        sample = _build_sample(sample_rows)

        return GraphSummaryResponse(
            node_count=summary.get("node_count", 0),
            relationship_count=summary.get("relationship_count", 0),
            relationship_types=summary.get("relationship_types", []),
            labels=labels,
            sample=sample,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neo4j query failed: {exc}",
        ) from exc


@admin_router.get("/summary", response_model=GraphSummaryResponse)
def admin_graph_summary(request: Request) -> GraphSummaryResponse:
    """Alias admin endpoint trả về thống kê đồ thị Neo4j."""
    return graph_summary(request)
