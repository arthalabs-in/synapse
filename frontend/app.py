"""SYNAPSE Streamlit workbench UI."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models import PipelineResult
from backend.prompt_cache import load_cached_result, store_cached_result
from backend.research_engine import SynapseResearchEngine
from config import config
from frontend import theme


DEMO_QUERY = config.DEMO_QUERY
UI_VERSION = "plain_workbench_empty_query_v2"
STAGE_DEFINITIONS = [
    (
        "Plan",
        "planner",
        "Interpret the question and decide what must be covered.",
        "Reading the question, identifying comparison axes, and preparing research jobs.",
    ),
    (
        "Search",
        "search",
        "Find candidate public sources for the research plan.",
        "Querying search providers for credible sources and source diversity.",
    ),
    (
        "Fetch",
        "research_jobs",
        "Fetch and normalize source text for citation.",
        "Opening selected URLs, cleaning page text, and preserving source metadata.",
    ),
    (
        "Extract",
        "evidence_extractor",
        "Pull quote-grounded evidence from fetched sources.",
        "Asking the model to extract claims with direct source quotes.",
    ),
    (
        "Ledger",
        "fact_checker",
        "Reconcile evidence into verified and partial facts.",
        "Checking support levels and separating verified, partial, and unsupported claims.",
    ),
    (
        "Draft",
        "synthesizer",
        "Write the answer using only the fact ledger.",
        "Synthesizing a neutral answer from verified evidence and citations.",
    ),
    (
        "Audit",
        "coverage_auditor",
        "Check coverage, unsupported claims, and gaps.",
        "Reviewing whether the answer missed evidence, caveats, or contradictions.",
    ),
    (
        "Patch",
        "patch_applicator",
        "Apply justified edits with fact-linked reasons.",
        "Applying justified report edits and recording why each change was made.",
    ),
]
LIVE_COMPLETED_SUMMARIES = {
    "planner": "Research plan ready.",
    "search": "Candidate public sources collected.",
    "research_jobs": "Selected sources fetched and normalized.",
    "evidence_extractor": "Quote-grounded evidence extracted.",
    "fact_checker": "Evidence reconciled into the fact ledger.",
    "synthesizer": "Grounded draft produced.",
    "coverage_auditor": "Coverage and unsupported-claim audit finished.",
    "patch_applicator": "Justified edits applied.",
}


st.set_page_config(
    page_title="SYNAPSE",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject_theme()


def main() -> None:
    if st.query_params.get("demo") == "1" and "result" not in st.session_state:
        st.session_state["result"] = load_demo_result()
    if st.session_state.get("_ui_version") != UI_VERSION and "result" not in st.session_state:
        st.session_state["query"] = ""
        st.session_state["_ui_version"] = UI_VERSION
    st.session_state.setdefault("run_requested", False)
    st.session_state.setdefault("run_in_progress", False)
    st.session_state.setdefault("active_stage", "")
    st.session_state.setdefault("run_history", [])

    current_result = st.session_state.get("result") or {}
    demo_mode = config.DEMO_MODE
    is_running = bool(st.session_state.get("run_in_progress"))

    with st.sidebar:
        render_sidebar(current_result)

    theme.workbench_header(
        "Research Workbench",
        "Ask a hard question. Get an answer you can audit.",
    )

    with st.container(border=True):
        theme.kicker("What do you want to research?")
        query = st.text_area(
            "Query input",
            key="query",
            placeholder="",
            height=140,
            label_visibility="collapsed",
        )
        c1, _ = st.columns([1.35, 5])
        with c1:
            st.button(
                "Research Running..." if is_running else "Start Research",
                type="primary",
                disabled=is_running or not query.strip(),
                use_container_width=True,
                on_click=request_run,
            )

    current_tab, history_tab = st.tabs(["Current run", f"History ({len(st.session_state['run_history'])})"])

    with current_tab:
        if st.session_state.get("run_requested"):
            with st.container(border=True):
                workflow_slot = st.empty()
                activity_slot = st.empty()
            try:
                result = run_pipeline_with_progress(
                    query.strip(),
                    demo_mode,
                    st.session_state.get("_uploads_payload") or [],
                    workflow_slot,
                    activity_slot,
                )
                st.session_state["result"] = result
                remember_run(result)
            finally:
                st.session_state["run_requested"] = False
                st.session_state["run_in_progress"] = False
                st.session_state["active_stage"] = ""
                st.rerun()

        result = st.session_state.get("result")
        if not result:
            render_empty_state()
        else:
            render_pipeline(result)
            if config.LIVE_TOOL_AGENT_ENABLED:
                render_live_tool_agent_panel(result)

    with history_tab:
        render_run_history(st.session_state["run_history"])


def request_run() -> None:
    previous_result = st.session_state.pop("result", None)
    if previous_result:
        remember_run(previous_result)
    st.session_state["run_requested"] = True
    st.session_state["run_in_progress"] = True
    st.session_state["active_stage"] = "planner"


def render_sidebar(current_result: dict[str, Any]) -> None:
    theme.sidebar_brand()
    theme.sidebar_nav(len(current_result.get("evidence_items") or []))
    theme.hairline()
    theme.status_card("All systems operational", "Ready for live research")

    llm_summary = config.active_llm_summary()
    with st.expander("Runtime details", expanded=False):
        theme.runtime_block(
            [
                ("Provider", theme.humanize(llm_summary["provider"])),
                ("Model", llm_summary["model"] or "not configured"),
                ("Endpoint", llm_summary["endpoint"] or "not configured"),
                ("Fixture", Path(config.GOLDEN_RESULT_PATH).name),
            ]
        )

    uploads_payload: list[dict[str, Any]] = []
    if config.MULTIMODAL_ENABLED:
        theme.hairline()
        theme.kicker("Multimodal uploads")
        uploaded_files = st.file_uploader(
            "Attach supporting files",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "pdf", "wav", "mp3", "mp4", "txt"],
            key="synapse_uploads",
            label_visibility="collapsed",
        )
        for uploaded in uploaded_files or []:
            data = uploaded.read()
            if not data:
                continue
            uploads_payload.append(
                {
                    "file_name": uploaded.name,
                    "mime_type": uploaded.type or "application/octet-stream",
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "data": data,
                }
            )
        if uploads_payload:
            st.caption(f"{len(uploads_payload)} file(s) staged for this run.")
    st.session_state["_uploads_payload"] = uploads_payload


def run_pipeline(query: str, demo_mode: bool, uploads: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    with st.spinner("Running SYNAPSE pipeline..."):
        try:
            engine = SynapseResearchEngine(demo_mode=demo_mode)
            result = run_async_engine(engine, query, uploads or [])
            return result.model_dump(mode="json") if isinstance(result, PipelineResult) else result
        except Exception as exc:
            st.warning(f"Live run failed. Loaded cached demo result. Error: {exc}")
            return load_demo_result()


def run_async_engine(engine: SynapseResearchEngine, query: str, uploads: list[dict[str, Any]]) -> PipelineResult:
    if uploads and config.MULTIMODAL_ENABLED:
        return asyncio.run(engine.run(query, uploads=uploads))
    return asyncio.run(engine.run(query))


def run_pipeline_with_progress(
    query: str,
    demo_mode: bool,
    uploads: list[dict[str, Any]],
    workflow_slot,
    activity_slot,
) -> dict[str, Any]:
    cached = None if uploads else load_cached_result(query)
    if cached:
        return run_cached_pipeline_with_progress(cached, workflow_slot, activity_slot)

    live_state = new_live_state()
    progress_queue: queue.Queue[dict[str, Any]] = queue.Queue()
    result_box: dict[str, Any] = {}

    def on_progress(event: dict[str, Any]) -> None:
        progress_queue.put(event)

    def worker() -> None:
        try:
            engine = SynapseResearchEngine(demo_mode=demo_mode, progress_callback=on_progress)
            result = run_async_engine(engine, query, uploads)
            result_box["result"] = result.model_dump(mode="json") if isinstance(result, PipelineResult) else result
        except Exception as exc:
            result_box["error"] = exc
        finally:
            progress_queue.put({"event": "worker_finished", "operation": "complete"})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    render_live_progress(workflow_slot, activity_slot, live_state)

    while thread.is_alive() or not progress_queue.empty():
        changed = False
        while True:
            try:
                event = progress_queue.get_nowait()
            except queue.Empty:
                break
            apply_progress_event(live_state, event)
            changed = True
        if changed or live_state.get("active_stage"):
            render_live_progress(workflow_slot, activity_slot, live_state)
        time.sleep(0.25)

    thread.join(timeout=0.1)
    if result_box.get("error"):
        st.warning(f"Live run failed. Loaded cached demo result. Error: {result_box['error']}")
        return load_demo_result()
    result = result_box.get("result") or load_demo_result()
    if not uploads and result_box.get("result"):
        store_cached_result(query, result)
    return result


def run_cached_pipeline_with_progress(
    result: dict[str, Any],
    workflow_slot,
    activity_slot,
) -> dict[str, Any]:
    live_state = new_live_state()
    for _, key, _, _ in STAGE_DEFINITIONS:
        apply_progress_event(live_state, {"event": "started", "operation": key})
        render_live_progress(workflow_slot, activity_slot, live_state)
        time.sleep(0.16)
        apply_progress_event(live_state, {"event": "completed", "operation": key, "seconds": 0.16})
        render_live_progress(workflow_slot, activity_slot, live_state)
        time.sleep(0.04)
    result.setdefault("history", []).append({"mode": "preloaded_demo", "source": "sqlite_prompt_cache"})
    return result


def new_live_state() -> dict[str, Any]:
    return {
        "active_counts": {},
        "completed": set(),
        "failed": set(),
        "durations": {},
        "stage_started_at": {},
        "active_stage": "",
        "last_event": {},
    }


def progress_stage_for_operation(operation: str) -> str:
    stage_keys = {item[1] for item in STAGE_DEFINITIONS}
    if operation in stage_keys:
        return operation
    if operation == "planner":
        return "planner"
    if operation.endswith(":searcher") or operation == "search":
        return "search"
    if "source_fetcher" in operation:
        return "research_jobs"
    if "evidence_extractor" in operation:
        return "evidence_extractor"
    if operation.startswith("fact_checker"):
        return "fact_checker"
    if operation.startswith("synthesizer"):
        return "synthesizer"
    if operation.startswith("coverage_auditor"):
        return "coverage_auditor"
    if operation.startswith("patch_applicator"):
        return "patch_applicator"
    return ""


def apply_progress_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    stage = progress_stage_for_operation(str(event.get("operation") or ""))
    if not stage:
        return

    event_type = event.get("event")
    active_counts = state["active_counts"]
    if event_type == "started":
        active_counts[stage] = active_counts.get(stage, 0) + 1
        state["stage_started_at"].setdefault(stage, time.perf_counter())
        state["active_stage"] = stage
        state["last_event"] = event
        return

    if event_type in {"completed", "failed"}:
        active_counts[stage] = max(0, active_counts.get(stage, 0) - 1)
        if event.get("seconds") is not None:
            state["durations"][stage] = max(float(event.get("seconds") or 0), float(state["durations"].get(stage, 0) or 0))
        if active_counts[stage] == 0:
            state["stage_started_at"].pop(stage, None)
            if event_type == "failed":
                state["failed"].add(stage)
            else:
                state["completed"].add(stage)
        state["active_stage"] = next((key for key, count in active_counts.items() if count > 0), "")
        state["last_event"] = event


def render_live_progress(workflow_slot, activity_slot, live_state: dict[str, Any]) -> None:
    workflow_slot.empty()
    with workflow_slot.container():
        theme.workflow_panel(stage_rows(live_state=live_state), title="Pipeline running")

    active_stage = live_state.get("active_stage")
    activity_slot.empty()
    if not active_stage:
        with activity_slot.container():
            theme.stage_activity("Starting", "Preparing the pipeline and provider clients.")
        return
    label, _, _, running_summary = next(item for item in STAGE_DEFINITIONS if item[1] == active_stage)
    with activity_slot.container():
        theme.stage_activity(label, running_summary)


def load_demo_result() -> dict[str, Any]:
    path = Path(config.GOLDEN_RESULT_PATH)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("history", []).append({"mode": "demo_mode", "source": "cached_golden"})
        return data
    return fallback_demo_result()


def remember_run(result: dict[str, Any]) -> None:
    if not result:
        return
    history = list(st.session_state.get("run_history") or [])
    key = run_history_key(result)
    if any(item.get("key") == key for item in history):
        return
    history.insert(0, build_history_item(result, key))
    st.session_state["run_history"] = history[:12]


def run_history_key(result: dict[str, Any]) -> str:
    payload = {
        "question": result.get("research_question") or "",
        "summary": ((result.get("report_v2") or result.get("report") or {}).get("answer_summary") or "")[:500],
        "total": (result.get("timings") or {}).get("total"),
        "evidence": len(result.get("evidence_items") or []),
    }
    return str(hash(json.dumps(payload, sort_keys=True, default=str)))


def build_history_item(result: dict[str, Any], key: str) -> dict[str, Any]:
    report = result.get("report_v2") or result.get("report") or {}
    return {
        "key": key,
        "created_at": datetime.now().strftime("%b %d, %I:%M %p"),
        "question": result.get("research_question") or "Untitled research run",
        "summary": report.get("answer_summary") or "No answer summary available.",
        "evidence_count": len(result.get("evidence_items") or []),
        "source_count": len(result.get("fetched_sources") or []),
        "degraded": bool(result.get("degraded") or result.get("errors")),
        "result": result,
    }


def render_run_history(history: list[dict[str, Any]]) -> None:
    theme.section("RUNS", "Research history", number="10")
    if not history:
        st.caption("No completed research runs yet.")
        return
    for index, item in enumerate(history):
        with st.expander(f"{item['created_at']} - {theme.clean_display_text(item['question'])[:90]}", expanded=index == 0):
            st.markdown(f"**Prompt**  \n{theme.clean_display_text(item['question'])}")
            st.markdown(f"**Answer**  \n{theme.clean_display_text(item['summary'])}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Evidence", item["evidence_count"])
            c2.metric("Sources", item["source_count"])
            c3.metric("Status", "Review" if item["degraded"] else "Clean")
            if st.button("Open this run", key=f"open_history_{item['key']}"):
                st.session_state["result"] = item["result"]
                st.rerun()


def render_empty_state() -> None:
    theme.workflow_panel(stage_rows(), title="Pipeline stages")
    left, right = st.columns([0.48, 0.52], gap="small")
    with left:
        theme.empty_recent_runs()
    with right:
        theme.output_preview()
    theme.footer_note("Unsupported claims are blocked before final output.")


def render_pipeline(result: dict[str, Any]) -> None:
    report = result.get("report_v2") or result.get("report") or {}
    patch = result.get("coverage_patch") or {}
    ledger = result.get("fact_ledger") or {}

    left, center, right = st.columns([0.23, 0.56, 0.31], gap="small")
    with left:
        render_workflow_rail(result)
        render_jobs(result)
    with center:
        render_answer_workbench(result, report)
        render_evidence_strip(result)
        render_source_strip(result)
    with right:
        render_validation_inspector(result, report, ledger, patch)
        render_provider_metrics(result)
        render_export(result)


def render_workflow_rail(result: dict[str, Any]) -> None:
    theme.workflow_panel(stage_rows(result), title="Workflow")


def stage_rows(
    result: dict[str, Any] | None = None,
    *,
    running: bool = False,
    live_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result = result or {}
    timings = result.get("timings") or {}
    errors = result.get("errors") or []
    error_text = " ".join(str(item.get("stage", "")) for item in errors if isinstance(item, dict))
    rows = []
    for index, (label, key, description, running_summary) in enumerate(STAGE_DEFINITIONS):
        status = "waiting"
        summary = description
        if live_state:
            active_count = int((live_state.get("active_counts") or {}).get(key, 0) or 0)
            if active_count > 0:
                status = "running"
                summary = running_summary
                seconds = time.perf_counter() - float((live_state.get("stage_started_at") or {}).get(key, time.perf_counter()))
            elif key in (live_state.get("failed") or set()):
                status = "review"
                summary = "This stage reported a warning or failure signal."
                seconds = float((live_state.get("durations") or {}).get(key, 0) or 0)
            elif key in (live_state.get("completed") or set()):
                status = "done"
                summary = LIVE_COMPLETED_SUMMARIES.get(key, description)
                seconds = float((live_state.get("durations") or {}).get(key, 0) or 0)
            else:
                seconds = 0.0
        elif running:
            status = "running" if index == 0 else "waiting"
            summary = running_summary if index == 0 else description
            seconds = 0.0
        elif result:
            status = "done"
            summary = completed_stage_summary(key, result) or description
            if key in error_text or any(key in str(item) for item in errors):
                status = "review"
                summary = "This stage produced a warning or degraded signal; inspect telemetry for details."
            seconds = float(timings.get(key, 0) or 0)
        else:
            seconds = 0.0
        rows.append(
            {
                "label": label,
                "key": key,
                "description": summary,
                "status": status,
                "seconds": seconds,
            }
        )
    return rows


def completed_stage_summary(key: str, result: dict[str, Any]) -> str:
    if key == "planner":
        jobs = len((result.get("planner_precontext") or {}).get("research_jobs") or [])
        checklist = len((result.get("planner_precontext") or {}).get("coverage_checklist") or [])
        return f"Planned {jobs} research job(s) and {checklist} coverage target(s)."
    if key == "search":
        return f"Collected {len(result.get('search_headers') or [])} search result header(s)."
    if key == "research_jobs":
        return f"Fetched {len(result.get('fetched_sources') or [])} source(s) and prepared text for extraction."
    if key == "evidence_extractor":
        return f"Extracted {len(result.get('evidence_items') or [])} quote-grounded evidence item(s)."
    if key == "fact_checker":
        ledger = result.get("fact_ledger") or {}
        verified = len(ledger.get("verified_facts") or [])
        partial = len(ledger.get("partial_facts") or [])
        return f"Reconciled {verified} verified fact(s) and {partial} partial fact(s)."
    if key == "synthesizer":
        report = result.get("report_v2") or result.get("report") or {}
        return f"Drafted {len(report.get('sections') or [])} cited answer section(s)."
    if key == "coverage_auditor":
        patch = result.get("coverage_patch") or {}
        return f"Coverage score is {float(patch.get('coverage_score') or 0):.0%}."
    if key == "patch_applicator":
        patch = result.get("coverage_patch") or {}
        return f"Recorded {len(patch.get('patch_operations') or [])} patch operation(s)."
    return ""


def render_jobs(result: dict[str, Any]) -> None:
    summaries = result.get("job_summaries") or []
    if not summaries:
        return
    theme.section("ASYNC", "Research jobs", number="01")
    metrics = []
    for index, summary in enumerate(summaries[:2]):
        metrics.append(
            (
                f"Job {index + 1}",
                f"Research Job {index + 1}",
                (
                    f"{summary.get('search_header_count', 0)} headers / "
                    f"{summary.get('evidence_count', 0)} evidence / "
                    f"{summary.get('extraction_failure_count', 0)} failures"
                ),
            )
        )
    theme.metric_grid(metrics)


def render_answer_workbench(result: dict[str, Any], report: dict[str, Any]) -> None:
    theme.section("ANSWER", "Grounded answer", number="02")
    theme.grounded_answer(report)
    render_grounded_precontext(result.get("planner_precontext") or {})


def render_grounded_precontext(planner: dict[str, Any]) -> None:
    grounded = planner.get("grounded_precontext") if isinstance(planner, dict) else None
    if not grounded:
        return
    with st.expander("Grounded precontext", expanded=False):
        st.write(grounded.get("summary", "No grounded summary available."))
        for chunk in grounded.get("supporting_chunks", [])[:6]:
            title = chunk.get("title") or chunk.get("uri", "source")
            uri = chunk.get("uri", "")
            snippet = chunk.get("snippet", "")
            st.markdown(f"**[{title}]({uri})** - {snippet}")


def render_evidence_strip(result: dict[str, Any]) -> None:
    items = sorted(
        result.get("evidence_items") or [],
        key=lambda item: item.get("relevance_to_query") or 0,
        reverse=True,
    )
    theme.section("EVIDENCE", f"Evidence ({len(items)} items)", number="03")
    if not items:
        st.caption("No extracted evidence available.")
        return
    cols = st.columns(3)
    for index, item in enumerate(items[:6]):
        with cols[index % 3]:
            theme.quote_card(item)
    if len(items) > 6:
        with st.expander(f"View all evidence ({len(items)} items)"):
            for item in items[6:]:
                theme.quote_card(item)


def render_source_strip(result: dict[str, Any]) -> None:
    sources = result.get("fetched_sources") or []
    theme.section("SOURCES", f"Fetched sources ({len(sources)})", number="04")
    if not sources:
        st.caption("No fetched sources available.")
        return
    cols = st.columns(3)
    for index, source in enumerate(sources[:6]):
        with cols[index % 3]:
            theme.source_row(source)


def render_validation_inspector(
    result: dict[str, Any],
    report: dict[str, Any],
    ledger: dict[str, Any],
    patch: dict[str, Any],
) -> None:
    theme.section("VALIDATOR", "Run integrity", number="05")
    theme.validator_card(result)

    verified = ledger.get("verified_facts") or []
    partial = ledger.get("partial_facts") or []
    unsupported = ledger.get("unsupported_claims") or []
    total_facts = max(1, len(verified) + len(partial) + len(unsupported))
    coverage = patch.get("coverage_score")
    if coverage is None:
        coverage = len(verified) / total_facts
    confidence = report.get("confidence_score", 0)
    support_ratio = (len(verified) + 0.5 * len(partial)) / total_facts
    theme.quality_panel(
        [
            ("Coverage", float(coverage or 0)),
            ("Citation integrity", float(confidence or 0)),
            ("Support ratio", float(support_ratio)),
        ]
    )
    render_evidence_quality_summary(result)

    theme.section("FACT LEDGER", "Verified claims", number="06")
    ledger_rows = []
    for fact in verified[:4]:
        ledger_rows.append((fact.get("fact_id", "fact"), fact.get("claim", ""), "Verified"))
    for fact in partial[:2]:
        ledger_rows.append((fact.get("fact_id", "fact"), fact.get("claim", ""), "Partial"))
    for item in unsupported[:1]:
        ledger_rows.append((item.get("claim_id", "claim"), item.get("claim", str(item)), "Blocked"))
    if ledger_rows:
        theme.ledger_table(ledger_rows)
    else:
        st.caption("No facts available.")

    theme.section("PATCH DIFF", "Why patched", number="07")
    operations = patch.get("patch_operations") or []
    if operations:
        for operation in operations[:2]:
            theme.patch_card(operation)
    else:
        st.caption("No patch operations.")


def render_evidence_quality_summary(result: dict[str, Any]) -> None:
    summary = ((result.get("run_quality") or {}).get("evidence_quality_summary") or {})
    if not summary:
        return
    average = float(summary.get("average_evidence_fit") or 0)
    missing = summary.get("missing_requirements") or []
    weak = summary.get("weak_requirements") or []
    strong = summary.get("strong_requirements") or []
    st.caption(
        f"Evidence fit: {average:.0%} average, "
        f"{len(strong)} strong area(s), {len(weak)} weak area(s), {len(missing)} missing area(s)."
    )
    visible_gaps = [*weak[:2], *missing[:3]]
    if visible_gaps:
        with st.expander("Coverage watchlist", expanded=False):
            for gap in visible_gaps:
                target = theme.humanize(gap.get("target") or "overall")
                dimension = theme.humanize(gap.get("dimension") or "coverage")
                status = theme.humanize(gap.get("status") or "needs evidence")
                st.caption(f"{target} · {dimension} · {status}")


def render_provider_metrics(result: dict[str, Any]) -> None:
    theme.section("METRICS", "Provider telemetry", number="08")
    metrics = result.get("provider_metrics") or {}
    if not metrics:
        st.caption("No provider metrics available.")
        return
    llm_calls = metrics.get("llm_calls") or []
    theme.console(
        [
            (f"LLM calls: {metrics.get('llm_call_count', len(llm_calls))}", "ok"),
            (f"Search calls: {metrics.get('search_call_count', len(metrics.get('search_calls') or []))}", "info"),
            (f"Fetch calls: {metrics.get('fetch_call_count', len(metrics.get('fetch_calls') or []))}", "info"),
            (
                f"Reasoning truncations: {metrics.get('truncated_by_reasoning_count', 0)}",
                "warn" if metrics.get("truncated_by_reasoning_count") else "ok",
            ),
        ]
    )

def render_export(result: dict[str, Any]) -> None:
    theme.section("EXPORT", "JSON download", number="09")
    payload = json.dumps(result, indent=2)
    st.download_button(
        "Download JSON",
        data=payload,
        file_name="synapse_pipeline_result.json",
        mime="application/json",
        use_container_width=True,
    )


def render_live_tool_agent_panel(result: dict[str, Any]) -> None:
    try:
        from agents.live_tool_agent import LiveToolAgent
    except Exception as exc:
        st.caption(f"Live tool agent unavailable: {exc}")
        return

    theme.section("LIVE", "Ask the live agent", number="10")
    question = st.text_input("Follow-up question", key="live_tool_agent_question")
    if not st.button("Ask live agent", disabled=not question.strip()):
        return
    with st.spinner("Live tool agent thinking..."):
        try:
            agent = LiveToolAgent(pipeline_result=result)
            answer = asyncio.run(agent.ask(question.strip()))
            st.write(answer.get("text", ""))
            if answer.get("citations"):
                st.caption("Citations: " + ", ".join(answer["citations"][:4]))
            if answer.get("tool_calls"):
                with st.expander("Tool calls"):
                    st.write(f"{len(answer['tool_calls'])} tool call(s) recorded.")
        except Exception as exc:
            st.error(f"Live tool agent failed: {exc}")


def fallback_demo_result() -> dict[str, Any]:
    return {
        "research_question": DEMO_QUERY,
        "planner_precontext": {
            "original_query": DEMO_QUERY,
            "query_interpretation": "Compare evidence-grounded Gemini research agent approaches.",
            "precontext_claims": [],
            "research_jobs": [],
            "coverage_checklist": ["grounding", "evaluation", "demo feasibility"],
            "planner_confidence": 0.7,
        },
        "search_headers": [],
        "fetched_sources": [],
        "evidence_items": [],
        "fact_ledger": {
            "verified_facts": [],
            "partial_facts": [],
            "unsupported_claims": [],
            "contradictions": [],
        },
        "report": {},
        "report_v1": {},
        "report_v2": {
            "title": "Demo unavailable",
            "answer_summary": "Golden demo fixture was not found.",
            "sections": [],
            "confidence_score": 0,
            "confidence_breakdown": {},
        },
        "coverage_patch": {"coverage_score": 0, "patch_operations": []},
        "job_summaries": [],
        "timings": {},
        "token_usage": {},
        "provider_metrics": {},
        "degraded": True,
        "degraded_mode": True,
        "errors": [{"stage": "demo", "error": "golden fixture missing"}],
        "iterations": 1,
        "history": [{"mode": "fallback"}],
    }


if __name__ == "__main__":
    main()
