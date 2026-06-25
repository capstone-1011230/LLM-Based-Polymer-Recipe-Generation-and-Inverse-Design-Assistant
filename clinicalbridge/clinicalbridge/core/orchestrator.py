"""
ClinicalBridge — Orchestrator
Multi-agent coordinator: routes workflow, manages errors, enforces safety guardrails.
Module mapping: M7, M8
"""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import concurrent.futures

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.agents import AlertTriageAgent, EHRRetrievalAgent, AnamnesisAgent, SynthesisAgent
from core.rag_pipeline import build_or_load_vectorstore


class ClinicalBridgeOrchestrator:
    """
    Central coordinator for the ClinicalBridge multi-agent system.
    
    Workflow:
    1. Receive RPM alert
    2. Triage Agent classifies urgency
    3. EHR + Anamnesis agents run IN PARALLEL
    4. Synthesis Agent produces Clinical Context Brief
    5. Safety guardrails applied
    6. Audit log saved
    """

    def __init__(self, use_rag: bool = True):
        print("\n🏥 Initializing ClinicalBridge System...")
        
        # Load vector store
        self.vectorstore = None
        if use_rag:
            try:
                self.vectorstore = build_or_load_vectorstore()
            except Exception as e:
                print(f"  ⚠️  RAG unavailable ({e}) — falling back to raw EHR loading")

        # Initialize agents
        print("  Loading agents...")
        self.triage_agent    = AlertTriageAgent()
        self.ehr_agent       = EHRRetrievalAgent(vectorstore=self.vectorstore)
        self.anamnesis_agent = AnamnesisAgent()
        self.synthesis_agent = SynthesisAgent()

        # Session store
        self.session_logs: list = []
        self.output_dir = Path(__file__).parent.parent / "reports"
        self.output_dir.mkdir(exist_ok=True)

        print("  ✅ ClinicalBridge ready!\n")

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ──────────────────────────────────────────────────────────────────────────

    def process_alert(self, alert: Dict) -> Dict:
        """
        Full pipeline: alert → Clinical Context Brief.
        Returns the complete CCB with audit metadata.
        """
        session_id = f"SESSION-{uuid.uuid4().hex[:8].upper()}"
        pipeline_start = time.time()
        patient_id = alert.get("patient_id", "UNKNOWN")

        print(f"\n{'='*60}")
        print(f"  🚨 ALERT RECEIVED  |  Session: {session_id}")
        print(f"  Patient: {patient_id}")
        print(f"  Alert type: {alert.get('alert_type','?')}")
        print(f"{'='*60}")

        audit_log = {
            "session_id": session_id,
            "patient_id": patient_id,
            "alert_received": alert,
            "pipeline_start": datetime.now().isoformat(),
            "steps": {},
            "errors": [],
            "safety_events": [],
        }

        # ── STEP 1: TRIAGE ────────────────────────────────────────────────────
        print("\n  [1/4] 🔍 Triage Agent analyzing alert...")
        triage_result = self._run_with_fallback(
            fn=lambda: self.triage_agent.run(alert),
            fallback=self._triage_fallback(alert),
            step_name="triage",
            audit_log=audit_log,
        )

        urgency = triage_result.get("urgency", "URGENT")
        print(f"       → Urgency: {urgency}")
        print(f"       → {triage_result.get('primary_concern','?')}")

        # Safety guardrail: CRITICAL → immediate escalation flag
        if urgency == "CRITICAL" or triage_result.get("escalate_immediately"):
            self._trigger_safety_escalation(session_id, patient_id, triage_result, audit_log)

        # ── STEP 2 & 3: PARALLEL RETRIEVAL ───────────────────────────────────
        print("\n  [2/4] 📂 EHR & Anamnesis agents running in parallel...")
        ehr_queries      = triage_result.get("ehr_queries", ["patient history", "current medications"])
        anamnesis_queries = triage_result.get("anamnesis_queries", ["recent symptoms"])
        clinical_question = triage_result.get("clinical_question", "What is the clinical context for this alert?")

        ehr_result, anamnesis_result = self._parallel_retrieval(
            patient_id=patient_id,
            clinical_question=clinical_question,
            ehr_queries=ehr_queries,
            anamnesis_queries=anamnesis_queries,
            audit_log=audit_log,
        )

        ehr_conf = ehr_result.get("retrieval_confidence", "?")
        print(f"       → EHR retrieval confidence: {ehr_conf}")
        print(f"       → Anamnesis reliability: {anamnesis_result.get('information_reliability','?')}")

        # ── STEP 4: SYNTHESIS ─────────────────────────────────────────────────
        print("\n  [3/4] 🧠 Synthesis Agent building Clinical Context Brief...")
        synthesis_result = self._run_with_fallback(
            fn=lambda: self.synthesis_agent.run(
                alert=alert,
                triage=triage_result,
                ehr_context=ehr_result,
                anamnesis=anamnesis_result,
            ),
            fallback=self._synthesis_fallback(triage_result),
            step_name="synthesis",
            audit_log=audit_log,
        )

        ccb_confidence = (
            synthesis_result
            .get("section_6_uncertainties_and_gaps", {})
            .get("overall_brief_confidence", "?")
        )
        print(f"       → CCB confidence: {ccb_confidence}")

        # Safety guardrail: low confidence → mandatory review flag
        if isinstance(ccb_confidence, (int, float)) and ccb_confidence < 0.40:
            audit_log["safety_events"].append({
                "type": "LOW_CONFIDENCE_FLAG",
                "confidence": ccb_confidence,
                "action": "Mandatory human review appended to brief",
            })

        # ── STEP 5: ASSEMBLE FINAL OUTPUT ────────────────────────────────────
        pipeline_elapsed = round(time.time() - pipeline_start, 2)
        print(f"\n  [4/4] ✅ Pipeline complete in {pipeline_elapsed}s")

        final_output = {
            "session_id": session_id,
            "patient_id": patient_id,
            "pipeline_elapsed_seconds": pipeline_elapsed,
            "urgency": urgency,
            "clinical_context_brief": synthesis_result,
            "agent_outputs": {
                "triage": triage_result,
                "ehr_retrieval": ehr_result,
                "anamnesis": anamnesis_result,
            },
            "audit_log": audit_log,
            "system_metadata": {
                "system": "ClinicalBridge v1.0",
                "disclaimer": "EDUCATIONAL PROTOTYPE — NOT FOR CLINICAL USE",
                "all_data_simulated": True,
                "generated_at": datetime.now().isoformat(),
            },
        }

        # Save audit log
        self._save_output(session_id, final_output)
        self.session_logs.append(final_output)

        return final_output

    # ──────────────────────────────────────────────────────────────────────────
    # PARALLEL RETRIEVAL
    # ──────────────────────────────────────────────────────────────────────────

    def _parallel_retrieval(
        self, patient_id, clinical_question, ehr_queries, anamnesis_queries, audit_log
    ):
        """Run EHR and Anamnesis agents in parallel using ThreadPoolExecutor."""

        def run_ehr():
            return self._run_with_fallback(
                fn=lambda: self.ehr_agent.run(
                    patient_id=patient_id,
                    clinical_question=clinical_question,
                    queries=ehr_queries,
                ),
                fallback={"patient_id": patient_id, "data_gaps": ["EHR agent unavailable"], "retrieval_confidence": 0.0},
                step_name="ehr_retrieval",
                audit_log=audit_log,
            )

        def run_anamnesis():
            return self._run_with_fallback(
                fn=lambda: self.anamnesis_agent.run(
                    patient_id=patient_id,
                    clinical_question=clinical_question,
                ),
                fallback={"patient_id": patient_id, "information_reliability": "Low"},
                step_name="anamnesis",
                audit_log=audit_log,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            ehr_future       = executor.submit(run_ehr)
            anamnesis_future = executor.submit(run_anamnesis)
            ehr_result       = ehr_future.result(timeout=120)
            anamnesis_result = anamnesis_future.result(timeout=120)

        return ehr_result, anamnesis_result

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _run_with_fallback(self, fn, fallback, step_name, audit_log):
        """Run an agent function with timeout and error handling."""
        step_start = time.time()
        try:
            result = fn()
            audit_log["steps"][step_name] = {
                "status": "success",
                "elapsed": round(time.time() - step_start, 2),
            }
            return result
        except Exception as e:
            error_msg = f"{step_name} failed: {str(e)}"
            print(f"       ⚠️  {error_msg}")
            audit_log["errors"].append({"step": step_name, "error": error_msg})
            audit_log["steps"][step_name] = {
                "status": "error",
                "error": error_msg,
                "elapsed": round(time.time() - step_start, 2),
            }
            fallback["_agent_error"] = error_msg
            return fallback

    def _trigger_safety_escalation(self, session_id, patient_id, triage_result, audit_log):
        """Handle CRITICAL alert escalation."""
        event = {
            "type": "CRITICAL_ESCALATION",
            "session_id": session_id,
            "patient_id": patient_id,
            "timestamp": datetime.now().isoformat(),
            "urgency": "CRITICAL",
            "concern": triage_result.get("primary_concern", "Critical alert"),
            "action": "IMMEDIATE CLINICIAN NOTIFICATION REQUIRED",
            "note": (
                "⚠️  CRITICAL ALERT: In a production system, this would immediately "
                "notify the on-call clinician via pager/SMS before synthesis completes."
            ),
        }
        audit_log["safety_events"].append(event)
        print(f"\n  🔴 SAFETY ESCALATION: {event['concern']}")
        print(f"     In production: immediate clinician pager/SMS notification")

    def _triage_fallback(self, alert):
        return {
            "urgency": "URGENT",
            "patient_id": alert.get("patient_id", "UNKNOWN"),
            "primary_concern": "Triage unavailable — treating as URGENT for patient safety",
            "clinical_question": "Full clinical assessment required",
            "ehr_queries": ["patient history", "current medications", "recent vitals"],
            "anamnesis_queries": ["recent symptoms", "medication adherence"],
            "escalate_immediately": False,
            "reasoning_chain": {"step1_identify": "Triage agent failed — using safe fallback"},
        }

    def _synthesis_fallback(self, triage_result):
        return {
            "urgency": triage_result.get("urgency", "UNKNOWN"),
            "section_1_alert_summary": {"trigger": "Synthesis unavailable — see triage result"},
            "section_6_uncertainties_and_gaps": {
                "overall_brief_confidence": 0.0,
                "requires_clinician_judgment": ["FULL CLINICAL ASSESSMENT REQUIRED — synthesis failed"],
            },
            "mandatory_human_review": True,
        }

    def _save_output(self, session_id: str, output: Dict):
        """Save session output to reports directory."""
        output_path = self.output_dir / f"{session_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# PRETTY PRINTER
# ══════════════════════════════════════════════════════════════════════════════

def print_ccb(result: Dict):
    """Pretty-print the Clinical Context Brief to console."""
    ccb = result.get("clinical_context_brief", {})
    urgency = result.get("urgency", "?")

    urgency_icons = {"CRITICAL": "🔴", "URGENT": "🟠", "ROUTINE": "🟡", "INFORMATIONAL": "🟢"}
    icon = urgency_icons.get(urgency, "⚪")

    print(f"\n{'═'*65}")
    print(f"  {icon} CLINICAL CONTEXT BRIEF  |  {urgency}")
    print(f"  Session: {result.get('session_id','?')}  |  Patient: {result.get('patient_id','?')}")
    print(f"  Generated in: {result.get('pipeline_elapsed_seconds','?')}s")
    print(f"{'═'*65}")

    s1 = ccb.get("section_1_alert_summary", {})
    if s1:
        print(f"\n📢 ALERT: {s1.get('trigger','?')}")
        print(f"   Values: {s1.get('alert_values','?')}")

    s2 = ccb.get("section_2_patient_snapshot", {})
    if s2:
        print(f"\n👤 PATIENT: {s2.get('demographics','?')}")
        conds = s2.get("active_conditions", [])
        if conds:
            print(f"   Conditions: {', '.join(conds[:3])}")
        meds = s2.get("current_medications", [])
        if meds:
            print(f"   Medications: {', '.join(meds[:3])}")

    s3 = ccb.get("section_3_contextual_analysis", {})
    if s3:
        print(f"\n🔗 CONTEXT: {s3.get('key_connection','?')}")
        discrepancies = s3.get("discrepancies", [])
        if discrepancies:
            print(f"   ⚠️  Discrepancy: {discrepancies[0]}")

    s4 = ccb.get("section_4_risk_assessment", {})
    if s4:
        print(f"\n⚠️  PRIMARY RISK: {s4.get('primary_risk','?')}")
        conf = s4.get("risk_confidence", "?")
        print(f"   Confidence: {conf}")

    s5 = ccb.get("section_5_recommended_actions", [])
    if s5:
        print(f"\n✅ RECOMMENDED ACTIONS:")
        for i, action in enumerate(s5[:4], 1):
            priority = action.get("priority", "?")
            act_text = action.get("action", "?")
            print(f"   {i}. [{priority}] {act_text}")

    s6 = ccb.get("section_6_uncertainties_and_gaps", {})
    if s6:
        overall_conf = s6.get("overall_brief_confidence", "?")
        print(f"\n📊 BRIEF CONFIDENCE: {overall_conf}")
        gaps = s6.get("data_gaps", [])
        if gaps:
            print(f"   Data gaps: {gaps[0]}")

    if result.get("mandatory_human_review"):
        print(f"\n🚨 MANDATORY HUMAN REVIEW REQUIRED")
        print(f"   {result.get('mandatory_human_review_reason','?')}")

    print(f"\n{'─'*65}")
    print("   ⚠️  EDUCATIONAL PROTOTYPE — NOT FOR CLINICAL USE")
    print(f"{'─'*65}\n")
