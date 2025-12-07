from services import read_schema_snapshot
from dotenv import load_dotenv
import os
from neo4j import GraphDatabase, Driver
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from typing import Optional

load_dotenv()

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
print("NEO4J_DATABASE:", NEO4J_DATABASE)
print("NEO4J_URI:", NEO4J_URI)
print("NEO4J_USER:", NEO4J_USER)
print("NEO4J_PASSWORD:", NEO4J_PASSWORD)
def connect_neo4j() -> Optional[Driver]:
    """_summary_

    Returns:
        Optional[Driver]: _description_
    """
    if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return None


driver = connect_neo4j()

try:
    driver = connect_neo4j()
    schema_text = read_schema_snapshot(driver)
    print("Chatbot service initialized successfully.")
    print("Schema Snapshot:")
    print(schema_text)
except Exception as exc:  # pragma: no cover - depends on env
    print(f"[startup] Chatbot service not initiealizd: {exc!r}")

