from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv
from neo4j import Driver

from config import GEMINI_MODEL, GOOGLE_API_KEY
from services.neo4j_exec import connect_neo4j

load_dotenv()

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "system_prompt.txt"
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant for Australian study, visa, and settlement questions. "
    "Answer briefly in Vietnamese with bullet points where helpful, add links if available, "
    "and keep a friendly, encouraging tone."
)

QUERY_TEMPLATES: Dict[str, str] = {
    "find_programs_by_university": """
        MATCH (u:University {name: $university_name})
        MATCH (u)-[:HAS_PROGRAMS]->(pg:ProgramGroup)
              -[:HAS_LEVEL]->(pl:ProgramLevel {name: $level})
              -[:OFFERS]->(p:Program)
        OPTIONAL MATCH (p)-[:HAS_REQUIRED]->(es:ExamScore)<-[:HAS_SCORE]-(e:Exam)
        RETURN u.name AS university,
               p.name AS program_name,
               p.url AS program_url,
               p.starting_months AS starting_months,
               collect({exam: e.name, score: es.value}) AS requirements
        LIMIT 10
    """,
    "find_programs_by_ielts": """
        MATCH (p:Program)-[:HAS_REQUIRED]->(es:ExamScore)
              <-[:HAS_SCORE]-(e:Exam {name: "IELTS"})
        WHERE es.value <= $max_score
        MATCH (p)<-[:OFFERS]-(pl:ProgramLevel)
              <-[:HAS_LEVEL]-(pg:ProgramGroup)
              <-[:HAS_PROGRAMS]-(u:University)
        RETURN u.name AS university,
               p.name AS program_name,
               es.value AS ielts_required,
               p.url AS url
        ORDER BY es.value ASC
        LIMIT 10
    """,
    "visa_info": """
        MATCH (v:Visa {subclass: $subclass})
        OPTIONAL MATCH (v)-[:HAS_ABOUT_INFO]->(a:AboutInfo)
        RETURN v.name_visa AS visa_name,
               v.subclass AS subclass,
               v.url AS official_url,
               collect({field: a.field, content: a.content}) AS about_information
    """,
    "visa_eligibility": """
        MATCH (v:Visa {subclass: $subclass})
              -[:HAS_ELIGIBILITY_GROUP]->(eg:EligibilityGroup)
              -[:HAS_REQUIREMENT]->(er:EligibilityRequirement)
        RETURN v.name_visa AS visa_name,
               eg.group_key AS requirement_group,
               collect({key: er.key, content: er.content}) AS requirements
        ORDER BY eg.group_key
    """,
    "settlement_info": """
        MATCH (cat:SettlementCategory)
        WHERE toLower(cat.name) CONTAINS toLower($keyword)
        MATCH (cat)-[:HAS_GROUP]->(tg:SettlementTaskGroup)
              -[:CONTAINS_SETTLEMENT_PAGE]->(sp:SettlementPage)
        RETURN cat.name AS category,
               collect(DISTINCT {
                   task_group: tg.name,
                   page_title: sp.title,
                   page_url: sp.url
               }) AS related_info
        LIMIT 5
    """,
    "comprehensive_pathway": """
        MATCH (p:Program)-[:FOCUSES_ON]->(subj:Subject)
        WHERE toLower(subj.name) CONTAINS toLower($field)
        MATCH (p)<-[:OFFERS]-(pl:ProgramLevel)<-[:HAS_LEVEL]-(pg:ProgramGroup)
              <-[:HAS_PROGRAMS]-(u:University)
        OPTIONAL MATCH (p)-[:HAS_REQUIRED]->(es:ExamScore)<-[:HAS_SCORE]-(e:Exam)
        WITH u, p, collect({exam: e.name, score: es.value}) AS requirements
        LIMIT 3
        MATCH (v:Visa {subclass: "500"})
        MATCH (vpr:Visa)
        WHERE vpr.subclass IN ["189", "190"]
        RETURN {
            study: {
                university: u.name,
                program: p.name,
                requirements: requirements,
                url: p.url
            },
            student_visa: {
                name: v.name_visa,
                subclass: v.subclass
            },
            pr_visas: collect(DISTINCT {
                name: vpr.name_visa,
                subclass: vpr.subclass
            })
        } AS pathway
    """,
}


@dataclass
class ChatbotResult:
    reply: str
    analysis: Dict[str, Any]
    query_results: Optional[List[Dict[str, Any]]]
    query_type: str


class ChatbotService:
    """Encapsulate chatbot logic for reuse across API and UI."""

    def __init__(self, driver: Optional[Driver] = None) -> None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required for chatbot responses.")

        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=self._load_system_prompt(),
        )
        self.driver = driver or connect_neo4j()

    @staticmethod
    def _load_system_prompt() -> str:
        if SYSTEM_PROMPT_PATH.exists():
            return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
        return DEFAULT_SYSTEM_PROMPT

    def detect_intent(self, user_query: str) -> Dict[str, Any]:
        prompt = f"""
Analyze the question and return JSON only.

User: "{user_query}"

Return format:
{{
    "intent": "STUDY|VISA|SETTLEMENT|PATHWAY|COMPARE",
    "entities": {{
        "university_name": "...",
        "level": "Bachelor|Master|Doctor",
        "field": "...",
        "exam_type": "IELTS|TOEFL",
        "score": 6.5,
        "visa_subclass": "500",
        "keyword": "..."
    }},
    "query_type": "find_programs_by_university|find_programs_by_ielts|visa_info|visa_eligibility|settlement_info|comprehensive_pathway"
}}

Only output valid JSON, no explanation.
"""
        response = self.model.generate_content(prompt)
        try:
            return json.loads(response.text.strip())
        except Exception:
            return {
                "intent": "STUDY",
                "entities": {},
                "query_type": "fallback",
            }

    def execute_cypher(self, query_type: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if query_type not in QUERY_TEMPLATES or not self.driver:
            return []

        query = QUERY_TEMPLATES[query_type]
        with self.driver.session(database=NEO4J_DATABASE) as session:
            result = session.run(query, **params)
            return [record.data() for record in result]

    def format_response(self, user_query: str, query_results: List[Dict[str, Any]]) -> str:
        prompt = f"""
User question: "{user_query}"

Database results:
{json.dumps(query_results, ensure_ascii=False, indent=2)}

Respond naturally in Vietnamese:
- Friendly tone and concise
- Use bullets and bold where helpful
- Add links if present
- Suggest next steps briefly
"""
        response = self.model.generate_content(prompt)
        return response.text

    def _fallback_response(self, user_query: str) -> str:
        response = self.model.generate_content(
            f"""
User question: "{user_query}"

No exact database match. Answer based on your knowledge about studying, visas, and settlement in Australia.
Keep the answer short, helpful, and invite the user to ask for more details.
"""
        )
        return response.text

    def chat(self, user_query: str) -> ChatbotResult:
        if not user_query or not user_query.strip():
            raise ValueError("message must not be empty.")

        cleaned_query = user_query.strip()
        analysis = self.detect_intent(cleaned_query)
        query_type = analysis.get("query_type") or analysis.get("intent") or "fallback"
        entities = analysis.get("entities") or {}

        rows = self.execute_cypher(query_type, entities)
        if rows:
            reply = self.format_response(cleaned_query, rows)
        else:
            reply = self._fallback_response(cleaned_query)

        return ChatbotResult(
            reply=reply,
            analysis=analysis,
            query_results=rows or None,
            query_type=query_type,
        )

    def close(self) -> None:
        if self.driver:
            self.driver.close()


@lru_cache(maxsize=1)
def get_chatbot_service() -> ChatbotService:
    return ChatbotService()


def reset_chatbot_service_cache() -> None:
    get_chatbot_service.cache_clear()
