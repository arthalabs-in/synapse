# Editorial UI and Documentation Design

## Scope

Refresh the Streamlit presentation without changing the research pipeline or its data contracts. Keep the repository documentation, but edit it so it reads as direct project documentation rather than application copy.

## Interface

Use the approved Editorial Light direction:

- warm off-white page and paper-white working surfaces
- dark neutral text with one blue accent
- editorial serif headings and plain sans-serif controls
- thin dividers instead of layered cards, glows, grids, or gradients
- a narrow navigation rail and a wide report workspace
- the grounded answer as the primary reading surface
- evidence and validation as a quieter right-hand context rail
- compact run metrics between the query composer and report

Preserve the existing Streamlit workflow, controls, result sections, history, progress reporting, downloads, and feature flags. The change is presentational. Existing renderer functions may be simplified or restyled, but their inputs and pipeline behavior remain unchanged.

## Wordmark

Use `SYN/APSE` as the visual idea, with the slash rendered as a separate blue diagonal signal.

The slash should be larger than the first mockup: clearly taller and wider than the surrounding letter strokes, while keeping the total wordmark compact enough for the sidebar and top header. It must remain legible at small sizes and should not require a separate image asset.

## Interaction

Motion is limited to interface feedback:

- a short page-content entrance
- subtle button lift on hover
- restrained row or evidence-item highlight on hover

Respect reduced-motion settings. Avoid decorative animation.

## Documentation

Keep technical and submission documentation. Rewrite where necessary using these rules:

- lead with what the project does, not a slogan
- prefer concrete nouns, commands, constraints, and failure behavior
- remove repeated pitches, inflated claims, generic audience lists, and canned “why this matters” language
- remove meta statements about generated or assisted writing
- avoid claiming that validation proves truth; state exactly what each validator checks
- keep architecture contracts, setup commands, deployment steps, and current limitations
- keep Horizons rules clearly separated from technical documentation
- do not create platform submission prose for the user to paste; Horizons requires the user to write that text

The root README should be the main entry point. Architecture and verification files should cover details once rather than repeat the README. Submission documents should function as checklists and factual notes, not polished application answers.

## Verification

- run the full deterministic pytest suite
- start Streamlit in demo mode and check the initial and populated states
- inspect desktop and narrow viewport screenshots
- confirm text contrast, responsive stacking, and slash legibility
- confirm all existing result panels and controls remain reachable
- scan tracked Markdown for removed meta-writing references and repeated promotional phrases

## Human Summary

SYNAPSE will keep the same research engine and information, but the app will move from a neon technical dashboard to a calm editorial workbench. The report will be easier to read, evidence will remain visible beside it, and the logo will use a larger blue slash as its identifying detail. The documentation will stay in the repository, with repetitive marketing language removed and technical facts stated plainly. No pipeline behavior or trust checks will be weakened.
