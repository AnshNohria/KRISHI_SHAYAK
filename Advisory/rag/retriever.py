"""Retrieve advisory chunks from ChromaDB collection (HTTP or local persistent)."""
import os
from pathlib import Path
from typing import List, Dict
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
try:
    import chromadb
    from chromadb.config import Settings
except Exception:  # pragma: no cover - optional dependency path
    chromadb = None
    Settings = None

# Resolve repo root: Advisory/rag -> Advisory -> repo
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = str(PROJECT_ROOT / 'data' / 'vector' / 'chroma')
MODEL_NAME = 'all-MiniLM-L6-v2'
_model = None
_client = None
_collection = None

def _load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def _get_collection():
    global _client, _collection
    if chromadb is None:
        return None
    if _client is None:
        # Prefer HTTP client if env vars are provided
        http_url = os.getenv('CHROMA_HTTP_URL')
        host = os.getenv('CHROMA_HOST')
        port = os.getenv('CHROMA_PORT')
        try:
            if http_url:
                parsed = urlparse(http_url)
                h = parsed.hostname or 'localhost'
                p = parsed.port or 8000
                _client = chromadb.HttpClient(host=h, port=p, settings=Settings(anonymized_telemetry=False))
            elif host or port:
                h = host or 'localhost'
                p = int(port or 8000)
                _client = chromadb.HttpClient(host=h, port=p, settings=Settings(anonymized_telemetry=False))
            else:
                _client = chromadb.PersistentClient(path=DATA_DIR, settings=Settings(anonymized_telemetry=False))
        except Exception:
            return None
    if _collection is None:
        try:
            _collection = _client.get_collection('icar_advisory')
        except Exception:
            # Create empty collection if not exists
            try:
                _collection = _client.create_collection('icar_advisory', metadata={"hnsw:space": "cosine"})
            except Exception:
                return None
    return _collection

class AdvisoryRetriever:
    def __init__(self):
        # Ensure collection is initialized if chromadb is available; else noop
        _get_collection()

    def query(self, text: str, k: int = 4, min_score: float = 0.25) -> List[Dict]:
        print(f"🔍 Query called with text='{text}', k={k}, min_score={min_score}")
        if not text.strip():
            print("❌ Empty query text")
            return []
        col = _get_collection()
        if col is None:
            print("❌ Could not get collection")
            return []
        print(f"✅ Got collection with {col.count()} documents")
        # Embed query explicitly to ensure same model/normalization as ingestion
        model = _load_model()
        print(f"✅ Loaded embedding model: {MODEL_NAME}")
        q_emb = model.encode([text], normalize_embeddings=True).tolist()
        print(f"✅ Generated embedding, length: {len(q_emb[0])}")
        try:
            res = col.query(query_embeddings=q_emb, n_results=k, include=['documents','metadatas','distances'])
            print(f"✅ ChromaDB query returned: {len(res.get('documents', [[]])[0])} results")
        except Exception as e:
            print(f"❌ ChromaDB query failed: {e}")
            return []
        docs: List[Dict] = []
        if not res or not res.get('documents'):
            return docs
        docs_list = res['documents'][0]
        metas_list = res.get('metadatas', [[]])[0]
        dists = res.get('distances', [[]])[0]
        # Convert distance (cosine distance if configured) to similarity ~ 1 - dist
        for doc, meta, dist in zip(docs_list, metas_list, dists):
            score = 1.0 - float(dist) if dist is not None else 0.0
            if score < min_score:
                continue
            docs.append({
                'text': doc,
                'source': (meta or {}).get('source', ''),
                'page_start': (meta or {}).get('page_start'),
                'page_end': (meta or {}).get('page_end'),
                'heading': (meta or {}).get('heading', ''),
                'score': score
            })
        return docs

_retriever_instance: AdvisoryRetriever = None

def get_retriever() -> AdvisoryRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = AdvisoryRetriever()
    return _retriever_instance
