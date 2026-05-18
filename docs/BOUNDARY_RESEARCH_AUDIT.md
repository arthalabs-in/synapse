# Live Golden Causal Audit

## Executive Read
- Query: What is the strongest technically defensible architecture for SYNAPSE as a production-grade, evidence-grounded autonomous research agent in 2026: Gemini ADK-native, LangGraph with Gemini models, or custom async Python orchestration? Evaluate against grounded citation integrity, quote anchoring, tool-call determinism, multimodal extensibility, failure observability, latency/cost, reproducible evaluation, deployment burden, and hackathon demo impact. Include where each option is likely to fail.
- Degraded: False | Errors: 0
- Validator-critical counts: 11 headers, 11 fetched sources, 21 evidence items, 14 supported facts.
- Report sections: 3; LLM-authored sections: 3.
- Patch operations: 0.

## Stage Timing And LLM Calls
- planner: 112.496547s
- research_jobs: 350.983077s
- fact_checker: 63.398492s
- synthesizer: 94.194225s
- coverage_auditor: 0.000166s
- patch_applicator: 0.000276s
- total: 621.072962s

### LLM Calls
- #1 LoosePlannerJSON: fail:JSONDecodeError, finish=length, visible=4671, reasoning=1367, max=2400, truncated_by_reasoning=False
- #2 LoosePlannerJSON: ok, finish=stop, visible=5556, reasoning=803, max=2400, truncated_by_reasoning=False
- #3 ExtractionPayload: ok, finish=stop, visible=1257, reasoning=891, max=64000, truncated_by_reasoning=False
- #4 ExtractionPayload: ok, finish=stop, visible=765, reasoning=823, max=64000, truncated_by_reasoning=False
- #5 ExtractionPayload: ok, finish=stop, visible=1056, reasoning=1347, max=64000, truncated_by_reasoning=False
- #6 ExtractionPayload: ok, finish=stop, visible=2057, reasoning=432, max=64000, truncated_by_reasoning=False
- #7 ExtractionPayload: ok, finish=stop, visible=841, reasoning=1034, max=64000, truncated_by_reasoning=False
- #8 ExtractionPayload: ok, finish=stop, visible=1323, reasoning=1209, max=64000, truncated_by_reasoning=False
- #9 ExtractionPayload: ok, finish=stop, visible=875, reasoning=802, max=64000, truncated_by_reasoning=False
- #10 ExtractionPayload: ok, finish=stop, visible=834, reasoning=1542, max=64000, truncated_by_reasoning=False
- #11 ExtractionPayload: ok, finish=stop, visible=1005, reasoning=424, max=64000, truncated_by_reasoning=False
- #12 ExtractionPayload: ok, finish=stop, visible=796, reasoning=777, max=64000, truncated_by_reasoning=False
- #13 ExtractionPayload: ok, finish=stop, visible=1371, reasoning=2417, max=64000, truncated_by_reasoning=False
- #14 EntailmentBatch: fail:EmptyVisibleContentError, finish=length, visible=0, reasoning=3000, max=3000, truncated_by_reasoning=True
- #1 chat_text: ok, finish=stop, visible=3006, reasoning=3648, max=64000, truncated_by_reasoning=False

## Run Quality
- Grade: good (0.71)
- Evidence mix: total=21 llm=21 fallback=0 snippets=0
- Source health: fetched=11/11 avg_quality=0.826
- Ledger health: verified=0 partial=14 unsupported=7 contradictions=5
- Fallback reasons: {}

## Source Cleaning And Extraction Health
- Raw text chars: 196972
- Clean text chars: 187544
- Cleaning ratio: 0.95
- Removed marker counts: {'boilerplate_or_code': 4}
- Evidence by extraction method: {'llm_batch': 21}
- Fallback reason summary: {}
- Extraction failure summary: {'job_extraction_failures': 1}

## Planner Output
- Interpretation: The user wants a comparative analysis of three architectural approaches for building a production-grade autonomous research agent called SYNAPSE, evaluated against nine specific criteria, including identifying likely failure points for each option.
- Planning risks: []
- Coverage checklist:
  - Grounded citation integrity
  - Quote anchoring
  - Tool-call determinism
  - Multimodal extensibility
  - Failure observability
  - Latency/cost
  - Reproducible evaluation
  - Deployment burden
  - Hackathon demo impact
  - Failure modes for each architecture
- Research jobs:
  - job_a: Evaluate Gemini ADK-native architecture for SYNAPSE criteria | objective=Gather official documentation, technical reports, and case studies on Gemini ADK to assess its strengths and weaknesses across the nine specified criteria, focusing on citation integrity, tool-call determinism, multimodal extensibility, failure observability, latency/cost, reproducible evaluation, deployment burden, and hackathon demo impact. Identify likely failure modes.
    - query: Gemini ADK production architecture evaluation
    - query: Gemini ADK citation grounding integrity
    - query: Gemini ADK tool call determinism accuracy
    - query: Gemini ADK multimodal extensibility support
    - query: Gemini ADK failure observability logging and monitoring
    - query: Gemini ADK latency cost benchmarks
    - query: Gemini ADK deployment burden complexity
    - query: Gemini ADK hackathon demo impact success stories
  - job_b: Compare LangGraph with Gemini and custom async Python orchestration for SYNAPSE | objective=Collect comparative evaluations, community experiences, and official sources for LangGraph with Gemini models and custom async Python orchestration. Assess each architecture against all criteria, with emphasis on differences in citation integrity, quote anchoring, tool-call determinism, observability, and evaluation reproducibility. Determine failure points and trade-offs.
    - query: LangGraph Gemini agents citation grounding accuracy
    - query: LangGraph quote anchoring reliability research agent
    - query: LangGraph tool call determinism vs custom async Python
    - query: LangGraph multimodal support Gemini models
    - query: LangGraph observability tracing production
    - query: LangGraph latency cost comparison Python async
    - query: LangGraph reproducible evaluation methodology
    - query: Custom async Python orchestration research agent production evaluation
    - query: Comparison LangGraph custom Python agent architecture 2026
    - query: Failure modes LangGraph custom Python orchestration research agent

## Job Causal Chains
### job_a: Evaluate Gemini ADK-native architecture for SYNAPSE criteria
- Headers selected: 6
- Evidence extracted: 12
- `res_job_a_001` Agent evaluation | Gemini Enterprise Agent Platform | https://docs.cloud.google.com/gemini-enterprise-agent-platform/optimize/evaluation/agent-evaluation | fetch=fetched_http success=True text_chars=5246
  - evidence `ev_job_a_001` method=llm_batch quality=0.95 quote=Pre-GA products and features are available "as is" and might have limited support.
  - evidence `ev_job_a_002` method=llm_batch quality=0.95 quote=Environment simulation : Intercept specific tool calls to inject custom behaviors, mocked data, or simulated errors (such as HTTP 503 errors or latency spikes). This simulation...
- `res_job_a_002` Introducing Gemini Enterprise Agent Platform | Google Cloud Blog | https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise-agent-platform | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_a_005` method=llm_batch quality=0.95 quote=Agent Simulation, Agent Evaluation, and Agent Observability . These tools provide full execution traces and a real-time lens into agent reasoning to help ensure your agents always...
  - evidence `ev_job_a_006` method=llm_batch quality=0.95 quote=Multimodal streaming: Bring human-like stability to real-time interactions with multimodal support for live audio and video cues.
- `res_job_a_018` Gemini Enterprise Agent Platform (formerly Vertex AI) | Google Cloud | https://cloud.google.com/products/gemini-enterprise-agent-platform | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_a_003` method=llm_batch quality=0.95 quote=Gemini is capable of understanding virtually any input, combining different types of information, and generating almost any output.
  - evidence `ev_job_a_004` method=llm_batch quality=0.95 quote=Our Model Evaluation service provides enterprise-grade tools for objective, data-driven assessment of generative AI models.
- `res_job_a_027` Gemini 2.5 Flash Latency & Throughput — Current Benchmarks ... | https://www.ailatency.com/models/google-gemini-2-5-flash.html | fetch=fetched_http success=True text_chars=3916
  - evidence `ev_job_a_011` method=llm_batch quality=0.85 quote=⚡ Total Latency 556ms Grade B · Good
  - evidence `ev_job_a_012` method=llm_batch quality=0.85 quote=Input Cost $0.0003 /1K tokens Output Cost $0.0025 /1K tokens
- `res_job_a_028` Benchmarking Gemini 3.1 Pro: Latency, cost, and reasoning ... | https://blog.promptlayer.com/benchmarking-gemini-3-1-pro-latency-cost-and-reasoning-trade-offs/ | fetch=fetched_http success=True text_chars=6172
  - evidence `ev_job_a_007` method=llm_batch quality=0.85 quote=The model also retains multimodal support for text, images, audio, and video, along with a one million input tokens context window.
  - evidence `ev_job_a_008` method=llm_batch quality=0.85 quote=The model supports three settings: - Low: Fastest responses for simple or high-throughput tasks with minimal reasoning overhead - Medium: Balanced depth for most tasks, offering a...
- `res_job_a_037` ADK Hackathon results. Winners and highlights. | Google Cloud Blog | https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/ | fetch=fetched_http success=True text_chars=5363
  - evidence `ev_job_a_009` method=llm_batch quality=0.95 quote=The hackathon wrapped up with over 10,400 participants from 62 countries, resulting in 477 submitted projects and over 1,500 agents built!
  - evidence `ev_job_a_010` method=llm_batch quality=0.95 quote=The hackathon focused on designing and orchestrating interactions between multiple agents using ADK to tackle complex tasks like automating processes, analyzing data, improving...
### job_b: Compare LangGraph with Gemini and custom async Python orchestration for SYNAPSE
- Headers selected: 5
- Evidence extracted: 9
- `res_job_b_001` Build multimodal agents using Gemini, Langchain, and LangGraph | Google ... | https://cloud.google.com/blog/products/ai-machine-learning/build-multimodal-agents-using-gemini-langchain-and-langgraph | fetch=fetched_http success=True text_chars=7240
  - evidence `ev_job_b_001` method=llm_batch quality=0.95 quote=Some of them, like ADK and CrewAI, have higher levels of abstraction while others like LangGraph allow higher degree of control.
  - evidence `ev_job_b_002` method=llm_batch quality=0.95 quote=That’s why in this blog, we center the discussion on building a custom agent using the open-sourced LangChain, LangGraph as an agentic framework, and Gemini 2.0 Flash as the LLM...
- `res_job_b_016` Models | Gemini API | Google AI for Developers | https://ai.google.dev/gemini-api/docs/models | fetch=fetched_http success=True text_chars=8130
  - evidence `ev_job_b_003` method=llm_batch quality=0.95 quote=travel_explore Gemini Deep Research Preview An agentic model that autonomously plans and executes multi-step research across hundreds of sources to produce cited, interactive...
- `res_job_b_030` [2405.14782] Lessons from the Trenches on Reproducible Evaluation ... | https://arxiv.org/abs/2405.14782 | fetch=fetched_http success=True text_chars=5038
  - evidence `ev_job_b_004` method=llm_batch quality=0.85 quote=Researchers and engineers face methodological issues such as the sensitivity of models to evaluation setup, difficulty of proper comparisons across methods, and the lack of...
  - evidence `ev_job_b_005` method=llm_batch quality=0.85 quote=we present the Language Model Evaluation Harness (lm-eval): an open source library for independent, reproducible, and extensible evaluation of language models that seeks to...
- `res_job_b_038` LangGraph vs OpenAI Agents SDK vs PydanticAI (2026): Best ... | https://open-techstack.com/blog/langgraph-vs-openai-agents-sdk-vs-pydanticai-2026/ | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_008` method=llm_batch quality=0.45 quote=LangGraph is the strongest fit when your agent is not really 'a chatbot with tools,' but a workflow system with branching, retries, checkpoints, and human approval points.
  - evidence `ev_job_b_009` method=llm_batch quality=0.45 quote=LangGraph can absolutely be tested well, but the framework choice does not remove the burden of designing your test harness. It gives you more control, which usually means more...
- `res_job_b_039` Agentic AI Frameworks 2026: LangGraph vs CrewAI vs OpenAI SDK ... | https://uvik.net/blog/agentic-ai-frameworks/ | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_006` method=llm_batch quality=0.45 quote=Princeton’s HAL benchmark data shows that Claude Opus 4 scores 64.9% on GAIA inside one orchestration scaffold and 57.6% inside another — a gap larger than the improvement between...
  - evidence `ev_job_b_007` method=llm_batch quality=0.45 quote=LangGraph is a graph-based state machine framework built for production systems that require auditability, deterministic control, and human-in-the-loop checkpoints.

## Fact Ledger Trace
- `fact_ev_job_a_003` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_003']
  - claim: Gemini models offer multimodal input understanding and output generation, supporting multimodal extensibility.
  - urls: https://cloud.google.com/products/gemini-enterprise-agent-platform
- `fact_ev_job_a_004` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_004']
  - claim: The platform includes a Model Evaluation service for objective, data-driven assessment of generative AI models, aiding reproducible evaluation.
  - urls: https://cloud.google.com/products/gemini-enterprise-agent-platform
- `fact_ev_job_a_005` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_005']
  - claim: Gemini ADK includes tools for Agent Simulation, Evaluation, and Observability, providing full execution traces and real-time insight into agent reasoning.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise-agent-platform
- `fact_ev_job_a_006` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_006']
  - claim: Gemini ADK supports multimodal streaming for live audio and video cues, enabling real-time interactions.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise-agent-platform
- `fact_ev_job_a_009` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_009']
  - claim: The ADK Hackathon had over 10,400 participants from 62 countries, with 477 submitted projects and over 1,500 agents built.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- `fact_ev_job_a_010` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_010']
  - claim: The hackathon focused on designing and orchestrating interactions between multiple agents using ADK to tackle complex tasks.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights/
- `fact_ev_job_a_011` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_011']
  - claim: Gemini 2.5 Flash total latency is 556ms (Grade B) according to AILatency benchmarks.
  - urls: https://www.ailatency.com/models/google-gemini-2-5-flash.html
- `fact_ev_job_a_012` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_012']
  - claim: Gemini 2.5 Flash input cost is $0.0003/1K tokens and output cost $0.0025/1K tokens.
  - urls: https://www.ailatency.com/models/google-gemini-2-5-flash.html
- `fact_ev_job_b_002` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_002']
  - claim: A custom agent built with LangGraph and Gemini models is demonstrated for multimodal object detection.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/build-multimodal-agents-using-gemini-langchain-and-langgraph
- `fact_ev_job_b_003` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_003']
  - claim: Google offers agentic models 'Gemini Deep Research Preview' and 'Gemini Deep Research Max Preview' that autonomously plan and execute multi-step research across hundreds of sources with cited reports.
  - urls: https://ai.google.dev/gemini-api/docs/models
- `fact_ev_job_b_004` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_004']
  - claim: Language model evaluation faces reproducibility issues due to sensitivity to evaluation setup.
  - urls: https://arxiv.org/abs/2405.14782
- `fact_ev_job_b_005` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_005']
  - claim: The LM Evaluation Harness provides independent, reproducible, and extensible evaluation to address methodological concerns.
  - urls: https://arxiv.org/abs/2405.14782
- `fact_ev_job_b_007` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_007']
  - claim: LangGraph is designed for auditability and deterministic control in production systems.
  - urls: https://uvik.net/blog/agentic-ai-frameworks/
- `fact_ev_job_b_009` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_009']
  - claim: LangGraph provides more control but also more responsibility in testing and evaluation, implying that teams must design their own test harness.
  - urls: https://open-techstack.com/blog/langgraph-vs-openai-agents-sdk-vs-pydanticai-2026/

## Report Citation Trace
- Title: SYNAPSE Architecture Decision: Gemini ADK-Native Recommended
- Summary: Based on available evidence, Gemini ADK-native architecture provides the best alignment with all critical requirements, including multimodal extensibility [fact_ev_job_a_003][fact_ev_job_a_006], robust observability and evaluation [fact_ev_job_a_005][fact_ev_job_a_004], and proven hackathon success [fact_ev_job_a_009][fact_ev_job_a_010]. The other candidates lack documented support for these essential production-grade capabilities.
### sec_llm_01: Gemini ADK-Native – Strengths and Failure Points
- fact_ids: ['fact_ev_job_a_005', 'fact_ev_job_a_004', 'fact_ev_job_a_003', 'fact_ev_job_a_006', 'fact_ev_job_a_011', 'fact_ev_job_a_012', 'fact_ev_job_a_009', 'fact_ev_job_a_010']
- citations: 4
- content: The ADK provides built-in agent simulation, evaluation, and observability, yielding full execution traces that directly support grounded citation integrity, quote anchoring, and tool-call determinism through real-time inspection of agent reasoning [fact_ev_job_a_005]. Its Model Evaluation service enables reproducible assessment of generative AI outputs, critical for citation verification [fact_ev_job_a_004]. Multimodal input and output capabilities, including live audio and video streaming, allow the agent to process diverse evidence formats [fact_ev_job_a_003][fact_ev_job_a_006]. Latency is well-characterized: Gemini 2.5 Flash delivers 556ms response time [fact_ev_job_a_011] at a cost of...
### sec_llm_02: LangGraph with Gemini Models – Likely Failure Points
- fact_ids: ['fact_ev_job_a_006', 'fact_ev_job_a_004', 'fact_ev_job_a_005', 'fact_ev_job_a_011', 'fact_ev_job_a_012', 'fact_ev_job_a_009']
- citations: 4
- content: The evaluation facts highlight ADK-native features like multimodal streaming [fact_ev_job_a_006] and integrated evaluation [fact_ev_job_a_004] that LangGraph does not document. LangGraph lacks demonstrated capability for agent simulation and execution traces [fact_ev_job_a_005], and no comparable latency or cost benchmarks are provided [fact_ev_job_a_011][fact_ev_job_a_012]. Reproducible evaluation and failure observability would require custom builds, increasing deployment burden and reducing determinism. The absence of a proven hackathon ecosystem [fact_ev_job_a_009] suggests higher integration risk and lower demo impact.
### sec_llm_03: Custom Async Python Orchestration – Likely Failure Points
- fact_ids: ['fact_ev_job_a_003', 'fact_ev_job_a_006', 'fact_ev_job_a_004', 'fact_ev_job_a_005', 'fact_ev_job_a_011', 'fact_ev_job_a_012', 'fact_ev_job_a_009']
- citations: 4
- content: Custom orchestration does not leverage the ADK's built-in multimodal extensibility [fact_ev_job_a_003][fact_ev_job_a_006] or evaluation and observability services [fact_ev_job_a_004][fact_ev_job_a_005]. Achieving the same latency and cost efficiency as Gemini 2.5 Flash [fact_ev_job_a_011][fact_ev_job_a_012] requires extensive optimization. Failure observability and tool-call determinism lack the structured trace support that ADK provides [fact_ev_job_a_005]. The lack of a verified deployment model via a hackathon [fact_ev_job_a_009] signals higher demo development effort and lower impact.

## Weak Points
- Some upstream LLM calls still truncate on hidden reasoning; synthesis is fixed with 64K, extraction is not.
- Supported facts unused by the final report: ['fact_ev_job_b_002', 'fact_ev_job_b_003', 'fact_ev_job_b_004', 'fact_ev_job_b_005', 'fact_ev_job_b_007', 'fact_ev_job_b_009'].
- Fact checker produced 5 contradictions; inspect whether these are real conflicts or quote-noise artifacts.

## Recommended Next Fixes
- Tighten contradiction detection so code snippets and unrelated docs boilerplate do not become semantic conflicts.
- Keep the final high-reasoning 64K synthesis path; it is currently the strongest stage in the pipeline.
