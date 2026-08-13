# SYNAPSE Provider Notes

Gemini is the default live provider. Provider construction remains centralized
so agents do not depend on Gemini-specific clients.

## Default Live Stack

```text
Planner              Gemini 2.5 Pro
Evidence extraction  Gemini 2.5 Flash
Fact checking        Gemini 2.5 Flash
Synthesis            Gemini 2.5 Pro
Coverage audit       Gemini 2.5 Pro
```

## Optional Gemini-Native Capabilities

| Capability | Module | Flag |
| --- | --- | --- |
| Google Search grounding | `agents/grounded_precontext.py` | `GEMINI_GROUNDING_ENABLED` |
| Multimodal evidence | `agents/multimodal_ingestor.py` | `MULTIMODAL_ENABLED` |
| Function-calling follow-up agent | `agents/live_tool_agent.py` | `LIVE_TOOL_AGENT_ENABLED` |
| Thinking budget controls | `backend/providers/llm/gemini.py` | `GEMINI_THINKING_BUDGET` |

## Current use

- Strong structured-output performance for Pydantic schemas.
- Pro / Flash split lets expensive reasoning stay in planning and synthesis,
  while cheaper model calls handle extraction fan-out.
- Multimodal support lets user uploads become first-class evidence sources.
- Grounding metadata can provide an additional citation-bearing precontext
  beside regular web and arXiv search.

## Provider Boundary

SYNAPSE should not become hard-wired to one model vendor. The providers under
`backend/providers/llm/` are modular, and agents should depend on the provider
interface rather than importing concrete providers directly.

## Live Failure Rules

- Empty visible model output is treated as a real error.
- Reasoning-token truncation is logged.
- Silent deterministic fallback is validator-detectable.
- Provider metrics are part of the submitted artifact.
