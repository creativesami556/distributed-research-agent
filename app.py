import os
import json
import streamlit as st
import arxiv
from ddgs import DDGS
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openai import OpenAI

# -------------------------------------------------------------
# Configuration (Users must set this in the sidebar UI)
# -------------------------------------------------------------
MEMORY_FILE = "agent_memory.json"

# -------------------------------------------------------------
# Memory Management 
# -------------------------------------------------------------
def load_persistent_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_persistent_memory(messages):
    serializable = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"] and msg.get("content"):
            serializable.append({"role": msg["role"], "content": msg["content"]})
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)

# -------------------------------------------------------------
# Research Tools
# -------------------------------------------------------------
def search_arxiv(query: str, max_results: int = 5) -> str:
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    client_arxiv = arxiv.Client()
    results = []
    for paper in client_arxiv.results(search):
        results.append({
            "title": paper.title,
            "published": paper.published.strftime("%Y"),
            "authors": [a.name for a in paper.authors[:3]],
            "summary": paper.summary.replace("\n", " "),
            "url": paper.entry_id
        })
    return json.dumps(results, indent=2)

def search_web(query: str, max_results: int = 5) -> str:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title"),
                "snippet": r.get("body"),
                "url": r.get("href")
            })
    return json.dumps(results, indent=2)

def create_ieee_docx(paper_data: dict, filename: str = "IEEE_Research_Paper.docx") -> str:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.63)
        section.right_margin = Inches(0.63)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(paper_data.get("title", "IEEE Research Paper"))
    r_title.font.name = 'Times New Roman'
    r_title.font.size = Pt(20)
    r_title.bold = True

    # Author
    p_auth = doc.add_paragraph()
    p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_auth = p_auth.add_run("Autonomous Research Agent System\nDepartment of Technical Research\n")
    r_auth.font.name = 'Times New Roman'
    r_auth.italic = True

    # Sections
    for sec in paper_data.get("sections", []):
        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_head = p_head.add_run(sec.get("heading", "").upper())
        r_head.bold = True

        p_body = doc.add_paragraph()
        p_body.paragraph_format.first_line_indent = Inches(0.2)
        p_body.add_run(sec.get("content", ""))

    doc.save(filename)
    return f"IEEE document successfully compiled and saved as {filename}"

available_tools = {
    "search_arxiv": search_arxiv,
    "search_web": search_web,
    "create_ieee_docx": create_ieee_docx
}

tool_declarations = [
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": "Search academic literature on arXiv.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live web using DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_ieee_docx",
            "description": "Synthesize findings into an IEEE-formatted DOCX.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "paper_data": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "sections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "heading": {"type": "string"},
                                        "content": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["title", "sections"]
                    }
                },
                "required": ["filename", "paper_data"]
            }
        }
    }
]

# -------------------------------------------------------------
# Streamlit UI Configuration
# -------------------------------------------------------------
st.set_page_view = "wide"
st.set_page_config(page_title="Distributed Research Agent", page_icon="🔬", layout="wide")

with st.sidebar:
    st.title("⚙️ Cluster Control")
    orchestrator_ip = st.text_input("Orchestrator IP Address", value="127.0.0.1")
    api_port = st.text_input("API Port", value="8080")
    
    st.divider()
    st.subheader("🧠 Memory Storage")
    if st.button("🗑️ Clear Conversation Memory"):
        st.session_state.messages = []
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)
        st.success("Memory cleared.")
        st.rerun()

client = OpenAI(base_url=f"http://{orchestrator_ip}:{api_port}/v1", api_key="not-needed")

st.title("🔬 Autonomous IEEE Research Agent")
st.caption("Distributed inference powered by llama.cpp cluster")

if "messages" not in st.session_state:
    st.session_state.messages = load_persistent_memory()

for msg in st.session_state.messages:
    if msg.get("role") in ["user", "assistant"] and msg.get("content"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Enter research topic..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = {
        "role": "system",
        "content": "You are an expert academic research engineer authoring IEEE papers."
    }
    
    active_dialogue = [system_prompt] + st.session_state.messages[-8:]

    with st.chat_message("assistant"):
        with st.status("🧠 Agent thinking and coordinating with cluster...", expanded=True) as status_box:
            latest_output_file = None

            while True:
                response = client.chat.completions.create(
                    model="default",
                    messages=active_dialogue,
                    tools=tool_declarations,
                    tool_choice="auto"
                )
                message = response.choices[0].message
                active_dialogue.append(message)

                if not message.tool_calls:
                    final_reply = message.content or "Task completed."
                    st.session_state.messages.append({"role": "assistant", "content": final_reply})
                    save_persistent_memory(st.session_state.messages)
                    status_box.update(label="✅ Task complete!", state="complete", expanded=False)
                    st.markdown(final_reply)
                    break

                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    st.write(f"Executing: `{func_name}`")

                    tool_fn = available_tools.get(func_name)
                    tool_output = tool_fn(**func_args) if tool_fn else "Error: Tool unavailable."

                    active_dialogue.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_output)
                    })

            if latest_output_file and os.path.exists(latest_output_file):
                with open(latest_output_file, "rb") as file_bytes:
                    st.download_button(
                        label=f"⬇️ Download {latest_output_file}",
                        data=file_bytes,
                        file_name=latest_output_file,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
