# Live Golden Causal Audit

## Executive Read
- Query: Which Gemini-first, evidence-grounded AI agent workflow should SYNAPSE build for the Milan AI Week hackathon? Focus on Gemini API or ADK function calling, grounding, multimodal inputs, evaluation, and demo feasibility.
- Degraded: False | Errors: 0
- Validator-critical counts: 9 headers, 9 fetched sources, 17 evidence items, 13 supported facts.
- Report sections: 4; LLM-authored sections: 4.
- Patch operations: 0.

## Stage Timing And LLM Calls
- planner: 110.635457s
- research_jobs: 279.852113s
- fact_checker: 129.733794s
- synthesizer: 31.533127s
- coverage_auditor: 0.000105s
- patch_applicator: 0.000236s
- total: 551.755033s

### LLM Calls
- #1 LoosePlannerJSON: fail:JSONDecodeError, finish=length, visible=3256, reasoning=1634, max=2400, truncated_by_reasoning=False
- #2 LoosePlannerJSON: ok, finish=stop, visible=3809, reasoning=1068, max=2400, truncated_by_reasoning=False
- #3 ExtractionPayload: ok, finish=stop, visible=608, reasoning=805, max=64000, truncated_by_reasoning=False
- #4 ExtractionPayload: ok, finish=stop, visible=570, reasoning=1008, max=64000, truncated_by_reasoning=False
- #5 ExtractionPayload: ok, finish=stop, visible=774, reasoning=777, max=64000, truncated_by_reasoning=False
- #6 ExtractionPayload: ok, finish=stop, visible=890, reasoning=690, max=64000, truncated_by_reasoning=False
- #7 ExtractionPayload: ok, finish=stop, visible=924, reasoning=2727, max=64000, truncated_by_reasoning=False
- #8 ExtractionPayload: ok, finish=stop, visible=739, reasoning=771, max=64000, truncated_by_reasoning=False
- #9 ExtractionPayload: ok, finish=stop, visible=954, reasoning=700, max=64000, truncated_by_reasoning=False
- #10 ExtractionPayload: ok, finish=stop, visible=962, reasoning=501, max=64000, truncated_by_reasoning=False
- #11 ExtractionPayload: ok, finish=stop, visible=1453, reasoning=1533, max=64000, truncated_by_reasoning=False
- #12 EntailmentBatch: fail:ValueError, finish=stop, visible=1171, reasoning=2349, max=3000, truncated_by_reasoning=False
- #13 EntailmentBatch: fail:JSONDecodeError, finish=length, visible=2726, reasoning=2320, max=3000, truncated_by_reasoning=False
- #1 chat_text: ok, finish=stop, visible=1998, reasoning=886, max=64000, truncated_by_reasoning=False

## Run Quality
- Grade: good (0.736)
- Evidence mix: total=17 llm=17 fallback=0 snippets=0
- Source health: fetched=9/9 avg_quality=0.406
- Ledger health: verified=0 partial=13 unsupported=4 contradictions=0
- Fallback reasons: {}

## Source Cleaning And Extraction Health
- Raw text chars: 113592
- Clean text chars: 102480
- Cleaning ratio: 0.9
- Removed marker counts: {'boilerplate_or_code': 4}
- Evidence by extraction method: {'llm_batch': 17}
- Fallback reason summary: {}
- Extraction failure summary: {'job_extraction_failures': 1}

## Planner Output
- Interpretation: The user is asking for recommendations on a specific agent workflow that leverages Gemini's strengths, is grounded in evidence (e.g., via function calling or grounding), and is feasible to demo at a hackathon. The focus is on using Gemini API or ADK with multimodal inputs and evaluation.
- Planning risks: []
- Coverage checklist:
  - Function calling capabilities and patterns
  - Grounding techniques (e.g., via Google Search or custom tools)
  - Multimodal input support (text, images, audio, video)
  - Evaluation methods for agent accuracy and reliability
  - Demo feasibility considerations (limited time, APIs, hardware)
  - Hackathon-specific tips (time constraints, presentability)
- Research jobs:
  - job_a: Official Gemini Agent Workflows & API Capabilities | objective=Compile official documentation and best practices for building agent workflows using Gemini API, including function calling, grounding, and multimodal inputs.
    - query: Gemini API agent workflow function calling grounding
    - query: Google ADK function calling Gemini
    - query: Gemini multimodal agent tutorial official
  - job_b: Hackathon-Relevant Evidence-Grounded Workflows & Evaluation | objective=Identify practical, demo-feasible agent workflows that emphasize evidence grounding, multimodal inputs, and evaluation strategies suitable for a hackathon setting.
    - query: evidence-grounded AI agent hackathon Gemini
    - query: Gemini agent evaluation metrics
    - query: multimodal document agent hackathon
    - query: Gemini ADK demo feasibility

## Job Causal Chains
### job_a: Official Gemini Agent Workflows & API Capabilities
- Headers selected: 3
- Evidence extracted: 6
- `res_job_a_007` Introduction to ADK Gemini Live API Toolkit - Google Codelabs | https://codelabs.developers.google.com/intro-to-adk-live | fetch=fetched_http success=True text_chars=7703
  - evidence `ev_job_a_001` method=llm_batch quality=0.95 quote=Tool execution : Automatically calling and resuming from function calls
  - evidence `ev_job_a_002` method=llm_batch quality=0.95 quote=By the end, you'll have a working voice AI that can: Accept text, audio, and image input
- `res_job_a_013` Building a Multimodal Agent with the ADK, Azure ACI, and Gemini ... | https://dev.to/gde/building-a-multimodal-agent-with-the-adk-azure-aci-and-gemini-flash-live-31-3hp6 | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_a_005` method=llm_batch quality=0.2 quote=Gemini Live is a conversational AI feature from Google that enables free-flowing, real-time voice, video, and screen-sharing interactions
  - evidence `ev_job_a_006` method=llm_batch quality=0.2 quote=The Google Agent Development Kit (ADK) is an open-source, Python-based framework designed to streamline the creation, deployment, and orchestration of sophisticated, multi-agent...
- `res_job_a_014` GitHub - google- gemini /cookbook: Examples and guides for using the... | https://github.com/google-gemini/cookbook | fetch=fetched_http success=True text_chars=9808
  - evidence `ev_job_a_003` method=llm_batch quality=0.2 quote=Grounding : use Google Search for grounded responses
  - evidence `ev_job_a_004` method=llm_batch quality=0.2 quote=Get started : Get started with Gemini models and the Gemini API, covering basic prompting and multimodal input.
### job_b: Hackathon-Relevant Evidence-Grounded Workflows & Evaluation
- Headers selected: 6
- Evidence extracted: 11
- `res_job_b_002` Gemini Live Agent Challenge: Redefining Interaction: From | https://geminiliveagentchallenge.devpost.com/ | fetch=fetched_http success=True text_chars=11949
  - evidence `ev_job_b_005` method=llm_batch quality=0.2 quote=Entrants must develop a NEW next-generation AI Agent that utilizes multimodal inputs and outputs and moves beyond simple text-in/text-out interactions.
  - evidence `ev_job_b_006` method=llm_batch quality=0.2 quote=Does the agent avoid hallucinations? Is there evidence of grounding?
- `res_job_b_006` Gemini 3 — Google DeepMind | https://deepmind.google/models/gemini/ | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_009` method=llm_batch quality=0.2 quote=Created with Gemini 3 Flash Visual context in an instant Leverage Gemini 3 Flash’s multimodal capabilities in visual recognition and reasoning to add contextual UI on image...
  - evidence `ev_job_b_010` method=llm_batch quality=0.2 quote=SWE-Bench Verified Agentic coding Single attempt 80.6%
- `res_job_b_011` Hacking with AgentQL at Multimodal AI Agents Hackathon ... | AgentQL | https://www.agentql.com/blog/2025-multimodal-agents-hackathon | fetch=fetched_http success=True text_chars=7462
  - evidence `ev_job_b_003` method=llm_batch quality=0.45 quote=Internship Hunt: Powered by Agno, Gemini, and AgentQL
  - evidence `ev_job_b_004` method=llm_batch quality=0.45 quote=Fixit is an AI-powered assistant that helps users diagnose and resolve appliance issues using text, image, audio, or video inputs.
- `res_job_b_016` Accelerate software development with Gemini - Cloud Solutions | https://googlecloudplatform.github.io/cloud-solutions/build-with-gemini-demo/ | fetch=fetched_http success=True text_chars=12000
  - evidence `ev_job_b_011` method=llm_batch quality=0.2 quote=Using Model Context Protocol (MCP) servers, it brings requirements from external systems(eg. JIRA, Confluence) into Gemini chat for efficient planning, review, and implementation.
- `res_job_b_018` Agent Development Kit | Gemini Enterprise Agent Platform | Google Cloud ... | https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk | fetch=fetched_http success=True text_chars=2170
  - evidence `ev_job_b_001` method=llm_batch quality=0.95 quote=Apply built-in and partner evaluation tools to test execution trajectories.
  - evidence `ev_job_b_002` method=llm_batch quality=0.95 quote=Set up your environment and get an agent running in a few minutes.
- `res_job_b_019` cloud-solutions/projects/build-with-gemini-demo/prototype-adk-agent ... | https://github.com/GoogleCloudPlatform/cloud-solutions/tree/main/projects/build-with-gemini-demo/prototype-adk-agent-with-gemini-cli | fetch=fetched_http success=True text_chars=7852
  - evidence `ev_job_b_007` method=llm_batch quality=0.2 quote=You will have a working ADK agent capable of looking up and summarizing in-memory ticket data, all built and debugged primarily through natural language commands in the Gemini CLI.
  - evidence `ev_job_b_008` method=llm_batch quality=0.2 quote=Sample queries to try: lookup ticket # 10 summarize ticket # 5

## Fact Ledger Trace
- `fact_ev_job_a_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_001']
  - claim: ADK Gemini Live API Toolkit automatically handles tool execution, including calling and resuming from function calls.
  - urls: https://codelabs.developers.google.com/intro-to-adk-live
- `fact_ev_job_a_002` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_002']
  - claim: A working voice AI built with ADK can accept text, audio, and image input.
  - urls: https://codelabs.developers.google.com/intro-to-adk-live
- `fact_ev_job_a_003` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_003']
  - claim: Grounding with Google Search is a recommended pattern for Gemini agents.
  - urls: https://github.com/google-gemini/cookbook
- `fact_ev_job_a_004` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_004']
  - claim: The Gemini API supports multimodal input handling as part of its basic usage.
  - urls: https://github.com/google-gemini/cookbook
- `fact_ev_job_a_005` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_005']
  - claim: Gemini Live enables real-time multimodal interactions including voice, video, and screen-sharing.
  - urls: https://dev.to/gde/building-a-multimodal-agent-with-the-adk-azure-aci-and-gemini-flash-live-31-3hp6
- `fact_ev_job_a_006` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_a_006']
  - claim: The ADK is an open-source Python framework for building multi-agent AI systems.
  - urls: https://dev.to/gde/building-a-multimodal-agent-with-the-adk-azure-aci-and-gemini-flash-live-31-3hp6
- `fact_ev_job_b_001` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_b_001']
  - claim: The Agent Development Kit includes built-in and partner evaluation tools to test agent execution trajectories.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_b_002` status=PARTIAL used_in_report=True confidence=0.55 evidence=['ev_job_b_002']
  - claim: Users can quickly set up an agent environment and get it running in a few minutes using the ADK.
  - urls: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- `fact_ev_job_b_004` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_004']
  - claim: Fixit is a real-time appliance troubleshooting agent that uses text, image, audio, or video inputs, demonstrating a multimodal agent hackathon project.
  - urls: https://www.agentql.com/blog/2025-multimodal-agents-hackathon
- `fact_ev_job_b_005` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_005']
  - claim: The Gemini Live Agent Challenge requires projects to leverage Google's Live API with multimodal inputs and outputs, moving beyond text-only interactions.
  - urls: https://geminiliveagentchallenge.devpost.com/
- `fact_ev_job_b_006` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_006']
  - claim: Judging criteria for the hackathon include evaluation of evidence grounding and avoidance of hallucinations.
  - urls: https://geminiliveagentchallenge.devpost.com/
- `fact_ev_job_b_009` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_009']
  - claim: Gemini 3 Flash provides a quick-win demo for multimodal agents by enabling visual context in an instant through multimodal recognition and reasoning for UI generation.
  - urls: https://deepmind.google/models/gemini/
- `fact_ev_job_b_011` status=PARTIAL used_in_report=False confidence=0.55 evidence=['ev_job_b_011']
  - claim: The Gemini CLI feature implementation demo uses MCP servers to bring external requirements (JIRA/Confluence) into context, grounding the agent in real-world data, which is relevant to evidence-grounded agents.
  - urls: https://googlecloudplatform.github.io/cloud-solutions/build-with-gemini-demo/

## Report Citation Trace
- Title: Multimodal Grounded Agent with ADK for Milan AI Week Hackathon
- Summary: We recommend building a multimodal, evidence-grounded AI agent using the ADK Gemini Live API Toolkit, which provides automatic tool execution and evaluation capabilities [fact_ev_job_a_001][fact_ev_job_b_001]. The agent leverages grounding with Google Search for verifiable responses and accepts text, audio, and image inputs via Gemini API multimodal support [fact_ev_job_a_003][fact_ev_job_a_004]. Rapid setup with ADK and real-time voice, video, and screen-sharing via Gemini Live make this...
### sec_llm_01: Architecture and Tool Execution
- fact_ids: ['fact_ev_job_a_006', 'fact_ev_job_a_001']
- citations: 2
- content: The ADK is an open-source Python framework for building multi-agent AI systems [fact_ev_job_a_006]. Its Gemini Live API Toolkit automatically handles tool execution, including calling and resuming from function calls, which streamlines agent orchestration [fact_ev_job_a_001].
### sec_llm_02: Multimodal Inputs and Real-Time Interaction
- fact_ids: ['fact_ev_job_a_002', 'fact_ev_job_a_004', 'fact_ev_job_a_005']
- citations: 3
- content: A working voice AI built with ADK accepts text, audio, and image input [fact_ev_job_a_002]. The Gemini API supports multimodal input handling as part of its basic usage [fact_ev_job_a_004]. Gemini Live further enables real-time multimodal interactions including voice, video, and screen-sharing for an engaging demo [fact_ev_job_a_005].
### sec_llm_03: Grounding for Evidence-Grounded Responses
- fact_ids: ['fact_ev_job_a_003']
- citations: 1
- content: Grounding with Google Search is a recommended pattern for Gemini agents to ensure responses are evidence-based and verifiable [fact_ev_job_a_003]. This directly supports the hackathon requirement for high-confidence, fact-backed outputs.
### sec_llm_04: Evaluation and Demo Feasibility
- fact_ids: ['fact_ev_job_b_001', 'fact_ev_job_b_002']
- citations: 1
- content: The Agent Development Kit includes built-in and partner evaluation tools to test agent execution trajectories [fact_ev_job_b_001]. Users can quickly set up an agent environment and get it running in a few minutes using the ADK, making the workflow practical for a hackathon timeline [fact_ev_job_b_002].

## Weak Points
- Supported facts unused by the final report: ['fact_ev_job_b_004', 'fact_ev_job_b_005', 'fact_ev_job_b_006', 'fact_ev_job_b_009', 'fact_ev_job_b_011'].

## Recommended Next Fixes
- Keep the final high-reasoning 64K synthesis path; it is currently the strongest stage in the pipeline.
