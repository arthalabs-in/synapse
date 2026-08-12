# Live Golden Causal Audit

## Executive Read
- Query: What is the strongest technically defensible architecture for SYNAPSE as a production-grade, evidence-grounded autonomous research agent in 2026: Gemini ADK-native, LangGraph with Gemini models, or custom async Python orchestration? Evaluate against grounded citation integrity, quote anchoring, tool-call determinism, multimodal extensibility, failure observability, latency/cost, reproducible evaluation, deployment burden, and hackathon demo impact. Include where each option is likely to fail.
- Degraded: False | Errors: 0
- Validator-critical counts: 9 headers, 9 fetched sources, 14 evidence items, 9 supported facts.
- Report sections: 5; LLM-authored sections: 5.
- Patch operations: 0.

## Stage Timing And LLM Calls
- planner: 32.464162s
- research_jobs: 295.176518s
- fact_checker: 41.966404s
- synthesizer: 48.541139s
- coverage_auditor: 42.600524s
- patch_applicator: 0.000274s
- total: 460.749262s

### LLM Calls
- #1 LoosePlannerJSON: ok, finish=stop, visible=3967, reasoning=860, max=2400, truncated_by_reasoning=False
- #2 ExtractionPayload: ok, finish=stop, visible=914, reasoning=493, max=64000, truncated_by_reasoning=False
- #3 ExtractionPayload: ok, finish=stop, visible=981, reasoning=1834, max=64000, truncated_by_reasoning=False
- #4 ExtractionPayload: ok, finish=stop, visible=1156, reasoning=2406, max=64000, truncated_by_reasoning=False
- #5 ExtractionPayload: ok, finish=stop, visible=1187, reasoning=1187, max=64000, truncated_by_reasoning=False
- #6 ExtractionPayload: ok, finish=stop, visible=1043, reasoning=1624, max=64000, truncated_by_reasoning=False
- #7 ExtractionPayload: ok, finish=stop, visible=1303, reasoning=2122, max=64000, truncated_by_reasoning=False
- #8 ExtractionPayload: ok, finish=stop, visible=1041, reasoning=794, max=64000, truncated_by_reasoning=False
- #9 ExtractionPayload: ok, finish=stop, visible=891, reasoning=3347, max=64000, truncated_by_reasoning=False
- #10 ExtractionPayload: ok, finish=stop, visible=817, reasoning=969, max=64000, truncated_by_reasoning=False
- #11 EntailmentBatch: fail:EmptyVisibleContentError, finish=length, visible=0, reasoning=3000, max=3000, truncated_by_reasoning=True
- #12 RevisionBriefPayload: ok, finish=stop, visible=2492, reasoning=1618, max=64000, truncated_by_reasoning=False
- #1 chat_text: ok, finish=stop, visible=2970, reasoning=2477, max=64000, truncated_by_reasoning=False

## Run Quality
- Grade: good (0.751)
- Evidence mix: total=14 llm=14 fallback=0 snippets=0
- Source health: fetched=9/9 avg_quality=0.629
- Ledger health: verified=0 partial=9 unsupported=5 contradictions=0
- Fallback reasons: {}

## Source Cleaning And Extraction Health
- Raw text chars: 201957
- Clean text chars: 188047
- Cleaning ratio: 0.93
- Removed marker counts: {'boilerplate_or_code': 4}
- Evidence by extraction method: {'llm_batch': 14}
- Fallback reason summary: {}
- Extraction failure summary: {'job_extraction_failures': 4}

## Planner Output
- Interpretation: The user wants a systematic comparison of three agent architectures for a research agent named SYNAPSE, evaluating them across technical criteria like citation integrity, tool-call determinism, multimodal extensibility, failure observability, and practical considerations like latency/cost, deployment, and demo impact, with identification of failure modes.
- Planning risks: []
- Coverage checklist:
  - grounded citation integrity
  - quote anchoring
  - tool-call determinism
  - multimodal extensibility
  - failure observability
  - latency/cost
  - reproducible evaluation
  - deployment burden
  - hackathon demo impact
  - failure modes for each option
- Research jobs:
  - job_a: Comparison of agent orchestration frameworks for evidence-grounded research agents | objective=Evaluate differences between Gemini ADK-native, LangGraph with Gemini, and custom async Python orchestration in terms of grounded citation integrity, quote anchoring, tool-call determinism, multimodal extensibility, and failure observability.
    - query: Gemini ADK agent architecture citation integrity
    - query: LangGraph tool-call determinism evidence grounding
    - query: custom async Python agent failure observability
    - query: multimodal extensibility agent framework 2026
    - query: quote anchoring in research agents
    - query: agent orchestration comparison 2026
  - job_b: Production-grade evaluation of agent architectures for SYNAPSE | objective=Assess latency/cost, reproducible evaluation, deployment burden, and hackathon demo impact for the three architectures, identifying failure modes.
    - query: LangGraph deployment overhead latency cost
    - query: Gemini ADK agent latency cost analysis
    - query: custom async Python agent performance production
    - query: reproducible evaluation agent workflows
    - query: hackathon demo agent architecture comparison
    - query: agent architecture failure modes 2026

## Job Causal Chains
### job_a: Comparison of agent orchestration frameworks for evidence-grounded research agents
- Headers selected: 5
- Evidence extracted: 8
- `res_job_a_001` Agent Development Kit | Gemini Enterprise Agent Platform | Google Cloud Documentation | https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk | fetch=fetched_http success=True text_chars=2170
  - evidence `ev_job_a_001` method=llm_batch quality=0.95 quote=Users can leverage flexible orchestration to define predictable pipelines using workflow agents or rely on agent-coordinated dynamic routing for more adaptive behavior.
  - evidence `ev_job_a_002` method=llm_batch quality=0.95 quote=Apply built-in and partner evaluation tools to test execution trajectories.
- `res_job_a_012` agentops · PyPI | https://pypi.org/project/agentops/0.3.6/ | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_a_007` method=llm_batch quality=0.2 quote=Failure Detection : Quickly identify and respond to agent failures and multi-agent interaction issues.
  - evidence `ev_job_a_008` method=llm_batch quality=0.2 quote=Comprehensive Observability: Track your AI agents' performance, user interactions, and API usage.
- `res_job_a_013` LangSmith: AI Agent & LLM Observability Platform | https://www.langchain.com/langsmith/observability | fetch=fetched_http success=True text_chars=5910
  - evidence `ev_job_a_005` method=llm_batch quality=0.2 quote=Find failures fast with agent tracing. See exactly what your agent is doing step by step. Pinpoint the issues hurting latency, cost, and response quality.
  - evidence `ev_job_a_006` method=llm_batch quality=0.2 quote=LangSmith works with any LLM framework. Trace applications built with OpenAI SDK, Anthropic SDK, Vercel AI SDK, LlamaIndex, or custom implementations, not just LangChain.
- `res_job_a_018` AI Agent Frameworks in 2026: 8 SDKs, ACP, and the Trade-offs ... | https://www.morphllm.com/ai-agent-framework | fetch=fetched_http success=True text_chars=12000
- `res_job_a_028` Multi-Agent Orchestration Platforms Compared: 2026 Edition | https://mentiko.com/blog/multi-agent-orchestration-comparison-2026 | fetch=fetched_http success=True text_chars=11389
  - evidence `ev_job_a_003` method=llm_batch quality=0.45 quote=Checkpointing and human-in-the-loop built into the graph model. Pause execution, wait for approval, resume.
  - evidence `ev_job_a_004` method=llm_batch quality=0.45 quote=You need monitoring, so you build a dashboard. Then scheduling. Then error recovery. Then RBAC. Each feature takes 2-4 weeks.
### job_b: Production-grade evaluation of agent architectures for SYNAPSE
- Headers selected: 4
- Evidence extracted: 6
- `res_job_b_002` LangGraph Pricing Guide: How Much Does It Cost? - ZenML Blog | https://www.zenml.io/blog/langgraph-pricing | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_006` method=llm_batch quality=0.45 quote=For instance, executing 1 million nodes would cost around $1,000 in usage fees alone.
- `res_job_b_006` Gemini Enterprise Agent Platform (formerly Vertex AI) | Google Cloud | https://cloud.google.com/products/gemini-enterprise-agent-platform | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_001` method=llm_batch quality=0.95 quote=New customers get up to $300 in free credits to try Agent Platform and other Google Cloud products.
  - evidence `ev_job_b_002` method=llm_batch quality=0.95 quote=Gemini Enterprise Agent Platform is Google Cloud's comprehensive platform for developers to build, scale, govern and optimize agents.
- `res_job_b_007` AI Agents for Gemini Enterprise app | Google Cloud | https://cloud.google.com/gemini-enterprise/agents | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_004` method=llm_batch quality=0.95 quote=Gemini Enterprise app gives you centralized visibility and control over all of your organization's AI agents—whether made by Google, third parties, or your own teams—in one place.
  - evidence `ev_job_b_005` method=llm_batch quality=0.95 quote=Create and deploy your own custom agents Empower every employee to transform their expertise into an “AI helper” using our no-code Agent Designer .
- `res_job_b_008` Agents overview | Gemini Enterprise Agent Platform | Google Cloud Documentation | https://docs.cloud.google.com/gemini-enterprise-agent-platform/agents/overview | fetch=fetched_http success=True text_chars=10615
  - evidence `ev_job_b_003` method=llm_batch quality=0.95 quote=Agent Studio (Low-code): A collaborative, visual workspace for discovering models, engineering prompts, and building agents without writing code. Ideal for rapid prototyping and...

## Fact Ledger Trace
- `fact_ev_job_a_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_001']
  - claim: The framework provides flexible orchestration for defining predictable pipelines using workflow agents, which contributes to tool-call determinism.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_a_002` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_002']
  - claim: The framework includes built-in and partner evaluation tools to test execution trajectories, aiding failure observability.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_a_005` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_005']
  - claim: LangSmith Observability's tracing feature helps find failures fast by showing step-by-step agent actions.
  - urls: https://www.langchain.com/langsmith/observability
- `fact_ev_job_a_007` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_007']
  - claim: AgentOps provides failure detection capabilities.
  - urls: https://pypi.org/project/agentops/0.3.6/
- `fact_ev_job_a_008` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_008']
  - claim: AgentOps offers comprehensive observability for AI agents.
  - urls: https://pypi.org/project/agentops/0.3.6/
- `fact_ev_job_b_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_b_001']
  - claim: Agents: Agent Platforms/platform developers to build, scale, govern and optimise agents. New customers get $300 free credits to try Agent Platform and other Google Cloud products, influencing initial cost evaluation.
  - urls: https://cloud.google.com/products/gemini-enterprise-agent-platform
- `fact_ev_job_b_003` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_b_003']
  - claim: Agent Studio provides a low-code visual workspace for rapid prototyping, ideal for hackathon demos.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/agents/overview
- `fact_ev_job_b_004` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_b_004']
  - claim: Gemini Enterprise app provides centralized visibility and control over all AI agents in one place.
  - urls: https://cloud.google.com/gemini-enterprise/agents
- `fact_ev_job_b_005` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_005']
  - claim: The platform includes a no-code Agent Designer for creating and deploying custom agents.
  - urls: https://cloud.google.com/gemini-enterprise/agents

## Report Citation Trace
- Title: Architecture Comparison for SYNAPSE – LangGraph Edges Ahead on Observability with Critical Evidence Gaps
- Summary: Based on partial evidence, LangGraph with Gemini models offers stronger failure observability through LangSmith tracing and AgentOps [fact_ev_job_a_005][fact_ev_job_a_008] and supports tool-call determinism via predictable pipeline orchestration [fact_ev_job_a_001]. Gemini ADK-native enables rapid prototyping for hackathon demos through Agent Studio [fact_ev_job_b_003] and provides initial cost incentives [fact_ev_job_b_001]. Custom async Python orchestration lacks any supporting evidence in...
### sec_llm_01: Failure Observability and Evaluation
- fact_ids: ['fact_ev_job_a_005', 'fact_ev_job_a_007', 'fact_ev_job_a_008', 'fact_ev_job_a_002']
- citations: 3
- content: LangGraph’s ecosystem provides comprehensive failure observability using LangSmith step-by-step tracing [fact_ev_job_a_005] and AgentOps failure detection [fact_ev_job_a_007][fact_ev_job_a_008]. The same framework also includes built-in and partner evaluation tools for testing execution trajectories [fact_ev_job_a_002]. No evidence is available for observability features in Gemini ADK-native or custom async Python orchestration.
### sec_llm_02: Tool-Call Determinism
- fact_ids: ['fact_ev_job_a_001']
- citations: 1
- content: LangGraph supports flexible orchestration with workflow agents that contributes to predictable pipelines and tool-call determinism [fact_ev_job_a_001]. There is no documented evidence covering determinism for Gemini ADK-native or custom async Python orchestration.
### sec_llm_03: Hackathon Demo Impact and Rapid Prototyping
- fact_ids: ['fact_ev_job_b_003']
- citations: 1
- content: Gemini ADK-native includes Agent Studio, a low-code visual workspace ideal for rapid prototyping and hackathon demonstrations [fact_ev_job_b_003]. Evidence for prototyping ease is absent for LangGraph and custom async Python orchestration.
### sec_llm_04: Cost and Deployment Burden
- fact_ids: ['fact_ev_job_b_001', 'fact_ev_job_b_004']
- citations: 2
- content: Gemini ADK-native offers initial cost reduction through $300 free credits for Google Cloud Agent Platform [fact_ev_job_b_001]. It also provides centralized visibility and control through Gemini Enterprise [fact_ev_job_b_004], potentially easing management burden. No comparable evidence exists for LangGraph or custom async Python orchestration.
### sec_llm_05: Grounded Citation Integrity, Quote Anchoring, Multimodal Extensibility, Reproducible Evaluation, and Latency
- fact_ids: ['fact_ev_job_a_001']
- citations: 1
- content: The provided facts contain no evidence for any of these criteria across all three architectures. These aspects remain unevaluated and must be addressed with additional evidence to support a full comparison.

## Weak Points
- Some upstream LLM calls still truncate on hidden reasoning; synthesis is fixed with 64K, extraction is not.
- Supported facts unused by the final report: ['fact_ev_job_b_005'].

## Revision Brief
- missing_intent: ["grounded citation integrity", "quote anchoring", "multimodal extensibility", "latency/cost", "reproducible evaluation", "deployment burden", "hackathon demo impact (balanced across options)", "failure modes for each option"]
- unused_supported_facts: ["fact_ev_job_b_005"]
- option_balance_gaps: ["LangGraph section uses ADK facts (fact_ev_job_a_001, fact_ev_job_a_002) to argue for tool-call determinism and evaluation, but these facts are about Gemini ADK, not LangGraph. No direct LangGraph evidence for determinism or citation integrity.", "Custom async Python has zero supporting evidence; report does not address it except by omission.", "Hackathon demo impact covered only for Gemini ADK (Agent Studio); no comparison for LangGraph or custom."]
- missed_contradictions_or_caveats: ["All used facts are partial (confidence 0.55); report does not reflect this uncertainty.", "Unsupported claims (ev_job_a_003, ev_job_a_004, ev_job_a_006, ev_job_b_002, ev_job_b_006) are excluded but report makes claims that are not fully supported.", "No evidence exists for several user-intent criteria; report should explicitly note evidence gaps."]
- unsupported_slips: ["Report credits LangGraph with failure observability using fact_ev_job_a_005 (LangSmith) and fact_ev_job_a_007/008 (AgentOps), but those tools are framework-agnostic and not exclusive to LangGraph.", "Report credits LangGraph with tool-call determinism using fact_ev_job_a_001, which is about ADK's orchestration, not LangGraph.", "Report uses fact_ev_job_a_002 (ADK evaluation tools) to claim LangGraph has built-in evaluation tools.", "Section 'Cost and Deployment Burden' uses fact_ev_job_b_004 (centralized visibility) to imply reduced deployment burden, but the fact does not directly support that."]
- suggested_revision_focus: ["Correct evidence attribution: remove or reassign facts that are not specific to LangGraph (ev_job_a_001, ev_job_a_002) and clearly label LangSmith/AgentOps as generic tools.", "Add explicit coverage statements for missing criteria (citation integrity, quote anchoring, multimodal extensibility, latency/cost, reproducible evaluation, deployment burden, failure modes) and note lack of evidence.", "Either locate evidence for custom async Python or state that no supported facts exist for this option; avoid implying absence of capability."]

## Recommended Next Fixes
- Keep the final high-reasoning 64K synthesis path; it is currently the strongest stage in the pipeline.
