"""
ClinicalBridge — Main Entry Point

Usage:
  python main.py                    # run default scenario (SCN-001)
  python main.py --scenario SCN-002 # run a specific scenario
  python main.py --all              # run all 5 scenarios + full evaluation
  python main.py --build-index      # build ChromaDB index only
  python main.py --patient P003     # run active RPM alert for a patient
"""

import argparse
import json
import sys
from pathlib import Path

# Path setup
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from core.orchestrator import ClinicalBridgeOrchestrator, print_ccb
from evaluation.evaluator import run_full_evaluation, load_scenarios, load_rpm_alert


def build_index_only():
    """Build ChromaDB index without running any alerts."""
    print("\n🗄️  Building EHR Vector Store...")
    from core.rag_pipeline import EHRVectorStore
    store = EHRVectorStore()
    store.build_index()
    print("\n✅ Index ready! You can now run scenarios.")


def run_scenario(orchestrator: ClinicalBridgeOrchestrator, scenario_id: str):
    """Run a specific clinical scenario."""
    scenarios = load_scenarios()
    scenario  = next((s for s in scenarios if s["scenario_id"] == scenario_id), None)
    if not scenario:
        print(f"❌ Scenario {scenario_id} not found. Available: {[s['scenario_id'] for s in scenarios]}")
        return

    print(f"\n📋 Scenario: {scenario['title']}")
    print(f"   {scenario['description']}\n")

    alert = {**scenario["triggering_alert"], "patient_id": scenario["patient_id"]}
    if "alert_id" not in alert:
        alert["alert_id"] = f"ALT-{scenario_id}"

    result = orchestrator.process_alert(alert)
    print_ccb(result)

    # Compare to gold standard
    gold  = scenario.get("gold_standard_brief", {})
    predicted_urgency = result["agent_outputs"]["triage"].get("urgency","?")
    expected_urgency  = scenario["expected_urgency"]
    match = "✅" if predicted_urgency == expected_urgency else "❌"
    print(f"  Gold Standard Comparison:")
    print(f"  Urgency: {match} Predicted={predicted_urgency}, Expected={expected_urgency}")
    print(f"  Gold concern: {gold.get('primary_concern','?')[:100]}...\n")

    return result


def run_patient_alert(orchestrator: ClinicalBridgeOrchestrator, patient_id: str):
    """Run the active RPM alert for a specific patient."""
    alert = load_rpm_alert(patient_id)
    if not alert:
        print(f"❌ No active alert for patient {patient_id}")
        return
    print(f"\n🚨 Running active alert for patient {patient_id}...")
    result = orchestrator.process_alert(alert)
    print_ccb(result)
    return result


def main():
    parser = argparse.ArgumentParser(description="ClinicalBridge — Multi-Agent Clinical Decision Support")
    parser.add_argument("--scenario", type=str, default="SCN-001",
                        help="Scenario ID to run (SCN-001 to SCN-005)")
    parser.add_argument("--all", action="store_true",
                        help="Run all scenarios + full evaluation")
    parser.add_argument("--build-index", action="store_true",
                        help="Build ChromaDB EHR index only")
    parser.add_argument("--patient", type=str,
                        help="Run active RPM alert for a patient ID (P001-P010)")
    parser.add_argument("--no-rag", action="store_true",
                        help="Disable RAG (use raw JSON fallback)")
    args = parser.parse_args()

    print("\n" + "╔" + "═"*58 + "╗")
    print("║  🏥  ClinicalBridge  —  Multi-Agent Clinical Decision Support  ║")
    print("║      EDUCATIONAL PROTOTYPE  |  ALL DATA SIMULATED             ║")
    print("╚" + "═"*58 + "╝")

    if args.build_index:
        build_index_only()
        return

    # Initialize orchestrator
    use_rag = not args.no_rag
    orchestrator = ClinicalBridgeOrchestrator(use_rag=use_rag)

    if args.patient:
        run_patient_alert(orchestrator, args.patient.upper())

    elif args.all:
        print("\n🔬 Running full evaluation suite (all 5 scenarios)...\n")
        scenarios = load_scenarios()
        for scenario in scenarios:
            run_scenario(orchestrator, scenario["scenario_id"])
        run_full_evaluation(orchestrator)

    else:
        run_scenario(orchestrator, args.scenario)


if __name__ == "__main__":
    main()
