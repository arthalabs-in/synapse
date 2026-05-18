# SYNAPSE Build-In-Public Posts

General posts for UOE Summer of Code or any broad AI/productivity audience.

## Post 1 - Problem

> Most AI research tools still ask users to trust fluent prose.
>
> I am building SYNAPSE to make AI answers auditable:
>
> - search real sources
> - fetch source text
> - extract exact quotes
> - verify claims into a fact ledger
> - block unsupported claims
> - patch the final answer with visible edit reasons
>
> The goal is simple: answers you can audit.

## Post 2 - Engineering

> SYNAPSE now runs as a full evidence pipeline:
>
> query -> planner -> search -> fetch -> evidence -> fact ledger -> synthesis
> -> coverage audit -> patch diff -> validator
>
> The interesting part is not the model. It is the contract between stages.
> Every final claim needs a source quote and a fact ID.

## Post 3 - Demo

> SYNAPSE now writes a live artifact and validates it.
>
> The validator rejects:
>
> - fake URLs
> - missing source quotes
> - unsupported claims in the final answer
> - patch operations without evidence references
> - silent model fallback
>
> If the validator passes, the answer is inspectable from source to report.

## Post 4 - Product

> The patch diff is becoming the clearest product moment.
>
> Instead of silently rewriting the answer, SYNAPSE records:
>
> - edit ID
> - target location
> - original text
> - replacement text
> - evidence references
> - reason for the edit
>
> This is what trustworthy AI should feel like: not magic, but visible work.
