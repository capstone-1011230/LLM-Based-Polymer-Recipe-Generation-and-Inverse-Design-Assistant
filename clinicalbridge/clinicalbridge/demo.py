"""
ClinicalBridge — Demo Script
============================
Runs SCN-001 (Missed Medication, URGENT) and SCN-003 (Silent Deterioration, CRITICAL)
end-to-end and writes a formatted transcript to demo_output.txt.

Usage:
    python demo.py              # interactive, with pauses for narration
    python demo.py --no-pause   # continuous, for automated recording
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from core.orchestrator import ClinicalBridgeOrchestrator
from evaluation.evaluator import load_scenarios

# ── helpers ──────────────────────────────────────────────────────────────────

TRANSCRIPT = []

def emit(line: str = ""):
    print(line)
    TRANSCRIPT.append(line)

def pause(msg: str = "Press ENTER to continue...", skip: bool = False):
    if not skip:
        input(f"\n  ⏸  {msg} ")
    else:
        time.sleep(0.3)

def banner(title: str, char: str = "═"):
    width = 66
    emit()
    emit(char * width)
    emit(f"  {title}")
    emit(char * width)

def section(title: str):
    emit()
    emit(f"  {'─'*62}")
    emit(f"  ▶  {title}")
    emit(f"  {'─'*62}")

def print_ccb_detailed(result: dict, scenario_title: str):
    """Print a comprehensive CCB for demo purposes."""
    ccb     = result.get("clinical_context_brief", {})
    urgency = result.get("urgency", "?")
    elapsed = result.get("pipeline_elapsed_seconds", "?")

    icons = {"CRITICAL": "🔴", "URGENT": "🟠", "ROUTINE": "🟡", "INFORMATIONAL": "🟢"}
    icon  = icons.get(urgency, "⚪")

    banner(f"{icon}  CLINICAL CONTEXT BRIEF  |  {urgency}", "═")
    emit(f"  Scenario  : {scenario_title}")
    emit(f"  Patient   : {result.get('patient_id','?')}")
    emit(f"  Session   : {result.get('session_id','?')}")
    emit(f"  Generated : {elapsed}s")

    # Section 1 — Alert Summary
    section("1 / ALERT SUMMARY")
    s1 = ccb.get("section_1_alert_summary", {})
    emit(f"  Trigger   : {s1.get('trigger', 'N/A')}")
    emit(f"  Values    : {s1.get('alert_values', 'N/A')}")
    emit(f"  Urgency   : {s1.get('urgency_classification', 'N/A')}")

    # Section 2 — Patient Snapshot
    section("2 / PATIENT SNAPSHOT")
    s2 = ccb.get("section_2_patient_snapshot", {})
    emit(f"  Demographics : {s2.get('demographics', 'N/A')}")
    for cond in (s2.get("active_conditions") or [])[:4]:
        emit(f"    • {cond}")
    emit()
    emit("  Current medications:")
    for med in (s2.get("current_medications") or [])[:4]:
        emit(f"    • {med}")

    # Section 3 — Contextual Analysis
    section("3 / CONTEXTUAL ANALYSIS")
    s3 = ccb.get("section_3_contextual_analysis", {})
    emit(f"  History link : {s3.get('how_alert_relates_to_history', 'N/A')}")
    emit(f"  Patient voice: {s3.get('patient_perspective', 'N/A')}")
    emit(f"  Key finding  : {s3.get('key_connection', 'N/A')}")
    for disc in (s3.get("discrepancies") or [])[:2]:
        emit(f"  ⚠️  {disc}")

    # Section 4 — Risk Assessment
    section("4 / RISK ASSESSMENT")
    s4 = ccb.get("section_4_risk_assessment", {})
    emit(f"  Primary risk : {s4.get('primary_risk', 'N/A')}")
    emit(f"  Confidence   : {s4.get('risk_confidence', 'N/A')}")
    for factor in (s4.get("contributing_factors") or [])[:3]:
        emit(f"    • {factor}")
    for diff in (s4.get("differential_considerations") or [])[:2]:
        if isinstance(diff, dict):
            emit(f"  Differential : {diff.get('consideration','?')} — {diff.get('supporting_evidence','')}")

    # Section 5 — Recommended Actions
    section("5 / RECOMMENDED ACTIONS")
    for i, action in enumerate((ccb.get("section_5_recommended_actions") or []), 1):
        if isinstance(action, dict):
            emit(f"  {i}. [{action.get('priority','?')}]  {action.get('action','?')}")
            emit(f"     Rationale: {action.get('rationale','?')}")
            emit(f"     Confidence: {action.get('confidence','?')}")
            emit()

    # Section 6 — Uncertainties & Gaps
    section("6 / UNCERTAINTIES & GAPS")
    s6 = ccb.get("section_6_uncertainties_and_gaps", {})
    emit(f"  Brief confidence: {s6.get('overall_brief_confidence', 'N/A')}")
    emit(f"  Rationale       : {s6.get('confidence_rationale', 'N/A')}")
    for gap in (s6.get("data_gaps") or [])[:3]:
        emit(f"  ⚠️  Gap: {gap}")
    for conflict in (s6.get("conflicting_information") or [])[:2]:
        emit(f"  ⚡ Conflict: {conflict}")
    for judgement in (s6.get("requires_clinician_judgment") or [])[:2]:
        emit(f"  🩺 Clinician call: {judgement}")

    emit()
    emit("  " + "─" * 62)
    emit("  ⚠️   EDUCATIONAL PROTOTYPE — NOT FOR CLINICAL USE")
    emit("       All data is simulated. Clinician review required.")
    emit("  " + "─" * 62)


def run_scenario_demo(orchestrator, scenario: dict, skip_pause: bool):
    scn_id  = scenario["scenario_id"]
    title   = scenario["title"]
    desc    = scenario["description"]
    patient = scenario["patient_id"]

    banner(f"SCENARIO {scn_id}: {title}", "╔")
    emit()
    emit(f"  Description : {desc}")
    emit(f"  Patient     : {patient}")
    emit(f"  Expected    : {scenario['expected_urgency']}")

    pause("Ready to process alert — press ENTER", skip=skip_pause)

    alert = {**scenario["triggering_alert"], "patient_id": patient}
    if "alert_id" not in alert:
        alert["alert_id"] = f"ALT-{scn_id}"

    section("ALERT DATA")
    emit(json.dumps(alert, indent=4))

    pause("Alert received — press ENTER to run agents", skip=skip_pause)

    t0     = time.time()
    result = orchestrator.process_alert(alert)
    elapsed = round(time.time() - t0, 1)

    print_ccb_detailed(result, title)

    # Gold-standard comparison
    gold       = scenario.get("gold_standard_brief", {})
    predicted  = result["agent_outputs"]["triage"].get("urgency", "?")
    expected   = scenario["expected_urgency"]
    match_icon = "✅" if predicted == expected else "❌"

    section("GOLD STANDARD COMPARISON")
    emit(f"  Urgency accuracy : {match_icon}  Predicted={predicted}  Expected={expected}")
    emit(f"  Pipeline time    : {elapsed}s")
    emit(f"  Gold concern     : {gold.get('primary_concern','N/A')[:120]}")

    pause(f"Scenario {scn_id} complete — press ENTER for next scenario", skip=skip_pause)
    return result


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ClinicalBridge Demo")
    parser.add_argument("--no-pause", action="store_true", help="Run without interactive pauses")
    args = parser.parse_args()
    skip = args.no_pause

    banner("🏥  ClinicalBridge — Live Demonstration", "╔")
    emit()
    emit("  System   : ClinicalBridge v1.0 — Multi-Agent Clinical Decision Support")
    emit("  Course   : COP-3442 Prompt Engineering — Capstone Project")
    emit("  Data     : All patient data is SIMULATED (no real patients)")
    emit()
    emit("  This demo runs two clinical scenarios end-to-end:")
    emit("    • SCN-001 : Missed Medication  (URGENT — hypertension)")
    emit("    • SCN-003 : Silent Deterioration (CRITICAL — heart failure)")
    emit()

    pause("Press ENTER to initialize the system", skip=skip)

    # Init
    banner("SYSTEM INITIALIZATION", "─")
    orchestrator = ClinicalBridgeOrchestrator(use_rag=True)

    all_scenarios = load_scenarios()
    demo_ids      = ["SCN-001", "SCN-003"]
    scenarios     = [s for s in all_scenarios if s["scenario_id"] in demo_ids]

    results = []
    for scenario in scenarios:
        result = run_scenario_demo(orchestrator, scenario, skip_pause=skip)
        results.append(result)

    # Summary
    banner("DEMONSTRATION SUMMARY", "═")
    emit()
    emit(f"  {'Scenario':<12} {'Patient':<8} {'Urgency':<12} {'Time':>6}  Result")
    emit(f"  {'─'*56}")
    for r in results:
        patient = r.get("patient_id", "?")
        urgency = r.get("urgency", "?")
        elapsed = r.get("pipeline_elapsed_seconds", "?")
        session = r.get("session_id", "?")
        scn_id  = next(
            (s["scenario_id"] for s in scenarios if s["patient_id"] == patient), "?"
        )
        icon = {"CRITICAL": "🔴", "URGENT": "🟠", "ROUTINE": "🟡"}.get(urgency, "⚪")
        emit(f"  {scn_id:<12} {patient:<8} {icon} {urgency:<10} {elapsed:>5}s  {session}")

    emit()
    emit("  Key capabilities demonstrated:")
    emit("    ✅ Rule-based triage with clinical threshold knowledge")
    emit("    ✅ RAG-powered EHR retrieval (ChromaDB + LangChain)")
    emit("    ✅ Patient voice extraction from anamnesis records")
    emit("    ✅ Multi-source synthesis with [EHR]/[ANAMNESIS]/[RPM] citation")
    emit("    ✅ Safety guardrails (no diagnosis, confidence scores, human review flag)")
    emit("    ✅ Parallel agent execution (EHR + Anamnesis run concurrently)")
    emit()
    emit("  ⚠️  EDUCATIONAL PROTOTYPE — NOT FOR CLINICAL USE")
    emit("     All data is simulated. System requires clinician oversight.")
    emit()

    # Save transcript
    out_path = Path(__file__).parent / "demo_output.txt"
    out_path.write_text("\n".join(TRANSCRIPT), encoding="utf-8")
    emit(f"  Transcript saved → {out_path}")
    emit()


if __name__ == "__main__":
    main()
