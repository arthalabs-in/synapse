# SYNAPSE — Project Charter
## Multi-Agent Research Synthesizer for AMD Developer Hackathon 2026

**Model Stack v1.1:** Qwen3.6-27B + vLLM + ROCm + AMD MI300X

---

## 1. PROJECT GOAL

Build and deploy SYNAPSE: a multi-agent research system that takes a research question, decomposes it into verifiable sub-questions, searches web and academic sources, verifies claims against their sources, synthesizes a structured report, detects missing evidence, loops back to search again, and delivers a citation-mandatory final report with a transparent confidence score.

SYNAPSE runs as a Streamlit Hugging Face Space frontend connected to a Qwen3.6-27B inference backend served through vLLM on AMD MI300X / ROCm.

**Winning Positioning:**
> "SYNAPSE is a self-auditing research agent that finds evidence gaps and searches again before giving you a final report."

**Updated Technical Positioning:**
> "SYNAPSE uses Qwen3.6-27B on AMD MI300X to run structured multi-agent research, claim verification, and evidence-gap repair with transparent confidence scoring."

---

## 2. OBJECTIVES

### Primary Objectives

| # | Objective | Measurable Target |
|---|-----------|-------------------|
| O1 | Build a working 5-agent CrewAI pipeline | All 5 agents execute sequentially with defined roles, goals, and backstories |
| O2 | Implement iterative gap-filling loop | System performs ≥1 additional search iteration when gaps are detected |
| O3 | Deploy Qwen3.6-27B on AMD MI300X via vLLM | OpenAI-compatible vLLM endpoint responds reliably |
| O4 | Deploy HF Space with Streamlit | Public HF Space under `lablab-ai-amd-developer-hackathon` org, live demo |
| O5 | Submit before May 10 12:00 PM PDT | GitHub repo, video, PDF slides, cover image, app URL all submitted |
| O11 | Use structured outputs | Every agent returns schema-valid JSON |
| O12 | Show model/infra credibility | README + video show Qwen3.6-27B, ROCm, vLLM, MI300X metrics |

### Secondary Objectives

| # | Objective | Measurable Target |
|---|-----------|-------------------|
| O6 | Win HF Special Prize (most likes) | ≥20 likes on HF Space |
| O7 | Build in Public extra challenge | 3 technical updates on X/Twitter tagging @lablab + @AIatAMD |
| O8 | Win Track 1 (AI Agents) prize | Top 3 placement |
| O9 | Show AMD benchmark | Tokens/sec and latency comparison vs CPU/sequential |
| O10 | Transparent confidence score | Formula-based 0-1 score with component breakdown |

---

## 3. SCOPE

### In-Scope (Must-Have)

- [ ] CrewAI agent definitions for all 5 agents with roles/goals/backstories
- [ ] Sequential task pipeline: Plan → Search → Verify → Synthesize → Gap-Detect
- [ ] Iterative loop: Gap detector triggers re-search (max 2 iterations for demo)
- [ ] Web search via DuckDuckGo (no API key)
- [ ] Academic search via arXiv API (no API key)
- [ ] Fact-checker marks: VERIFIED / PARTIAL / UNSUPPORTED
- [ ] Structured JSON outputs from all agents
- [ ] Synthesizer produces report with inline citations, confidence score
- [ ] Streamlit frontend with agent timeline visualization
- [ ] vLLM on AMD Developer Cloud (MI300X)
- [ ] Hugging Face Space deployment
- [ ] Public GitHub repo with clean README
- [ ] 5-minute MP4 demo video
- [ ] 8-slide PDF presentation
- [ ] 16:9 cover image
- [ ] Cached demo mode for reliability
- [ ] AMD performance benchmark panel

### Out-of-Scope (Nice-to-Have / Future)

- [ ] PDF/document upload
- [ ] User authentication
- [ ] Persistent history/database
- [ ] Multi-user sessions
- [ ] Export to PDF/Word/Notion
- [ ] Vector database (FAISS/Pinecone)
- [ ] More than 2 iteration loops
- [ ] Fine-tuning models
- [ ] Real-time collaborative editing
- [ ] Mobile-responsive UI (Streamlit default is fine)

## MODEL STACK v1.1

### Primary LLM

- Model: `Qwen/Qwen3.6-27B`
- Role: all reasoning-heavy agents
- Serving: vLLM OpenAI-compatible server
- Hardware: AMD MI300X via AMD Developer Cloud
- Mode: text-only MVP using `--language-model-only`
- Context target:
  - Live demo: 32K–64K
  - Stretch: 128K
  - Do not use 262K unless running 8×MI300X and benchmarked

### Why Qwen3.6-27B

Qwen3.6-27B is newer than the original Qwen3-32B plan, Apache-2.0 licensed, compatible with vLLM, and built for agentic coding and repository-level reasoning. For SYNAPSE, the important parts are structured reasoning, tool-call compatibility, long context, and stable open-weight deployment.

### Model Fallbacks

1. `Qwen/Qwen3.6-27B-FP8`
   - Use only if ROCm/vLLM serves it cleanly.
   - Best when BF16 is too slow or memory-heavy.

2. `Qwen/Qwen3.6-35B-A3B`
   - Sparse MoE fallback.
   - 35B total / 3B active.
   - Potentially faster, but test serving stability before depending on it.

3. `Qwen3-30B-A3B`
   - Legacy fallback from previous plan.
   - Keep only as emergency backup.

4. `Qwen3-14B`
   - Nuclear fallback if all 27B/35B deployment fails.

---

## 4. FUNCTIONAL REQUIREMENTS

### FR-001: Query Input
**As a** user, **I want** to type a research question, **so that** the system can investigate it.
- Input: free text, max 500 characters
- Example: "What are the practical tradeoffs between AMD MI300X and NVIDIA H100 for LLM inference?"

### FR-002: Agent Planning
**As a** system, **I want** to decompose the query into sub-questions, **so that** research is structured.
- Output: JSON array of 3-7 sub-questions with priority scores
- Each sub-question must be answerable via web/arxiv search

### FR-003: Web Search
**As a** Search Executor agent, **I want** to query DuckDuckGo, **so that** I find current web sources.
- Max 5 results per sub-question
- Fields: title, URL, snippet

### FR-004: Academic Search
**As a** Search Executor agent, **I want** to query arXiv, **so that** I find peer-reviewed sources.
- Max 5 results per sub-question
- Fields: title, PDF URL, abstract snippet

### FR-005: Evidence Extraction
**As a** system, **I want** to extract factual claims from search results, **so that** they can be verified.
- Output: JSON array of claims with source attribution

### FR-006: Fact Verification
**As a** Fact Checker agent, **I want** to label each claim, **so that** hallucinations are blocked.
- Labels: VERIFIED, PARTIAL, UNSUPPORTED
- Must include notes explaining the decision

### FR-007: Report Synthesis
**As a** Synthesizer agent, **I want** to combine verified facts into a report, **so that** the user gets structured output.
- Sections: title, summary, key findings (with inline citations), areas of consensus/contradiction
- Confidence score: 0.0 to 1.0

### FR-008: Gap Detection
**As a** Gap Detector agent, **I want** to identify missing information, **so that** the report can be improved.
- Output: JSON array of gaps with suggested search queries
- Max 5 gaps

### FR-009: Iterative Search
**As a** system, **I want** to re-search when gaps are found, **so that** coverage improves.
- Trigger: Gap detector returns ≥1 gap
- Action: Run Search Executor with suggested queries
- Limit: max 1 additional iteration for demo (configurable to 3)

### FR-010: Agent Timeline Visualization
**As a** user, **I want** to see which agent is running, **so that** I understand the process.
- Streamlit UI shows: Planner → Searcher → Fact Checker → Synthesizer → Gap Detector → (loop if needed)
- Each step shows status: running / complete / found gaps

### FR-011: Claim Audit Table
**As a** user, **I want** to see every claim with its verification status, **so that** I trust the output.
- Table columns: claim, source, status, notes
- Color coding: green (verified), yellow (partial), red (unsupported)

### FR-012: Confidence Score Display
**As a** user, **I want** to see a confidence score with breakdown, **so that** I understand report reliability.
- Formula: `0.40*verified_ratio + 0.20*source_quality + 0.20*agreement + 0.10*recency + 0.10*gap_resolution`
- Show components in expandable section

### FR-013: Before/After Comparison
**As a** user, **I want** to see how the report improved after gap-filling, **so that** I value the iteration.
- Show initial report confidence vs final report confidence
- Show what new facts were added

### FR-014: Sources List
**As a** user, **I want** to see all sources, **so that** I can verify independently.
- Deduplicated list of all URLs/titles used
- Grouped by verification status

### FR-015: Cached Demo Mode
**As a** system, **I want** to use pre-cached results if live search fails, **so that** the demo never breaks.
- Flag: `DEMO_MODE=true` in environment
- Uses JSON file with cached search results for golden query
- Label in UI: "Running in demo mode with cached results"

### FR-016: AMD Performance Panel
**As a** user, **I want** to see AMD GPU performance metrics, **so that** I understand the compute advantage.
- Metrics: tokens/sec, total inference time, per-agent latency, speedup vs CPU estimate
- Source: vLLM server logs or benchmark script

### FR-017: Report Export
**As a** user, **I want** to download the report as JSON, **so that** I can use it elsewhere.
- Download button for JSON export
- Content: full report object including all metadata

---

## 5. NON-FUNCTIONAL REQUIREMENTS

### NFR-001: Performance
- Cached golden demo: < 45 seconds
- Live web/arXiv demo: < 90 seconds
- Each small JSON agent call: < 10–20 seconds
- Synthesizer call: < 30 seconds
- Search queries: < 15 seconds combined
- Max live context per request: 32K–64K
- Max generated tokens per agent call capped by profile

### NFR-002: Reliability
- System must work in cached demo mode even if search APIs fail.
- All LLM agents must request schema-constrained JSON using vLLM structured outputs.
- Pydantic validates every agent response.
- If structured decoding fails, retry once with lower temperature.
- If retry fails, use parser repair.
- vLLM connection errors show a user-friendly message and activate cached demo mode.

### NFR-003: Scalability
- Single-user demo is sufficient (no multi-user required)
- No persistent database needed

### NFR-004: Security
- No user authentication
- No PII collection
- API keys stored in environment variables only

### NFR-005: Usability
- First-time user understands system in < 30 seconds
- Demo video shows complete flow in < 5 minutes
- UI is dark-themed (hackathon aesthetic)

### NFR-006: Maintainability
- Each agent is a separate module
- LLM client is centralized and swappable
- Configuration via environment variables

---

## 6. USER STORIES

### Persona 1: Hackathon Judge
> "I have 5 minutes to evaluate this project. I need to understand what it does, why it's original, and see it working immediately."

**Acceptance:** Video starts with problem, shows agent timeline, shows gap detection, shows final report with citations. Judge nods within 30 seconds.

### Persona 2: AMD Sponsor Representative
> "I want to see that this team actually used AMD Developer Cloud and ROCm, not just mentioned it."

**Acceptance:** UI shows benchmark panel with MI300X metrics. Video mentions vLLM + ROCm. Build-in-public posts show setup process.

### Persona 3: Consulting Analyst (Target User)
> "I need to write a research brief on AMD vs NVIDIA for LLM inference. I spend 4 hours on this normally."

**Acceptance:** Types query, gets structured report with citations in < 2 minutes. Confidence score tells them which claims are solid vs shaky.

### Persona 4: Build-in-Public Viewer
> "I'm scrolling Twitter. I see a technical update about AMD hackathon projects. Is this interesting enough to click?"

**Acceptance:** Tweet includes GIF of agent timeline + specific technical detail (e.g., "vLLM structured outputs on MI300X cut agent latency by 3x").

---

## 7. SUCCESS CRITERIA

### Product Success
- [ ] 5-agent pipeline runs end-to-end without errors
- [ ] Gap detector triggers at least 1 re-search in 80% of queries
- [ ] Fact checker correctly identifies at least 1 unsupported claim in test set
- [ ] Confidence score changes between initial and final report
- [ ] HF Space loads in < 10 seconds

### Hackathon Success
- [ ] Submission completed before deadline
- [ ] All mandatory deliverables present
- [ ] HF Space has ≥20 likes
- [ ] 3 build-in-public posts published
- [ ] Track 1 Top 3 placement

### Technical Success
- [ ] vLLM serving on AMD MI300X
- [ ] Structured JSON outputs from all agents
- [ ] Cached demo mode works offline
- [ ] AMD benchmark numbers collected

---

## 8. CONSTRAINTS

| # | Constraint | Impact |
|---|------------|--------|
| C1 | 6-day timeline (May 4-10) | Scope must be aggressively cut |
| C2 | CrewAI preferred, LangGraph fallback allowed | Track allows frameworks like CrewAI/LangChain/AutoGen; CrewAI remains primary for presentation clarity |
| C3 | Must use AMD Developer Cloud / ROCm | Infrastructure dependency; approval may take time |
| C4 | Must publish HF Space under event org | Requires HF account + org membership |
| C5 | Must be original and MIT-compliant | No plagiarism; existing code must be disclosed |
| C6 | Remote = pre-recorded video | No live pitching; video quality is critical |
| C7 | Solo builder (no team) | All work falls on one person |
| C8 | Age constraint (high school) | May affect eligibility for some prizes; check rules |

---

## 9. ASSUMPTIONS

| # | Assumption | Risk if False |
|---|------------|---------------|
| A1 | AMD Developer Cloud access granted within 24h | Build is blocked; fallback to local GPU or CPU |
| A2 | vLLM ROCm image supports Qwen3.6-27B cleanly | Build/install newer vLLM or use fallback model |
| A3 | Qwen3.6-27B BF16 fits on 1×MI300X at 32K–64K context | Reduce context, use FP8 variant, or use smaller fallback |
| A4 | `--language-model-only` works for text-only MVP | If false, lower context and memory utilization |
| A5 | DuckDuckGo search remains unblocked | Fallback to cached demo mode |
| A6 | CrewAI works with custom LLM client | May need LangGraph fallback |
| A7 | HF Space supports Streamlit natively | May need Gradio or Docker fallback |
| A8 | 14B model fits on MI300X vRAM | May need 7B model or quantization |

---

## 10. DELIVERABLES

### Code Deliverables
- [ ] Public GitHub repo (`synapse-amd-hackathon`)
- [ ] HF Space (`lablab-ai-amd-developer-hackathon/synapse`)
- [ ] README with architecture diagram
- [ ] requirements.txt with pinned versions
- [ ] .env.example for configuration

### Demo Deliverables
- [ ] Live HF Space URL
- [ ] 5-minute MP4 video (intro → architecture → demo → AMD → business)
- [ ] 8-slide PDF presentation
- [ ] 16:9 PNG cover image

### Documentation Deliverables
- [ ] PROJECT_CHARTER.md (this document)
- [ ] IMPLEMENTATION_PLAN.md (day-by-day tasks)
- [ ] Build-in-public thread (3 posts)

---

## 11. ARCHITECTURE

### High-Level Flow

```
User Query
    ↓
Planner Agent
    - Qwen3.6-27B
    - non-thinking
    - JSON schema output
    ↓
Search Executor
    - DuckDuckGo + arXiv
    - concurrent searches per sub-question
    ↓
Evidence Extractor
    - Qwen3.6-27B
    - non-thinking
    - claim/source JSON
    ↓
Fact Checker
    - Qwen3.6-27B
    - thinking enabled
    - VERIFIED / PARTIAL / UNSUPPORTED
    ↓
Synthesizer
    - Qwen3.6-27B
    - report JSON
    - citations + confidence score
    ↓
Gap Detector
    - Qwen3.6-27B
    - thinking enabled
    - missing evidence + follow-up queries
    ↓
Conditional Loop
    - if high/medium severity gaps exist:
        run one additional search + verification pass
    ↓
Final Output
    - cited report
    - claim audit table
    - gap summary
    - confidence breakdown
    - AMD performance metrics
```

### Component Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Streamlit   │ ←→ │   CrewAI      │ ←→ │   vLLM on    │
│   Frontend    │     │   Orchestrator│     │   AMD MI300X │
└─────────────┘     └─────────────┘     └─────────────┘
                                │
                    ┌─────────────┐
                    │   Search Tools    │
                    │   (DuckDuckGo     │
                    │    + arXiv)       │
                    └─────────────┘
```

### Agent Definitions (CrewAI)

**Agent 1: Query Planner**
- Role: Research Query Planner
- Goal: Decompose complex research questions into specific, verifiable sub-questions
- Backstory: Expert research strategist who breaks broad questions into 3-7 searchable sub-questions
- Tools: None (pure reasoning)
- Expected Output: JSON with `sub_questions` array

**Agent 2: Search Executor**
- Role: Search Executor
- Goal: Find authoritative sources for each sub-question
- Backstory: World-class research librarian with access to web and academic databases
- Tools: DuckDuckGo search, arXiv search
- Expected Output: JSON with `findings` array

**Agent 3: Fact Checker**
- Role: Fact Verification Specialist
- Goal: Verify every claim against its cited source
- Backstory: Ruthless fact-checker who protects against hallucination
- Tools: None (pure reasoning over provided context)
- Expected Output: JSON with `verified_facts` array

**Agent 4: Synthesizer**
- Role: Research Synthesizer
- Goal: Combine verified facts into a coherent, cited research report
- Backstory: Senior research analyst who weaves facts into structured reports
- Tools: None (pure reasoning)
- Expected Output: JSON report with title, summary, sections, confidence_score

**Agent 5: Gap Detector**
- Role: Knowledge Gap Analyst
- Goal: Identify missing information and recommend follow-up research
- Backstory: Critical reviewer who finds what's unanswered
- Tools: None (pure reasoning)
- Expected Output: JSON with `gaps` array

---

## 12. DATA MODELS

### SubQuestion
```json
{
  "question": "string",
  "priority": 1
}
```

### Finding
```json
{
  "claim": "string",
  "source_title": "string",
  "source_url": "string"
}
```

### VerifiedFact
```json
{
  "claim": "string",
  "source_title": "string",
  "source_url": "string",
  "status": "VERIFIED | PARTIAL | UNSUPPORTED",
  "notes": "string"
}
```

### ResearchGap
```json
{
  "description": "string",
  "suggested_query": "string"
}
```

### ResearchReport
```json
{
  "title": "string",
  "summary": "string",
  "sections": [
    {
      "heading": "string",
      "content": "string",
      "sources": ["string"]
    }
  ],
  "confidence_score": 0.85,
  "confidence_breakdown": {
    "verified_ratio": 0.40,
    "source_quality": 0.20,
    "agreement": 0.20,
    "recency": 0.10,
    "gap_resolution": 0.10
  },
  "sources": ["string"],
  "iterations": 2,
  "initial_confidence": 0.65,
  "final_confidence": 0.85,
  "model": "Qwen/Qwen3.6-27B",
  "serving_backend": "vLLM on AMD MI300X",
  "context_window_used": 65536,
  "thinking_profiles": {
    "planner": false,
    "fact_checker": true,
    "gap_detector": true
  }
}
```

---

## 13. UI/UX REQUIREMENTS

### Layout
- Dark theme (Streamlit `base="dark"`)
- Wide layout
- Left sidebar: config + agent list
- Main area: query input → progress → report

### States
1. **Idle:** Query input + "Start Research" button
2. **Running:** Progress bar + agent timeline + status messages
3. **Complete:** Report view + claim audit table + gap card + export button

### Components
- **Agent Timeline:** Horizontal or vertical timeline showing 5 agent steps
- **Claim Audit Table:** Sortable table with color-coded status
- **Gap Detector Card:** Shows gaps found + queries used to fill them
- **Confidence Meter:** Visual bar (0-100%) with expandable breakdown
- **Before/After:** Side-by-side or stacked comparison of report versions
- **AMD Benchmark Card:** Small panel with tokens/sec and latency
- **Export Button:** Downloads full report JSON

---

## 14. AMD REQUIREMENTS

### Must Show
- [ ] Model served via vLLM on AMD MI300X
- [ ] ROCm mentioned in README and video
- [ ] Benchmark numbers vs CPU or sequential API calls
- [ ] Screenshot of `rocm-smi` or GPU utilization in video

### Nice to Show
- [ ] PagedAttention explanation in slides
- [ ] Batch processing of agent calls
- [ ] Comparison with NVIDIA equivalent (diplomatic)

---

## 15. RISK REGISTER

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R1 | AMD cloud access delayed | Medium | Critical | Start local GPU/CPU immediately; pivot to Ollama if needed |
| R2 | CrewAI JSON parsing fails | High | High | Implement regex fallback for all agents; validate schemas |
| R3 | vLLM ROCm image lacks Qwen3.6 support | Medium | Critical | Check `vllm --version`; use latest ROCm image/wheel; fallback to Qwen3-30B-A3B |
| R11 | 262K context causes OOM or bad latency | High | High | Use 32K–64K for demo; 128K only after benchmark |
| R12 | Vision encoder wastes memory | Medium | High | Serve with `--language-model-only` |
| R13 | Structured JSON decoding fails | Medium | High | vLLM structured outputs + Pydantic + retry + repair |
| R14 | Tool calling parser mismatch | Medium | Medium | Keep tools external in Python; use model for decisions, not actual browser control |
| R4 | Search APIs rate-limited | Medium | High | Cached demo mode with golden query; fallback JSON |
| R5 | 6 days insufficient | Medium | Critical | Ruthless scope cutting; ship v0.1 by day 5 |
| R6 | HF Spaces timeout/limitations | Low | Medium | Test early; use lighter model; Gradio fallback |
| R7 | Another team builds same thing | Low | Medium | Gap detection is unique moat; emphasize in all materials |
| R8 | Video quality poor | Medium | Medium | Script outline now; record early; allow time for re-recording |
| R9 | JSON schema drift between agents | High | High | Centralized Pydantic models; strict validation |
| R10 | Model hallucinates fake citations | High | Critical | Fact checker must validate URLs exist; unsupported = blocked |

---

## 16. TESTING STRATEGY

### Unit Tests
- [ ] `test_planner.py`: Planner returns valid JSON with 3-7 sub-questions
- [ ] `test_searcher.py`: Searcher returns findings with URLs
- [ ] `test_fact_checker.py`: Fact checker correctly labels claims
- [ ] `test_synthesizer.py`: Synthesizer returns report with confidence score
- [ ] `test_gap_detector.py`: Gap detector returns gaps when report is thin
- [ ] `test_research_engine.py`: Full pipeline runs end-to-end

### Integration Tests
- [ ] `test_amd_connection.py`: vLLM endpoint responds
- [ ] `test_hf_space.py`: Space loads without errors
- [ ] `test_cached_mode.py`: Demo mode works without internet

### Acceptance Tests
- [ ] Golden query completes in < 60 seconds
- [ ] Gap detector triggers on thin query
- [ ] Confidence score increases after iteration
- [ ] All citations have valid URLs
- [ ] UI renders correctly on mobile (basic)

---

## 17. BUILD-IN-PUBLIC PLAN

### Post 1 (Day 2): AMD Setup
- Topic: "Got vLLM running on AMD MI300X for the first time"
- Content: Screenshot of rocm-smi, tokens/sec metric, one pain point
- Tags: @lablab @AIatAMD #AMDlablab #BuildInPublic

### Post 2 (Day 4): Multi-Agent Loop
- Topic: "5 agents, 1 research question, 0 hallucinations"
- Content: GIF of agent timeline, fact checker catching unsupported claim
- Tags: @lablab @AIatAMD #CrewAI #vLLM

### Post 3 (Day 6): Gap Detection
- Topic: "The thing Perplexity can't do: find what it missed"
- Content: Before/after report comparison, confidence improvement
- Tags: @lablab @AIatAMD #AIAgents #Hackathon

---

## 18. DECISION LOG

| # | Decision | Rationale |
|------|----------|-----------|
| Apr 29 | Use Qwen3.6-27B as primary model | Newer Qwen3.6 open-weight dense model; compatible with vLLM; strong agentic/coding/reasoning profile |
| Apr 29 | Serve text-only with `--language-model-only` | SYNAPSE MVP is text research; skipping vision frees memory for KV cache |
| Apr 29 | Use 32K–64K context for live demo | Better latency/reliability than chasing 262K context |
| Apr 29 | Keep Qwen3.6-35B-A3B as fallback | MoE model has 35B total / 3B active; potentially efficient if serving is stable |
| Apr 29 | Use vLLM structured outputs before parser fallback | Reduces JSON schema drift between agents |
| Apr 29 | CrewAI preferred, not mandatory | Track allows frameworks like CrewAI/LangChain/AutoGen; fallback allowed |
| Apr 29 | Keep cached demo mode mandatory | Search/model infra can fail; demo must never die |

---

## 19. GLOSSARY

| Term | Definition |
|------|------------|
| **CrewAI** | Multi-agent orchestration framework with roles, goals, and tasks |
| **vLLM** | High-throughput LLM inference engine with PagedAttention |
| **ROCm** | AMD's open-source GPU computing platform (CUDA equivalent) |
| **MI300X** | AMD Instinct data center GPU used for AI/ML workloads |
| **HF Space** | Hugging Face hosting for ML demo apps (Streamlit/Gradio/Docker) |
| **Gap Detection** | Identifying missing information in a research report and triggering more search |
| **Confidence Score** | Transparent 0-1 metric indicating report reliability |
| **Cached Demo Mode** | Using pre-stored results instead of live search for reliability |

---

*Document Version: 1.0*  
*Author: SYNAPSE Team*  
*Date: May 4, 2026*  
*Status: Approved for Build*
