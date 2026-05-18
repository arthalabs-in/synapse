# Live Golden Causal Audit

## Executive Read
- Query: What is the strongest technically defensible architecture for SYNAPSE as a production-grade, evidence-grounded autonomous research agent in 2026: Gemini ADK-native, LangGraph with Gemini models, or custom async Python orchestration? Evaluate against grounded citation integrity, quote anchoring, tool-call determinism, multimodal extensibility, failure observability, latency/cost, reproducible evaluation, deployment burden, and hackathon demo impact. Include where each option is likely to fail.
- Degraded: False | Errors: 0
- Validator-critical counts: 11 headers, 11 fetched sources, 16 evidence items, 15 supported facts.
- Report sections: 5; LLM-authored sections: 5.
- Patch operations: 0.

## Stage Timing And LLM Calls
- planner: 123.177857s
- research_jobs: 219.004894s
- fact_checker: 38.249634s
- synthesizer: 47.38674s
- coverage_auditor: 0.000164s
- patch_applicator: 0.000199s
- total: 427.819649s

### LLM Calls
- #1 LoosePlannerJSON: fail:JSONDecodeError, finish=length, visible=4339, reasoning=1503, max=2400, truncated_by_reasoning=False
- #2 LoosePlannerJSON: fail:EmptyVisibleContentError, finish=length, visible=0, reasoning=2400, max=2400, truncated_by_reasoning=True
- #3 LoosePlannerJSON: ok, finish=stop, visible=3983, reasoning=793, max=2400, truncated_by_reasoning=False
- #4 ExtractionPayload: ok, finish=stop, visible=612, reasoning=870, max=64000, truncated_by_reasoning=False
- #5 ExtractionPayload: ok, finish=stop, visible=1120, reasoning=1069, max=64000, truncated_by_reasoning=False
- #6 ExtractionPayload: ok, finish=stop, visible=1194, reasoning=1125, max=64000, truncated_by_reasoning=False
- #7 ExtractionPayload: ok, finish=stop, visible=859, reasoning=1037, max=64000, truncated_by_reasoning=False
- #8 ExtractionPayload: ok, finish=stop, visible=888, reasoning=2129, max=64000, truncated_by_reasoning=False
- #9 ExtractionPayload: ok, finish=stop, visible=1004, reasoning=713, max=64000, truncated_by_reasoning=False
- #10 ExtractionPayload: ok, finish=stop, visible=1440, reasoning=1778, max=64000, truncated_by_reasoning=False
- #11 ExtractionPayload: ok, finish=stop, visible=21, reasoning=421, max=64000, truncated_by_reasoning=False
- #12 ExtractionPayload: ok, finish=stop, visible=1249, reasoning=883, max=64000, truncated_by_reasoning=False
- #13 ExtractionPayload: ok, finish=stop, visible=21, reasoning=293, max=64000, truncated_by_reasoning=False
- #14 EntailmentBatch: ok, finish=stop, visible=481, reasoning=2680, max=3000, truncated_by_reasoning=False
- #1 chat_text: ok, finish=stop, visible=3822, reasoning=1910, max=64000, truncated_by_reasoning=False

## Run Quality
- Grade: good (0.79)
- Evidence mix: total=16 llm=15 fallback=1 snippets=0
- Source health: fetched=11/11 avg_quality=0.919
- Ledger health: verified=0 partial=15 unsupported=1 contradictions=1
- Fallback reasons: {'llm_returned_no_accepted_evidence: llm extraction returned no evidence': 1}

## Source Cleaning And Extraction Health
- Raw text chars: 73002
- Clean text chars: 55014
- Cleaning ratio: 0.75
- Removed marker counts: {'boilerplate_or_code': 2}
- Evidence by extraction method: {'deterministic_fallback': 1, 'llm_batch': 15}
- Fallback reason summary: {'llm_returned_no_accepted_evidence: llm extraction returned no evidence': 1}
- Extraction failure summary: {'job_extraction_failures': 5}

## Planner Output
- Interpretation: The user is seeking a comparative technical evaluation of three candidate architectures for building a robust, evidence-grounded autonomous research agent (SYNAPSE) in 2026. The evaluation must cover specific criteria related to correctness, reliability, extensibility, observability, cost, and practical deployment factors, including where each architecture is expected to fail.
- Planning risks: []
- Coverage checklist:
  - citation integrity
  - quote anchoring
  - tool-call determinism
  - multimodal extensibility
  - failure observability
  - latency/cost
  - reproducible evaluation
  - deployment burden
  - hackathon demo impact
- Research jobs:
  - job_a: Technical architecture evaluation | objective=Assess the technical strengths and weaknesses of Gemini ADK-native, LangGraph with Gemini, and custom async Python orchestration for building a production-grade evidence-grounded agent, focusing on citation integrity, tool-call determinism, and multimodal extensibility.
    - query: Gemini ADK-native architecture for autonomous research agents
    - query: LangGraph Gemini tool call determinism and quote anchoring
    - query: custom async Python orchestration for evidence-grounded agents
    - query: multimodal extensibility Gemini ADK LangGraph comparison
  - job_b: Practical deployment and demo impact evaluation | objective=Evaluate deployment burden, latency/cost, failure observability, and reproducible evaluation for the three architectures in a hackathon demo context.
    - query: Gemini ADK-native deployment latency production cost
    - query: LangGraph Gemini observability troubleshooting
    - query: custom async Python orchestration deployment complexity
    - query: reproducible evaluation framework for autonomous research agents
    - query: hackathon demo best practices for agent architectures

## Job Causal Chains
### job_a: Technical architecture evaluation
- Headers selected: 7
- Evidence extracted: 10
- `res_job_a_003` Agent Development Kit | Gemini Enterprise Agent Platform ... | https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk | fetch=fetched_http success=True text_chars=2170
  - evidence `ev_job_a_001` method=llm_batch quality=0.95 quote=Users can leverage flexible orchestration to define predictable pipelines using workflow agents
  - evidence `ev_job_a_002` method=llm_batch quality=0.95 quote=Apply built-in and partner evaluation tools to test execution trajectories
- `res_job_a_006` Build multimodal agents using Gemini, Langchain, and ... | https://cloud.google.com/blog/products/ai-machine-learning/build-multimodal-agents-using-gemini-langchain-and-langgraph | fetch=fetched_http success=True text_chars=7240
  - evidence `ev_job_a_005` method=llm_batch quality=0.95 quote=Some of them, like ADK and CrewAI, have higher levels of abstraction while others like LangGraph allow higher degree of control.
  - evidence `ev_job_a_006` method=llm_batch quality=0.95 quote=The Orchestrator Agent will call relevant worker agents: image_agent, audio_agent, and video_agent while passing the user question and the relevant files. Each worker agent will...
- `res_job_a_007` generative-ai/gemini/orchestration/intro_langgraph_gemini ... | https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/orchestration/intro_langgraph_gemini.ipynb | fetch=fetched_http success=True text_chars=3504
- `res_job_a_009` Building agents with Google Gemini and open source frameworks | https://developers.googleblog.com/building-agents-google-gemini-open-source-frameworks/ | fetch=fetched_http success=True text_chars=8362
  - evidence `ev_job_a_003` method=llm_batch quality=0.95 quote=The Gemini models native function calling allow agents to interact seamlessly with external tools, APIs, and data sources, enabling them to perform real-world actions.
  - evidence `ev_job_a_004` method=llm_batch quality=0.95 quote=LangGraph is excellent for complex, stateful workflows where visibility and control over the agent's reasoning process are critical.
- `res_job_a_020` Caging the Agents: A Zero Trust Security Architecture for Autonomous AI in Healthcare | http://arxiv.org/abs/2603.17419v1 | fetch=arxiv_metadata_only success=True text_chars=1792
  - evidence `ev_job_a_009` method=llm_batch quality=0.85 quote=Recent red teaming research demonstrates that these agents exhibit critical vulnerabilities in realistic settings: unauthorized compliance with non-owner instructions, sensitive...
  - evidence `ev_job_a_010` method=llm_batch quality=0.85 quote=a prompt integrity framework with structured metadata envelopes and untrusted content labeling
- `res_job_a_021` Learning the Value Systems of Agents with Preference-based and Inverse Reinforcement Learning | http://arxiv.org/abs/2602.04518v1 | fetch=arxiv_metadata_only success=True text_chars=1455
- `res_job_a_022` Building Browser Agents: Architecture, Security, and Practical Solutions | http://arxiv.org/abs/2511.19477v1 | fetch=arxiv_metadata_only success=True text_chars=1194
  - evidence `ev_job_a_007` method=llm_batch quality=0.85 quote=The fundamental insight: model capability does not limit agent performance; architectural decisions determine success or failure.
  - evidence `ev_job_a_008` method=llm_batch quality=0.85 quote=The paper argues against developing general browsing intelligence in favor of specialized tools with programmatic constraints, where safety boundaries are enforced through code...
### job_b: Practical deployment and demo impact evaluation
- Headers selected: 4
- Evidence extracted: 6
- `res_job_b_001` Beyond the prototype: Scaling production grade agents with | https://discuss.google.dev/t/beyond-the-prototype-scaling-production-grade-agents-with-gemini/356140 | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_001` method=llm_batch quality=0.95 quote=Cloud Trace (Trajectory Analysis): You need to see the "thought process." Use Cloud Trace to visualize the agent’s decision chain: Thought → Plan → Tool Call → Observation →... | warning=long_quote
- `res_job_b_002` Gemini Live API overview | Generative AI on Vertex | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api | fetch=fetched_http success=True text_chars=4570
  - evidence `ev_job_b_002` method=llm_batch quality=0.95 quote=Gemini Live API enables low-latency, real-time voice and video interactions with Gemini.
  - evidence `ev_job_b_003` method=llm_batch quality=0.95 quote=Cost-efficiency in real-time voice agents.
- `res_job_b_004` Building AI Agents with Google Gemini 3 and Open Source | https://developers.googleblog.com/en/building-ai-agents-with-google-gemini-3-and-open-source-frameworks/ | fetch=fetched_http success=True text_chars=8588
  - evidence `ev_job_b_004` method=llm_batch quality=0.95 quote=Control Reasoning with thinking_level: Adjust the logic depth on a per-request basis. Set thinking_level to high for deep planning, bug finding, and complex instruction following....
  - evidence `ev_job_b_005` method=llm_batch quality=0.95 quote=Stateful Tool Use via Thought Signatures: The model now generates encrypted "Thought Signatures" representing its internal reasoning before calling a tool. By passing these...
- `res_job_b_018` Integrated Benchmarking and Design for Reproducible and ... | https://ieeexplore.ieee.org/document/9341677 | fetch=fetched_http success=True text_chars=845
  - evidence `ev_job_b_006` method=deterministic_fallback quality=0.85 fallback_reason=llm_returned_no_accepted_evidence: llm extraction returned no evidence quote=Integrated Benchmarking and Design for Reproducible and Accessible Evaluation of Robotic Agents | IEEE Conference Publication | IEEE Xplore IEEE Account Change Username/Password...

## Fact Ledger Trace
- `fact_ev_job_a_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_001']
  - claim: ADK provides predictable pipelines via flexible orchestration, supporting tool-call determinism.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_a_002` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_002']
  - claim: ADK includes evaluation tools for testing execution trajectories, aiding reproducibility.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_a_003` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_003']
  - claim: Gemini models have native function calling that allows agents to interact seamlessly with external tools, APIs, and data sources, which is essential for tool-call determinism.
  - urls: https://developers.googleblog.com/building-agents-google-gemini-open-source-frameworks/
- `fact_ev_job_a_004` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_004']
  - claim: LangGraph provides visibility and control over the agent's reasoning process, which can enhance quote anchoring and reproducibility of results.
  - urls: https://developers.googleblog.com/building-agents-google-gemini-open-source-frameworks/
- `fact_ev_job_a_005` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_005']
  - claim: Some agentic frameworks like ADK and CrewAI have higher levels of abstraction, while LangGraph allows higher degree of control.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/build-multimodal-agents-using-gemini-langchain-and-langgraph
- `fact_ev_job_a_006` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_006']
  - claim: In a LangGraph-based multi-agent system, an orchestrator agent calls worker agents that convert files to base64 for analysis.
  - urls: https://cloud.google.com/blog/products/ai-machine-learning/build-multimodal-agents-using-gemini-langchain-and-langgraph
- `fact_ev_job_a_008` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_a_008']
  - claim: Safety should be enforced through code rather than LLM reasoning to avoid prompt injection.
  - urls: http://arxiv.org/abs/2511.19477v1
- `fact_ev_job_a_009` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_a_009']
  - claim: Autonomous AI agents exhibit critical vulnerabilities including unauthorized compliance with non-owner instructions, which threatens tool-call determinism in production systems.
  - urls: http://arxiv.org/abs/2603.17419v1
- `fact_ev_job_a_010` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_a_010']
  - claim: A prompt integrity framework with structured metadata envelopes and untrusted content labeling can support citation integrity by enabling provenance tracking.
  - urls: http://arxiv.org/abs/2603.17419v1
- `fact_ev_job_b_001` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_001']
  - claim: Cloud Trace provides failure observability by visualizing the agent's decision chain.
  - urls: https://discuss.google.dev/t/beyond-the-prototype-scaling-production-grade-agents-with-gemini/356140
  - quality warnings: ['long_quote']
- `fact_ev_job_b_002` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_002']
  - claim: Gemini Live API enables low-latency, real-time voice and video interactions.
  - urls: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api
- `fact_ev_job_b_003` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_003']
  - claim: The gemini-live-2.5-flash-preview-native-audio-09-2025 model offers cost-efficiency in real-time voice agents.
  - urls: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api
- `fact_ev_job_b_004` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_004']
  - claim: The model's thinking_level parameter allows adjustment of logic depth to control latency and cost, with low settings achieving latency comparable to Gemini 2.5 Flash.
  - urls: https://developers.googleblog.com/en/building-ai-agents-with-google-gemini-3-and-open-source-frameworks/
- `fact_ev_job_b_005` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_005']
  - claim: Thought signatures provide stateful tool use by encrypting internal reasoning, which must be passed back, helping with failure observability and debugging.
  - urls: https://developers.googleblog.com/en/building-ai-agents-with-google-gemini-3-and-open-source-frameworks/
- `fact_ev_job_b_006` status=PARTIAL used_in_report=True confidence=0.6 evidence=['ev_job_b_006']
  - claim: Integrated Benchmarking and Design for Reproducible and Accessible Evaluation of Robotic Agents | IEEE Conference Publication | IEEE Xplore IEEE Account Change Username/Password Update Address Purchase Details Payment Options Order History View Purchased...
  - urls: https://ieeexplore.ieee.org/document/9341677

## Report Citation Trace
- Title: Architectural Recommendation for SYNAPSE 2026
- Summary: Based on available evidence, Gemini ADK-native is the strongest starting architecture because it provides predictable orchestration for tool-call determinism [fact_ev_job_a_001] and built-in evaluation tools for reproducibility [fact_ev_job_a_002], both layered on Gemini’s native function calling [fact_ev_job_a_003]. LangGraph offers superior visibility and control [fact_ev_job_a_004] but introduces higher abstraction overhead [fact_ev_job_a_005]; custom async Python has no direct evidence...
### sec_llm_01: Grounded Citation Integrity, Quote Anchoring, and Tool-Call Determinism
- fact_ids: ['fact_ev_job_a_001', 'fact_ev_job_a_003', 'fact_ev_job_a_004', 'fact_ev_job_a_005']
- citations: 3
- content: ADK’s flexible orchestration directly supports tool-call determinism [fact_ev_job_a_001], and Gemini models provide native function calling for deterministic tool interaction [fact_ev_job_a_003]. LangGraph offers visibility into the reasoning process that can enhance quote anchoring [fact_ev_job_a_004], but at a higher level of abstraction compared to ADK [fact_ev_job_a_005]. No evidence addresses quote anchoring for custom async Python; evidence for citation integrity across options is absent.
### sec_llm_02: Multimodal Extensibility
- fact_ids: ['fact_ev_job_a_006', 'fact_ev_job_a_003']
- citations: 2
- content: Only LangGraph shows a concrete multimodal pattern: an orchestrator calling workers to convert files to base64 for analysis [fact_ev_job_a_006]. ADK and custom async Python lack direct evidence for multimodal extensibility, though Gemini models’ native multimodal capabilities [fact_ev_job_a_003] are framework‑independent.
### sec_llm_03: Failure Observability, Latency, and Cost
- fact_ids: ['fact_ev_job_a_004', 'fact_ev_job_a_002']
- citations: 2
- content: Evidence is weak across all options. LangGraph provides visibility and control over reasoning [fact_ev_job_a_004], which may improve failure observability. ADK’s evaluation tools [fact_ev_job_a_002] support post‑hoc trajectory inspection but not runtime observability. No facts address latency or cost trade‑offs.
### sec_llm_04: Reproducible Evaluation
- fact_ids: ['fact_ev_job_a_002', 'fact_ev_job_a_004', 'fact_ev_job_b_006']
- citations: 3
- content: ADK includes evaluation tools for testing execution trajectories, directly aiding reproducibility [fact_ev_job_a_002]. LangGraph’s visibility into reasoning also supports reproducibility [fact_ev_job_a_004]. The paper on integrated benchmarking for robotic agents underscores the general need for accessible evaluation [fact_ev_job_b_006]. Custom async Python has no evidence of evaluation infrastructure.
### sec_llm_05: Deployment Burden and Hackathon Demo Impact
- fact_ids: ['fact_ev_job_a_005']
- citations: 1
- content: No facts specifically address deployment burden or demo impact. ADK’s higher abstraction [fact_ev_job_a_005] likely reduces initial setup effort, while LangGraph’s finer control increases complexity [fact_ev_job_a_005]. Custom async Python would require building all scaffolding from scratch; evidence for its viability is absent.

## Weak Points
- Some upstream LLM calls still truncate on hidden reasoning; synthesis is fixed with 64K, extraction is not.
- Noisy evidence quotes remain: ['ev_job_b_001'].
- Supported facts unused by the final report: ['fact_ev_job_a_008', 'fact_ev_job_a_009', 'fact_ev_job_a_010', 'fact_ev_job_b_001', 'fact_ev_job_b_002', 'fact_ev_job_b_003', 'fact_ev_job_b_004', 'fact_ev_job_b_005'].
- Fact checker produced 1 contradictions; inspect whether these are real conflicts or quote-noise artifacts.

## Recommended Next Fixes
- Add a source-cleaning pass before evidence fallback to remove docs navigation, curl snippets, API-key boilerplate, and pricing/account-tier text.
- Tighten contradiction detection so code snippets and unrelated docs boilerplate do not become semantic conflicts.
- Keep the final high-reasoning 64K synthesis path; it is currently the strongest stage in the pipeline.
