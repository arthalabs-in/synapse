# Live Golden Causal Audit

## Executive Read
- Query: What is the strongest technically defensible architecture for SYNAPSE as a production-grade, evidence-grounded autonomous research agent in 2026: Gemini ADK-native, LangGraph with Gemini models, or custom async Python orchestration? Evaluate against grounded citation integrity, quote anchoring, tool-call determinism, multimodal extensibility, failure observability, latency/cost, reproducible evaluation, deployment burden, and hackathon demo impact. Include where each option is likely to fail.
- Degraded: False | Errors: 0
- Validator-critical counts: 6 headers, 6 fetched sources, 9 evidence items, 6 supported facts.
- Report sections: 5; LLM-authored sections: 5.
- Patch operations: 2.

## Stage Timing And LLM Calls
- planner: 32.718741s
- research_jobs: 173.093673s
- fact_checker: 45.347673s
- synthesizer: 46.515493s
- coverage_auditor: 89.159405s
- patch_applicator: 0.000306s
- total: 386.835537s

### LLM Calls
- #1 LoosePlannerJSON: ok, finish=stop, visible=4056, reasoning=635, max=2400, truncated_by_reasoning=False
- #2 ExtractionPayload: ok, finish=stop, visible=1002, reasoning=780, max=64000, truncated_by_reasoning=False
- #3 ExtractionPayload: ok, finish=stop, visible=1939, reasoning=1730, max=64000, truncated_by_reasoning=False
- #4 ExtractionPayload: ok, finish=stop, visible=1063, reasoning=915, max=64000, truncated_by_reasoning=False
- #5 ExtractionPayload: ok, finish=stop, visible=1017, reasoning=2292, max=64000, truncated_by_reasoning=False
- #6 ExtractionPayload: ok, finish=stop, visible=1355, reasoning=1327, max=64000, truncated_by_reasoning=False
- #7 ExtractionPayload: ok, finish=stop, visible=21, reasoning=326, max=64000, truncated_by_reasoning=False
- #8 EntailmentBatch: fail:ValueError, finish=stop, visible=553, reasoning=1704, max=3000, truncated_by_reasoning=False
- #9 EntailmentBatch: fail:ValueError, finish=stop, visible=514, reasoning=1320, max=3000, truncated_by_reasoning=False
- #10 RevisionBriefPayload: ok, finish=stop, visible=5983, reasoning=4104, max=64000, truncated_by_reasoning=False
- #1 chat_text: ok, finish=stop, visible=3380, reasoning=1869, max=64000, truncated_by_reasoning=False

## Run Quality
- Grade: good (0.803)
- Evidence mix: total=9 llm=9 fallback=0 snippets=0
- Source health: fetched=6/6 avg_quality=0.717
- Ledger health: verified=0 partial=6 unsupported=3 contradictions=0
- Fallback reasons: {}

## Source Cleaning And Extraction Health
- Raw text chars: 66791
- Clean text chars: 60010
- Cleaning ratio: 0.9
- Removed marker counts: {'boilerplate_or_code': 2}
- Evidence by extraction method: {'llm_batch': 9}
- Fallback reason summary: {}
- Extraction failure summary: {'job_extraction_failures': 3}

## Planner Output
- Interpretation: User requests a rigorous technical comparison of three architectures (Gemini ADK, LangGraph+Gemini, custom async Python) for building a production-level autonomous research agent, evaluated across specific criteria including citation integrity, determinism, observability, cost, and deployment. The answer should highlight failure modes for each.
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
  - job_a: Technical architecture comparison: determinism, observability, latency/cost | objective=Gather evidence comparing Gemini ADK-native, LangGraph with Gemini, and custom async Python orchestration on tool-call determinism, failure observability, and latency/cost for a production agent.
    - query: Gemini ADK tool call determinism reliability
    - query: LangGraph agent failure observability monitoring
    - query: custom async Python agent latency cost comparison
    - query: Gemini ADK latency benchmarks
    - query: LangGraph tool call determinism
    - query: agent orchestration failure handling observability
  - job_b: Evaluation of citation integrity, multimodal extensibility, deployment, and demo impact | objective=Gather evidence on how each architecture supports grounded citation integrity, quote anchoring, multimodal extensibility, reproducible evaluation, deployment burden, and hackathon demo impact.
    - query: Gemini ADK citation grounding quote anchoring
    - query: LangGraph citation integrity evidence
    - query: custom Python agent citation tracking
    - query: multimodal extensibility Gemini ADK
    - query: LangGraph multimodal support
    - query: deployment burden Gemini ADK vs LangGraph vs custom
    - query: hackathon demo impact agent architecture

## Job Causal Chains
### job_a: Technical architecture comparison: determinism, observability, latency/cost
- Headers selected: 4
- Evidence extracted: 5
- `res_job_a_004` Agent Development Kit | Gemini Enterprise Agent Platform | Google Cloud ... | https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk | fetch=fetched_http success=True text_chars=2170
  - evidence `ev_job_a_001` method=llm_batch quality=0.95 quote=Users can leverage flexible orchestration to define predictable pipelines using workflow agents or rely on agent-coordinated dynamic routing for more adaptive behavior.
  - evidence `ev_job_a_002` method=llm_batch quality=0.95 quote=Apply built-in and partner evaluation tools to test execution trajectories.
- `res_job_a_005` Google ADK Tutorial: Build AI Agents with Gemini (Code Examples) | https://www.aimakers.co/blog/gemini-adk-agents/ | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_a_004` method=llm_batch quality=0.45 quote=Use SequentialAgent , ParallelAgent , and LoopAgent when you know the execution path in advance. These workflow agents follow a fixed pattern every time, making them predictable,...
  - evidence `ev_job_a_005` method=llm_batch quality=0.45 quote=ADK includes built-in event logging that captures every step of an agent's execution: tool calls, LLM invocations, agent transfers, and state changes. In production, export these... | warning=long_quote
- `res_job_a_012` Python Async vs Sync: 6 Benchmarks That Will Change How You Think About Concurrency | Henry Hoang | https://henryonai.github.io/blog/python-async-vs-sync-benchmark | fetch=fetched_http success=True text_chars=7191
  - evidence `ev_job_a_003` method=llm_batch quality=0.85 quote=Percentile Sync Async Ratio p50 (median) 4.6ms 1,165ms 253x p95 38.4ms 1,185ms 31x p99 41.2ms 1,192ms 29x Why? This is Cal Paterson's finding proven in practice: Sync (threads):... | warning=long_quote
- `res_job_a_017` Gemini Ultra 2.0 response latency benchmarks revealed - ShareBlog | https://shareblog.org/en/tech/software/gemini-ultra-2-0-response-latency-benchmarks-optimization.html | fetch=fetched_http success=True text_chars=661
### job_b: Evaluation of citation integrity, multimodal extensibility, deployment, and demo impact
- Headers selected: 2
- Evidence extracted: 4
- `res_job_b_016` Topics tagged adk | https://discuss.google.dev/tag/adk | fetch=fetched_http success=True text_chars=4561
  - evidence `ev_job_b_001` method=llm_batch quality=0.95 quote=Reasoning Engine / ADK stream path fails when structured output is enforced (response_mime_type unexpected in Runner.run_async)
  - evidence `ev_job_b_002` method=llm_batch quality=0.95 quote=Deploying ADK agents with MCP on Vertex AI Agent Engine using custom installation scripts
- `res_job_b_028` Google ADK vs LangGraph : Which One Develops and Deploys AI... | https://www.zenml.io/blog/google-adk-vs-langgraph | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_003` method=llm_batch quality=0.45 quote=It provides higher-level abstractions and pre-built workflow patterns that promote a modular, testable architecture.
  - evidence `ev_job_b_004` method=llm_batch quality=0.45 quote=It offers tight control over agent workflows and integrates with the LangChain ecosystem for LLMs, tools, memory, plus LangSmith/Langfuse for tracing and eval.

## Fact Ledger Trace
- `fact_ev_job_a_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_001']
  - claim: Gemini ADK-native supports deterministic tool calls via workflow agents that define predictable pipelines.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_a_002` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_002']
  - claim: Gemini ADK-native provides failure observability through built-in evaluation tools for testing execution trajectories.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_a_003` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_003']
  - claim: Async Python exhibits significantly higher latency variance (p99) compared to sync with thread pools, making it less predictable for low-latency requirements.
  - urls: https://henryonai.github.io/blog/python-async-vs-sync-benchmark
  - quality warnings: ['long_quote']
- `fact_ev_job_a_004` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_004']
  - claim: Google ADK supports deterministic orchestration via SequentialAgent, ParallelAgent, and LoopAgent agents that follow fixed patterns, making them predictable and testable.
  - urls: https://www.aimakers.co/blog/gemini-adk-agents/
- `fact_ev_job_a_005` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_005']
  - claim: Google ADK provides built-in event logging for monitoring and tracing of agent executions, capturing every step including tool calls, LLM invocations, agent transfers, and state changes.
  - urls: https://www.aimakers.co/blog/gemini-adk-agents/
  - quality warnings: ['long_quote']
- `fact_ev_job_b_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_b_001']
  - claim: ADK stream path fails when structured output is enforced, indicating a potential failure point for citation and multimodal support.
  - urls: https://discuss.google.dev/tag/adk

## Report Citation Trace
- Title: Evidence-Based Architecture Recommendation for SYNAPSE 2026
- Summary: Gemini ADK-native is the strongest option supported by evidence, offering deterministic orchestration [fact_ev_job_a_001, fact_ev_job_a_004] and built-in failure observability [fact_ev_job_a_002, fact_ev_job_a_005]. However, its stream path fails under structured output enforcement [fact_ev_job_b_001], a risk for citation integrity. LangGraph lacks any evidence; async Python only shows latency variance [fact_ev_job_a_003]. Recommend ADK with the structured output caveat.
### sec_llm_01: Tool-Call Determinism and Reproducible Evaluation
- fact_ids: ['fact_ev_job_a_004', 'fact_ev_job_a_003', 'fact_ev_job_a_001']
- citations: 3
- content: Gemini ADK supports deterministic tool-call pipelines through SequentialAgent, ParallelAgent, and LoopAgent, making execution predictable and testable [fact_ev_job_a_004]. Additionally, official ADK documentation describes workflow agents that define predictable pipelines, further supporting determinism [fact_ev_job_a_001]. Fact_ev_job_a_001 confirms that ADK workflow agents define predictable pipelines, which directly supports reproducible evaluation. Async Python introduces higher latency variance (p99) compared to sync approaches, threatening reproducibility of timing behavior [fact_ev_job_a_003]. No facts address LangGraph for determinism or reproducibility.
### sec_llm_02: Failure Observability
- fact_ids: ['fact_ev_job_a_002', 'fact_ev_job_a_005']
- citations: 2
- content: ADK provides built-in evaluation tools for testing execution trajectories, enabling failure observation and debugging [fact_ev_job_a_002]. Fact_ev_job_a_005 adds that ADK includes event logging that captures every step including tool calls, LLM invocations, agent transfers, and state changes. These features support the failure observability criterion. No facts cover LangGraph or async Python on observability. ADK provides built-in evaluation tools for testing execution trajectories, enabling failure observation and debugging [fact_ev_job_a_002]. Moreover, ADK includes built-in event logging that captures every step including tool calls, LLM invocations, agent transfers, and state changes,...
### sec_llm_03: Multimodal Extensibility and Citation Integrity
- fact_ids: ['fact_ev_job_b_001']
- citations: 1
- content: ADK’s stream path fails when structured output is enforced [fact_ev_job_b_001]. If citation anchoring or multimodal extensibility depend on structured output, this is a direct failure point. No facts address LangGraph or async Python for citation integrity, quote anchoring, or multimodal support, so the evidence set is incomplete for those options.
### sec_llm_04: Latency and Cost
- fact_ids: ['fact_ev_job_a_003']
- citations: 1
- content: Async Python exhibits significantly higher latency variance (p99) relative to synchronous thread pools [fact_ev_job_a_003], making it less predictable for low-latency requirements and potentially increasing cost from tail latency. No facts address ADK or LangGraph latency or cost, so ADK’s latency profile is not established from this evidence.
### sec_llm_05: Deployment Burden and Hackathon Impact
- fact_ids: ['fact_ev_job_b_001']
- citations: 1
- content: ADK’s built-in observability [fact_ev_job_a_002, fact_ev_job_a_005] and deterministic orchestration [fact_ev_job_a_001, fact_ev_job_a_004] could reduce debugging time during deployment and strengthen demo reliability, but no direct facts measure deployment burden. LangGraph and async Python have no facts for these criteria. ADK’s structured output limitation [fact_ev_job_b_001] may complicate demos that require strict formatting.

## Weak Points
- Noisy evidence quotes remain: ['ev_job_a_003', 'ev_job_a_005'].

## Revision Brief
- missing_intent: ["Quote anchoring: no evidence or mention in the report.", "Multimodal extensibility: only a failure point mentioned, no positive evaluation.", "Deployment burden: no direct evidence, only a mention that no facts exist.", "Hackathon demo impact: no direct evidence, only a mention that no facts exist.", "Failure modes for each architecture: only ADK failure mode (stream path) discussed; LangGraph and async Python failure modes missing."]
- unused_supported_facts: ["fact_ev_job_a_001: official ADK docs support deterministic tool calls via workflow agents; relevant to sec_llm_01.", "fact_ev_job_a_005: blog describes built-in event logging for full visibility; relevant to sec_llm_02."]
- option_balance_gaps: ["LangGraph has no supporting evidence for any criterion; the report notes this but cannot compare.", "Async Python has evidence only for latency/cost; evaluation is incomplete for other criteria.", "ADK has evidence for determinism and observability but all facts are partial/low confidence."]
- missed_contradictions_or_caveats: ["Report does not caveat the low confidence and partial status of all facts.", "Key fact fact_ev_job_b_001 is from a forum topic title, a weak source; no source quality caveat added.", "Claim that ADK is 'strongest option supported by evidence' overstates the evidence (confidence 0.42)."]
- unsupported_slips: ["Answer_summary overstates support: 'Gemini ADK-native is the strongest option supported by evidence' should be weakened to reflect partial, low-confidence evidence."]
- suggested_revision_focus: ["Integrate unused facts fact_ev_job_a_001 and fact_ev_job_a_005 into sec_llm_01 and sec_llm_02 respectively.", "Add explicit caveats about low confidence, partial status, and weak sources for all key claims.", "For missing criteria, add statements acknowledging no evidence found rather than leaving unaddressed."]

## UI-Ready Patch Operations
- `edit_001` add | label=Add deterministic pipeline evidence | location=sections[section_id=sec_llm_01].content | refs=['fact_ev_job_a_001']
  - reason: Integrate unused supported fact fact_ev_job_a_001 into the tool-call determinism section.
  - before: Gemini ADK supports deterministic tool-call pipelines through SequentialAgent, ParallelAgent, and LoopAgent, making execution predictable and testable [fact_ev_job_a_004].
  - after: Gemini ADK supports deterministic tool-call pipelines through SequentialAgent, ParallelAgent, and LoopAgent, making execution predictable and testable [fact_ev_job_a_004]. Additionally, official ADK documentation describes workflow agents that define...
- `edit_002` add | label=Add event logging evidence | location=sections[section_id=sec_llm_02].content | refs=['fact_ev_job_a_005']
  - reason: Integrate unused supported fact fact_ev_job_a_005 into the failure observability section.
  - before: ADK provides built-in evaluation tools for testing execution trajectories, enabling failure observation and debugging [fact_ev_job_a_002]. No facts cover LangGraph or async Python on observability.
  - after: ADK provides built-in evaluation tools for testing execution trajectories, enabling failure observation and debugging [fact_ev_job_a_002]. Moreover, ADK includes built-in event logging that captures every step including tool calls, LLM invocations, agent...

## Recommended Next Fixes
- Add a source-cleaning pass before evidence fallback to remove docs navigation, curl snippets, API-key boilerplate, and pricing/account-tier text.
- Keep the final high-reasoning 64K synthesis path; it is currently the strongest stage in the pipeline.
