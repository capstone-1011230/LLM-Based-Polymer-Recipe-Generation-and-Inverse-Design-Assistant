# ClinicalBridge 🏥
### Multi-Agent Clinical Decision Support System
**COP-3442 Prompt Engineering — Capstone Project**

> ⚠️ EDUCATIONAL PROTOTYPE — All data is simulated. Not for clinical use.

---

## 🏗️ Architecture

```
RPM Alert → [Triage Agent] → urgency + queries
                           ↓
              ┌────────────┴────────────┐
         [EHR Agent]              [Anamnesis Agent]
         RAG/ChromaDB             Patient self-report
              └────────────┬────────────┘
                           ↓
                   [Synthesis Agent]
                           ↓
               Clinical Context Brief (CCB)
```

## 📁 Project Structure

```
clinicalbridge/
├── main.py                    # Entry point
├── requirements.txt
├── .env                       # GROQ_API_KEY (not committed)
├── data/
│   ├── generate_data.py       # Simulated data generator
│   ├── ehr/                   # 10 patient EHR JSON files
│   ├── rpm/                   # 10 patient RPM JSON files
│   ├── anamnesis/             # 10 patient anamnesis JSON files
│   └── scenarios/             # 5 clinical test scenarios
├── agents/
│   └── agents.py              # 4 LangChain agents
├── core/
│   ├── orchestrator.py        # Multi-agent coordinator
│   ├── rag_pipeline.py        # ChromaDB EHR vector store
│   └── chroma_db/             # Persisted vector index
├── prompts/
│   └── prompt_library.py      # All prompts (v1, v2, v3) + iteration logs
├── evaluation/
│   └── evaluator.py           # Metrics framework
└── reports/                   # Session outputs + evaluation reports
```

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create .env file
```
GROQ_API_KEY=your_key_here
```

### 3. Generate simulated data
```bash
python data/generate_data.py
```

### 4. Build EHR vector index (first time only)
```bash
python main.py --build-index
```

### 5. Run a scenario
```bash
python main.py                     # SCN-001: Missed Medication
python main.py --scenario SCN-002  # SCN-002: False Alarm
python main.py --scenario SCN-003  # SCN-003: Silent Deterioration
python main.py --scenario SCN-004  # SCN-004: Incomplete Record
python main.py --scenario SCN-005  # SCN-005: Conflicting Data
python main.py --all               # All scenarios + evaluation report
```

### 6. Run without RAG (faster, no ChromaDB needed)
```bash
python main.py --no-rag
```

---

## 🤖 Agents

| Agent | LLM Temp | Module | Purpose |
|-------|----------|--------|---------|
| Alert Triage Agent | 0.05 | M2,M3,M4 | Classify urgency, formulate queries |
| EHR Retrieval Agent | 0.00 | M6,M7 | RAG search over patient EHR |
| Anamnesis Agent | 0.10 | M3,M4,M7 | Interpret patient self-report |
| Synthesis Agent | 0.15 | M4,M6,M8 | Build Clinical Context Brief |

## 📋 Clinical Scenarios

| ID | Title | Patient | Challenge |
|----|-------|---------|-----------|
| SCN-001 | The Missed Medication | P001 | ACE inhibitor stopped → BP spike |
| SCN-002 | The False Alarm | P002 | Glucose spike = dietary, not pathological |
| SCN-003 | The Silent Deterioration | P006 | Gradual weight gain trend in HF |
| SCN-004 | The Incomplete Record | P010 | Sparse EHR, rely on anamnesis |
| SCN-005 | The Conflicting Data | P003 | Self-report contradicts lab results |

## 📊 Evaluation Targets

| Metric | Target |
|--------|--------|
| Urgency accuracy | ≥ 90% |
| CCB completeness | ≥ 85% |
| Safety compliance | ≥ 90% |
| Hallucination rate | ≤ 5% |
| Latency | ≤ 30s |

---

## 🔧 Tech Stack
- **LLM**: Groq (llama-3.1-8b-instant) — free tier
- **Framework**: LangChain v0.2+
- **Vector Store**: ChromaDB
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Language**: Python 3.11+

---

*Bahçeşehir University | AI Engineering | COP-3442 Prompt Engineering*
