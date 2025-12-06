from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from flow import build_flow
from services import connect_neo4j, read_schema_snapshot, execute_cypher
from services.database import init_db
from .user_routes import router as user_router

class Text2CypherRequest(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """
    question: str
    execute: bool = False

class Text2CypherResponse(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """
    extraction: Dict[str, Any]
    cypher: str
    params: Dict[str, Any]
    rows: Optional[List[Dict[str, Any]]] = None

app = FastAPI(title="Text2Cypher API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include user routes
app.include_router(user_router)

@app.on_event("startup")
def _startup() -> None:
    # Initialize database tables
    init_db()
    
    # Build once; reuse between requests
    # app.state.flow = build_flow()
    # app.state.driver = connect_neo4j()
    # app.state.schema_text = read_schema_snapshot(app.state.driver)

@app.on_event("shutdown")
def _shutdown() -> None:
    driver = getattr(app.state, "driver", None)
    if driver:
        driver.close()

@app.get("/health")
def health():
    """_summary_

    Returns:
        _type_: _description_
    """
    return {"status": "ok"}

@app.get("/schema")
def schema():
    """_summary_

    Returns:
        _type_: _description_
    """
    return {"schema": app.state.schema_text}

@app.post("/text2cypher", response_model=Text2CypherResponse)
def text2cypher(req: Text2CypherRequest):
    """_summary_

    Args:
        req (Text2CypherRequest): _description_

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    try:
        state = {
            "question": req.question,
            "schema_text": app.state.schema_text,
            "extraction": None,
            "query": None,
            "rows": None,
        }

        final = app.state.flow.invoke(state)
        extraction = final["extraction"]
        query = final["query"]

        rows = None
        if req.execute:
            rows = execute_cypher(app.state.driver, query.cypher, query.params)

        return Text2CypherResponse(
            extraction=extraction.model_dump(),
            cypher=query.cypher,
            params=query.params,
            rows=rows,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e