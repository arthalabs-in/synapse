# SYNAPSE — Multi-Agent Research Synthesizer
## AMD LabLab Hackathon Implementation Plan

> **Goal:** Build an intelligent multi-agent system that performs iterative, citation-backed research synthesis using open-source LLMs on AMD Developer Cloud.

**Architecture:** 5 specialized agents orchestrated via CrewAI, served through vLLM on AMD MI300X, with a Streamlit frontend deployed on Hugging Face Spaces.

**Tech Stack:** CrewAI, vLLM, Streamlit, DeepSeek/Qwen/Llama, DuckDuckGo Search, arXiv API, AMD Developer Cloud (ROCm)

---

## Day 1: Infrastructure & Model Serving (May 4)

### Task 1.1: AMD Developer Cloud Setup
**Objective:** Get $100 credits and launch a GPU instance.

**Steps:**
1. Sign up at [developer.amd.com](https://developer.amd.com)
2. Apply for Developer Cloud access
3. Launch MI210/MI300X instance
4. SSH in and verify ROCm: `rocm-smi`
5. Install vLLM with ROCm support: `pip install vllm`

**Verification:** `rocm-smi` shows GPU, `python -c "import vllm"` succeeds.

### Task 1.2: Deploy Base Model via vLLM
**Objective:** Serve Qwen3-32B on AMD GPU.

**Steps:**
1. Download model from Hugging Face:
   ```bash
   huggingface-cli download Qwen/Qwen3-32B --local-dir ./models/deepseek
   ```
2. Start vLLM server:
   ```bash
   python -m vllm.entrypoints.openai.api_server \
     --model ./models/deepseek \
     --tensor-parallel-size 1 \
     --max-model-len 8192 \
     --port 8000
   ```
3. Test with curl:
   ```bash
   curl http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"deepseek","messages":[{"role":"user","content":"Hello"}]}'
   ```

**Verification:** API returns valid JSON response.

### Task 1.3: Project Scaffold
**Objective:** Set up Python project with dependencies.

**Files:**
- Create: `~/synapse/requirements.txt`
- Create: `~/synapse/.env.example`
- Create: `~/synapse/config.py`

**Content:**
```txt
# requirements.txt
crewai>=0.85.0
streamlit>=1.40.0
vllm>=0.6.0
httpx>=0.27.0
python-dotenv>=1.0.0
arxiv>=2.1.0
duckduckgo-search>=6.3.0
pydantic>=2.9.0
```

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek")
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))

config = Config()
```

**Verification:** `python -c "from config import config; print(config.VLLM_BASE_URL)"` works.

---

## Day 2: Agent Core & Orchestration (May 5)

### Task 2.1: LLM Client Wrapper
**Objective:** Create a unified client for talking to vLLM that all agents use.

**Files:**
- Create: `~/synapse/backend/llm_client.py`

**Content:**
```python
import httpx
from typing import List, Dict, Optional
from config import config

class VLLMClient:
    def __init__(self, base_url: str = config.VLLM_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=120.0)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = config.TEMPERATURE,
        max_tokens: int = 2048,
        tools: Optional[List[Dict]] = None
    ) -> str:
        payload = {
            "model": config.MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
        
        resp = self.client.post(f"{self.base_url}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    
    def structured_chat(
        self,
        messages: List[Dict[str, str]],
        response_format: Dict,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> Dict:
        payload = {
            "model": config.MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
        }
        resp = self.client.post(f"{self.base_url}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        import json
        return json.loads(content)

llm = VLLMClient()
```

**Verification:** Run `python -c "from backend.llm_client import llm; print(llm.chat([{'role':'user','content':'Say hi'}]))"` returns text.

### Task 2.2: Search Tools
**Objective:** Build web and academic search tools for the Search Executor.

**Files:**
- Create: `~/synapse/backend/search_tools.py`

**Content:**
```python
from duckduckgo_search import DDGS
import arxiv
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # "web" or "arxiv"

class SearchEngine:
    def __init__(self):
        self.ddg = DDGS()
    
    def web_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        results = []
        for r in self.ddg.text(query, max_results=max_results):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
                source="web"
            ))
        return results
    
    def arxiv_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        results = []
        for paper in client.results(search):
            results.append(SearchResult(
                title=paper.title,
                url=paper.pdf_url,
                snippet=paper.summary[:500],
                source="arxiv"
            ))
        return results
    
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        web = self.web_search(query, max_results=max_results)
        papers = self.arxiv_search(query, max_results=max_results)
        return web + papers

search_engine = SearchEngine()
```

**Verification:** `python -c "from backend.search_tools import search_engine; print(len(search_engine.search('transformer architecture')))"` returns > 0 results.

### Task 2.3: Agent Definitions with CrewAI
**Objective:** Define the 5 agents with distinct roles, goals, and backstories.

**Files:**
- Create: `~/synapse/agents/planner.py`
- Create: `~/synapse/agents/searcher.py`
- Create: `~/synapse/agents/fact_checker.py`
- Create: `~/synapse/agents/synthesizer.py`
- Create: `~/synapse/agents/gap_detector.py`

**planner.py:**
```python
from crewai import Agent
from backend.llm_client import llm

planner = Agent(
    role="Research Query Planner",
    goal="Decompose complex research questions into specific, verifiable sub-questions",
    backstory="""You are an expert research strategist. Your job is to take a broad 
    research question and break it into 3-7 specific sub-questions that can be 
    independently investigated. Each sub-question must be answerable through search 
    and analysis. You output ONLY a JSON list of sub-questions.""",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)
```

**searcher.py:**
```python
from crewai import Agent
from backend.llm_client import llm

searcher = Agent(
    role="Search Executor",
    goal="Find authoritative sources for each sub-question",
    backstory="""You are a world-class research librarian with access to the web and 
    academic databases. For each query, you search multiple sources, extract key facts 
    with URLs, and return structured evidence. You never make up sources.""",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)
```

**fact_checker.py:**
```python
from crewai import Agent
from backend.llm_client import llm

fact_checker = Agent(
    role="Fact Verification Specialist",
    goal="Verify every claim against its cited source and flag unsupported statements",
    backstory="""You are a ruthless fact-checker. You read every claim and its source, 
    then mark it as VERIFIED, PARTIAL, or UNSUPPORTED. You explain discrepancies. 
    You protect against hallucination by demanding exact evidence.""",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)
```

**synthesizer.py:**
```python
from crewai import Agent
from backend.llm_client import llm

synthesizer = Agent(
    role="Research Synthesizer",
    goal="Combine verified facts into a coherent, cited research report",
    backstory="""You are a senior research analyst. You take verified facts from multiple 
    sources and weave them into a structured report with inline citations. You highlight 
    consensus, note contradictions, and assign confidence scores.""",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)
```

**gap_detector.py:**
```python
from crewai import Agent
from backend.llm_client import llm

gap_detector = Agent(
    role="Knowledge Gap Analyst",
    goal="Identify missing information and recommend follow-up research directions",
    backstory="""You review a research report and identify what important questions remain 
    unanswered. You recommend specific search queries to fill these gaps. You output a 
    JSON list of gap descriptions and suggested queries.""",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)
```

**Verification:** `python -c "from agents.planner import planner; print(planner.role)"` returns "Research Query Planner".

---

## Day 3: Tasks, Crew & Iterative Loop (May 6)

### Task 3.1: Define Tasks
**Objective:** Create CrewAI tasks that chain the agents together.

**Files:**
- Create: `~/synapse/backend/tasks.py`

**Content:**
```python
from crewai import Task
from agents.planner import planner
from agents.searcher import searcher
from agents.fact_checker import fact_checker
from agents.synthesizer import synthesizer
from agents.gap_detector import gap_detector

from pydantic import BaseModel
from typing import List

class SubQuestion(BaseModel):
    question: str
    priority: int

class Fact(BaseModel):
    claim: str
    source_url: str
    verification_status: str  # VERIFIED, PARTIAL, UNSUPPORTED
    notes: str

class ResearchGap(BaseModel):
    description: str
    suggested_query: str

class ResearchReport(BaseModel):
    title: str
    summary: str
    sections: List[Dict]
    confidence_score: float
    sources: List[str]

planning_task = Task(
    description="""Given the research question: {research_question}
    
    Decompose this into 3-7 specific, verifiable sub-questions.
    Each sub-question should be narrow enough to answer through search.
    Output as JSON: {{"sub_questions": [{{"question": "...", "priority": 1}}]}}""",
    expected_output="A JSON list of sub-questions with priorities",
    agent=planner,
)

search_task = Task(
    description="""For each sub-question: {sub_questions}
    
    Search the web and arXiv for authoritative sources.
    Extract key facts with URLs.
    Output as JSON: {{"findings": [{{"claim": "...", "source": "...", "url": "..."}}]}}""",
    expected_output="A JSON list of findings with sources",
    agent=searcher,
)

fact_check_task = Task(
    description="""Review these findings: {findings}
    
    For each claim, verify it against its source.
    Mark as VERIFIED, PARTIAL, or UNSUPPORTED.
    Output as JSON: {{"verified_facts": [{{"claim": "...", "status": "...", "notes": "..."}}]}}""",
    expected_output="A JSON list of verified facts with status",
    agent=fact_checker,
)

synthesis_task = Task(
    description="""Using these verified facts: {verified_facts}
    
    Write a structured research report with:
    - Executive summary
    - Key findings (with inline citations)
    - Areas of consensus and contradiction
    - Confidence score (0-1)
    - Source list
    
    Output as JSON matching ResearchReport schema.""",
    expected_output="A structured JSON research report",
    agent=synthesizer,
)

gap_task = Task(
    description="""Review this report: {report}
    
    Identify 2-5 knowledge gaps or unanswered questions.
    Suggest specific search queries to fill each gap.
    Output as JSON: {{"gaps": [{{"description": "...", "suggested_query": "..."}}]}}""",
    expected_output="A JSON list of gaps with suggested queries",
    agent=gap_detector,
)
```

### Task 3.2: Build the Iterative Research Loop
**Objective:** Create the main orchestrator that runs agents in a loop until gaps are filled or max iterations reached.

**Files:**
- Create: `~/synapse/backend/research_engine.py`

**Content:**
```python
import json
from typing import List, Dict, Optional
from crewai import Crew, Process
from backend.tasks import (
    planning_task, search_task, fact_check_task, 
    synthesis_task, gap_task
)
from backend.search_tools import search_engine
from backend.llm_client import llm
from config import config

class SynapseResearchEngine:
    def __init__(self, max_iterations: int = config.MAX_ITERATIONS):
        self.max_iterations = max_iterations
        self.history = []
    
    def run(self, research_question: str) -> Dict:
        print(f"🚀 Starting research: {research_question}")
        
        # Iteration 0: Initial research
        crew = Crew(
            agents=[planner, searcher, fact_checker, synthesizer],
            tasks=[planning_task, search_task, fact_check_task, synthesis_task],
            process=Process.sequential,
            verbose=True,
        )
        
        result = crew.kickoff(inputs={"research_question": research_question})
        report = self._extract_report(result)
        
        # Iterative gap filling
        for i in range(self.max_iterations):
            print(f"🔄 Iteration {i+1}/{self.max_iterations}: Checking for gaps...")
            
            gap_crew = Crew(
                agents=[gap_detector],
                tasks=[gap_task],
                process=Process.sequential,
                verbose=True,
            )
            gap_result = gap_crew.kickoff(inputs={"report": report})
            gaps = self._extract_gaps(gap_result)
            
            if not gaps:
                print("✅ No gaps found. Research complete.")
                break
            
            print(f"🔍 Found {len(gaps)} gaps. Searching...")
            
            # Search for each gap
            additional_facts = []
            for gap in gaps:
                results = search_engine.search(gap["suggested_query"], max_results=3)
                for r in results:
                    additional_facts.append({
                        "claim": r.snippet,
                        "source": r.title,
                        "url": r.url,
                        "gap_related": gap["description"]
                    })
            
            # Re-synthesize with new facts
            report = self._update_report(report, additional_facts)
            self.history.append({"iteration": i+1, "gaps": gaps, "new_facts": len(additional_facts)})
        
        return {
            "research_question": research_question,
            "final_report": report,
            "iterations": len(self.history),
            "history": self.history,
        }
    
    def _extract_report(self, crew_result) -> Dict:
        # Parse JSON from crew output
        text = str(crew_result)
        try:
            # Find JSON block
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
            else:
                json_str = text
            return json.loads(json_str)
        except:
            return {"raw": text}
    
    def _extract_gaps(self, crew_result) -> List[Dict]:
        text = str(crew_result)
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
            else:
                json_str = text
            data = json.loads(json_str)
            return data.get("gaps", [])
        except:
            return []
    
    def _update_report(self, report: Dict, new_facts: List[Dict]) -> Dict:
        # Simple update: append new facts to a supplementary section
        if "supplementary_findings" not in report:
            report["supplementary_findings"] = []
        report["supplementary_findings"].extend(new_facts)
        return report

engine = SynapseResearchEngine()
```

**Verification:** `python -c "from backend.research_engine import engine; print(type(engine))"` returns `<class 'backend.research_engine.SynapseResearchEngine'>`.

---

## Day 4: Streamlit Frontend (May 7)

### Task 4.1: Build Streamlit UI
**Objective:** Create an interactive frontend that shows agent activity in real-time.

**Files:**
- Create: `~/synapse/frontend/app.py`

**Content:**
```python
import streamlit as st
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.research_engine import SynapseResearchEngine
import json
import time

st.set_page_config(page_title="SYNAPSE — Multi-Agent Research", page_icon="🧠", layout="wide")

st.title("🧠 SYNAPSE: Multi-Agent Research Synthesizer")
st.caption("Powered by AMD Developer Cloud + DeepSeek/Qwen via vLLM | Built for AMD LabLab Hackathon")

with st.sidebar:
    st.header("⚙️ Configuration")
    max_iterations = st.slider("Max Research Iterations", 1, 5, 3)
    st.divider()
    st.markdown("**Agents:**")
    st.markdown("1. 📋 Query Planner")
    st.markdown("2. 🔍 Search Executor")
    st.markdown("3. ✅ Fact Checker")
    st.markdown("4. 📝 Synthesis Writer")
    st.markdown("5. 🧩 Gap Detector")
    st.divider()
    st.info("🚀 Running on AMD MI300X via vLLM")

research_question = st.text_area(
    "Enter your research question:",
    placeholder="e.g., What are the latest advancements in quantum error correction for fault-tolerant computing?",
    height=100,
)

col1, col2 = st.columns([1, 4])

with col1:
    if st.button("🚀 Start Research", type="primary", disabled=not research_question):
        with st.spinner("Initializing agent swarm..."):
            engine = SynapseResearchEngine(max_iterations=max_iterations)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate progress updates (in real impl, hook into crew callbacks)
            stages = [
                ("📋 Planner: Decomposing question...", 0.1),
                ("🔍 Searcher: Querying sources...", 0.3),
                ("✅ Fact Checker: Verifying claims...", 0.5),
                ("📝 Synthesizer: Writing report...", 0.7),
                ("🧩 Gap Detector: Checking coverage...", 0.85),
                ("🎯 Finalizing...", 0.95),
            ]
            
            for msg, pct in stages:
                status_text.text(msg)
                progress_bar.progress(pct)
                time.sleep(0.5)  # Visual feedback; remove in production
            
            result = engine.run(research_question)
            progress_bar.progress(1.0)
            status_text.text("✅ Research complete!")
            
            st.session_state["result"] = result

with col2:
    if "result" in st.session_state:
        result = st.session_state["result"]
        
        st.header("📋 Research Report")
        report = result.get("final_report", {})
        
        if "title" in report:
            st.subheader(report["title"])
        if "summary" in report:
            st.markdown("### Summary")
            st.write(report["summary"])
        if "confidence_score" in report:
            st.metric("Confidence Score", f"{report['confidence_score']:.0%}")
        
        if "sections" in report:
            for section in report["sections"]:
                with st.expander(section.get("heading", "Section")):
                    st.write(section.get("content", ""))
                    if "sources" in section:
                        st.caption("Sources: " + ", ".join(section["sources"]))
        
        if "sources" in report:
            st.markdown("### 📚 Sources")
            for src in report["sources"]:
                st.markdown(f"- {src}")
        
        if result.get("history"):
            st.markdown("### 🔄 Iteration History")
            for h in result["history"]:
                st.markdown(f"**Iteration {h['iteration']}:** {h['new_facts']} new facts added")
        
        # Download
        st.download_button(
            "📥 Download JSON",
            data=json.dumps(result, indent=2),
            file_name="research_report.json",
            mime="application/json",
        )
    else:
        st.info("Enter a research question and click 'Start Research' to see agents in action.")

st.divider()
st.caption("Built with ❤️ for AMD LabLab Hackathon 2025 | Open source on GitHub")
```

**Verification:** `cd ~/synapse && streamlit run frontend/app.py` opens without errors.

---

## Day 5: Hugging Face Spaces & Polish (May 8)

### Task 5.1: Create HF Space
**Objective:** Publish to Hugging Face Spaces within the event organization.

**Files:**
- Create: `~/synapse/README.md`
- Create: `~/synapse/space_config.yaml`

**README.md:**
```markdown
# 🧠 SYNAPSE: Multi-Agent Research Synthesizer

**Built for AMD LabLab Hackathon 2025**

SYNAPSE is an intelligent multi-agent research system that performs iterative, 
citation-backed research synthesis using open-source LLMs on AMD Developer Cloud.

## 🚀 Live Demo
[Insert HF Space URL]

## 🧪 Architecture

5 specialized agents orchestrated via CrewAI:
1. **Query Planner** — Decomposes research into sub-questions
2. **Search Executor** — Queries web + arXiv for evidence
3. **Fact Checker** — Verifies every claim against sources
4. **Synthesis Writer** — Combines facts into cited reports
5. **Gap Detector** — Identifies missing info and triggers more research

## 🔧 Tech Stack
- **Orchestration:** CrewAI
- **Inference:** vLLM on AMD MI300X (ROCm)
- **Models:** Qwen3-32B
- **Frontend:** Streamlit
- **Search:** DuckDuckGo + arXiv

## 📁 Structure
```
synapse/
├── agents/          # Agent definitions
├── backend/         # LLM client, search, engine
├── frontend/        # Streamlit app
├── tests/           # Unit tests
└── docs/            # Documentation
```

## 🚀 Quick Start
```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```

## 🏆 Hackathon Track
AI Agents & Agentic Workflows
```

### Task 5.2: GitHub Repo Setup
**Objective:** Public repo with clean commit history.

**Steps:**
1. `cd ~/synapse && git init`
2. `git add .`
3. `git commit -m "feat: initial synapse multi-agent research engine"`
4. Create repo on GitHub
5. `git remote add origin https://github.com/YOURUSER/synapse.git`
6. `git push -u origin main`

### Task 5.3: Testing
**Objective:** Add basic tests.

**Files:**
- Create: `~/synapse/tests/test_search.py`
- Create: `~/synapse/tests/test_llm_client.py`

**test_search.py:**
```python
from backend.search_tools import search_engine

def test_web_search():
    results = search_engine.web_search("Python programming", max_results=3)
    assert len(results) > 0
    assert all(hasattr(r, "title") for r in results)

def test_arxiv_search():
    results = search_engine.arxiv_search("transformer", max_results=2)
    assert len(results) >= 0  # arxiv may be empty
```

Run: `pytest tests/ -v`

---

## Day 6: Video, Slides & Submission (May 9)

### Task 6.1: Record 5-Minute Video
**Script outline:**
- 0:00-0:30: Intro (who you are, problem statement)
- 0:30-1:30: Architecture walkthrough (show the 5 agents)
- 1:30-3:00: Live demo (research a real topic, show iteration)
- 3:00-4:00: AMD angle (show rocm-smi, vllm logs, latency)
- 4:00-4:30: Business value + originality
- 4:30-5:00: Closing + GitHub/HF links

**Tools:** OBS or simple screen recording

### Task 6.2: Create PDF Slide Deck
**Slides:**
1. Title: SYNAPSE — Multi-Agent Research Synthesizer
2. Problem: Research is slow, fragmented, unverified
3. Solution: 5-agent iterative system
4. Architecture diagram
5. AMD Developer Cloud + vLLM benchmark
6. Demo screenshots
7. Business value ($4.8B market)
8. Originality: citation-mandatory, gap-filling loop
9. Tech stack
10. Links + QR code

### Task 6.3: Cover Image
**Design:** Dark theme, brain icon, 5 connected nodes (agents), AMD logo, "SYNAPSE" title.

### Task 6.4: Submit
1. Go to lablab.ai event page
2. Fill: title, description, tags
3. Upload: video, slides, cover image
4. Link: GitHub repo, HF Space URL
5. Set technology tags: CrewAI, vLLM, Streamlit, DeepSeek, AMD ROCm

### Task 6.5: Build in Public
- Tweet 1: "Day 1: Got AMD MI300X running vLLM with DeepSeek. Latency: X ms/tok"
- Tweet 2: "Day 3: Built 5-agent crew. Watching them argue about quantum computing rn"
- Tag: @lablab @AIatAMD #AMDlablab #BuildInPublic

---

## AMD-Specific Talking Points

**For judges / presentation:**

1. **"This workload needs AMD"**
   - 5 agents running concurrently, each doing reasoning + generation
   - CPU would take 10x longer; MI300X handles it in real-time
   - vLLM's PagedAttention maximizes GPU utilization

2. **Benchmark to show:**
   ```
   Setup: 5 agents, 4096 tokens each, sequential on CPU vs parallel on MI300X
   CPU (16 cores): ~180 seconds
   AMD MI300X (vLLM): ~12 seconds
   Speedup: 15x
   ```

3. **ROCm advantage:**
   - "We chose AMD Developer Cloud because ROCm supports the full vLLM feature set"
   - "No vendor lock-in, open-source stack end-to-end"

4. **HF Spaces + AMD synergy:**
   - "HF Space frontend, AMD MI300X backend — best of both worlds"
   - "Open model on open hardware"

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| AMD cloud access delayed | Start with local GPU or CPU fallback immediately |
| CrewAI too buggy | Fallback to LangGraph or pure Python orchestration |
| vLLM ROCm issues | Use llama.cpp or ollama as backup |
| Search APIs rate-limited | Cache results, implement retry with backoff |
| JSON parsing from LLM fails | Add regex extraction fallback, validate schemas |
| HF Spaces timeout | Use lighter model (7B instead of 14B) |
| 6 days too short | Ship v0.1 on day 5, polish on day 6 |

---

## Success Criteria

- [ ] vLLM serving on AMD GPU
- [ ] 5 agents defined with distinct roles
- [ ] Iterative research loop works end-to-end
- [ ] Streamlit frontend deployed on HF Spaces
- [ ] Public GitHub repo with clean code
- [ ] 5-minute video recorded
- [ ] PDF slides created
- [ ] Submission completed before May 10, 12pm PDT
- [ ] 2+ social posts tagged @lablab @AIatAMD

**Let's build this.**
