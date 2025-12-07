"""
CHATBOT TƯ VẤN DU HỌC, VISA & ĐỊNH CƯ ÚC
Full-stack application with Streamlit UI + Gemini + Neo4j
"""

import streamlit as st
import google.generativeai as genai
from neo4j import GraphDatabase
import json
import os
from dotenv import load_dotenv

# ============================================================
# 1. CẤU HÌNH & KẾT NỐI
# ============================================================

load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Load System Prompt
with open(r'system_prompt.txt', 'r', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read()

# Initialize Gemini Model
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# Neo4j Driver
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

# ============================================================
# 2. CYPHER QUERY TEMPLATES
# ============================================================

QUERY_TEMPLATES = {
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
    """
}

# ============================================================
# 3. INTENT DETECTION
# ============================================================

def detect_intent(user_query):
    """Sử dụng Gemini để phát hiện intent"""
    prompt = f"""
    Phân tích câu hỏi sau và trả về JSON:
    
    User: "{user_query}"
    
    Trả về format:
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
        "query_type": "find_programs_by_university|find_programs_by_ielts|visa_info|..."
    }}
    
    Chỉ trả về JSON, không giải thích.
    """
    
    response = model.generate_content(prompt)
    try:
        # Parse JSON từ response
        result = json.loads(response.text.strip())
        return result
    except:
        # Fallback
        return {
            "intent": "STUDY",
            "entities": {},
            "query_type": "fallback"
        }

# ============================================================
# 4. EXECUTE CYPHER QUERY
# ============================================================

def execute_cypher(query_type, params):
    """Thực thi Cypher query"""
    if query_type not in QUERY_TEMPLATES:
        return None
    
    query = QUERY_TEMPLATES[query_type]
    
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query, **params)
        data = [record.data() for record in result]
        return data

# ============================================================
# 5. FORMAT RESPONSE
# ============================================================

def format_response(user_query, query_results):
    """Sử dụng Gemini để format response tự nhiên"""
    prompt = f"""
    User hỏi: "{user_query}"
    
    Kết quả từ database:
    {json.dumps(query_results, ensure_ascii=False, indent=2)}
    
    Hãy trả lời user một cách TỰ NHIÊN, thân thiện với:
    - Emoji phù hợp
    - Format đẹp (bullets, bold)
    - Đầy đủ thông tin
    - Gợi ý bước tiếp theo
    - Links (nếu có)
    
    Không nói về JSON hay database.
    """
    
    response = model.generate_content(prompt)
    return response.text

# ============================================================
# 6. MAIN CHATBOT LOGIC
# ============================================================

def chatbot_response(user_query):
    """Main function xử lý câu hỏi"""
    
    # Step 1: Detect intent & extract entities
    analysis = detect_intent(user_query)
    
    # Step 2: Execute query
    query_results = execute_cypher(
        analysis.get("query_type", "fallback"),
        analysis.get("entities", {})
    )
    
    # Step 3: Format response
    if query_results:
        response = format_response(user_query, query_results)
    else:
        # Fallback: Gemini trả lời trực tiếp
        response = model.generate_content(f"""
        User hỏi: "{user_query}"
        
        Không tìm thấy kết quả chính xác. 
        Hãy trả lời dựa trên kiến thức của bạn về du học, visa, định cư Úc.
        Nhắc user có thể hỏi cụ thể hơn.
        """).text
    
    return response

# ============================================================
# 7. STREAMLIT UI
# ============================================================

def main():
    # Page config
    st.set_page_config(
        page_title="🇦🇺 Chatbot Tư vấn Du học Úc",
        page_icon="🎓",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stTextInput > div > div > input {
        font-size: 18px;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #2196F3;
    }
    .bot-message {
        background-color: #ffffff;
        border-left: 5px solid #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🇦🇺 Chatbot Tư vấn Du học, Visa & Định cư Úc")
    st.markdown("*Được hỗ trợ bởi Gemini AI và Neo4j Knowledge Graph*")
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Gợi ý câu hỏi")
        
        st.markdown("### 🎓 Du học")
        if st.button("Tìm chương trình IT tại UNSW"):
            st.session_state.sample_query = "Tìm chương trình Master về Computer Science tại UNSW"
        if st.button("Trường nào IELTS 6.5?"):
            st.session_state.sample_query = "Trường nào yêu cầu IELTS 6.5 trở xuống?"
        
        st.markdown("### 🛂 Visa")
        if st.button("Visa 500 là gì?"):
            st.session_state.sample_query = "Visa 500 là gì và điều kiện xin như thế nào?"
        if st.button("Visa định cư nào dễ?"):
            st.session_state.sample_query = "Có những visa định cư nào?"
        
        st.markdown("### 🏠 Định cư")
        if st.button("Làm sao tìm việc?"):
            st.session_state.sample_query = "Làm sao tìm việc tại Úc?"
        
        st.markdown("### 🎯 Lộ trình")
        if st.button("Lộ trình IT → PR"):
            st.session_state.sample_query = "Tôi muốn học IT và định cư, hướng dẫn chi tiết"
        
        st.markdown("---")
        st.markdown("### ⚙️ Thống kê")
        if st.button("Xem thống kê hệ thống"):
            with driver.session(database=NEO4J_DATABASE) as session:
                stats = session.run("""
                    MATCH (u:University) WITH count(u) AS unis
                    MATCH (p:Program) WITH unis, count(p) AS progs
                    MATCH (v:Visa) WITH unis, progs, count(v) AS visas
                    RETURN unis, progs, visas
                """).single()
                
                st.metric("Universities", stats["unis"])
                st.metric("Programs", stats["progs"])
                st.metric("Visas", stats["visas"])
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        role_class = "user-message" if message["role"] == "user" else "bot-message"
        icon = "👤" if message["role"] == "user" else "🤖"
        
        st.markdown(f"""
        <div class="chat-message {role_class}">
            <strong>{icon} {message["role"].upper()}</strong><br>
            {message["content"]}
        </div>
        """, unsafe_allow_html=True)
    
    # User input
    user_input = st.chat_input("Hỏi gì đi... (VD: Tìm chương trình Master IT)")
    
    # Handle sample query from sidebar
    if "sample_query" in st.session_state:
        user_input = st.session_state.sample_query
        del st.session_state.sample_query
    
    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Show user message
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 USER</strong><br>
            {user_input}
        </div>
        """, unsafe_allow_html=True)
        
        # Get bot response
        with st.spinner("🤔 Đang suy nghĩ..."):
            bot_response = chatbot_response(user_input)
        
        # Add bot message
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_response
        })
        
        # Show bot message
        st.markdown(f"""
        <div class="chat-message bot-message">
            <strong>🤖 ASSISTANT</strong><br>
            {bot_response}
        </div>
        """, unsafe_allow_html=True)
        
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        💡 <strong>Tips:</strong> Hỏi cụ thể để nhận câu trả lời chính xác hơn!<br>
        📧 Contact: your-email@example.com | 🌐 Website: your-website.com
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 8. RUN APP
# ============================================================

if __name__ == "__main__":
    main()