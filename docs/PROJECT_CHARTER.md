# Project scope

SYNAPSE explores a narrow question: can a research assistant keep enough of its
intermediate evidence visible for a person to audit the final answer?

## In scope

- planning a question into bounded research jobs
- searching and fetching public sources
- preserving exact source passages beside extracted claims
- classifying claim support in a fact ledger
- writing reports from ledger facts
- showing coverage edits and degradation signals
- producing a portable run artifact for inspection

## Non-goals

- proving that every accepted claim is true
- bypassing private pages, access controls, or paywalls
- replacing expert review in high-stakes work
- hiding live provider failure behind demo data
- supporting arbitrary model and search vendors through agent-specific imports

## Operating assumptions

Public sources are untrusted input. Model output is untrusted input. A URL by
itself is not evidence, and a validator pass is not a factual guarantee.

The system is useful when a reviewer needs to see the source quote, claim
status, report reference, and any later edit in one run artifact.

## Known limitations

- source-quality heuristics are coarse
- quote extraction can preserve a passage while misreading its context
- contradiction detection depends on the evidence collected
- live search and model providers can fail or truncate output
- demo mode demonstrates the interface, not current live-provider behavior
