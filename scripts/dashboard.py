"""
Day 13 Monitoring & LLMOps — Dashboard (6 panels)
Run: streamlit run scripts/dashboard.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
import yaml

# ── Config ──────────────────────────────────────────────────────────────────
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASHBOARD_YAML = REPO_ROOT / "config" / "dashboard.yaml"
SLO_YAML = REPO_ROOT / "config" / "slo.yaml"

st.set_page_config(page_title="Day 13 Monitoring Dashboard", layout="wide")


# ── Load data ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_logs() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


@st.cache_data(ttl=60)
def load_dashboard_config() -> dict:
    return yaml.safe_load(DASHBOARD_YAML.read_text(encoding="utf-8"))


@st.cache_data(ttl=60)
def load_slo_config() -> dict:
    return yaml.safe_load(SLO_YAML.read_text(encoding="utf-8"))


def percentile(values: list[int | float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


# ── Parse timestamps ───────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> datetime:
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    records = load_logs()
    config = load_dashboard_config()
    slo_config = load_slo_config()

    dashboard_cfg = config["dashboard"]
    panels_cfg = {p["id"]: p for p in dashboard_cfg["panels"]}

    st.title("📊 K4-L3A Day 13 Monitoring & LLMOps Dashboard")
    st.caption(f"Time range: {dashboard_cfg['time_range_minutes']} min | Refresh: {dashboard_cfg['refresh_seconds']}s | Records: {len(records)}")

    if not records:
        st.warning("No log records found. Start the API and run the load test first.")
        return

    # Filter events
    response_events = [r for r in records if r.get("event") == "response_sent"]
    request_events = [r for r in records if r.get("event") == "request_received"]
    error_events = [r for r in records if r.get("event") == "request_failed"]

    # ── Row 1: Latency | Traffic | Errors ──
    col1, col2, col3 = st.columns(3)

    # Panel 1: Latency
    with col1:
        panel = panels_cfg["latency"]
        st.subheader(f"⏱ {panel['title']}")
        latencies = [r["latency_ms"] for r in response_events if r.get("latency_ms") is not None]
        ttfts = [r["ttft_ms"] for r in response_events if r.get("ttft_ms") is not None]
        threshold = panel["threshold"]["value"]

        if latencies:
            p50 = percentile(latencies, 50)
            p95 = percentile(latencies, 95)
            p99 = percentile(latencies, 99)
            ttft_p95 = percentile(ttfts, 95) if ttfts else 0.0

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("P50", f"{p50:.0f} ms")
            mc2.metric("P95", f"{p95:.0f} ms", delta=f"{'✅' if p95 <= threshold else '⚠️'}")
            mc3.metric("P99", f"{p99:.0f} ms")
            mc4.metric("TTFT P95", f"{ttft_p95:.0f} ms")

            st.caption(f"SLO threshold: P95 ≤ {threshold} ms")

            # Chart
            chart_data = {"Latency (ms)": latencies}
            st.line_chart(chart_data, use_container_width=True)
        else:
            st.info("No latency data")

    # Panel 2: Traffic
    with col2:
        panel = panels_cfg["traffic"]
        st.subheader(f"📈 {panel['title']}")
        total_requests = len(request_events)
        threshold = panel["threshold"]["value"]

        if request_events:
            # Calculate rate per minute using time range
            timestamps = [parse_ts(r["ts"]) for r in request_events]
            if len(timestamps) > 1:
                time_range_sec = (max(timestamps) - min(timestamps)).total_seconds()
                rpm = total_requests / max(time_range_sec / 60, 1)
            else:
                rpm = total_requests

            mc1, mc2 = st.columns(2)
            mc1.metric("Total Requests", total_requests)
            mc2.metric("Rate/min", f"{rpm:.1f}", delta=f"{'✅' if rpm >= threshold else '⚠️'}")

            st.caption(f"Threshold: ≥ {threshold} req/min")

            # Distribution by minute
            minute_counts: dict[str, int] = {}
            for ts in timestamps:
                key = ts.strftime("%H:%M")
                minute_counts[key] = minute_counts.get(key, 0) + 1
            st.bar_chart(minute_counts, use_container_width=True)
        else:
            st.info("No traffic data")

    # Panel 3: Errors
    with col3:
        panel = panels_cfg["errors"]
        st.subheader(f"❌ {panel['title']}")
        total_req = len(request_events)
        total_err = len(error_events)
        threshold = panel["threshold"]["value"]

        error_rate = (total_err / total_req * 100) if total_req > 0 else 0.0

        # Tool success rate
        tool_events = [r for r in response_events if r.get("tool_success") is not None]
        tool_success = sum(1 for r in tool_events if r.get("tool_success") is True)
        tool_rate = (tool_success / len(tool_events) * 100) if tool_events else 100.0

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Error Rate", f"{error_rate:.1f}%", delta=f"{'✅' if error_rate <= threshold else '⚠️'}")
        mc2.metric("Errors", total_err)
        mc3.metric("Retrieval Success", f"{tool_rate:.1f}%")

        st.caption(f"Threshold: Error rate ≤ {threshold}%")

        # Error breakdown
        if error_events:
            breakdown: dict[str, int] = {}
            for r in error_events:
                et = r.get("error_type", "unknown")
                breakdown[et] = breakdown.get(et, 0) + 1
            st.bar_chart(breakdown, use_container_width=True)
        else:
            st.success("No errors detected!")

    st.divider()

    # ── Row 2: Cost | Tokens | Quality ──
    col4, col5, col6 = st.columns(3)

    # Panel 4: Cost
    with col4:
        panel = panels_cfg["cost"]
        st.subheader(f"💰 {panel['title']}")
        costs = [r["cost_usd"] for r in response_events if r.get("cost_usd") is not None]
        threshold = panel["threshold"]["value"]

        if costs:
            total_cost = sum(costs)
            avg_cost = mean(costs)

            mc1, mc2 = st.columns(2)
            mc1.metric("Total Cost", f"${total_cost:.4f}", delta=f"{'✅' if total_cost <= threshold else '⚠️'}")
            mc2.metric("Avg/Request", f"${avg_cost:.6f}")

            st.caption(f"Budget threshold: ≤ ${threshold}")
            st.line_chart({"Cost (USD)": costs}, use_container_width=True)
        else:
            st.info("No cost data")

    # Panel 5: Tokens
    with col5:
        panel = panels_cfg["tokens"]
        st.subheader(f"🔤 {panel['title']}")
        tokens_in = [r["tokens_in"] for r in response_events if r.get("tokens_in") is not None]
        tokens_out = [r["tokens_out"] for r in response_events if r.get("tokens_out") is not None]
        threshold = panel["threshold"]["value"]

        if tokens_in or tokens_out:
            total_in = sum(tokens_in)
            total_out = sum(tokens_out)
            total_all = total_in + total_out

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Input Tokens", f"{total_in:,}")
            mc2.metric("Output Tokens", f"{total_out:,}")
            mc3.metric("Total", f"{total_all:,}", delta=f"{'✅' if total_all <= threshold else '⚠️'}")

            st.caption(f"Threshold: ≤ {threshold:,} tokens")
            st.bar_chart({"Input": tokens_in, "Output": tokens_out}, use_container_width=True)
        else:
            st.info("No token data")

    # Panel 6: Quality
    with col6:
        panel = panels_cfg["quality"]
        st.subheader(f"⭐ {panel['title']}")
        scores = [r["quality_score"] for r in response_events if r.get("quality_score") is not None]
        threshold = panel["threshold"]["value"]

        if scores:
            avg_quality = mean(scores)
            min_q = min(scores)
            max_q = max(scores)

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Mean Quality", f"{avg_quality:.2f}", delta=f"{'✅' if avg_quality >= threshold else '⚠️'}")
            mc2.metric("Min", f"{min_q:.2f}")
            mc3.metric("Max", f"{max_q:.2f}")

            st.caption(f"Threshold: ≥ {threshold}")
            st.line_chart({"Quality Score": scores}, use_container_width=True)
        else:
            st.info("No quality data")

    # ── SLO Section ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🎯 SLO & Error Budget")

    primary_slo = slo_config.get("primary_slo", {})
    guardrails = slo_config.get("guardrails", {})

    latencies_all = [r["latency_ms"] for r in response_events if r.get("latency_ms") is not None]
    total_received = len(request_events)

    if latencies_all and total_received > 0:
        good_count = sum(1 for lat in latencies_all if lat <= 3000)
        sli_pct = (good_count / total_received) * 100
        target_pct = primary_slo.get("target_percent", 99.5)
        budget_pct = primary_slo.get("error_budget_percent", 0.5)
        budget_used = max(0, 100 - sli_pct)
        budget_remaining = max(0, budget_pct - budget_used)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("SLI (good/total)", f"{sli_pct:.2f}%")
        sc2.metric("Target", f"{target_pct}%")
        sc3.metric("Error Budget", f"{budget_pct}%")
        sc4.metric("Budget Remaining", f"{budget_remaining:.2f}%", delta=f"{'✅' if budget_remaining > 0 else '🔴'}")

    # Guardrails
    gcol1, gcol2, gcol3, gcol4 = st.columns(4)
    error_rate = (len(error_events) / total_received * 100) if total_received > 0 else 0.0
    gcol1.metric("Error Rate", f"{error_rate:.1f}%", delta=f"max {guardrails.get('error_rate_pct_max', 2)}%")

    all_costs = [r["cost_usd"] for r in response_events if r.get("cost_usd") is not None]
    gcol2.metric("Total Cost", f"${sum(all_costs):.4f}", delta=f"max ${guardrails.get('daily_cost_usd_max', 2.5)}")

    all_quality = [r["quality_score"] for r in response_events if r.get("quality_score") is not None]
    gcol3.metric("Avg Quality", f"{mean(all_quality):.2f}" if all_quality else "N/A", delta=f"min {guardrails.get('quality_score_avg_min', 0.75)}")

    tool_events = [r for r in response_events if r.get("tool_success") is not None]
    ts = sum(1 for r in tool_events if r.get("tool_success") is True)
    tr = (ts / len(tool_events) * 100) if tool_events else 100.0
    gcol4.metric("Retrieval Success", f"{tr:.1f}%", delta=f"min {guardrails.get('retrieval_success_rate_pct_min', 90)}%")


if __name__ == "__main__":
    main()
