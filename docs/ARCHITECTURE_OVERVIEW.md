# Architecture overview

```mermaid
flowchart LR
    Q[Question] --> P[Plan]
    P --> S[Search]
    S --> F[Fetch text]
    F --> E[Quoted evidence]
    E --> L[Fact ledger]
    L --> R[Report]
    R --> A[Coverage audit]
    A --> X[Validated patch]
    X --> O[Final artifact]
```

Search results are leads. Fetched source text grounds evidence. Evidence enters
the fact ledger, and only ledger facts may enter the report. The coverage pass
can edit the draft only through referenced patch operations.

Detailed contracts and provider boundaries are documented in
[ARCHITECTURE.md](../ARCHITECTURE.md).
