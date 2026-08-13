"""SYNAPSE interface system for the Streamlit demo.

This module owns the visual language and small HTML render helpers. The design
target is an audit cockpit: dense, dark, legible, and built around the evidence
chain rather than a generic dashboard.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any, Literal
from urllib.parse import urlparse

import streamlit as st


Tone = Literal["ok", "warn", "bad", "info", "muted"]


_LEGACY_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<style>
  :root {
    --bg: #07090d;
    --bg-2: #0b0f16;
    --panel: rgba(15, 20, 29, 0.86);
    --panel-2: rgba(18, 25, 36, 0.92);
    --line: rgba(148, 163, 184, 0.16);
    --line-strong: rgba(148, 163, 184, 0.28);
    --text: #edf2f7;
    --soft: #a9b4c4;
    --muted: #687589;
    --cyan: #22d3ee;
    --green: #a3e635;
    --amber: #fbbf24;
    --red: #fb7185;
    --blue: #60a5fa;
    --shadow: 0 24px 80px rgba(0,0,0,0.42);
    --mono: "JetBrains Mono", "SF Mono", Consolas, monospace;
    --sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }

  html, body, .stApp, [class*="css"] {
    font-family: var(--sans);
    color: var(--text);
  }

  .stApp {
    background:
      radial-gradient(circle at 8% 0%, rgba(34, 211, 238, 0.14), transparent 28rem),
      radial-gradient(circle at 100% 18%, rgba(163, 230, 53, 0.08), transparent 30rem),
      linear-gradient(180deg, #07090d 0%, #0a0d13 50%, #07090d 100%);
  }

  .stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
      linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.014) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,0.7), transparent 78%);
    z-index: 0;
  }

  .block-container {
    max-width: 1500px;
    padding-top: 1rem !important;
    padding-bottom: 3rem;
  }

  div[data-testid="stAppViewContainer"] > header,
  header[data-testid="stHeader"],
  header.stAppHeader,
  .stAppHeader,
  [data-testid="stToolbar"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    visibility: hidden !important;
  }

  [data-testid="stDecoration"] {
    display: none !important;
  }

  div[data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
  }

  h1, h2, h3, h4, p, label, span, div {
    letter-spacing: 0;
  }

  section[data-testid="stSidebar"] {
    background: rgba(8, 11, 17, 0.97);
    border-right: 1px solid var(--line);
  }

  section[data-testid="stSidebar"] > div {
    padding-top: 1rem !important;
  }

  section[data-testid="stSidebar"] * {
    color: var(--soft);
  }

  [data-testid="stSidebar"] .stButton > button {
    width: 100%;
  }

  [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: rgba(96,165,250,0.48) !important;
    border-radius: 12px !important;
    background: linear-gradient(180deg, rgba(14,19,28,0.86), rgba(8,12,18,0.9)) !important;
    box-shadow: 0 18px 64px rgba(37,99,235,0.12);
  }

  .syn-nav {
    display: grid;
    gap: 8px;
    margin: 18px 0;
  }

  .syn-nav-item {
    display: grid;
    grid-template-columns: 22px 1fr auto;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    color: var(--soft);
    font-size: 13px;
  }

  .syn-nav-item.active {
    background: linear-gradient(90deg, rgba(96,165,250,0.22), rgba(96,165,250,0.06));
    border: 1px solid rgba(96,165,250,0.22);
    color: var(--text);
  }

  .syn-nav-icon {
    width: 20px;
    height: 20px;
    display: grid;
    place-items: center;
    color: var(--blue);
  }

  .syn-icon {
    width: 18px;
    height: 18px;
    display: block;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
    fill: none;
  }

  .syn-icon-lg {
    width: 38px;
    height: 38px;
  }

  .syn-nav-count {
    min-width: 24px;
    height: 24px;
    display: grid;
    place-items: center;
    border-radius: 999px;
    background: rgba(148,163,184,0.12);
    color: var(--soft);
    font-family: var(--mono);
    font-size: 10px;
  }

  .stTextArea textarea,
  .stTextInput input {
    background: rgba(7, 10, 16, 0.86) !important;
    border: 1px solid var(--line-strong) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: var(--sans) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
  }

  .stTextArea textarea {
    min-height: 106px;
    font-size: 15px !important;
    line-height: 1.55 !important;
  }

  .stTextArea textarea:focus,
  .stTextInput input:focus {
    border-color: rgba(34,211,238,0.72) !important;
    box-shadow: 0 0 0 1px rgba(34,211,238,0.22), 0 0 32px rgba(34,211,238,0.08) !important;
  }

  .stButton > button,
  .stDownloadButton > button {
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: rgba(15, 23, 42, 0.82);
    color: var(--text);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0;
    padding: 0.68rem 0.9rem;
    transition: transform 150ms ease, border-color 150ms ease, background 150ms ease;
  }

  .stButton > button:hover,
  .stDownloadButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(34, 211, 238, 0.7);
    background: rgba(15, 23, 42, 1);
    color: #ffffff;
  }

  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1fb6d6, #a3e635);
    color: #061014;
    border: 0;
  }

  [data-testid="stMetric"] {
    background: transparent;
    border: 0;
    padding: 0;
  }

  [data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-family: var(--mono) !important;
    font-size: 10px !important;
  }

  [data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-family: var(--sans) !important;
    font-size: 28px !important;
    font-weight: 750 !important;
  }

  [data-testid="stExpander"] {
    background: rgba(11, 15, 22, 0.72) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
  }

  .streamlit-expanderHeader,
  details summary {
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 11px !important;
  }

  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(11, 15, 22, 0.58);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 4px;
  }

  .stTabs [data-baseweb="tab"] {
    height: 36px;
    border-radius: 7px;
    color: var(--soft) !important;
    font-family: var(--mono) !important;
    font-size: 11px !important;
    padding: 0 14px !important;
  }

  .stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: rgba(34, 211, 238, 0.12);
    color: var(--text) !important;
  }

  [data-testid="stDataFrame"],
  [data-testid="stJson"],
  [data-testid="stCodeBlock"] {
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
  }

  [data-testid="stAlert"] {
    background: rgba(251, 191, 36, 0.08) !important;
    border: 1px solid rgba(251, 191, 36, 0.24);
    border-radius: 8px;
    color: var(--text);
  }

  .syn-shell {
    display: grid;
    gap: 18px;
    animation: syn-rise 420ms ease both;
  }

  @keyframes syn-rise {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .syn-hero {
    position: relative;
    overflow: hidden;
    min-height: 260px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background:
      linear-gradient(125deg, rgba(8, 12, 18, 0.96), rgba(13, 18, 28, 0.88)),
      radial-gradient(circle at 80% 20%, rgba(34, 211, 238, 0.22), transparent 24rem);
    box-shadow: var(--shadow);
    padding: 30px;
  }

  .syn-hero::after {
    content: "";
    position: absolute;
    inset: auto 0 0 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--cyan), var(--green), transparent);
    opacity: 0.85;
  }

  .syn-orbit {
    position: absolute;
    right: 34px;
    top: 30px;
    width: min(38vw, 480px);
    height: 200px;
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 999px;
    transform: rotate(-7deg);
    opacity: 0.7;
  }

  .syn-orbit::before,
  .syn-orbit::after {
    content: "";
    position: absolute;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: var(--green);
    box-shadow: 0 0 24px rgba(163,230,53,0.8);
  }

  .syn-orbit::before { left: 44px; top: 42px; }
  .syn-orbit::after { right: 76px; bottom: 34px; background: var(--cyan); box-shadow: 0 0 24px rgba(34,211,238,0.8); }

  .syn-kicker {
    font-family: var(--mono);
    color: var(--cyan);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  .syn-title {
    margin: 18px 0 12px;
    max-width: 880px;
    font-size: clamp(54px, 8vw, 104px);
    line-height: 0.92;
    font-weight: 850;
    color: var(--text);
  }

  .syn-title span {
    color: var(--green);
  }

  .syn-lede {
    max-width: 760px;
    color: var(--soft);
    font-size: 17px;
    line-height: 1.65;
    margin: 0;
  }

  .syn-brand-row {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin-top: 24px;
  }

  .syn-panel {
    border: 1px solid var(--line);
    background: var(--panel);
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.18);
  }

  .syn-panel.tight { padding: 13px 14px; }

  .syn-workbench-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 20px;
    padding: 18px 0 26px;
  }

  .syn-query-title {
    color: var(--text);
    font-size: clamp(31px, 3.2vw, 46px);
    font-weight: 800;
    line-height: 1.05;
    max-width: 900px;
    margin: 0 0 10px;
  }

  .syn-query-subtitle {
    color: var(--soft);
    font-size: 16px;
    line-height: 1.45;
  }

  .syn-utility-button {
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    padding: 10px 13px;
    color: var(--soft);
    font-size: 12px;
    font-family: var(--mono);
    white-space: nowrap;
  }

  .syn-empty-panel {
    min-height: 210px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(13,18,26,0.7);
    padding: 18px;
  }

  .syn-empty-center {
    min-height: 128px;
    display: grid;
    place-items: center;
    text-align: center;
    color: var(--muted);
    font-size: 13px;
  }

  .syn-output-row {
    display: grid;
    grid-template-columns: 30px 1fr 1.2fr;
    gap: 12px;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid var(--line);
    color: var(--soft);
    font-size: 13px;
  }

  .syn-output-row:last-child { border-bottom: 0; }

  .syn-output-icon {
    width: 26px;
    height: 26px;
    border-radius: 7px;
    display: grid;
    place-items: center;
    background: rgba(96,165,250,0.14);
    color: var(--blue);
  }

  .syn-output-name {
    color: var(--text);
    font-weight: 650;
  }

  .syn-status-card {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: rgba(13,18,26,0.72);
    padding: 13px;
    color: var(--soft);
    font-size: 12px;
  }

  .syn-status-dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 999px;
    margin-right: 8px;
    background: var(--green);
    box-shadow: 0 0 14px rgba(163,230,53,0.6);
  }

  .syn-footer-note {
    margin-top: 18px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
    color: var(--muted);
    text-align: center;
    font-size: 12px;
  }

  .syn-workflow {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(13, 18, 26, 0.84);
    padding: 15px;
    margin: 10px 0 16px;
  }

  .syn-workflow-title,
  .syn-card-title {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    align-items: center;
    margin-bottom: 12px;
    color: var(--text);
    font-weight: 750;
    font-size: 13px;
    text-transform: uppercase;
    font-family: var(--mono);
  }

  .syn-step {
    display: grid;
    grid-template-columns: 24px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: start;
    min-height: 54px;
    padding: 9px 0;
    border-top: 1px solid var(--line);
    color: var(--soft);
    font-size: 13px;
  }

  .syn-step:first-of-type {
    border-top: 0;
  }

  .syn-step-name {
    color: var(--text);
    font-weight: 700;
    line-height: 1.25;
  }

  .syn-step-desc {
    color: var(--muted);
    font-size: 11px;
    line-height: 1.45;
    margin-top: 3px;
  }

  .syn-dot {
    width: 22px;
    height: 22px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    background: rgba(148,163,184,0.12);
    color: var(--muted);
  }

  .syn-dot.done {
    background: rgba(163,230,53,0.18);
    color: var(--green);
  }

  .syn-dot.running {
    background: rgba(96,165,250,0.18);
    color: var(--blue);
    position: relative;
    animation: syn-pulse 1.2s ease-in-out infinite;
  }

  .syn-dot.review {
    background: rgba(251,191,36,0.16);
    color: var(--amber);
  }

  .syn-dot.running::after {
    content: "";
    position: absolute;
    inset: -5px;
    border: 1px solid rgba(96,165,250,0.45);
    border-radius: 999px;
    animation: syn-ring 1.2s ease-out infinite;
  }

  @keyframes syn-pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
  }

  @keyframes syn-ring {
    from { opacity: 0.85; transform: scale(0.75); }
    to { opacity: 0; transform: scale(1.35); }
  }

  .syn-step-time {
    color: var(--muted);
    font-family: var(--mono);
    font-size: 10px;
    white-space: nowrap;
    padding-top: 2px;
  }

  .syn-activity {
    display: grid;
    grid-template-columns: 22px 1fr;
    gap: 10px;
    align-items: center;
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 10px;
    background: rgba(96,165,250,0.08);
    padding: 11px 12px;
    margin: 10px 0 14px;
    color: var(--soft);
    font-size: 12px;
  }

  .syn-activity-title {
    color: var(--text);
    font-weight: 750;
    margin-bottom: 2px;
  }

  .syn-answer {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(13, 18, 26, 0.82);
    overflow: hidden;
  }

  .syn-answer-summary {
    padding: 16px;
    color: var(--text);
    font-size: 16px;
    line-height: 1.55;
    border-bottom: 1px solid var(--line);
  }

  .syn-answer-section {
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 16px;
    padding: 15px 16px;
    border-bottom: 1px solid var(--line);
  }

  .syn-answer-section:last-child { border-bottom: 0; }

  .syn-answer-section h3 {
    margin: 0;
    color: var(--text);
    font-size: 14px;
    line-height: 1.35;
  }

  .syn-answer-section p {
    margin: 0;
    color: var(--soft);
    font-size: 13px;
    line-height: 1.58;
  }

  .syn-source-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .syn-panel-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 13px;
  }

  .syn-panel-title h2,
  .syn-panel-title h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 750;
    color: var(--text);
  }

  .syn-panel-title .eyebrow {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--muted);
  }

  .syn-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-height: 24px;
    padding: 4px 9px;
    border-radius: 999px;
    border: 1px solid var(--line);
    color: var(--soft);
    background: rgba(15,23,42,0.72);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
  }

  .syn-chip::before {
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: var(--blue);
  }

  .syn-chip.ok { border-color: rgba(163,230,53,0.26); color: #d9f99d; }
  .syn-chip.ok::before { background: var(--green); box-shadow: 0 0 12px rgba(163,230,53,0.78); }
  .syn-chip.warn { border-color: rgba(251,191,36,0.28); color: #fde68a; }
  .syn-chip.warn::before { background: var(--amber); }
  .syn-chip.bad { border-color: rgba(251,113,133,0.34); color: #fecdd3; }
  .syn-chip.bad::before { background: var(--red); }
  .syn-chip.muted { color: var(--muted); }
  .syn-chip.muted::before { background: var(--muted); }

  .syn-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .syn-metric {
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 13px 14px;
    background: linear-gradient(180deg, rgba(18,25,36,0.92), rgba(12,16,24,0.9));
  }

  .syn-metric .label {
    font-family: var(--mono);
    color: var(--muted);
    font-size: 10px;
    margin-bottom: 7px;
  }

  .syn-metric .value {
    color: var(--text);
    font-size: 25px;
    font-weight: 800;
    line-height: 1;
  }

  .syn-metric .hint {
    color: var(--muted);
    font-size: 11px;
    margin-top: 8px;
  }

  .syn-stage-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 8px;
  }

  .syn-stage {
    position: relative;
    min-height: 96px;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 12px;
    background: rgba(7,10,16,0.62);
  }

  .syn-stage .idx {
    font-family: var(--mono);
    color: var(--green);
    font-size: 10px;
  }

  .syn-stage .name {
    margin-top: 13px;
    color: var(--text);
    font-weight: 750;
    font-size: 13px;
  }

  .syn-stage .time {
    margin-top: 5px;
    color: var(--muted);
    font-family: var(--mono);
    font-size: 10px;
  }

  .syn-stage::after {
    content: "";
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 10px;
    height: 2px;
    border-radius: 99px;
    background: linear-gradient(90deg, var(--cyan), var(--green));
    opacity: 0.68;
  }

  .syn-quote-card,
  .syn-fact-row,
  .syn-source-row,
  .syn-patch {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: rgba(7,10,16,0.58);
    padding: 14px;
    margin: 10px 0;
  }

  .syn-quote-card,
  .syn-source-row {
    transition: border-color 150ms ease, transform 150ms ease, background 150ms ease;
  }

  .syn-quote-card:hover,
  .syn-source-row:hover {
    transform: translateY(-1px);
    border-color: rgba(96,165,250,0.42);
    background: rgba(12,18,28,0.9);
  }

  .syn-card-head {
    display: grid;
    grid-template-columns: 34px 1fr;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
  }

  .syn-favicon {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.05);
    padding: 5px;
  }

  .syn-favicon .syn-icon {
    width: 18px;
    height: 18px;
    color: var(--muted);
  }

  .syn-domain {
    color: var(--text);
    font-weight: 650;
    font-size: 13px;
    line-height: 1.25;
  }

  .syn-quote-card .quote {
    color: var(--text);
    font-size: 15px;
    line-height: 1.58;
    margin: 10px 0 12px;
  }

  .syn-quote-card .claim,
  .syn-fact-row .claim {
    color: var(--soft);
    font-size: 13px;
    line-height: 1.5;
  }

  .syn-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .syn-url {
    color: var(--muted);
    font-family: var(--mono);
    font-size: 10px;
    word-break: break-all;
  }

  .syn-report {
    border-left: 2px solid var(--cyan);
    padding-left: 16px;
  }

  .syn-report-summary {
    color: var(--text);
    font-size: 18px;
    line-height: 1.65;
    font-weight: 500;
  }

  .syn-section-body {
    color: var(--soft);
    line-height: 1.64;
    font-size: 14px;
  }

  .syn-patch .before,
  .syn-patch .after {
    border-radius: 8px;
    padding: 10px 12px;
    margin-top: 8px;
    font-size: 13px;
    line-height: 1.55;
  }

  .syn-patch .before {
    color: #fecdd3;
    background: rgba(251,113,133,0.08);
    border: 1px solid rgba(251,113,133,0.18);
  }

  .syn-patch .after {
    color: #dcfce7;
    background: rgba(163,230,53,0.08);
    border: 1px solid rgba(163,230,53,0.18);
  }

  .syn-console {
    background: #05070b;
    border: 1px solid rgba(34,211,238,0.22);
    border-radius: 10px;
    padding: 14px;
    font-family: var(--mono);
    color: #cbd5e1;
    font-size: 12px;
    line-height: 1.7;
    box-shadow: inset 0 0 42px rgba(34,211,238,0.045);
  }

  .syn-console .ok { color: var(--green); }
  .syn-console .warn { color: var(--amber); }

  .syn-validator {
    border: 1px solid rgba(163,230,53,0.22);
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(34,197,94,0.2), rgba(9,13,20,0.94) 72%);
    padding: 16px;
    margin-bottom: 12px;
  }

  .syn-validator.bad {
    border-color: rgba(251,113,133,0.32);
    background: linear-gradient(135deg, rgba(251,113,133,0.18), rgba(9,13,20,0.94) 72%);
  }

  .syn-validator-main {
    display: grid;
    grid-template-columns: 42px 1fr;
    gap: 12px;
    align-items: center;
  }

  .syn-validator-mark {
    width: 42px;
    height: 42px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    background: var(--green);
    color: #07120c;
    font-size: 24px;
    font-weight: 800;
  }

  .syn-validator.bad .syn-validator-mark {
    background: var(--red);
    color: #19070b;
  }

  .syn-validator-title {
    color: #d9f99d;
    font-weight: 760;
    font-size: 16px;
    line-height: 1.25;
  }

  .syn-validator-sub {
    color: var(--soft);
    font-size: 12px;
    margin-top: 3px;
  }

  .syn-quality-row {
    display: grid;
    grid-template-columns: 1fr 48px;
    gap: 10px;
    align-items: center;
    color: var(--soft);
    font-size: 12px;
    margin: 10px 0;
  }

  .syn-bar {
    height: 7px;
    border-radius: 999px;
    overflow: hidden;
    background: rgba(148,163,184,0.14);
    margin-top: 5px;
  }

  .syn-bar > span {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, var(--green), var(--amber));
  }

  .syn-ledger-mini {
    border: 1px solid var(--line);
    border-radius: 10px;
    overflow: hidden;
    font-size: 12px;
  }

  .syn-ledger-line {
    display: grid;
    grid-template-columns: 82px 1fr 72px;
    gap: 8px;
    padding: 9px 10px;
    border-bottom: 1px solid var(--line);
    color: var(--soft);
  }

  .syn-ledger-line:last-child { border-bottom: 0; }
  .syn-ledger-line .id { color: var(--blue); font-family: var(--mono); }
  .syn-ledger-line .status.ok { color: var(--green); }
  .syn-ledger-line .status.warn { color: var(--amber); }
  .syn-ledger-line .status.bad { color: var(--red); }

  .syn-sidebar-logo {
    font-size: 22px;
    font-weight: 850;
    color: var(--text);
    letter-spacing: -0.04em;
  }

  .syn-sidebar-logo span { color: var(--green); }

  .syn-sidebar-note {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.5;
    margin: 7px 0 18px;
  }

  @media (max-width: 960px) {
    .syn-metric-grid,
    .syn-stage-grid,
    .syn-source-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .syn-orbit { display: none; }
    .syn-answer-section { grid-template-columns: 1fr; }
  }

  @media (max-width: 640px) {
    .syn-metric-grid,
    .syn-stage-grid,
    .syn-source-grid {
      grid-template-columns: 1fr;
    }
    .syn-hero { padding: 22px; }
  }
</style>
"""


_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap" rel="stylesheet">

<style>
  :root {
    --paper: #f3f0e8;
    --surface: #fbfaf6;
    --ink: #171716;
    --text: #171716;
    --soft: #68675f;
    --muted: #85837b;
    --line: #d6d1c5;
    --line-strong: #bdb7aa;
    --accent: #3157d5;
    --accent-soft: #e3e9ff;
    --blue: #3157d5;
    --cyan: #3157d5;
    --ok: #25724b;
    --green: #25724b;
    --warn: #a15f15;
    --amber: #a15f15;
    --bad: #a33a32;
    --red: #a33a32;
    --serif: "Newsreader", Georgia, serif;
    --sans: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --mono: "JetBrains Mono", Consolas, monospace;
  }

  html, body, .stApp, [class*="css"] {
    color: var(--ink);
    font-family: var(--sans);
  }

  .stApp { background: var(--paper); }

  .block-container {
    max-width: 1480px;
    padding: 1.3rem clamp(1rem, 3.4vw, 3.8rem) 5rem;
    animation: syn-enter 320ms ease-out both;
  }

  div[data-testid="stAppViewContainer"] > header,
  header[data-testid="stHeader"],
  header.stAppHeader,
  .stAppHeader,
  [data-testid="stToolbar"],
  [data-testid="stDecoration"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    visibility: hidden !important;
  }

  div[data-testid="stAppViewContainer"] { padding-top: 0 !important; }

  section[data-testid="stSidebar"] {
    background: #ebe7dc;
    border-right: 1px solid var(--line);
  }

  section[data-testid="stSidebar"] > div { padding-top: 1.4rem !important; }
  section[data-testid="stSidebar"] * { color: var(--soft); }
  [data-testid="stSidebar"] .stButton > button { width: 100%; }

  h1, h2, h3, h4, p, label, span, div { letter-spacing: 0; }

  .stTextArea textarea,
  .stTextInput input {
    background: transparent !important;
    border: 0 !important;
    color: var(--ink) !important;
    border-radius: 0 !important;
    font-family: var(--sans) !important;
    box-shadow: none !important;
  }

  .stTextArea textarea {
    min-height: 94px;
    font-size: 17px !important;
    line-height: 1.55 !important;
  }

  .stTextArea textarea:focus,
  .stTextInput input:focus { box-shadow: none !important; }

  [data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--line) !important;
    border-radius: 0 !important;
    background: var(--surface) !important;
    box-shadow: 0 16px 44px rgba(44, 40, 28, 0.05);
  }

  .stButton > button,
  .stDownloadButton > button {
    border-radius: 5px;
    border: 1px solid var(--line-strong);
    background: var(--surface);
    color: var(--ink);
    font-family: var(--sans);
    font-size: 12px;
    font-weight: 600;
    padding: 0.68rem 0.95rem;
    transition: transform 150ms ease, border-color 150ms ease, background 150ms ease;
  }

  .stButton > button:hover,
  .stDownloadButton > button:hover {
    transform: translateY(-1px);
    border-color: var(--accent);
    background: #ffffff;
    color: var(--ink);
  }

  .stButton > button[kind="primary"] {
    background: var(--accent);
    border-color: var(--accent);
    color: #ffffff;
    box-shadow: 0 6px 15px rgba(49, 87, 213, 0.18);
  }

  [data-testid="stMetric"] { background: transparent; border: 0; padding: 0; }
  [data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 10px !important; }
  [data-testid="stMetricValue"] { color: var(--ink) !important; font-family: var(--serif) !important; }

  [data-testid="stExpander"] {
    background: transparent !important;
    border: 0 !important;
    border-top: 1px solid var(--line) !important;
    border-radius: 0 !important;
  }

  .streamlit-expanderHeader, details summary { color: var(--ink) !important; font-size: 12px !important; }

  .stTabs [data-baseweb="tab-list"] {
    gap: 22px;
    background: transparent;
    border-bottom: 1px solid var(--line);
  }

  .stTabs [data-baseweb="tab"] {
    height: 42px;
    color: var(--muted) !important;
    font-family: var(--sans) !important;
    font-size: 12px !important;
    padding: 0 !important;
  }

  .stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--ink) !important; }
  .stTabs [data-baseweb="tab-highlight"] { background: var(--accent) !important; }

  [data-testid="stDataFrame"], [data-testid="stJson"], [data-testid="stCodeBlock"] {
    border: 1px solid var(--line);
    border-radius: 0;
  }

  .syn-wordmark,
  .syn-sidebar-logo {
    display: inline-flex;
    align-items: center;
    color: var(--ink) !important;
    font-family: var(--sans);
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.15em;
    white-space: nowrap;
  }

  .syn-logo-slash {
    display: inline-block;
    width: 18px;
    height: 3px;
    margin: 0 4px 1px 0;
    background: var(--accent);
    transform: rotate(-56deg);
    transform-origin: center;
  }

  .syn-sidebar-note {
    color: var(--muted) !important;
    font-size: 11px;
    line-height: 1.55;
    margin: 9px 0 20px;
  }

  .syn-nav { display: grid; gap: 4px; margin: 20px 0; }
  .syn-nav-item {
    display: grid;
    grid-template-columns: 22px 1fr auto;
    align-items: center;
    gap: 10px;
    padding: 9px 10px;
    border-radius: 5px;
    color: var(--soft);
    font-size: 12px;
  }
  .syn-nav-item.active { background: var(--surface); color: var(--ink); }
  .syn-nav-icon { width: 19px; height: 19px; color: var(--muted); }
  .syn-nav-count { color: var(--muted); font: 10px var(--mono); }
  .syn-icon { width: 17px; height: 17px; display: block; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .syn-icon-lg { width: 34px; height: 34px; }

  .syn-status-card {
    border-top: 1px solid var(--line);
    padding: 15px 2px 0;
    color: var(--soft);
    font-size: 11px;
  }
  .syn-status-dot { display: inline-block; width: 6px; height: 6px; margin-right: 7px; border-radius: 50%; background: var(--ok); }

  .syn-workbench-head {
    display: flex;
    justify-content: space-between;
    align-items: end;
    padding: 1.2rem 0 1.8rem;
  }
  .syn-query-title {
    color: var(--ink);
    font-family: var(--serif);
    font-size: clamp(42px, 5vw, 68px);
    font-weight: 600;
    letter-spacing: -0.045em;
    line-height: 0.98;
  }
  .syn-query-subtitle { max-width: 680px; margin-top: 12px; color: var(--soft); font-size: 14px; line-height: 1.6; }
  .syn-kicker, .eyebrow { color: var(--accent); font: 700 10px/1.3 var(--sans); letter-spacing: 0.12em; text-transform: uppercase; }

  .syn-panel-title {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 18px;
    padding: 26px 0 15px;
    border-bottom: 1px solid var(--line);
  }
  .syn-panel-title h2 { margin: 5px 0 0; color: var(--ink); font-family: var(--serif); font-size: 28px; font-weight: 600; letter-spacing: -0.025em; }
  .syn-panel, .syn-panel.tight { background: transparent; border: 0; padding: 0; }

  .syn-metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
  .syn-metric { padding: 15px 16px 15px 0; }
  .syn-metric:nth-child(even) { border-left: 1px solid var(--line); padding-left: 16px; }
  .syn-metric .label { color: var(--muted); font: 700 9px var(--sans); text-transform: uppercase; letter-spacing: 0.1em; }
  .syn-metric .value { margin: 5px 0 3px; color: var(--ink); font-family: var(--serif); font-size: 21px; }
  .syn-metric .hint { color: var(--soft); font-size: 10px; line-height: 1.5; }

  .syn-workflow { border-top: 1px solid var(--line); }
  .syn-workflow-title { display: flex; justify-content: space-between; padding: 14px 0; color: var(--ink); font-size: 12px; font-weight: 700; }
  .syn-step { display: grid; grid-template-columns: 20px 1fr auto; gap: 9px; padding: 11px 0; border-top: 1px solid rgba(214, 209, 197, 0.7); }
  .syn-dot { color: var(--muted); }
  .syn-dot.done { color: var(--ok); }
  .syn-dot.running { color: var(--accent); }
  .syn-dot.review { color: var(--warn); }
  .syn-step-name { color: var(--ink); font-size: 11px; font-weight: 600; }
  .syn-step-desc { margin-top: 3px; color: var(--muted); font-size: 9px; line-height: 1.45; }
  .syn-step-time { color: var(--muted); font: 9px var(--mono); }

  .syn-activity { display: grid; grid-template-columns: 22px 1fr; gap: 10px; padding: 14px 0; color: var(--soft); font-size: 11px; }
  .syn-activity-title { color: var(--ink); font-weight: 600; }

  .syn-answer { padding-top: 4px; }
  .syn-answer-summary,
  .syn-report-summary {
    margin: 18px 0 28px;
    padding-left: 20px;
    border-left: 3px solid var(--accent);
    color: var(--ink);
    font-family: var(--serif);
    font-size: 22px;
    line-height: 1.45;
  }
  .syn-answer-section { display: grid; grid-template-columns: 1fr; gap: 8px; padding: 22px 0; border-top: 1px solid var(--line); }
  .syn-answer-section h3 { margin: 0; color: var(--ink); font-size: 17px; font-weight: 600; }
  .syn-answer-section p, .syn-section-body { margin: 0; color: #55544f; font-size: 14px; line-height: 1.72; }

  .syn-meta { display: flex; flex-wrap: wrap; gap: 6px; }
  .syn-chip { padding: 3px 6px; border: 1px solid var(--line); border-radius: 99px; color: var(--muted); font: 8px var(--mono); text-transform: uppercase; }
  .syn-chip.ok { color: var(--ok); border-color: #b9d2c2; background: #edf6ef; }
  .syn-chip.warn { color: var(--warn); border-color: #ddc59e; background: #faf2e4; }
  .syn-chip.bad { color: var(--bad); border-color: #dfb4af; background: #faecea; }
  .syn-chip.info { color: var(--accent); border-color: #c4d0ff; background: var(--accent-soft); }

  .syn-quote-card, .syn-source-row, .syn-fact-row, .syn-patch {
    padding: 17px 0;
    border-top: 1px solid var(--line);
    background: transparent;
    transition: background 150ms ease, padding 150ms ease;
  }
  .syn-quote-card:hover, .syn-source-row:hover { margin: 0 -8px; padding-right: 8px; padding-left: 8px; background: #f7f4ed; }
  .syn-card-head { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; }
  .syn-favicon { width: 20px; height: 20px; object-fit: contain; }
  .syn-domain { color: var(--ink); font-size: 11px; font-weight: 600; }
  .syn-url { margin-top: 7px; color: var(--muted); font: 9px/1.5 var(--mono); word-break: break-word; }
  .syn-quote-card .quote { margin: 12px 0 8px; color: var(--ink); font-family: var(--serif); font-size: 16px; line-height: 1.5; }
  .syn-quote-card .claim, .syn-fact-row .claim, .syn-patch .claim { color: var(--soft); font-size: 11px; line-height: 1.55; }
  .syn-patch .before, .syn-patch .after { margin-top: 9px; padding: 10px; color: var(--soft); font: 10px/1.5 var(--mono); }
  .syn-patch .before { border-left: 2px solid var(--bad); background: #faecea; }
  .syn-patch .after { border-left: 2px solid var(--ok); background: #edf6ef; }

  .syn-validator { margin: 16px 0; padding: 16px; border-top: 2px solid var(--ok); background: #edf6ef; }
  .syn-validator.bad { border-color: var(--bad); background: #faecea; }
  .syn-validator-main { display: flex; gap: 11px; align-items: center; }
  .syn-validator-mark { color: var(--ok); }
  .syn-validator.bad .syn-validator-mark { color: var(--bad); }
  .syn-validator-title { color: var(--ink); font-size: 12px; font-weight: 700; }
  .syn-validator-sub { margin-top: 3px; color: var(--soft); font-size: 10px; }

  .syn-quality-row { display: grid; grid-template-columns: 1fr 42px; gap: 10px; margin: 10px 0; color: var(--soft); font-size: 10px; }
  .syn-bar { height: 3px; margin-top: 5px; background: var(--line); overflow: hidden; }
  .syn-bar > span { display: block; height: 100%; background: var(--accent); }
  .syn-ledger-mini { border-top: 1px solid var(--line); }
  .syn-ledger-line { display: grid; grid-template-columns: 66px 1fr 58px; gap: 8px; padding: 10px 0; border-bottom: 1px solid var(--line); color: var(--soft); font-size: 10px; }
  .syn-ledger-line .id { color: var(--accent); font-family: var(--mono); }
  .syn-ledger-line .status.ok { color: var(--ok); }
  .syn-ledger-line .status.warn { color: var(--warn); }
  .syn-ledger-line .status.bad { color: var(--bad); }

  .syn-console { padding: 13px 0; border-top: 1px solid var(--line); color: var(--soft); font: 9px/1.7 var(--mono); }
  .syn-console .ok { color: var(--ok); }
  .syn-console .warn { color: var(--warn); }
  .syn-empty-panel { min-height: 220px; border-top: 1px solid var(--line); padding: 18px 0; }
  .syn-card-title { color: var(--ink); font-size: 12px; font-weight: 700; }
  .syn-empty-center { min-height: 160px; display: grid; place-items: center; text-align: center; color: var(--muted); font-size: 11px; }
  .syn-output-row { display: grid; grid-template-columns: 28px 90px 1fr; gap: 9px; padding: 12px 0; border-top: 1px solid var(--line); color: var(--muted); font-size: 10px; }
  .syn-output-icon { color: var(--accent); }
  .syn-output-name { color: var(--ink); font-weight: 600; }
  .syn-footer-note { margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--line); color: var(--muted); font-size: 10px; }
  .syn-stage-grid, .syn-source-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
  .syn-stage { padding: 12px 0; border-top: 1px solid var(--line); }
  .syn-stage .idx, .syn-stage .time { color: var(--muted); font: 9px var(--mono); }
  .syn-stage .name { margin: 4px 0; color: var(--ink); font-size: 12px; }

  @keyframes syn-enter {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 960px) {
    .syn-metric-grid, .syn-stage-grid, .syn-source-grid { grid-template-columns: 1fr; }
    .syn-metric:nth-child(even) { border-left: 0; padding-left: 0; }
  }

  @media (max-width: 640px) {
    .block-container { padding: 1rem 1rem 3rem; }
    .syn-query-title { font-size: 40px; }
    .syn-wordmark, .syn-sidebar-logo { font-size: 17px; }
    .syn-logo-slash { width: 15px; }
    .syn-panel-title h2 { font-size: 24px; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def esc(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def humanize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.strip()
    if not text:
        return ""
    replacements = {
        "llm": "LLM",
        "url": "URL",
        "http": "HTTP",
        "https": "HTTPS",
        "api": "API",
        "json": "JSON",
        "id": "ID",
    }
    parts = (
        text.replace("-", "_")
        .replace("/", " ")
        .replace(".", " ")
        .replace("[", " ")
        .replace("]", " ")
        .split()
    )
    words: list[str] = []
    for part in parts:
        for word in part.split("_"):
            if not word:
                continue
            lower = word.lower()
            words.append(replacements.get(lower, word[:1].upper() + word[1:]))
    return " ".join(words)


def friendly_id(value: Any, prefix: str = "") -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return prefix or ""
    if prefix and text.lower() == prefix.lower():
        return prefix
    job_match = re.search(r"job[_-]([a-zA-Z])[_-](\d+)$", text)
    if job_match:
        return f"{prefix} {job_match.group(1).upper()}{int(job_match.group(2))}".strip()
    tail = text.split("_")[-1].split("-")[-1]
    if tail.isdigit():
        tail = str(int(tail))
    return f"{prefix} {tail}".strip() if prefix else humanize(text)


def friendly_refs(values: list[Any] | tuple[Any, ...] | None, prefix: str = "Fact") -> str:
    refs = [friendly_id(value, prefix) for value in (values or [])]
    return ", ".join(ref for ref in refs if ref)


def friendly_target(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return "Report"
    lower = text.lower()
    if "section" in lower:
        return "Answer Section"
    if "summary" in lower:
        return "Answer Summary"
    if "title" in lower:
        return "Title"
    return humanize(text)


def friendly_patch_refs(operation: dict[str, Any]) -> str:
    ref_groups = [
        ("fact_ids", "Fact"),
        ("contradiction_ids", "Contradiction"),
        ("result_ids", "Result"),
    ]
    for key, prefix in ref_groups:
        refs = operation.get(key) or []
        if refs:
            return friendly_refs(refs, prefix)
    return ""


_INLINE_ID_PATTERN = re.compile(
    r"\b(?P<prefix>fact|ev|evidence|claim|result|contradiction|section|edit)[A-Za-z0-9_-]*[_-][A-Za-z0-9_-]+\b",
    re.IGNORECASE,
)


def clean_display_text(value: Any) -> str:
    text = "" if value is None else str(value)

    def replace_id(match: re.Match[str]) -> str:
        raw = match.group(0)
        prefix = match.group("prefix").lower()
        display_prefix = {
            "fact": "Fact",
            "ev": "Evidence",
            "evidence": "Evidence",
            "claim": "Claim",
            "result": "Result",
            "contradiction": "Contradiction",
            "section": "Section",
            "edit": "Edit",
        }.get(prefix, "")
        return friendly_id(raw, display_prefix)

    return _INLINE_ID_PATTERN.sub(replace_id, text)


_LUCIDE_PATHS: dict[str, str] = {
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "archive": '<rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>',
    "book-open": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "circle": '<circle cx="12" cy="12" r="10"/>',
    "circle-alert": '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "file-search": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><circle cx="11.5" cy="14.5" r="2.5"/><path d="m13.3 16.3 2.2 2.2"/>',
    "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
    "git-compare": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M6 9v12"/><path d="m3 18 3 3 3-3"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 0 20"/><path d="M12 2a15.3 15.3 0 0 0 0 20"/>',
    "inbox": '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.7 4H7.3a2 2 0 0 0-1.8 1.1z"/>',
    "list-checks": '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
    "quote": '<path d="M3 21c3 0 7-1 7-8V5c0-1.25-.76-2-2-2H4c-1.25 0-2 .75-2 2v6c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.75-2-2-2h-4c-1.25 0-2 .75-2 2v6c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.68-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
}


def icon(name: str, *, cls: str = "syn-icon") -> str:
    body = _LUCIDE_PATHS.get(name, _LUCIDE_PATHS["file-text"])
    return (
        f'<svg class="{esc(cls)}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 24 24" aria-hidden="true">{body}</svg>'
    )


def domain_from_url(url: str) -> str:
    parsed = urlparse(url or "")
    return parsed.netloc.removeprefix("www.") or parsed.path.split("/")[0] or "source"


def favicon_url(url: str) -> str:
    domain = domain_from_url(url)
    if domain == "source":
        return ""
    return f"https://www.google.com/s2/favicons?domain={esc(domain)}&sz=64"


def favicon_img(url: str) -> str:
    src = favicon_url(url)
    if src:
        return f'<img class="syn-favicon" src="{src}" alt="">'
    return f'<div class="syn-favicon" aria-hidden="true">{icon("file-text")}</div>'


def chip(text: str, tone: Tone = "info") -> str:
    return f'<span class="syn-chip {tone}">{esc(text)}</span>'


def wordmark() -> str:
    return '<span class="syn-wordmark">SYN<span class="syn-logo-slash"></span>APSE</span>'


def chip_row(items: list[tuple[str, Tone]]) -> None:
    st.markdown(
        '<div class="syn-meta">' + "".join(chip(label, tone) for label, tone in items) + "</div>",
        unsafe_allow_html=True,
    )


def section_heading(title: str, eyebrow: str = "", right: str = "") -> None:
    st.markdown(
        f"""
        <div class="syn-panel-title" style="margin-top:18px;">
          <div>
            <div class="eyebrow">{esc(eyebrow)}</div>
            <h2>{esc(title)}</h2>
          </div>
          <div>{right}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, lede: str, chips: list[tuple[str, Tone]]) -> None:
    st.markdown(
        f"""
        <div class="syn-hero">
          <div class="syn-orbit"></div>
          <div class="syn-kicker">Evidence integrity system</div>
          <div class="syn-title">{esc(title)} <span>/</span></div>
          <p class="syn-lede">{esc(lede)}</p>
          <div class="syn-brand-row">{''.join(chip(label, tone) for label, tone in chips)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workbench_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="syn-workbench-head">
          <div>
            <div class="syn-query-title">{esc(title)}</div>
            <div class="syn-query-subtitle">{esc(subtitle)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav(evidence_count: int = 0) -> None:
    rows = [
        ("activity", "Runs", "", True),
        ("file-search", "Research", "", False),
        ("quote", "Evidence", str(evidence_count) if evidence_count else "", False),
        ("list-checks", "Fact Ledger", "", False),
        ("shield-check", "Validator", "", False),
    ]
    body = []
    for icon_name, label, count, active in rows:
        body.append(
            f'<div class="syn-nav-item {"active" if active else ""}">'
            f'<div class="syn-nav-icon">{icon(icon_name)}</div>'
            f"<div>{esc(label)}</div>"
            f'<div class="syn-nav-count">{esc(count)}</div>'
            "</div>"
        )
    st.markdown('<div class="syn-nav">' + "".join(body) + "</div>", unsafe_allow_html=True)


def status_card(title: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="syn-status-card">
          <div><span class="syn-status-dot"></span>{esc(title)}</div>
          <div style="margin-top:10px;color:var(--muted);">{esc(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_recent_runs() -> None:
    st.markdown(
        f"""
        <div class="syn-empty-panel">
          <div class="syn-card-title"><span>Recent Runs</span></div>
          <div class="syn-empty-center">
            <div>
              <div style="display:grid;place-items:center;margin-bottom:12px;color:var(--muted);">{icon("inbox", cls="syn-icon syn-icon-lg")}</div>
              <div style="color:var(--text);font-weight:650;margin-bottom:6px;">No runs yet</div>
              <div>Start your first research query to see runs here.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def output_preview() -> None:
    rows = [
        ("quote", "Evidence", "Cited, source-linked evidence cards."),
        ("list-checks", "Fact Ledger", "Verified facts with claim status."),
        ("git-compare", "Patch Diff", "Change summary with justifications."),
        ("shield-check", "Validator", "Checks that block unsupported claims."),
    ]
    body = ['<div class="syn-empty-panel"><div class="syn-card-title"><span>What SYNAPSE will produce</span></div>']
    for icon_name, name, desc in rows:
        body.append(
            '<div class="syn-output-row">'
            f'<div class="syn-output-icon">{icon(icon_name)}</div>'
            f'<div class="syn-output-name">{esc(name)}</div>'
            f'<div>{esc(desc)}</div>'
            "</div>"
        )
    body.append("</div>")
    st.markdown("".join(body), unsafe_allow_html=True)


def footer_note(text: str) -> None:
    st.markdown(f'<div class="syn-footer-note">{esc(text)}</div>', unsafe_allow_html=True)


def workflow_panel(stages: list[dict[str, Any]], title: str = "Workflow") -> None:
    status_icons = {
        "done": "circle-check",
        "running": "activity",
        "review": "circle-alert",
        "waiting": "circle",
    }
    body = []
    for stage in stages:
        status = str(stage.get("status") or "waiting")
        icon_name = status_icons.get(status, "circle")
        seconds = float(stage.get("seconds") or 0)
        time_text = f"{seconds:.2f}s" if status in {"done", "review"} else status
        body.append(
            f'<div class="syn-step"><div class="syn-dot {esc(status)}">'
            f'{icon(icon_name)}</div><div><div class="syn-step-name">{esc(stage.get("label", ""))}</div>'
            f'<div class="syn-step-desc">{esc(stage.get("description", ""))}</div></div>'
            f'<div class="syn-step-time">{esc(time_text)}</div></div>'
        )
    header = f'<div class="syn-workflow-title"><span>{esc(title)}</span><span>{icon("chevron-down")}</span></div>'
    st.html('<div class="syn-workflow">' + header + "".join(body) + "</div>")


def stage_activity(title: str, detail: str) -> None:
    st.html(
        '<div class="syn-activity">'
        f'<div class="syn-dot running">{icon("activity")}</div>'
        f'<div><div class="syn-activity-title">{esc(title)}</div><div>{esc(detail)}</div></div>'
        "</div>"
    )


def panel_start(title: str, eyebrow: str = "", right: str = "", tight: bool = False) -> None:
    cls = "syn-panel tight" if tight else "syn-panel"
    st.markdown(
        f"""
        <div class="{cls}">
          <div class="syn-panel-title">
            <div>
              <div class="eyebrow">{esc(eyebrow)}</div>
              <h2>{esc(title)}</h2>
            </div>
            <div>{right}</div>
          </div>
        """,
        unsafe_allow_html=True,
    )


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def metric_grid(metrics: list[tuple[str, str, str]]) -> None:
    body = []
    for label, value, hint in metrics:
        body.append(
            '<div class="syn-metric">'
            f'<div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div>'
            f'<div class="hint">{esc(hint)}</div>'
            "</div>"
        )
    st.markdown('<div class="syn-metric-grid">' + "".join(body) + "</div>", unsafe_allow_html=True)


def timeline(stages: list[tuple[str, str, float]]) -> None:
    body = []
    for index, (name, key, seconds) in enumerate(stages, start=1):
        body.append(
            '<div class="syn-stage">'
            f'<div class="idx">{index:02d} / {esc(humanize(key))}</div>'
            f'<div class="name">{esc(name)}</div>'
            f'<div class="time">{seconds:.2f}s</div>'
            "</div>"
        )
    st.markdown('<div class="syn-stage-grid">' + "".join(body) + "</div>", unsafe_allow_html=True)


def quote_card(item: dict[str, Any]) -> None:
    quote = item.get("source_quote") or ""
    claim = item.get("claim") or ""
    evidence_id = item.get("evidence_id") or "evidence"
    source_type = item.get("source_type") or "source"
    method = item.get("extraction_method") or "unknown"
    target = item.get("target") or ""
    dimension = item.get("dimension") or ""
    fit = item.get("evidence_fit_score")
    url = item.get("source_url") or ""
    quality = item.get("source_quality_score")
    domain = domain_from_url(url)
    st.markdown(
        f"""
        <div class="syn-quote-card">
          <div class="syn-card-head">
            {favicon_img(url)}
            <div>
              <div class="syn-domain">{esc(item.get("source_title") or domain)}</div>
              <div class="syn-url">{esc(domain)}</div>
            </div>
          </div>
          <div class="syn-meta">
            {chip(friendly_id(evidence_id, "Evidence"), "ok")}
            {chip(humanize(source_type), "info")}
            {chip(humanize(method), "muted")}
            {chip("Quality " + str(quality), "warn" if quality and quality < 0.55 else "ok")}
            {chip(humanize(target), "info") if target else ""}
            {chip(humanize(dimension), "muted") if dimension else ""}
            {chip("Fit " + str(round(float(fit), 2)), "warn" if fit and float(fit) < 0.55 else "ok") if fit is not None else ""}
          </div>
          <div class="quote">"{esc(clean_display_text(quote))}"</div>
          <div class="claim">{esc(clean_display_text(claim))}</div>
          <div class="syn-url">{esc(url)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fact_row(fact: dict[str, Any], status: str) -> None:
    tone: Tone = "ok" if status == "VERIFIED" else "warn"
    st.markdown(
        f"""
        <div class="syn-fact-row">
          <div class="syn-meta">
            {chip(humanize(status), tone)}
            {chip(friendly_id(fact.get("fact_id", "fact"), "Fact"), "info")}
            {chip("Confidence " + str(fact.get("confidence", "")), "muted")}
          </div>
          <div class="claim">{esc(clean_display_text(fact.get("claim", "")))}</div>
          <div class="syn-url">{esc(", ".join((fact.get("source_urls") or [])[:2]))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def source_row(source: dict[str, Any]) -> None:
    tone: Tone = "ok" if source.get("success") else "bad"
    url = source.get("url", "")
    domain = domain_from_url(url)
    st.markdown(
        f"""
        <div class="syn-source-row">
          <div class="syn-card-head">
            {favicon_img(url)}
            <div>
              <div class="syn-domain">{esc(source.get("title") or domain)}</div>
              <div class="syn-url">{esc(domain)}</div>
            </div>
          </div>
          <div class="syn-meta">
            {chip(humanize(source.get("fetch_status", "fetch")), tone)}
            {chip(humanize(source.get("source_type", "source")), "info")}
            {chip(str(len(source.get("text") or "")) + " chars", "muted")}
          </div>
          <div class="syn-url">{esc(url)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def report_summary(text: str) -> None:
    if not text:
        return
    st.markdown(
        f'<div class="syn-report"><div class="syn-report-summary">{esc(clean_display_text(text))}</div></div>',
        unsafe_allow_html=True,
    )


def report_section(section: dict[str, Any]) -> None:
    facts = friendly_refs(section.get("used_fact_ids") or [], "Fact")
    citations = ", ".join((section.get("citations") or [])[:2])
    st.markdown(
        f"""
        <div class="syn-quote-card">
          <div class="syn-meta">
            {chip(friendly_id(section.get("section_id", "section"), "Section"), "info")}
            {chip("Facts " + str(len(section.get("used_fact_ids") or [])), "ok")}
          </div>
          <h3 style="margin:12px 0 8px;font-size:17px;color:var(--text);">{esc(clean_display_text(section.get("heading", "Section")))}</h3>
          <div class="syn-section-body">{esc(clean_display_text(section.get("content", "")))}</div>
          <div class="syn-url">{esc(facts)}</div>
          <div class="syn-url">{esc(citations)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def grounded_answer(report: dict[str, Any]) -> None:
    summary = report.get("answer_summary", "")
    sections = report.get("sections") or []
    body = (
        '<div class="syn-answer"><div class="syn-answer-summary">'
        f'{esc(clean_display_text(summary or "No synthesized answer available."))}</div>'
    )
    for section in sections[:6]:
        facts = friendly_refs(section.get("used_fact_ids") or [], "Fact")
        body += (
            '<div class="syn-answer-section">'
            f'<h3>{esc(clean_display_text(section.get("heading", "Section")))}</h3>'
            f'<div><p>{esc(clean_display_text(section.get("content", "")))}</p><div class="syn-url">{esc(facts)}</div></div>'
            "</div>"
        )
    body += "</div>"
    st.markdown(body, unsafe_allow_html=True)


def validator_card(result: dict[str, Any]) -> None:
    degraded = bool(result.get("degraded") or result.get("errors"))
    title = "Validation needs review" if degraded else "Live golden validation passed"
    subtitle = f"{len(result.get('errors') or [])} errors recorded"
    if not degraded:
        subtitle = "No explicit degradation detected"
    st.markdown(
        f"""
        <div class="syn-validator {'bad' if degraded else ''}">
          <div class="syn-validator-main">
            <div class="syn-validator-mark">{icon("circle-alert" if degraded else "check")}</div>
            <div>
              <div class="syn-validator-title">{esc(title)}</div>
              <div class="syn-validator-sub">{esc(subtitle)}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def quality_panel(rows: list[tuple[str, float]]) -> None:
    body = []
    for label, value in rows:
        pct = max(0, min(1, value))
        body.append(
            '<div class="syn-quality-row">'
            f'<div><div>{esc(label)}</div><div class="syn-bar"><span style="width:{pct * 100:.0f}%"></span></div></div>'
            f'<div>{pct * 100:.0f}%</div>'
            "</div>"
        )
    st.markdown("".join(body), unsafe_allow_html=True)


def ledger_table(facts: list[tuple[str, str, str]]) -> None:
    body = []
    for fact_id, claim, status in facts:
        tone = "ok" if status == "Verified" else "warn" if status == "Partial" else "bad"
        id_prefix = "Claim" if status == "Blocked" else "Fact"
        body.append(
            '<div class="syn-ledger-line">'
            f'<div class="id">{esc(friendly_id(fact_id, id_prefix))}</div>'
            f'<div>{esc(clean_display_text(claim))}</div>'
            f'<div class="status {tone}">{esc(status)}</div>'
            "</div>"
        )
    st.markdown('<div class="syn-ledger-mini">' + "".join(body) + "</div>", unsafe_allow_html=True)


def patch_card(operation: dict[str, Any]) -> None:
    refs = friendly_patch_refs(operation)
    target = operation.get("target_path") or operation.get("target_section_id")
    before = operation.get("original_text") or ""
    after = operation.get("replacement_text") or operation.get("text") or ""
    st.markdown(
        f"""
        <div class="syn-patch">
          <div class="syn-meta">
            {chip(friendly_id(operation.get("edit_id") or operation.get("op") or "edit", "Edit"), "warn")}
            {chip(friendly_target(target), "info")}
            {chip(refs if refs else "Referenced", "ok" if refs else "muted")}
          </div>
          <h3 style="margin:12px 0 6px;font-size:16px;color:var(--text);">{esc(clean_display_text(operation.get("edit_label") or humanize(operation.get("op")) or "Patch"))}</h3>
          <div class="claim">{esc(clean_display_text(operation.get("reason", "")))}</div>
          <div class="before">{esc(clean_display_text(before))}</div>
          <div class="after">{esc(clean_display_text(after))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def console(lines: list[tuple[str, Tone]]) -> None:
    rendered = []
    for text, tone in lines:
        cls = "ok" if tone == "ok" else "warn" if tone == "warn" else ""
        prefix = "PASS" if tone == "ok" else "WARN" if tone == "warn" else "INFO"
        rendered.append(f'<div><span class="{cls}">{prefix}</span>  {esc(text)}</div>')
    st.markdown('<div class="syn-console">' + "".join(rendered) + "</div>", unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.markdown(
        f"""
        <div class="syn-sidebar-logo">{wordmark()}</div>
        <div class="syn-sidebar-note">Research runs, source evidence, fact status, and validation details.</div>
        """,
        unsafe_allow_html=True,
    )


def runtime_block(rows: list[tuple[str, Any]]) -> None:
    body = []
    for label, value in rows:
        body.append(
            f"""
            <div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--line);">
              <span style="font-family:var(--mono);font-size:10px;color:var(--muted);">{esc(label)}</span>
              <span style="font-family:var(--mono);font-size:10px;color:var(--soft);text-align:right;word-break:break-all;">{esc(value)}</span>
            </div>
            """
        )
    st.markdown("".join(body), unsafe_allow_html=True)


def hairline() -> None:
    st.markdown('<div style="height:1px;background:var(--line);margin:18px 0;"></div>', unsafe_allow_html=True)


def kicker(text: str, accent: bool = False) -> None:
    color = "var(--green)" if accent else "var(--cyan)"
    st.markdown(
        f'<div class="syn-kicker" style="color:{color};margin:12px 0 8px;">{esc(text)}</div>',
        unsafe_allow_html=True,
    )


def section(label: str, title: str, number: str | None = None) -> None:
    prefix = f"{number} / {label}" if number else label
    section_heading(title, prefix)


def mode_pill(mode: str) -> None:
    tone: Tone = "bad" if "degraded" in mode else "ok" if "live" in mode else "muted"
    chip_row([(mode.replace("_", " "), tone)])


def chips(items: list[tuple[str, str]]) -> None:
    mapped: list[tuple[str, Tone]] = []
    for label, tone in items:
        mapped_tone: Tone = {
            "default": "ok",
            "accent": "warn",
            "mute": "muted",
            "muted": "muted",
            "danger": "bad",
        }.get(tone, "info")  # type: ignore[assignment]
        mapped.append((label, mapped_tone))
    chip_row(mapped)


def evidence_quote(quote: str, attribution: str = "") -> None:
    st.markdown(
        f"""
        <div class="syn-quote-card">
          <div class="syn-meta">{chip("strongest quote", "ok")}{chip(attribution or "source", "info")}</div>
          <div class="quote">"{esc(quote)}"</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
