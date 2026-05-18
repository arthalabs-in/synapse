# SYNAPSE Competitive Intelligence Prompt
## Copy-paste this ENTIRE block into ChatGPT / Claude / DeepSeek

---

## SYSTEM CONTEXT

You are an elite hackathon strategist and product analyst. You have been hired to conduct a comprehensive competitive intelligence review for a team building "SYNAPSE" — a Multi-Agent Research Synthesizer — for the AMD Developer Hackathon on LabLab.ai.

Your job is to perform a 5-part analysis (A through E) using ONLY the data provided below. Do not hallucinate. If data is missing, state it explicitly.

---

## PART 0: HACKATHON META-DATA (USE THIS FOR ALL JUDGMENTS)

**Event:** AMD Developer Hackathon by LabLab.ai  
**URL:** https://lablab.ai/ai-hackathons/amd-developer  
**Dates:** May 4 – May 10, 2026 (6 days, currently Day 1)  
**Deadline:** May 10, 2026 12:00 PM PDT  
**Total Participants:** 7,063+ and growing  
**Total Teams:** ~210+ registered  
**Prize Pool:** $21,500+  
**HF Special Prize:** Reachy Mini robot + 6mo HF Pro + $500 credits (most likes on HF Space)  
**On-site:** May 9-10 at MindsDB SF (invite only)  

**Tracks:**
- Track 1: AI Agents & Agentic Workflows (Beginner-friendly) — OUR TRACK
- Track 2: Fine-Tuning on AMD GPUs (Advanced)
- Track 3: Vision & Multimodal AI

**Judging Criteria (equally weighted, 4 factors):**
1. **Application of Technology** — "How effectively the chosen model(s) are integrated into the solution"
2. **Presentation** — "The clarity and effectiveness of the project presentation"
3. **Business Value** — "The impact and practical value, considering how well it fits into business areas"
4. **Originality** — "The uniqueness & creativity of the solution, highlighting approaches and ability to demonstrate behaviors"

**Submission Requirements (ALL mandatory):**
- Public GitHub repo
- Demo app on Streamlit/Replit/Vercel
- Application URL
- 5-minute MP4 video
- PDF slide deck
- Cover image (16:9)
- Project title + short description (255 chars) + long description (100+ words)
- MUST publish as Hugging Face Space within the event's HF organization

**AMD Requirements:**
- Must use AMD Developer Cloud / ROCm
- $100 credits provided
- Access to MI300X GPUs
- Must sign up for AMD AI Developer Program

**Build in Public Extra Challenge:**
- Share 2+ technical updates on social (tag @lablab + @AIatAMD)
- Separate prize pool

---

## PART 1: OUR PRODUCT — SYNAPSE

**Name:** SYNAPSE — Multi-Agent Research Synthesizer  
**Track:** Track 1 (AI Agents & Agentic Workflows)  
**Tech Stack:** Python, vLLM, CrewAI-inspired orchestration, Streamlit, DuckDuckGo Search, arXiv API  
**Model:** Qwen3-32B via vLLM on AMD MI300X  
**Deployment:** Hugging Face Space (Streamlit) + public GitHub repo  

**Architecture (5 Agents):**
1. **Query Planner** — Decomposes a broad research question into 3-7 specific, verifiable sub-questions (JSON output)
2. **Search Executor** — Queries DuckDuckGo (web) + arXiv (academic) for each sub-question; extracts findings with URLs
3. **Fact Checker** — Reviews every claim against its source; marks VERIFIED / PARTIAL / UNSUPPORTED with notes
4. **Synthesizer** — Combines verified facts into a structured research report with inline citations, confidence score (0-1), consensus/contradiction highlights
5. **Gap Detector** — Identifies unanswered questions and missing information; outputs suggested search queries to fill gaps

**Iterative Loop:**
- Initial pass runs Planner → Searcher → Fact Checker → Synthesizer
- Gap Detector reviews the report
- If gaps found, system loops back to Searcher with new queries (max 3 iterations)
- Each iteration appends new facts and updates the report

**Key Differentiators:**
- **Only hackathon project with iterative gap-filling** — no other team mentions this
- **Citation-mandatory output** — every claim must have provenance; hallucinations are blocked
- **Academic + web hybrid search** — arXiv credibility + web breadth
- **Confidence scores** — quantified trust metric per report
- **Real-time agent visualization** — Streamlit UI shows each agent lighting up as it works
- **Clear AMD angle** — 5 agents running concurrently on MI300X via vLLM; benchmarkable speedup vs CPU

**Target Users:** Researchers, consultants, analysts, journalists, students, legal professionals  
**Market Size:** $4.8B document AI market, 35% YoY growth  
**ROI Pitch:** "Reduce document/research review from 4 hours to 4 minutes"

**Demo Moment:**
User types: "What are the latest advancements in quantum error correction for fault-tolerant computing?"
→ Watch 5 agents coordinate in real-time
→ Get structured report with inline citations
→ Gap Detector says: "Missing: recent experimental results from IBM/Google"
→ Agents search again
→ Updated report with confidence score

**Business Value Props:**
- Consultants: $200/hour for research → automated in 30 seconds
- Journalists: verify claims before publishing
- Students: literature review gap detection
- Legal: case law research with source verification

---

## PART 2: COMPLETE TEAM DATASET (ALL ~210 TEAMS)

Below is the COMPLETE list of all teams registered for this hackathon as of Day 1, extracted from the official LabLab.ai team registry. No submissions exist yet (all show "Team Leader hasn't made a submission yet").

### DIRECT COMPETITORS (Research / Synthesis / Document Intelligence / Multi-Agent)

| Team | Members | Project Description |
|------|---------|---------------------|
| **Quantext** | 6 (Surbhi Sharma, Juan Manuel López, Agustín Marquez, Alejandro Alvarez, Carlos Juarez, Angel Hernández) | "Adaptive AI system that selects models and agents by task complexity, optimizing GPU memory via KV-cache quantization" |
| **TaskFlow Intelligence** | 1 (Harshdeep Singh, AI Full Stack Developer) | "Execution-first AI agents that complete real tasks end-to-end using multi-agent orchestration on AMD compute" |
| **Mindhunt** | ? | "Efficiently complete research gaps and then develop a product" |
| **DoZuMind AI** | 6 (Sinalo Ntlanganiso, Nitesh Gupta, Solomon Pak, mohamed1408, Meheraz Alif, Abd ul Hussain) | "AI documentation gen with fine-tuned LLMs on MI300X. Multimodal + agentic workflows" |
| **Fortress AI** | 1 (Marwane Oraiche, FullStack Dev) | "Private RAG platform to chat with sensitive documents locally. Secure, fast, 100% private AI for enterprises" |
| **AlertNet AI** | 1 (Unknown Hacker alok2singh) | "Multi-agent systems that detect critical clinical risks from unstructured patient data in real time" |
| **Legal Legend / Clade** | 1 | "Intelligent, agent-based AI systems for real-world problem solving. Specialized in legal" |
| **Open Intelligence Agency** | 1 (Unknown Hacker rascimat) | "Building an AI powered Open-source intelligence (OSINT) tool" |
| **AgenticInbox** | ? | "Agentic workflow for personal knowledge management. Using RAG and HF models to turn scattered data into actionable insights" |

### ADJACENT COMPETITORS (RAG / Chat-with-Docs / Knowledge / Agents)

| Team | Members | Description |
|------|---------|-------------|
| **AetherCore** | 2 (Daksh Patil, Unknown) | "Multi-agent AI system that analyses code based on user-defined problems, providing targeted solutions" |
| **GhostMode AI Systems** | 1 (Muhammad Mubashar pasha_dev_) | "AI agent system with tool-calling, memory & evaluation using React, FastAPI & open-source LLMs" |
| **Nera** | 1 (Unknown itzangel) | "Building agentic AI workflows and enterprise automation systems optimized for AMD Instinct accelerators" |
| **AgentForge1** | 1 (Vignesh Das) | "AI agent workflow using n8n and AMD Developer Cloud. Full-stack app with Next.js frontend" |
| **Zerith** | ? | "Creating an AI system to turn PDFs into clear summaries and quizzes" |
| **Friction AI** | ? | "The friction between agents generates the optimized result" |
| **HyperSonic** | ? | "Agentic AI-based coding tool" |
| **JoDevs** | 1 (Jawad Alarman) | "Agentic DevOps copilot for AI backends on AMD Developer Cloud" |
| **NeuralForge VM** | ? | "Building cutting-edge AI agents on AMD hardware" |
| **Team Neurals** | ? | "Team of 3 developing agents" |
| **AI_Swarm** | ? | "Designing multi-agent workflows with tool use, memory, and reasoning" |
| **Agent Instinct** | 1 (Unknown yaseeniqbal) | "Multi-agent AI system optimizing warehouse logistics in real time using AMD GPUs, visualized through Unity digital twin" |
| **AhiaIntel** | ? | "Self-healing AI agents to streamline complex business workflows" |
| **Not the best but still good** | ? | "Building the next generation of Autonomous Agent Swarms" |
| **CloserAI Labs** | 1 (charleskojomark13) | "7-agent AI sales team that finds leads, writes personalized outreach, handles objections, and books meetings" |
| **Arrzinee** | ? | "Three AI agents argue any question from opposing sides. A Judge weighs the debate" |
| **Multi_agent_proj3ct_team** | ? | "Create a multi agent team which would work similar to ordinary team of developers, QA, etc" |
| **AgentX Labs** | ? | "We build high-performance AI agents that think, act, and scale" |
| **NeuralNomads** | ? | "Building AI agents on AMD ROCm" |
| **Snayu AI** | ? | "Building context-aware, reasoning-first agentic system" |
| **Agentic Architects** | ? | "Team of ai engineers" |
| **API Shield AI Security** | ? | "Defensive AI model to detect and mitigate API security vulnerabilities" |
| **Agentbuy Bridge** | ? | "Users pay $0.005 USD to unlock direct Chinese supplier details" |
| **Order X AI** | ? | "AI desktop agent that sees, understands, and executes tasks in real time" |
| **Pragnastra** | ? | "Builds AI agent systems and high-performance applications using AMD GPUs" |
| **Spacewanderers** | ? | "Backend engineer looking to build multi agent system to automate user pain points" |
| **Aware** | ? | "Track 1: agentic system. Have AI engineer + Backend dev. Looking for member" |
| **The Intelligencia** | ? | "Core architectures. Deep algorithms. We build systems that hold under pressure" |
| **MAGA (Make AI Great Again)** | ? | "Focused on improving AI efficiency and reducing resource consumption" |
| **AgentStack** | ? | "Building high-performance AI systems powered by AMD GPUs" |
| **OrchestrAI** | ? | "We orchestrate intelligent agents to work together seamlessly" |
| **CyberX-AI** | ? | "Libyan Cybersecurity AI research team" |
| **HACKNOIR DEFENDER** | ? | "Cybersecurity-driven team leveraging AI for smart, scalable, secure solutions" |
| **YaiMakMak** | ? | "Building agentic AI systems for cybersecurity automation on AMD ROCm" |

### GENERIC / VAGUE / NO DIRECTION

The remaining ~150 teams have descriptions like:
- "We don't brainstorm. We deploy." (flux)
- "Everything is new, everything is challenging" (vikram)
- "Build to last. With the credits attained." (CratosAi)
- "We win ts easy." (Goats)
- "Gonna steal your jobs with 0 skills. 😉" (Octopus Crime)
- "No idea on what to build yet" (The Idea)
- "Just too cool to win" (2cool)
- "Joining because of a classroom assignment" (UznirK)

### NON-COMPETING (DIFFERENT VERTICALS)

| Category | Example Teams |
|----------|--------------|
| Sales/Marketing | CloserAI Labs, CashCat, Finguard, Arrzinee |
| Healthcare/Medical | AlertNet AI, DocIA, VitalSync |
| Cybersecurity | HACKNOIR DEFENDER, YaiMakMak, API Shield, Heindall |
| Coding/DevTools | HyperSonic, AetherCore, JoDevs, merolav technologies |
| Vision/Multimodal | FlyingCat, Team Believer, BlueMinds, Apex |
| Gaming | Himalayan Stealth |
| Finance/Trading | gh0ststudio, Ostrich 0, CashCat |
| Agriculture | AgriSync, Kekera Labs, FarmerAI |
| Hardware/Verilog | Tarang, Silicon Agents |
| Edge/On-device | Evolving Edge |

---

## PART 3: HUGGING FACE SPACES SUBMISSIONS (REAL-TIME DATA)

As of Day 1, only **2 Spaces** exist in the hackathon's HF organization:

| Space | Team | Description | Likes |
|-------|------|-------------|-------|
| **Plant Disease Assistant** | merolav | DINOv2-L on MI300X, diagnoses 22 crop diseases from leaf images | 1 |
| **SentinelBrain-14B MoE Dashboard** | qubitpage | 14.8B Mixture-of-Experts training dashboard | 0 |

**HF Special Prize:** Awarded to the Space with the most likes. Currently winnable with ~20+ likes.

---

## PART 4: WINNING PATTERNS FROM PAST LABLAB HACKATHONS

Analyzed winner from "Agentic Economy on Arc" (ended Apr 26, 2026):

**Winner: Cairn — Nanopayment Environmental Oracle**

**What they submitted:**
- Title: "Cairn — Nanopayment Environmental Oracle"
- Description: 300+ words explaining problem (sensor data paywalled), solution (per-query nanopayments), market (insurance, climate risk, research), and why it needs sponsor tech (Arc sub-cent transactions)
- Badges: Medal + Application Badge
- Category Tags: "Per-API Monetization Engine", "Agent-to-Agent Payment Loop"
- Tech Stack: Anthropic Claude, Arc, Circle, Claude Code, Codex, Featherless, GPT-5, x402
- Links: GitHub repo, PDF presentation, live demo URL (Vercel)
- Video: Embedded demo video
- Team: 1 person (solo)

**Winning Formula Observed:**
1. Clear problem → solution → market narrative
2. Specific vertical + agentic twist (not generic "AI agents")
3. Live demo URL that works
4. PDF presentation (not just slides)
5. 2-5 minute video: problem → demo → tech
6. Public GitHub with clean README
7. Heavy use of sponsor tech prominently displayed
8. Solo or small teams can and do win

---

## PART 5: COMPETITIVE COMPARISON MATRIX

Use this to compare SYNAPSE against top threats:

| Dimension | SYNAPSE (Us) | Quantext | TaskFlow | DoZuMind | CloserAI |
|-----------|-------------|----------|----------|----------|----------|
| **Domain** | Research synthesis | Model/agent routing | Generic task execution | Documentation gen | Sales pipeline |
| **Agents** | 5 (distinct roles) | Adaptive (unknown count) | Multi-agent (vague) | Multimodal + agentic | 7 (sales-specific) |
| **Iteration** | ✅ Gap-filling loop | ❌ None mentioned | ❌ None mentioned | ❌ None mentioned | ❌ None mentioned |
| **Citations** | ✅ Mandatory, verified | ❌ None | ❌ None | ❌ None | ❌ None |
| **Academic Search** | ✅ Web + arXiv | ❌ None | ❌ None | ❌ None | ❌ None |
| **Confidence Score** | ✅ 0-1 per report | ❌ None | ❌ None | ❌ None | ❌ None |
| **User-Facing** | ✅ Streamlit demo | ❌ Infrastructure only | ❓ Unknown | ✅ Likely | ✅ Yes |
| **Business Value** | High (universal pain) | Low (engineers only) | Medium (generic) | Medium (docs niche) | High (sales is $$$) |
| **AMD Angle** | Strong (5 agents on GPU) | Strong (GPU optimization) | Medium (orchestration) | Strong (fine-tuned on MI300X) | Weak (mostly API calls) |
| **Demo Clarity** | High (type → watch → read) | Low (infra is invisible) | Medium (generic tasks) | Medium (doc gen) | High (sales pipeline) |
| **Originality** | Very High (gap loop + citations) | Medium (model routing exists) | Low (generic agents) | Medium (doc gen is common) | Medium (sales agents exist) |
| **Team Size** | 1 (solo) | 6 | 1 | 6 | 1 |
| **HF Space** | Planned | Unknown | Unknown | Unknown | Unknown |

---

## 📋 YOUR TASK: PERFORM ANALYSIS A THROUGH E

Use ONLY the data provided above. Do not hallucinate teams, submissions, or capabilities that are not listed. If information is missing, explicitly state "Insufficient data."

### A. ANALYZE ALL SUBMISSIONS

1. List every team that has made an actual submission (GitHub repo, HF Space, or demo URL). Based on our data, as of Day 1, how many teams have submitted?
2. For the 2 HF Spaces that exist, analyze their technical depth, demo quality, and threat level to SYNAPSE.
3. Categorize all ~210 teams into: (a) Serious Threats, (b) Moderate Threats, (c) Noise, (d) Different Vertical.
4. What percentage of teams are solo vs. multi-person? What does this imply for execution speed?

### B. FIND THE BEST PRODUCT DESCRIPTION

1. Rank the top 10 product descriptions by quality using these criteria:
   - Clarity (can you understand it in 10 seconds?)
   - Specificity (not "AI agents" but "AI agents for X")
   - Technical depth (mentions concrete tools/architecture)
   - Business value (clear market/pain point)
   - Demo-ability (can you imagine a 5-minute video?)

2. Identify the SINGLE best product description and explain why it wins on the judging criteria.

3. Compare each top description against SYNAPSE's description. What do they do better? What do they lack?

### C. COMPARE BEST PRODUCT WITH SYNAPSE

1. Take the #1 best product from Part B and do a head-to-head comparison with SYNAPSE across all 4 judging criteria.
2. For each criterion, score both products 1-10 and explain the gap.
3. Identify 3 specific weaknesses in SYNAPSE relative to the best competitor, and propose fixes.
4. Identify 3 specific strengths where SYNAPSE dominates, and propose how to emphasize them in the pitch.

### D. COMPARE ALL JUDGMENT CRITERIA WITH SYNAPSE

For EACH of the 4 judging criteria, provide a detailed analysis:

**1. Application of Technology**
- What technology is SYNAPSE using? (vLLM, CrewAI-inspired pipeline, AMD MI300X, etc.)
- How effectively is it integrated? (Each agent has a distinct role, iterative loop, fallback handling)
- What could improve this score? (Better error handling? More agents? Structured output validation?)
- Score 1-10 with justification.

**2. Presentation**
- How clear is SYNAPSE's story? (Problem → 5 agents → cited report → gap detection)
- How effective would the 5-minute video be? (Walk through each agent's output)
- What risks exist? (JSON parsing failures? Search API rate limits?)
- Score 1-10 with justification.

**3. Business Value**
- What is the market size? ($4.8B document AI, $200/hour consultant research)
- Who are the users? (Researchers, consultants, journalists, students, legal)
- What is the ROI? (4 hours → 4 minutes)
- How does it compare to other teams' business value?
- Score 1-10 with justification.

**4. Originality**
- What is genuinely unique? (Iterative gap-filling loop, citation-mandatory gate, confidence scores)
- What exists in the market already? (Perplexity, Elicit, Consensus — but none have iterative gaps + mandatory citations)
- How original is this compared to other hackathon projects?
- Score 1-10 with justification.

### E. EVALUATE WINNING CHANCE

1. **Probability Assessment:** Based on the competitive landscape, assign a probability (%) that SYNAPSE wins:
   - Grand Prize ($5,000)
   - Track 1 First Place ($2,500)
   - Track 1 Second Place ($1,500)
   - Track 1 Third Place ($1,000)
   - HF Special Prize (Reachy Mini + credits)
   - Build in Public Prize

2. **Scenario Analysis:**
   - **Best case:** What happens if SYNAPSE ships perfectly with a polished demo, working HF Space, viral tweet thread, and clean video?
   - **Most likely case:** What happens with a solid but not perfect submission?
   - **Worst case:** What could cause SYNAPSE to fail completely?

3. **Critical Success Factors:** List the top 5 things SYNAPSE MUST do to maximize winning probability, ranked by impact.

4. **Critical Failure Modes:** List the top 5 things that could sink the project, ranked by likelihood and severity.

5. **Final Recommendation:** Should the team proceed with SYNAPSE for this hackathon, or pivot? If pivot, to what? Be brutally honest.

---

## OUTPUT FORMAT

Structure your response with clear headers for A, B, C, D, E. Use tables for comparisons. Be specific. Cite team names and descriptions from the data above. Do not generalize.

If you lack data to answer a question, say "INSUFFICIENT DATA" rather than guessing.
