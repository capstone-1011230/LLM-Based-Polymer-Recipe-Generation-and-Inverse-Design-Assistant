"""
ClinicalBridge — RAG Pipeline
EHR verilerini ChromaDB'ye yükler ve semantic search yapar.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent / "core" / "chroma_db"


def ehr_to_documents(ehr: Dict, patient_id: str) -> List[Document]:
    """Convert EHR JSON into LangChain Documents for embedding."""
    docs = []

    # 1. Visit notes → each note is its own document
    for note in ehr.get("visit_notes", []):
        content = f"""
VISIT NOTE — Patient: {patient_id}
Date: {note.get('date', 'Unknown')}
Provider: {note.get('provider', 'Unknown')}
Type: {note.get('type', 'Unknown')}
Vitals: BP {note.get('vital_signs', {}).get('bp', 'N/A')}, HR {note.get('vital_signs', {}).get('hr', 'N/A')}, Weight {note.get('vital_signs', {}).get('weight_kg', 'N/A')} kg, SpO2 {note.get('vital_signs', {}).get('spo2', 'N/A')}%
Note: {note.get('note', '')}
""".strip()
        docs.append(Document(
            page_content=content,
            metadata={
                "patient_id": patient_id,
                "doc_type": "visit_note",
                "date": note.get("date", ""),
                "provider": note.get("provider", ""),
                "source": f"visit_note_{note.get('date','')}",
            }
        ))

    # 2. Medication list → single document
    meds = ehr.get("medications", [])
    if meds:
        med_lines = "\n".join([
            f"- {m.get('name','?')} {m.get('dose','?')} {m.get('frequency','?')} "
            f"[Status: {m.get('status','?')}] [Prescribed: {m.get('prescribed_date','?')}] "
            f"[Dr: {m.get('prescribing_physician','?')}]"
            for m in meds
        ])
        docs.append(Document(
            page_content=f"MEDICATION LIST — Patient: {patient_id}\n{med_lines}",
            metadata={"patient_id": patient_id, "doc_type": "medications", "source": "medication_list"}
        ))

    # 3. Problem list → single document
    problems = ehr.get("problem_list", [])
    if problems:
        prob_lines = "\n".join([
            f"- {p.get('condition','?')} (ICD-10: {p.get('icd10','?')}) "
            f"[Status: {p.get('status','?')}] [Onset: {p.get('onset_date','?')}] "
            f"[Severity: {p.get('severity','?')}]"
            for p in problems
        ])
        docs.append(Document(
            page_content=f"PROBLEM LIST — Patient: {patient_id}\n{prob_lines}",
            metadata={"patient_id": patient_id, "doc_type": "problem_list", "source": "problem_list"}
        ))

    # 4. Lab results → grouped by date
    labs = ehr.get("lab_results", [])
    if labs:
        # Group by date
        by_date: Dict[str, List] = {}
        for lab in labs:
            d = lab.get("date", "unknown")
            by_date.setdefault(d, []).append(lab)
        for date, lab_list in by_date.items():
            lab_lines = "\n".join([
                f"- {l.get('test','?')}: {l.get('value','?')} {l.get('unit','?')} [{l.get('status','?')}]"
                for l in lab_list
            ])
            docs.append(Document(
                page_content=f"LAB RESULTS — Patient: {patient_id} — Date: {date}\n{lab_lines}",
                metadata={"patient_id": patient_id, "doc_type": "lab_results", "date": date, "source": f"labs_{date}"}
            ))

    # 5. Allergies
    allergies = ehr.get("allergies", [])
    if allergies:
        allergy_lines = "\n".join([
            f"- {a.get('allergen','?')}: {a.get('reaction','?')} [Severity: {a.get('severity','?')}]"
            for a in allergies
        ])
        docs.append(Document(
            page_content=f"ALLERGIES & ADVERSE REACTIONS — Patient: {patient_id}\n{allergy_lines}",
            metadata={"patient_id": patient_id, "doc_type": "allergies", "source": "allergy_list"}
        ))

    # 6. Patient demographics summary
    info = ehr.get("patient_info", {})
    docs.append(Document(
        page_content=(
            f"PATIENT INFO — ID: {patient_id}\n"
            f"Name: {info.get('name','?')}, Age: {info.get('age','?')}, Sex: {info.get('sex','?')}\n"
            f"DOB: {info.get('dob','?')}, MRN: {info.get('mrn','?')}\n"
            f"Primary Care: {info.get('primary_care_physician','?')}"
        ),
        metadata={"patient_id": patient_id, "doc_type": "demographics", "source": "patient_info"}
    ))

    return docs


class EHRVectorStore:
    """ChromaDB-backed vector store for EHR documents."""

    def __init__(self, persist_directory: str = str(CHROMA_DIR)):
        self.persist_directory = persist_directory
        print("  Loading embedding model (this may take a moment on first run)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " "],
        )
        self.vectorstore = None

    def build_index(self, ehr_dir: str = str(DATA_DIR / "ehr")) -> None:
        """Load all EHR JSON files and build ChromaDB index."""
        all_docs = []
        ehr_path = Path(ehr_dir)

        for ehr_file in sorted(ehr_path.glob("*.json")):
            patient_id = ehr_file.stem.replace("_ehr", "")
            with open(ehr_file, encoding="utf-8") as f:
                ehr = json.load(f)
            docs = ehr_to_documents(ehr, patient_id)
            chunks = self.splitter.split_documents(docs)
            all_docs.extend(chunks)
            print(f"    Indexed {patient_id}: {len(docs)} documents → {len(chunks)} chunks")

        print(f"\n  Building ChromaDB index with {len(all_docs)} total chunks...")
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vectorstore = Chroma.from_documents(
            documents=all_docs,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_name="ehr_collection",
        )
        print(f"  ✓ Index built and persisted at {self.persist_directory}")

    def load_index(self) -> bool:
        """Load existing ChromaDB index."""
        if not Path(self.persist_directory).exists():
            return False
        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name="ehr_collection",
            )
            return True
        except Exception:
            return False

    def search(self, query: str, patient_id: str, k: int = 5) -> List[Document]:
        """Semantic search filtered to a specific patient."""
        if self.vectorstore is None:
            raise RuntimeError("Vector store not loaded. Call build_index() or load_index() first.")
        results = self.vectorstore.similarity_search(
            query,
            k=k,
            filter={"patient_id": patient_id},
        )
        return results

    def search_multi_query(self, queries: List[str], patient_id: str, k_per_query: int = 3) -> List[Document]:
        """Run multiple queries and deduplicate results."""
        seen_contents = set()
        all_results = []
        for q in queries:
            results = self.search(q, patient_id, k=k_per_query)
            for doc in results:
                if doc.page_content not in seen_contents:
                    seen_contents.add(doc.page_content)
                    all_results.append(doc)
        return all_results

    def format_context(self, docs: List[Document]) -> str:
        """Format retrieved documents into a context string for the LLM."""
        if not docs:
            return "NO EHR DOCUMENTS RETRIEVED FOR THIS PATIENT."
        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            parts.append(
                f"[Document {i} | Type: {meta.get('doc_type','?')} | "
                f"Date: {meta.get('date','N/A')} | Source: {meta.get('source','?')}]\n"
                f"{doc.page_content}"
            )
        return "\n\n---\n\n".join(parts)


def build_or_load_vectorstore() -> EHRVectorStore:
    """Build if not exists, else load existing index."""
    store = EHRVectorStore()
    if store.load_index():
        print("  ✓ Loaded existing ChromaDB index")
    else:
        print("  Building new ChromaDB index...")
        store.build_index()
    return store


if __name__ == "__main__":
    print("\n🗄️  Building EHR Vector Store...")
    store = EHRVectorStore()
    store.build_index()
    # Quick test
    print("\n🔍 Test search: 'hypertension medication blood pressure'")
    results = store.search("hypertension medication blood pressure", "P001", k=3)
    for r in results:
        print(f"  → [{r.metadata.get('doc_type')}] {r.page_content[:100]}...")
    print("\n✅ RAG pipeline ready!")
