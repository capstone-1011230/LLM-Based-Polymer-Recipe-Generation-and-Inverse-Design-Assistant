"""
ClinicalBridge - Simulated Patient Data Generator
ALL DATA IS ENTIRELY FICTIONAL - NO REAL PATIENTS
"""

import json
import random
import os
from datetime import datetime, timedelta

random.seed(42)

def rnd_date(start_days_ago, end_days_ago=0):
    days = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

def rnd_ts(days_ago=0, hour=None):
    h = hour if hour is not None else random.randint(0, 23)
    m = random.randint(0, 59)
    base = datetime.now() - timedelta(days=days_ago)
    return base.replace(hour=h, minute=m, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:00")

def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"  saved -> {path}")

PATIENTS = [
    {"id":"P001","name":"Margaret Sullivan","age":68,"sex":"F","conditions":["hypertension","heart_failure"],"medications":["lisinopril","furosemide","metoprolol"]},
    {"id":"P002","name":"Robert Chen","age":54,"sex":"M","conditions":["type2_diabetes","hypertension"],"medications":["metformin","amlodipine","atorvastatin"]},
    {"id":"P003","name":"Eleanor Vasquez","age":72,"sex":"F","conditions":["heart_failure","atrial_fibrillation"],"medications":["warfarin","digoxin","furosemide"]},
    {"id":"P004","name":"James Okonkwo","age":61,"sex":"M","conditions":["type2_diabetes","chronic_kidney_disease"],"medications":["insulin_glargine","lisinopril","erythropoietin"]},
    {"id":"P005","name":"Patricia Novak","age":58,"sex":"F","conditions":["hypertension","asthma"],"medications":["amlodipine","salbutamol","budesonide"]},
    {"id":"P006","name":"David Fitzgerald","age":77,"sex":"M","conditions":["heart_failure","type2_diabetes","hypertension"],"medications":["bisoprolol","empagliflozin","ramipril"]},
    {"id":"P007","name":"Susan Park","age":45,"sex":"F","conditions":["type1_diabetes","hypertension"],"medications":["insulin_aspart","insulin_glargine","losartan"]},
    {"id":"P008","name":"Thomas Meier","age":83,"sex":"M","conditions":["atrial_fibrillation","heart_failure"],"medications":["apixaban","digoxin","carvedilol"]},
    {"id":"P009","name":"Linda Osei","age":63,"sex":"F","conditions":["hypertension","type2_diabetes","obesity"],"medications":["metformin","hydrochlorothiazide","orlistat"]},
    {"id":"P010","name":"Carlos Rivera","age":50,"sex":"M","conditions":["hypertension","anxiety_disorder"],"medications":["ramipril","sertraline"]},
]

ICD10 = {
    "hypertension":"I10","heart_failure":"I50.9","type2_diabetes":"E11.9",
    "type1_diabetes":"E10.9","atrial_fibrillation":"I48.91",
    "chronic_kidney_disease":"N18.3","asthma":"J45.909",
    "obesity":"E66.9","anxiety_disorder":"F41.1",
}

def generate_ehr(patient):
    pid = patient["id"]
    conditions = patient["conditions"]
    problem_list = []
    for c in conditions:
        problem_list.append({
            "condition": c.replace("_"," ").title(),
            "icd10": ICD10.get(c,"Z99.9"),
            "onset_date": rnd_date(3650, 365),
            "status": "Active",
            "severity": random.choice(["Mild","Moderate","Moderate","Severe"]),
        })
    dose_map = {
        "lisinopril":"10mg","furosemide":"40mg","metoprolol":"50mg",
        "metformin":"1000mg","amlodipine":"5mg","atorvastatin":"40mg",
        "warfarin":"5mg","digoxin":"0.125mg","insulin_glargine":"20 units",
        "insulin_aspart":"variable","losartan":"50mg","bisoprolol":"5mg",
        "empagliflozin":"10mg","ramipril":"5mg","apixaban":"5mg",
        "carvedilol":"12.5mg","hydrochlorothiazide":"25mg","orlistat":"120mg",
        "salbutamol":"2 puffs PRN","budesonide":"200mcg","sertraline":"50mg",
        "erythropoietin":"4000 units SC 3x/week",
    }
    medications = []
    for med in patient["medications"]:
        medications.append({
            "name": med.replace("_"," ").title(),
            "dose": dose_map.get(med,"standard dose"),
            "frequency": random.choice(["Once daily","Twice daily","As needed"]),
            "prescribed_date": rnd_date(730, 30),
            "prescribing_physician": random.choice(["Dr. Williams","Dr. Patel","Dr. Nakamura"]),
            "status": "Active",
        })
    visit_notes = []
    for i in range(random.randint(4,6)):
        visit_notes.append({
            "date": rnd_date(365, i*30),
            "provider": random.choice(["Dr. Williams","Dr. Patel","Dr. Nakamura"]),
            "type": random.choice(["Follow-up","Urgent Visit","Annual Review"]),
            "note": f"Patient presents for {conditions[0].replace('_',' ')} follow-up. BP {random.randint(120,180)}/{random.randint(80,110)}. Continue current regimen.",
            "vital_signs": {
                "bp": f"{random.randint(120,180)}/{random.randint(80,110)}",
                "hr": random.randint(58,105),
                "weight_kg": round(random.uniform(60,115),1),
                "spo2": random.randint(94,100),
            },
        })
    lab_results = []
    for days_ago in [90, 30, 7]:
        lab_results.append({
            "test": "Creatinine","value": round(random.uniform(0.7,2.0),2),
            "unit":"mg/dL","date":rnd_date(days_ago+5,days_ago),"status":"Normal"
        })
        if "hypertension" in conditions or "heart_failure" in conditions:
            lab_results.append({
                "test":"Potassium","value":round(random.uniform(3.5,5.0),1),
                "unit":"mEq/L","date":rnd_date(days_ago+5,days_ago),"status":"Normal"
            })
        if "type2_diabetes" in conditions or "type1_diabetes" in conditions:
            lab_results.append({
                "test":"HbA1c","value":round(random.uniform(6.5,10.5),1),
                "unit":"%","date":rnd_date(days_ago+5,days_ago),
                "status":"Abnormal" if random.random()>0.5 else "Normal"
            })
        if "atrial_fibrillation" in conditions:
            lab_results.append({
                "test":"INR","value":round(random.uniform(1.4,3.5),1),
                "unit":"ratio","date":rnd_date(days_ago+5,days_ago),
                "status":"Abnormal" if random.random()>0.6 else "Normal"
            })
    allergies = []
    if random.random() > 0.5:
        allergies = [{"allergen":"ACE Inhibitors","reaction":"Persistent cough","severity":"Mild"}]
    return {
        "patient_id": pid,
        "patient_info": {
            "name":patient["name"],"age":patient["age"],"sex":patient["sex"],
            "mrn":f"MRN-{pid}-2019",
            "primary_care_physician":random.choice(["Dr. Williams","Dr. Patel","Dr. Nakamura"]),
        },
        "problem_list": problem_list,
        "medications": medications,
        "allergies": allergies,
        "lab_results": sorted(lab_results, key=lambda x:x["date"], reverse=True),
        "visit_notes": sorted(visit_notes, key=lambda x:x["date"], reverse=True),
        "generated_note": "SIMULATED DATA - NOT REAL PATIENT RECORD",
    }

def generate_rpm(patient):
    pid = patient["id"]
    conditions = patient["conditions"]
    readings = []
    for day in range(14, 0, -1):
        for hour in [7, 13, 21]:
            r = {"timestamp":rnd_ts(days_ago=day,hour=hour),"patient_id":pid}
            if "hypertension" in conditions or "heart_failure" in conditions:
                if day <= 2:
                    r["blood_pressure"] = {"systolic":random.randint(155,185),"diastolic":random.randint(95,115)}
                else:
                    r["blood_pressure"] = {"systolic":random.randint(125,145),"diastolic":random.randint(82,92)}
            else:
                r["blood_pressure"] = {"systolic":random.randint(115,130),"diastolic":random.randint(72,85)}
            r["heart_rate_bpm"] = random.randint(55,130) if "atrial_fibrillation" in conditions else random.randint(58,88)
            if "type2_diabetes" in conditions or "type1_diabetes" in conditions:
                r["glucose_mg_dl"] = random.randint(90,310) if day<=3 else random.randint(90,180)
            r["spo2_percent"] = random.randint(92,97) if ("heart_failure" in conditions and day<=2) else random.randint(96,100)
            if "heart_failure" in conditions:
                r["weight_kg"] = round(82.0 + (14-day)*0.22 + random.uniform(-0.3,0.3),1)
            readings.append(r)
    latest = readings[-1]
    alert = None
    bp = latest.get("blood_pressure",{})
    if bp.get("systolic",0) >= 180:
        alert = {
            "alert_id":f"ALT-{pid}","patient_id":pid,
            "timestamp":latest["timestamp"],"device_type":"Blood Pressure Monitor",
            "alert_type":"CRITICAL_BP","measured_values":bp,
            "threshold_breached":"Systolic >= 180 mmHg",
            "patient_baseline":{"systolic":135,"diastolic":85},
            "consecutive_high_readings":random.randint(3,8),
            "alert_message":f"Critical BP {bp.get('systolic','?')}/{bp.get('diastolic','?')} mmHg detected.",
        }
    elif latest.get("glucose_mg_dl",0) >= 250:
        alert = {
            "alert_id":f"ALT-{pid}","patient_id":pid,
            "timestamp":latest["timestamp"],"device_type":"CGM",
            "alert_type":"HIGH_GLUCOSE","measured_values":{"glucose_mg_dl":latest["glucose_mg_dl"]},
            "threshold_breached":"Glucose >= 250 mg/dL",
            "patient_baseline":{"glucose_mg_dl":130},
            "alert_message":f"High glucose {latest['glucose_mg_dl']} mg/dL detected.",
        }
    elif latest.get("spo2_percent",100) <= 93:
        alert = {
            "alert_id":f"ALT-{pid}","patient_id":pid,
            "timestamp":latest["timestamp"],"device_type":"Pulse Oximeter",
            "alert_type":"LOW_SPO2","measured_values":{"spo2":latest["spo2_percent"]},
            "threshold_breached":"SpO2 <= 93%",
            "patient_baseline":{"spo2":97},
            "alert_message":f"Low SpO2 {latest['spo2_percent']}% detected.",
        }
    return {
        "patient_id":pid,"readings":readings,"active_alert":alert,
        "generated_note":"SIMULATED DATA - NOT REAL PATIENT RECORD",
    }

def generate_anamnesis(patient):
    pid = patient["id"]
    primary = patient["conditions"][0]
    narratives = {
        "hypertension":["I stopped taking my blood pressure pill about 10 days ago because it was making me cough all the time.","I have been having morning headaches for the past week."],
        "heart_failure":["My ankles have been really swollen for the past two weeks.","I get out of breath just walking to the kitchen."],
        "type2_diabetes":["I went to a wedding last weekend and ate a lot of sweets. My sugar has been high since then.","I ran out of metformin four days ago."],
        "atrial_fibrillation":["My heart feels like it is fluttering or skipping beats.","I forgot to take my warfarin for three days."],
    }
    chosen = random.choice(narratives.get(primary, ["I have not been feeling well recently."]))
    adherence = random.choice(["Full adherence","Missed doses this week","Stopped one medication","Irregular adherence"])
    return {
        "patient_id":pid,
        "intake_date":rnd_date(1,0),
        "chief_complaint":chosen,
        "medication_adherence":{
            "status":adherence,
            "detail":"Patient stopped Lisinopril 10 days ago due to persistent cough." if "Stopped" in adherence else f"Patient missed doses this week.",
        },
        "review_of_systems":{
            "cardiovascular":random.choice(["No chest pain","Occasional palpitations","Mild chest tightness"]),
            "respiratory":random.choice(["No cough","Mild shortness of breath","Persistent dry cough"]),
            "general":random.choice(["Fatigue","Feeling well","Weight gain of 3 kg in 2 weeks"]),
        },
        "lifestyle_factors":{
            "physical_activity":random.choice(["Walks 20 min daily","No exercise","Dog walks twice daily"]),
            "diet":random.choice(["Low salt diet","High salt, daughter cooks","Processed food recently"]),
            "alcohol":random.choice(["None","Occasional"]),
            "smoking":random.choice(["Never","Former smoker"]),
        },
        "family_history":random.choice(["Father had heart attack at 65","Mother had stroke at 70","No significant family history"]),
        "patient_concerns":random.choice(["Worried condition is worsening","Wants to know if ER needed","Does not want more medications"]),
        "symptom_diary":[
            {"date":rnd_date(7,7),"entry":f"Symptoms started. {chosen}"},
            {"date":rnd_date(3,3),"entry":"Symptoms persisting. Took medication but not feeling better."},
            {"date":rnd_date(1,1),"entry":"Still not right. Decided to contact clinic."},
        ],
        "generated_note":"SIMULATED DATA - NOT REAL PATIENT RECORD",
    }

def generate_scenarios():
    return [
        {
            "scenario_id":"SCN-001","title":"The Missed Medication","patient_id":"P001",
            "description":"Hypertensive patient BP spikes. Anamnesis reveals stopped ACE inhibitor due to cough.",
            "triggering_alert":{"alert_type":"CRITICAL_BP","measured_values":{"systolic":178,"diastolic":108},"consecutive_high_readings":6,"alert_message":"Critical BP 178/108 mmHg, 6 consecutive high readings."},
            "key_ehr_facts":["Active diagnosis: Hypertension (I10)","Current medication: Lisinopril 10mg daily","Last visit: BP well-controlled at 128/82 two months ago"],
            "key_anamnesis_facts":["Patient stopped Lisinopril 10 days ago due to persistent dry cough","Reports morning headaches for 1 week"],
            "expected_urgency":"URGENT",
            "gold_standard_brief":{"primary_concern":"Hypertensive urgency secondary to self-discontinuation of ACE inhibitor due to cough side effect.","recommended_actions":["Contact patient immediately","Switch to ARB (e.g. Losartan)","Recheck BP in 24-48 hours"],"confidence":0.91},
        },
        {
            "scenario_id":"SCN-002","title":"The False Alarm","patient_id":"P002",
            "description":"Diabetic patient glucose alert. Anamnesis reveals planned dietary change - alert is benign.",
            "triggering_alert":{"alert_type":"HIGH_GLUCOSE","measured_values":{"glucose_mg_dl":267},"alert_message":"High glucose 267 mg/dL detected."},
            "key_ehr_facts":["Type 2 Diabetes (E11.9)","Metformin increased 5 days ago","Physician note: expect transient glucose fluctuation during titration"],
            "key_anamnesis_facts":["Patient attended celebration dinner last night","Confirms full medication adherence","Fasting glucose this morning was 142 mg/dL"],
            "expected_urgency":"ROUTINE",
            "gold_standard_brief":{"primary_concern":"Post-prandial glucose spike attributable to dietary deviation during medication titration. Likely benign.","recommended_actions":["No immediate intervention","Monitor next 3 fasting readings","Reinforce dietary counseling"],"confidence":0.87},
        },
        {
            "scenario_id":"SCN-003","title":"The Silent Deterioration","patient_id":"P006",
            "description":"Heart failure patient gradual weight gain over 2 weeks. Trend suggests fluid retention.",
            "triggering_alert":{"alert_type":"WEIGHT_TREND","measured_values":{"weight_kg":89.4,"baseline_weight_kg":83.0,"gain_kg":6.4,"period_days":14},"alert_message":"Gradual weight gain 6.4 kg over 14 days."},
            "key_ehr_facts":["Heart Failure (I50.9)","Last BNP 450 pg/mL elevated","EF 35% on echo","Furosemide NOT currently prescribed"],
            "key_anamnesis_facts":["Bilateral ankle swelling worsening 2 weeks","Shortness of breath walking to bathroom","Sleeping on 2 pillows instead of 1"],
            "expected_urgency":"CRITICAL",
            "gold_standard_brief":{"primary_concern":"High suspicion acute decompensated heart failure with fluid retention.","recommended_actions":["Urgent clinical assessment within 24h","Consider initiating Furosemide","Order BNP and CXR","Consider ED if acutely dyspneic"],"confidence":0.94},
        },
        {
            "scenario_id":"SCN-004","title":"The Incomplete Record","patient_id":"P010",
            "description":"Transferred patient. EHR sparse. System must rely on anamnesis and flag gaps.",
            "triggering_alert":{"alert_type":"CRITICAL_BP","measured_values":{"systolic":168,"diastolic":102},"alert_message":"Critical BP 168/102 mmHg in recently registered patient."},
            "key_ehr_facts":["EHR imported from external system - HIGH INCOMPLETENESS","Only available: Name, DOB, one medication (Ramipril 5mg)","No lab results, no visit notes"],
            "key_anamnesis_facts":["Patient self-reports hypertension for 8 years","Also reports anxiety disorder on sertraline","Reports Ramipril causes dizziness - considering stopping"],
            "expected_urgency":"URGENT",
            "gold_standard_brief":{"primary_concern":"BP elevation in newly transferred patient with critically incomplete EHR.","recommended_actions":["Expedite record transfer - URGENT","Obtain complete medication list from patient","Schedule urgent review within 48h"],"confidence":0.62},
        },
        {
            "scenario_id":"SCN-005","title":"The Conflicting Data","patient_id":"P003",
            "description":"Patient reports full adherence but lab results show sub-therapeutic drug levels.",
            "triggering_alert":{"alert_type":"LOW_SPO2","measured_values":{"spo2":93},"alert_message":"SpO2 93% in atrial fibrillation patient on anticoagulation."},
            "key_ehr_facts":["Atrial Fibrillation (I48.91)","Warfarin 5mg daily","Last INR: 1.4 (sub-therapeutic, target 2.0-3.0)","Digoxin level: 0.6 ng/mL (sub-therapeutic)"],
            "key_anamnesis_facts":["Patient insists she takes ALL medications exactly as prescribed","Denies any missed doses","Reports new fatigue and mild shortness of breath for 1 week"],
            "expected_urgency":"URGENT",
            "gold_standard_brief":{"primary_concern":"Clinically significant discrepancy between reported adherence and sub-therapeutic drug levels. Elevated stroke risk.","recommended_actions":["Urgent INR recheck","Assess SpO2 for respiratory cause","Investigate INR drop non-accusatorily","Cardiology consultation"],"confidence":0.83},
        },
    ]

def main():
    print("\nClinicalBridge - Simulated Data Generator")
    print("ALL DATA IS ENTIRELY FICTIONAL\n")
    base = os.path.dirname(os.path.abspath(__file__))
    for patient in PATIENTS:
        pid = patient["id"]
        print(f"Generating {patient['name']} ({pid})...")
        save(f"{base}/ehr/{pid}_ehr.json", generate_ehr(patient))
        save(f"{base}/rpm/{pid}_rpm.json", generate_rpm(patient))
        save(f"{base}/anamnesis/{pid}_anamnesis.json", generate_anamnesis(patient))
    print("\nGenerating scenarios...")
    scenarios = generate_scenarios()
    save(f"{base}/scenarios/all_scenarios.json", scenarios)
    for s in scenarios:
        save(f"{base}/scenarios/{s['scenario_id']}.json", s)
    save(f"{base}/patient_index.json", [{"id":p["id"],"name":p["name"],"conditions":p["conditions"]} for p in PATIENTS])
    print(f"\nDone! 10 patients x 3 files + 5 scenarios generated.")

if __name__ == "__main__":
    main()
