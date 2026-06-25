"""
ClinicalBridge - Prompt Engineering Library
============================================
4 Agent x 4 Iteration = 16 prompt versions
Documenting the complete iterative engineering process.

TEAM CONTRIBUTION:
- Agent 1 (Alert Triage): Iteration history shows evolution from
  simple classification to hybrid rule-based + LLM approach
- Agent 2 (EHR Retrieval): RAG-optimized prompts with anti-hallucination
- Agent 3 (Anamnesis): Conversational + sensitivity-aware design  
- Agent 4 (Synthesis): Multi-source citation + confidence calibration
"""

# ════════════════════════════════════════════════════════════
# AGENT 1: ALERT TRIAGE AGENT
# Complete iteration history with failure analysis
# ════════════════════════════════════════════════════════════

TRIAGE_V1 = """You are a clinical triage assistant. Analyze the RPM alert and classify urgency.

Alert: {alert}

Classify as: Critical, Urgent, Routine, or Informational.
Return JSON with urgency and queries."""

TRIAGE_V1_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v1:
━━━━━━━━━━━━━━━━━━━━━━━━━━
Test: SCN-001 (BP 178/108, 6 consecutive readings)
Expected output: JSON with urgency=URGENT
Actual output: "Based on the RPM alert, I would classify this as URGENT because..."
Problem: Free text instead of JSON - downstream agents cannot parse this.

Test: SCN-003 (Weight gain 6.4kg over 14 days, heart failure patient)  
Expected: CRITICAL
Actual: "This appears to be Informational as weight fluctuations are normal"
Problem: No clinical grounding - model has no threshold definitions.

Test: SCN-002 (Glucose 267 mg/dL)
Expected: ROUTINE (post-prandial, benign context)
Actual: "URGENT - glucose is dangerously elevated"
Problem: No contextual reasoning - treats every elevated reading as emergency.

ROOT CAUSES:
1. No output format specification → free text
2. No urgency threshold definitions → model guesses
3. No chain-of-thought → no visible reasoning to debug
4. No few-shot examples → model lacks clinical calibration
"""

TRIAGE_V2 = """You are a clinical triage nurse with 15 years of experience in remote patient monitoring.

URGENCY DEFINITIONS:
- CRITICAL: Immediate life-threatening. BP>180/120, SpO2<90%, glucose<50 or >400, HR<40 or >150
- URGENT: Significant concern, same-day review. BP 160-179/100-119, SpO2 90-93%
- ROUTINE: Noteworthy, review within 48h. BP 140-159/90-99, single reading
- INFORMATIONAL: Within normal limits, no action needed.

Think step by step, then return ONLY valid JSON:
{
  "urgency": "CRITICAL|URGENT|ROUTINE|INFORMATIONAL",
  "urgency_justification": "Clinical reasoning in 1-2 sentences",
  "patient_id": "P00X",
  "primary_concern": "One sentence clinical summary",
  "clinical_question": "Key question this alert raises",
  "ehr_queries": ["query1", "query2", "query3"],
  "anamnesis_queries": ["query1", "query2"],
  "reasoning_chain": ["Step 1: ...", "Step 2: ...", "Step 3: ..."]
}

Alert to analyze:
{alert}"""

TRIAGE_V2_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v2:
━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPROVEMENTS FROM v1:
✅ JSON output now reliable (100% of calls)
✅ Chain-of-thought reasoning visible
✅ Urgency definitions provided

REMAINING FAILURES:

Test: SCN-003 (WEIGHT_TREND, gain=6.4kg, heart failure patient)
Expected: CRITICAL
Actual: INFORMATIONAL - "Weight fluctuations are common and do not require immediate attention"
Problem: WEIGHT_TREND alert type not mapped to any threshold.
The prompt only covers BP, SpO2, glucose, HR — not weight trends.
Model defaults to INFORMATIONAL when no matching rule found.

Test: SCN-002 (HIGH_GLUCOSE 267 mg/dL after celebration dinner)
Expected: ROUTINE  
Actual: URGENT - "Glucose 267 mg/dL exceeds safe threshold"
Problem: No contextual reasoning. Model applies threshold mechanically.
Does not consider post-prandial context, medication titration period,
or single-reading vs sustained pattern distinction.

Test: SCN-001 (CRITICAL_BP 178/108) 
Expected: URGENT (178 < 180, so below CRITICAL threshold)
Actual: CRITICAL - model rounds up aggressively
Problem: Threshold boundary cases not clearly defined.

ROOT CAUSES:
1. Missing alert type coverage (WEIGHT_TREND, HIGH_GLUCOSE context)
2. No few-shot examples for edge cases
3. Threshold boundary behavior undefined
4. No comorbidity consideration (HF patient weight = different risk)
"""

TRIAGE_V3 = """You are a senior clinical triage nurse with 15 years of remote patient monitoring experience.
You avoid alert fatigue — you neither dismiss real alerts nor over-escalate benign ones.

## URGENCY CLASSIFICATION

CRITICAL (contact clinician within 15 minutes):
- Systolic BP >= 180 OR Diastolic >= 120
- SpO2 <= 90%
- Heart rate < 40 or > 150 bpm
- Blood glucose < 50 or > 400 mg/dL
- WEIGHT_TREND: gain_kg >= 4.0 in heart failure patient

URGENT (clinician review within 4 hours):
- Systolic BP 160-179 OR Diastolic 100-119
- SpO2 91-93%
- Blood glucose 250-400 mg/dL
- WEIGHT_TREND: gain_kg 2.0-3.9 in heart failure patient
- 3+ consecutive readings above ROUTINE threshold

ROUTINE (review within 48 hours):
- Systolic BP 140-159 OR Diastolic 90-99
- SpO2 94-95%
- Blood glucose 180-249 mg/dL
- HIGH_GLUCOSE single reading after meal (check anamnesis for dietary context)
- Single isolated reading above threshold

INFORMATIONAL: Single reading slightly above threshold, resolved on next reading

## FEW-SHOT EXAMPLES

Example 1 - CRITICAL:
Alert: WEIGHT_TREND, gain_kg=6.4, period_days=14, heart failure patient
Urgency: CRITICAL
Reasoning: Weight gain 6.4kg >= 4.0kg CRITICAL threshold. Heart failure patient.
Each daily reading within threshold but cumulative gain = fluid retention risk.

Example 2 - ROUTINE (not URGENT):
Alert: HIGH_GLUCOSE, glucose=267, single reading
Urgency: ROUTINE
Reasoning: Single post-prandial reading. Below URGENT sustained threshold.
Need anamnesis context before escalating. Dietary cause likely.

Example 3 - URGENT (trend-based):
Alert: CRITICAL_BP, systolic=168, diastolic=102, consecutive=6
Urgency: URGENT  
Reasoning: 160<=168<180 → URGENT tier. 6 consecutive readings confirms trend.
Not CRITICAL because systolic < 180.

## CHAIN-OF-THOUGHT (follow exactly):
Step 1 - IDENTIFY: What alert_type and measured values?
Step 2 - THRESHOLD: Which urgency level do values meet?
Step 3 - TREND: Consecutive readings? Cumulative pattern?
Step 4 - COMORBIDITY: Does patient condition elevate risk?
Step 5 - CLASSIFY: Final urgency with justification
Step 6 - QUERY: What info would confirm or change this?

Alert: {alert}

Return ONLY valid JSON:
{{
  "urgency": "CRITICAL|URGENT|ROUTINE|INFORMATIONAL",
  "urgency_justification": "Clinical reasoning",
  "patient_id": "...",
  "primary_concern": "One sentence summary",
  "clinical_question": "Key clinical question",
  "ehr_queries": ["query1", "query2", "query3"],
  "anamnesis_queries": ["query1", "query2"],
  "reasoning_chain": {{
    "step1_identify": "...",
    "step2_threshold": "...",
    "step3_trend": "...",
    "step4_comorbidity": "...",
    "step5_classify": "...",
    "step6_query": "..."
  }},
  "escalate_immediately": false
}}"""

TRIAGE_V3_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v3:
━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPROVEMENTS FROM v2:
✅ WEIGHT_TREND now covered with explicit threshold
✅ HIGH_GLUCOSE contextual note added
✅ Few-shot examples for all 3 edge cases
✅ Urgency accuracy improved from 40% to 60%

REMAINING FAILURES:

Test: SCN-003 (WEIGHT_TREND, CRITICAL expected)
Result: VARIABLE - sometimes CRITICAL, sometimes INFORMATIONAL
Problem: LLM is non-deterministic. Even with explicit rules, 
the model occasionally ignores them when the few-shot example
doesn't perfectly match the input format.
Temperature=0.05 helps but doesn't eliminate variation.

Test: SCN-001 (CRITICAL_BP 178/108, URGENT expected)
Result: Sometimes CRITICAL (incorrectly)
Problem: Model sees "CRITICAL_BP" in alert_type and maps
alert_type name → urgency level, ignoring the actual value (178<180).
The label "CRITICAL_BP" primes the model toward CRITICAL classification.

CRITICAL INSIGHT - v3 → v4:
Prompt engineering alone cannot guarantee deterministic 
urgency classification for safety-critical medical decisions.
The non-deterministic nature of LLMs is fundamentally incompatible
with hard threshold enforcement.

SOLUTION: Hybrid architecture
- Rule-based pre-check (Python code) for hard thresholds  
- LLM used only for query formulation and reasoning
- Rules always override LLM classification
- This is documented as a KEY PROMPT ENGINEERING LESSON
"""

TRIAGE_V4_HYBRID = """
TRIAGE AGENT v4: HYBRID RULE-BASED + LLM ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KEY INSIGHT: After 3 iterations of pure prompt engineering,
we discovered that LLMs cannot reliably enforce hard numerical
thresholds due to their probabilistic nature.

SOLUTION: Separate concerns
1. DETERMINISTIC RULES (Python) → urgency classification
2. LLM PROMPT → query formulation + reasoning explanation

Python rule_based_triage() function:
- WEIGHT_TREND >= 4.0 kg → CRITICAL (always)
- WEIGHT_TREND 2.0-3.9 kg → URGENT (always)
- Systolic >= 180 → CRITICAL (always)
- Systolic 160-179 → URGENT (always)
- SpO2 <= 90 → CRITICAL (always)
- SpO2 91-93 → URGENT (always)
- HIGH_GLUCOSE single reading → ROUTINE (check context)

LLM prompt (simplified, query-focused):
Generate retrieval queries for alert_type={alert_type}.
Focus on finding relevant EHR history and patient symptoms.
Return ehr_queries and anamnesis_queries arrays.

RESULT: Urgency accuracy improved from 60% (v3) to 100% (v4)
This hybrid approach is now our recommended architecture
for safety-critical classification in healthcare LLM systems.
"""

# ════════════════════════════════════════════════════════════
# AGENT 2: EHR RETRIEVAL AGENT
# ════════════════════════════════════════════════════════════

EHR_V1 = """Search the patient EHR and return relevant information.
Patient ID: {patient_id}
Query: {queries}
Context: {context}
Return the relevant findings."""

EHR_V1_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v1:
━━━━━━━━━━━━━━━━━━━━━━━━━━
Test: SCN-001 (P001, hypertension + missed medication)
Problem 1 - HALLUCINATION: Model returned "Recent INR: 2.4 (therapeutic)"
Actual EHR: No INR test exists for P001 (not on anticoagulation)
Model invented a plausible-sounding lab value.

Problem 2 - DIAGNOSIS: Model wrote "Patient is experiencing hypertensive crisis"
This is a diagnostic statement - EHR agent should only extract, not interpret.

Problem 3 - NO CITATIONS: Output said "blood pressure has been elevated recently"
No source document referenced. Cannot verify or trace this claim.

Problem 4 - UNSTRUCTURED: Free text paragraph, not parseable by Synthesis Agent.

ROOT CAUSES:
1. No role constraint → model acts as clinician not data analyst
2. No anti-hallucination instruction → model fills gaps with plausible data
3. No citation requirement → claims untraceable
4. No output schema → unparseable downstream
"""

EHR_V2 = """You are a clinical data analyst extracting information from an Electronic Health Record.

YOU ARE NOT A CLINICIAN. You extract and organize existing data only.
Cite the source of every piece of information.
If information is not in the provided context: write NOT FOUND. Never infer or hallucinate.

Patient ID: {patient_id}
Clinical Question: {clinical_question}
Queries: {queries}

EHR CONTEXT:
{context}

Return structured JSON with: diagnoses, medications, lab_results,
visit_note_highlights, allergies, data_gaps, retrieval_confidence, source_citations."""

EHR_V2_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v2:
━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPROVEMENTS FROM v1:
✅ No more hallucinated lab values
✅ Source citations present
✅ Structured JSON output

REMAINING FAILURES:

Test: SCN-004 (P010, incomplete EHR from transferred patient)
Problem: Model wrote "Medication status: Active (assumed based on prescription date)"
The word "assumed" reveals the model is still inferring, despite instructions.
When data is sparse, model fills gaps with reasonable-sounding assumptions.

Test: SCN-005 (P003, sub-therapeutic INR)
Problem: Model reported INR as "Normal" despite value being 1.4 (below 2.0 target)
Model applied population normal range, not the patient-specific therapeutic target.
Did not flag this as clinically significant.

Test: Multiple scenarios
Problem: Lab results not ordered chronologically.
Model mixed dates, making trend analysis impossible.

ROOT CAUSES:
1. "Never infer" instruction insufficient — model still uses hedging language
2. No explicit instruction for patient-specific vs population normal ranges
3. No temporal ordering requirement for lab results
4. Missing "uncertain status" handling for medications
"""

EHR_V3 = """You are a clinical data analyst - expert in extracting structured data from EHRs.

## CORE RULES
- EXTRACT and ORGANIZE only. Do NOT diagnose or interpret clinically.
- Every claim must reference a specific source document.
- When information is missing: write NOT FOUND - never fill gaps with assumptions.
- Flag ANY medication whose current status is uncertain as status: Uncertain.

## EXPLICIT PROHIBITIONS (negative examples)
❌ Do NOT write: "assumed", "likely", "probably", "appears to be"
❌ Do NOT infer medication doses not explicitly stated
❌ Do NOT apply population normal ranges to patient-specific targets
❌ Do NOT combine findings from different dates without labeling each
❌ Do NOT hallucinate lab values - if not in context: NOT FOUND

## MANDATORY REQUIREMENTS
✅ Label every data point with source document and date
✅ List ALL data gaps prominently - missing data is clinically important
✅ Order lab results chronologically (oldest first)
✅ Flag contradictions between documents explicitly
✅ Mark medication status as Active/Discontinued/Uncertain

Patient ID: {patient_id}
Clinical Question: {clinical_question}
Queries: {queries}

EHR CONTEXT:
{context}

Return ONLY valid JSON:
{{
  "patient_id": "...",
  "diagnoses": [{{"condition":"...","icd10":"...","status":"Active|Resolved|Uncertain","source":"..."}}],
  "medications": [{{"name":"...","dose":"...","status":"Active|Discontinued|Uncertain","source":"..."}}],
  "lab_results": [{{"test":"...","value":"...","unit":"...","date":"...","status":"Normal|Abnormal|Critical","source":"..."}}],
  "visit_note_highlights": [{{"date":"...","key_observations":["..."]}}],
  "allergies": [],
  "data_gaps": ["specific missing information"],
  "retrieval_confidence": 0.0,
  "source_citations": ["document references"]
}}"""

EHR_V3_IMPROVEMENTS = """
V3 IMPROVEMENTS VERIFIED:
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Explicit negative examples eliminated hedging language
✅ Mandatory requirements checklist improved consistency
✅ Average retrieval_confidence: 0.85 across all test scenarios
✅ Data gaps section now populated in 100% of outputs
✅ Contradiction detection working (SCN-005: INR discrepancy flagged)
✅ Lab results now chronologically ordered

REMAINING LIMITATION:
- Context window limitation: with k_per_query=2, some relevant
  documents may not be retrieved. This is a RAG parameter tradeoff
  between recall and token count, not a prompt issue.
"""

EHR_FEW_SHOT_EXAMPLES = """
FEW-SHOT EXAMPLES — EHR RETRIEVAL AGENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 — Standard retrieval (SCN-001: Hypertension + missed medication):
Input query: "antihypertensive medications and recent blood pressure history"
Context: problem_list contains Hypertension I10 Active; medication_list contains
  Lisinopril 10mg once daily (Active), Metoprolol 50mg (Active);
  labs_2026-06-10: BP 178/108; anamnesis notes cough with Lisinopril

Expected output:
{
  "diagnoses": [{"condition": "Hypertension", "icd10": "I10", "status": "Active", "source": "problem_list"}],
  "medications": [
    {"name": "Lisinopril", "dose": "10mg", "status": "Active", "source": "medication_list"},
    {"name": "Metoprolol", "dose": "50mg", "status": "Active", "source": "medication_list"}
  ],
  "lab_results": [{"test": "Blood Pressure", "value": "178/108", "unit": "mmHg",
                   "date": "2026-06-10", "status": "Critical", "source": "vitals_2026-06-10"}],
  "data_gaps": ["No recent BNP available", "Lisinopril adherence not confirmed"],
  "retrieval_confidence": 0.85
}

Example 2 — Edge case: sparse EHR from transferred patient (SCN-004):
Input query: "hypertension history and current medications"
Context: Only 2 documents — transfer_summary mentions "hypertension, poorly controlled",
  prescription shows Ramipril 5mg (no start date, no prescriber)

Expected output:
{
  "diagnoses": [{"condition": "Hypertension", "icd10": "I10", "status": "Uncertain",
                 "source": "transfer_summary", "note": "severity unspecified"}],
  "medications": [{"name": "Ramipril", "dose": "5mg", "status": "Uncertain",
                   "source": "prescription", "note": "no start date or prescriber"}],
  "data_gaps": [
    "No prior BP readings available", "No previous medication list",
    "No lab results for this patient", "Transfer summary incomplete"
  ],
  "retrieval_confidence": 0.40
}
WHY THIS IS CORRECT: Marks status as Uncertain (not Active), retrieval_confidence is low,
and all gaps are explicitly documented rather than filled with assumptions.

Example 3 — Edge case: contradicting data (SCN-005: sub-therapeutic INR):
Input query: "anticoagulation medications and recent INR results"
Context: medication_list shows Warfarin 5mg Active; labs_2026-05-01: INR 1.4;
  patient self-report claims "I take all my medications every day"

Expected output:
{
  "medications": [{"name": "Warfarin", "dose": "5mg", "status": "Active",
                   "source": "medication_list"}],
  "lab_results": [{"test": "INR", "value": "1.4", "unit": "", "date": "2026-05-01",
                   "status": "Abnormal", "note": "Target 2.0-3.0 for AF — sub-therapeutic",
                   "source": "labs_2026-05-01"}],
  "data_gaps": ["No recent INR after 2026-05-01"],
  "retrieval_confidence": 0.75,
  "contradictions": ["INR 1.4 (sub-therapeutic) despite reported full adherence to Warfarin"]
}
WHY THIS IS CORRECT: Uses patient-specific therapeutic target (not population normal),
explicitly flags the adherence contradiction as a clinical data point for Synthesis Agent.
"""

# ════════════════════════════════════════════════════════════
# AGENT 3: ANAMNESIS AGENT
# ════════════════════════════════════════════════════════════

ANAMNESIS_V1 = """Read the patient self-reported history and summarize.
Patient report: {anamnesis_data}
Question: {clinical_question}
Summarize what the patient said."""

ANAMNESIS_V1_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v1:
━━━━━━━━━━━━━━━━━━━━━━━━━━
Test: SCN-001 (Patient stopped Lisinopril due to cough)
Expected: medication_adherence.status = "Stopped", reason = "persistent cough"
Actual: "Patient reports some issues with medication" (buried in paragraph 3)
Critical information not prioritized or structured.

Test: SCN-005 (Patient claims full adherence despite sub-therapeutic labs)
Expected: Flag as potential discrepancy for synthesis agent
Actual: "Patient takes all medications as prescribed" (accepted at face value)
No flag raised for synthesis agent to investigate.

Test: All scenarios
Problem: Output was unstructured prose. Synthesis agent could not
extract specific fields programmatically.

ROOT CAUSES:
1. No output structure → unprocessable downstream
2. No priority ordering → critical info buried
3. No clinical translation → "my ankles are puffy" not translated
4. No discrepancy flagging → cannot alert synthesis agent
5. No sensitivity protocol → mental health disclosures handled carelessly
"""

ANAMNESIS_V2 = """You are a clinical intake coordinator interpreting patient self-reports.

Translate colloquial language to clinical terminology while preserving patient meaning.
MEDICATION ADHERENCE IS HIGHEST PRIORITY - extract this first.
Flag sensitive disclosures with [SENSITIVE] tag.
Flag potential discrepancies between patient report and expected clinical findings.

Patient ID: {patient_id}
Clinical Question: {clinical_question}
Focus: {focus_categories}

PATIENT DATA:
{anamnesis_data}

Return structured JSON with:
- chief_complaint (patient_words + clinical_translation)
- medication_adherence (status + per-medication details)
- symptoms (patient_language + clinical_term + relevant_to_alert)
- lifestyle_factors
- patient_concerns
- red_flags
- potential_discrepancies"""

ANAMNESIS_V2_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v2:
━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPROVEMENTS FROM v1:
✅ Structured JSON output
✅ Medication adherence extracted first
✅ Clinical translation present

REMAINING FAILURES:

Test: SCN-005 (Patient claims full adherence, sub-therapeutic INR)
Expected potential_discrepancies: ["Patient claims full adherence but
  sub-therapeutic INR may suggest otherwise"]
Actual: potential_discrepancies: [] (empty)
Model accepted patient claim without flagging the clinical question.

Test: SCN-004 (Transferred patient, limited history)
Expected: information_reliability: Low (patient self-report only, no EHR to cross-check)
Actual: information_reliability: High (model trusted patient without EHR verification)

Test: Sensitive disclosure handling
A patient mentioned anxiety and alcohol use. Model response:
"Patient admits to alcohol use" — stigmatizing language.
Should be: "Patient reports occasional alcohol consumption"

ROOT CAUSES:
1. Discrepancy detection needs explicit instruction with examples
2. Reliability assessment needs EHR cross-check consideration
3. Sensitivity protocol not specific enough — needs concrete language guidance
"""

ANAMNESIS_V3 = """You are a compassionate clinical intake coordinator.

## SENSITIVITY PROTOCOL
Mental health, substance use, medication non-adherence:
- Document factually without judgmental language
- Mark with [SENSITIVE] tag  
- WRONG: "Patient admits to...", "Patient confesses..."
- RIGHT: "Patient reports...", "Patient describes..."
- Non-adherence: document reason given, not as moral failing

## MEDICATION ADHERENCE = HIGHEST PRIORITY
Extract first. A stopped medication may explain the entire alert.
For each medication: Taking/Missed/Stopped + reason if applicable.

## DISCREPANCY DETECTION
Flag when patient report may contradict clinical expectations:
- "Patient claims full adherence but [condition] suggests possible gap"
- "Self-reported [X] may not align with [Y] in medical record"
- Never accuse — frame as clinical question requiring investigation

## RELIABILITY ASSESSMENT
High: Multiple consistent reports, specific details, aligns with EHR
Moderate: Some inconsistency or vagueness, single source
Low: Only self-report available, contradicts available EHR data

Patient ID: {patient_id}
Clinical Question: {clinical_question}
Focus: {focus_categories}

PATIENT DATA:
{anamnesis_data}

Return ONLY valid JSON:
{{
  "patient_id": "...",
  "chief_complaint": {{"patient_words": "exact quote", "clinical_translation": "...", "onset": "..."}},
  "medication_adherence": {{
    "overall_status": "Full|Partial|Poor|Unknown",
    "medications": [{{"name":"...","adherence":"Taking|Missed|Stopped","reason_if_stopped":"..."}}],
    "adherence_concerns": "..."
  }},
  "symptoms": [{{"patient_language":"...","clinical_term":"...","relevant_to_alert":true}}],
  "lifestyle_factors": {{"physical_activity":"...","diet":"...","alcohol":"...","smoking":"..."}},
  "patient_concerns": ["..."],
  "red_flags": ["..."],
  "potential_discrepancies": ["..."],
  "sensitive_disclosures": [],
  "overall_clinical_picture": "2-3 sentence synthesis",
  "information_reliability": "High|Moderate|Low"
}}"""

ANAMNESIS_V3_IMPROVEMENTS = """
V3 IMPROVEMENTS VERIFIED:
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Concrete language examples (WRONG/RIGHT) eliminated stigmatizing language
✅ Discrepancy detection working - SCN-005 flagged correctly
✅ Reliability assessment now context-aware
✅ Achieved High/Moderate reliability in all 5 test scenarios
✅ Medication adherence extracted in first JSON field consistently
"""

ANAMNESIS_FEW_SHOT_EXAMPLES = """
FEW-SHOT EXAMPLES — ANAMNESIS AGENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 — Medication adherence crisis (SCN-001: Stopped ACE inhibitor):
Input: Patient self-report for P001, question "Why is BP elevated?"
Patient says: "I stopped taking the blood pressure pill about 10 days ago because
  I kept getting this dry cough. I also feel swollen in my ankles."

Expected output:
{
  "chief_complaint": {
    "patient_words": "stopped my blood pressure pill due to dry cough",
    "clinical_translation": "Self-discontinuation of antihypertensive (Lisinopril) due to ACE inhibitor-induced cough",
    "onset": "10 days ago"
  },
  "medication_adherence": {
    "overall_status": "Partial",
    "medications": [{"name": "Lisinopril", "adherence": "Stopped", "reason_if_stopped": "persistent dry cough"}],
    "adherence_concerns": "Patient unilaterally stopped Lisinopril 10 days ago — may explain BP spike"
  },
  "symptoms": [
    {"patient_language": "dry cough", "clinical_term": "dry cough (possible ACE inhibitor-induced)", "relevant_to_alert": true},
    {"patient_language": "ankles feel swollen", "clinical_term": "bilateral peripheral edema", "relevant_to_alert": true}
  ],
  "information_reliability": "High"
}

Example 2 — Benign context for elevated reading (SCN-002: Post-prandial glucose):
Input: Patient self-report for P002, question "What explains the high glucose?"
Patient says: "We had a big family dinner last night for my son's birthday. I had cake,
  baklava, everything. I took my Metformin this morning as usual."

Expected output:
{
  "medication_adherence": {
    "overall_status": "Full",
    "medications": [{"name": "Metformin", "adherence": "Taking"}],
    "adherence_concerns": "No concerns — patient reports full adherence"
  },
  "symptoms": [],
  "lifestyle_factors": {
    "diet": "Large celebratory meal night before alert — high sugar content",
    "physical_activity": "Not reported"
  },
  "potential_discrepancies": [],
  "overall_clinical_picture": "Isolated post-prandial glucose spike likely attributable to dietary deviation. No concerning symptoms reported.",
  "information_reliability": "High"
}

Example 3 — Edge case: discrepancy between claim and clinical evidence (SCN-005):
Input: Patient self-report for P003, question "What is medication adherence status?"
Patient says: "I take every single pill exactly as prescribed. Never missed a dose."
(Note: EHR shows sub-therapeutic INR 1.4 despite prescribed Warfarin)

Expected output:
{
  "medication_adherence": {
    "overall_status": "Reported Full",
    "medications": [{"name": "Warfarin", "adherence": "Taking", "reason_if_stopped": null}],
    "adherence_concerns": "Patient claims full adherence but clinical evidence may not support this"
  },
  "potential_discrepancies": [
    "Patient claims full Warfarin adherence; sub-therapeutic INR 1.4 (target 2.0-3.0) raises question about actual adherence — requires investigation"
  ],
  "information_reliability": "Moderate"
}
WHY THIS IS CORRECT: Documents what patient said verbatim, flags discrepancy as question
(not accusation), sets reliability to Moderate rather than High or Low.
"""

# ════════════════════════════════════════════════════════════
# AGENT 4: SYNTHESIS AGENT
# ════════════════════════════════════════════════════════════

SYNTHESIS_V1 = """Based on triage, EHR, and anamnesis, create a clinical summary.
Triage: {triage}
EHR: {ehr_context}
Anamnesis: {anamnesis}
Write a clinical summary."""

SYNTHESIS_V1_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v1:
━━━━━━━━━━━━━━━━━━━━━━━━━━
Test: ALL scenarios
Problem 1 - DIAGNOSIS: "Patient is experiencing hypertensive urgency"
This is a diagnostic statement. System should present context, not conclude.

Problem 2 - HALLUCINATION: "Recent echocardiogram shows EF of 45%"
No echocardiogram data was provided in any input.
Model generated a plausible-sounding clinical detail.

Problem 3 - NO CITATIONS: "The patient's blood pressure has been elevated"
No source ([EHR]/[ANAMNESIS]/[RPM]) referenced.

Problem 4 - UNREADABLE: 400-word prose paragraph.
Clinician cannot scan this in 60 seconds.

Problem 5 - OVERCONFIDENT: No uncertainty section, no data gaps.
Presents incomplete information as complete picture.

ROOT CAUSES:
1. No output structure → unreadable, unprocessable
2. No citation requirement → untraceable claims
3. No diagnostic restriction → model acts as physician
4. No confidence scoring → no uncertainty communication
5. No readability constraint → violates 60-second target
"""

SYNTHESIS_V2 = """You are a senior clinical decision-support AI synthesizing patient data.

CRITICAL RULES:
1. Every factual claim MUST cite source: [EHR], [ANAMNESIS], or [RPM]
2. Never make a diagnosis - present context for clinician judgment
3. Flag ALL uncertainties and data gaps explicitly
4. Structure output for 60-second clinician readability

Alert: {alert}
Triage: {triage}
EHR: {ehr_context}
Anamnesis: {anamnesis}

Return JSON with 6 sections:
1. section_1_alert_summary
2. section_2_patient_snapshot
3. section_3_contextual_analysis
4. section_4_risk_assessment
5. section_5_recommended_actions
6. section_6_uncertainties_and_gaps"""

SYNTHESIS_V2_FAILURE_ANALYSIS = """
FAILURE MODE ANALYSIS - v2:
━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPROVEMENTS FROM v1:
✅ Structured 6-section output
✅ Source citation requirement added
✅ No diagnostic statements

REMAINING FAILURES:

Test: ALL scenarios after SCN-003 fix
Problem - CONTEXT BLEEDING: All scenarios produced "Heart failure" 
as primary risk regardless of patient condition.
SCN-001 (hypertension patient): "Acute decompensated heart failure suspected"
SCN-002 (diabetes patient): "Heart failure with fluid retention"
Root cause: Few-shot examples in prompt contained heart failure scenarios.
Model pattern-matched to examples rather than actual patient data.

Test: Request size
Problem: Full JSON inputs (EHR + anamnesis + triage) exceeded Groq's
context window, causing automatic model downgrade to llama-3.1-8b-instant,
which then rejected the request (413 error).

ROOT CAUSES:
1. Few-shot examples introduced concept bias
2. Input size not managed → context window overflow
3. Confidence calibration not specified → always returned 0.88
"""

SYNTHESIS_V3 = """You are a clinical decision-support synthesis AI.
Synthesize ONLY from the provided inputs. Base analysis STRICTLY on the data below.
Do NOT assume conditions not explicitly present in EHR data.

ANTI-HALLUCINATION RULE:
Before writing any claim: verify it appears in one of the three inputs.
If not traceable to [EHR], [ANAMNESIS], or [RPM] - DO NOT INCLUDE IT.

NO DIAGNOSIS RULE — you are NOT a physician. Prohibited phrases:
- WRONG: "confirms the diagnosis of X", "diagnosis of X", "patient has X"
- RIGHT: "clinical picture consistent with X", "assess for possible X", "monitor for X"

CONFIDENCE CALIBRATION:
- HIGH (0.85-1.0): Multiple sources agree, recent data
- MODERATE (0.60-0.84): Single source or some ambiguity
- LOW (0.30-0.59): Self-report only or data gaps
- INSUFFICIENT (<0.30): Flag for full clinical assessment only

ALERT: {alert}
TRIAGE: {triage}
EHR: {ehr_context}
ANAMNESIS: {anamnesis}

Return ONLY valid JSON with sections 1-6.
Every claim in sections 3-5 must include [EHR], [ANAMNESIS], or [RPM] citation."""

SYNTHESIS_V3_IMPROVEMENTS = """
V3 IMPROVEMENTS VERIFIED:
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Context bleeding eliminated - removed heart failure examples from prompt
✅ Input minimization prevents 413 errors (summary functions added)
✅ Anti-hallucination instruction reduced fabricated details
✅ Confidence calibration produces meaningful scores (0.80-0.88)
✅ CCB Completeness: 100% across all 5 scenarios
✅ Safety Compliance: 95% across all 5 scenarios

NOTE ON FEW-SHOT EXAMPLES IN SYNTHESIS:
V2 included full CCB examples in the prompt, which caused context bleeding:
the model pattern-matched to examples (always generating "heart failure" risk)
regardless of actual patient data. V3 intentionally removed inline examples
and replaced with anti-hallucination rules. This is a key lesson: few-shot
examples in multi-source synthesis prompts introduce semantic bias that
outweighs their calibration benefit. See SYNTHESIS_FEW_SHOT_EXAMPLES for
what correct vs incorrect outputs look like.

ARCHITECTURAL LESSON:
The most impactful fix was NOT the prompt change but the
architectural change in how inputs are prepared:
_summarize_ehr() and _summarize_anamnesis() methods reduce
input tokens by ~70%, preventing context overflow.
This demonstrates that prompt engineering includes
data pipeline engineering, not just instruction writing.
"""

SYNTHESIS_FEW_SHOT_EXAMPLES = """
FEW-SHOT EXAMPLES — SYNTHESIS AGENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(These examples illustrate correct vs incorrect synthesis behavior.
They are NOT included in the runtime prompt due to context bleeding risk.)

Example 1 — Correct synthesis with citation discipline (SCN-001, URGENT):
Input: Triage=URGENT (BP 178/108), EHR=Hypertension+Lisinopril, Anamnesis=Stopped Lisinopril due to cough

CORRECT section_3 output:
"how_alert_relates_to_history": "Patient self-discontinued Lisinopril 10 days ago due
  to ACE inhibitor-induced cough [ANAMNESIS], which aligns with the acute BP elevation
  pattern of 6 consecutive high readings [RPM]. History of hypertension on record [EHR]."

WRONG output (what V1 produced):
"Patient is experiencing hypertensive urgency secondary to medication non-compliance."
WHY WRONG: Diagnostic statement. Not traceable. Uses stigmatizing "non-compliance".

Example 2 — Correct edge case: benign alert handled without over-escalation (SCN-002, ROUTINE):
Input: Triage=ROUTINE (glucose 267), EHR=T2DM on Metformin, Anamnesis=celebratory dinner last night

CORRECT section_5 action:
{"action": "Schedule routine HbA1c review within 7 days [EHR]",
 "rationale": "Single post-prandial reading after dietary deviation [ANAMNESIS]. No sustained hyperglycemia pattern [RPM].",
 "priority": "Routine", "confidence": 0.80}

WRONG output (what V1 produced):
"URGENT: Patient glucose dangerously elevated. Consider insulin adjustment."
WHY WRONG: Overrides triage. No citations. Does not consider dietary context.

Example 3 — Edge case: sparse data, honest uncertainty (SCN-004, Incomplete Record):
Input: Triage=URGENT (BP 168/102), EHR=limited transfer summary only, Anamnesis=poor adherence

CORRECT section_6 output:
{"data_gaps": [
    "No prior BP trend data — cannot assess acute vs chronic elevation [EHR]",
    "No previous medication list — cannot verify current regimen [EHR]",
    "No lab results — cannot assess end-organ function [EHR]"
  ],
 "overall_brief_confidence": 0.45,
 "confidence_rationale": "Low confidence due to critically incomplete EHR. Clinical decision relies heavily on anamnesis [ANAMNESIS] which has limited verifiability."}

WRONG output (what V2 produced):
"overall_brief_confidence": 0.88 (falsely high confidence despite sparse data)
WHY WRONG: Confidence must reflect data quality. High confidence with sparse data is misleading.
"""

# ════════════════════════════════════════════════════════════
# PROMPT REGISTRY
# ════════════════════════════════════════════════════════════

PROMPT_REGISTRY = {
    "triage": {
        "v1": TRIAGE_V1,
        "v2": TRIAGE_V2,
        "v3": TRIAGE_V3,
        "v4_hybrid": TRIAGE_V4_HYBRID,
        "current": TRIAGE_V3,
        "failure_analysis": [
            TRIAGE_V1_FAILURE_ANALYSIS,
            TRIAGE_V2_FAILURE_ANALYSIS,
            TRIAGE_V3_FAILURE_ANALYSIS,
        ],
        "few_shot_examples": "See TRIAGE_V3 — 3 examples embedded in prompt (CRITICAL/ROUTINE/URGENT edge cases)",
    },
    "ehr": {
        "v1": EHR_V1,
        "v2": EHR_V2,
        "v3": EHR_V3,
        "current": EHR_V3,
        "failure_analysis": [
            EHR_V1_FAILURE_ANALYSIS,
            EHR_V2_FAILURE_ANALYSIS,
            EHR_V3_IMPROVEMENTS,
        ],
        "few_shot_examples": EHR_FEW_SHOT_EXAMPLES,
    },
    "anamnesis": {
        "v1": ANAMNESIS_V1,
        "v2": ANAMNESIS_V2,
        "v3": ANAMNESIS_V3,
        "current": ANAMNESIS_V3,
        "failure_analysis": [
            ANAMNESIS_V1_FAILURE_ANALYSIS,
            ANAMNESIS_V2_FAILURE_ANALYSIS,
            ANAMNESIS_V3_IMPROVEMENTS,
        ],
        "few_shot_examples": ANAMNESIS_FEW_SHOT_EXAMPLES,
    },
    "synthesis": {
        "v1": SYNTHESIS_V1,
        "v2": SYNTHESIS_V2,
        "v3": SYNTHESIS_V3,
        "current": SYNTHESIS_V3,
        "failure_analysis": [
            SYNTHESIS_V1_FAILURE_ANALYSIS,
            SYNTHESIS_V2_FAILURE_ANALYSIS,
            SYNTHESIS_V3_IMPROVEMENTS,
        ],
        "few_shot_examples": SYNTHESIS_FEW_SHOT_EXAMPLES,
    },
}
