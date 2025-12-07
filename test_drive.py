from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Load biến môi trường trước
load_dotenv()

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD  # noqa: E402

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Cypher lấy quan hệ giữa các label
CYPHER_REL_BY_LABEL = """
MATCH (a)-[r]->(b)
WITH DISTINCT labels(a) AS fromLabels, type(r) AS relType, labels(b) AS toLabels
UNWIND fromLabels AS fromLabel
UNWIND toLabels AS toLabel
RETURN DISTINCT fromLabel, relType, toLabel
ORDER BY fromLabel, relType, toLabel
"""


def connect_neo4j() -> Driver:
    """Tạo Neo4j Driver, báo lỗi rõ nếu thiếu env."""
    if not NEO4J_URI:
        raise RuntimeError("NEO4J_URI is not set")
    if not NEO4J_USER:
        raise RuntimeError("NEO4J_USER is not set")
    if not NEO4J_PASSWORD:
        raise RuntimeError("NEO4J_PASSWORD is not set")

    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def get_label_relationships(driver: Driver):
    """Chạy Cypher để lấy relationships giữa các labels."""
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(CYPHER_REL_BY_LABEL)
        return [record.data() for record in result]


def main() -> None:
    print("NEO4J_DATABASE:", NEO4J_DATABASE)
    print("NEO4J_URI:", NEO4J_URI)
    print("NEO4J_USER:", NEO4J_USER)
    print("NEO4J_PASSWORD set:", bool(NEO4J_PASSWORD))

    driver: Optional[Driver] = None

    try:
        driver = connect_neo4j()

        rels = get_label_relationships(driver)
        print("Relationships between labels:")
        for r in rels:
            # Ví dụ: University -[HAS_PROGRAMS]-> ProgramGroup
            print(f"{r['fromLabel']} -[{r['relType']}]-> {r['toLabel']}")

    except Exception as exc:  # pragma: no cover - depends on env
        print(f"[startup] Error: {exc!r}")
    finally:
        if driver is not None:
            driver.close()


if __name__ == "__main__":
    main()
