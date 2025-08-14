"""Ingest ICAR seasonal advisory PDFs into a ChromaDB store (HTTP or local)."""
import os, hashlib, json, re, tempfile
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from pypdf import PdfReader
import requests
from sentence_transformers import SentenceTransformer
try:
    import chromadb
    from chromadb.config import Settings
except Exception:  # pragma: no cover - optional dependency path
    chromadb = None
    Settings = None

DATA_DIR = Path('data/vector')
STORE_DIR = DATA_DIR / 'icar_store'
CHROMA_DIR = DATA_DIR / 'chroma'
MANIFEST = DATA_DIR / 'icar_manifest.json'

MODEL_NAME = 'all-MiniLM-L6-v2'
_model = None
_client = None
_collection = None

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

@dataclass
class Chunk:
    id: str
    source: str
    page_start: int
    page_end: int
    heading: str
    text: str

HEADING_RE = re.compile(r'^(?:[A-Z][A-Z \-/]{4,}|[A-Z][A-Za-z ]{3,}\d{0,2})$')

def extract_pdf(path: Path) -> List[str]:
    reader = PdfReader(str(path))
    pages = []
    for i,p in enumerate(reader.pages):
        try:
            t = p.extract_text() or ''
        except Exception:
            t = ''
        t = re.sub(r'[ \t]+', ' ', t)
        t = re.sub(r'\n{2,}', '\n', t)
        pages.append(t.strip())
    return pages

def split_into_chunks(pages: List[str], source: str, target_chars=900, overlap=120) -> List[Chunk]:
    chunks: List[Chunk] = []
    buffer = []
    char_count = 0
    start_page = 0
    def flush(end_page:int):
        nonlocal buffer, char_count, start_page
        if not buffer:
            return
        text = '\n'.join(buffer).strip()
        # detect heading (first line all-caps or Title like)
        first_line = text.split('\n',1)[0][:120]
        heading = first_line if HEADING_RE.match(first_line.strip()) else ''
        cid = f"{source}-{len(chunks)}"
        chunks.append(Chunk(id=cid, source=source, page_start=start_page+1, page_end=end_page, heading=heading, text=text))
        # prepare overlap
        if overlap>0 and text:
            tail = text[-overlap:]
            buffer = [tail]
            char_count = len(tail)
        else:
            buffer = []
            char_count = 0
        start_page = end_page
    for idx, page in enumerate(pages):
        if not page:
            continue
        lines = page.split('\n')
        for line in lines:
            if line.strip()=='' and char_count>target_chars*0.6:
                flush(idx+1)
                continue
            buffer.append(line)
            char_count += len(line)+1
            if char_count >= target_chars:
                flush(idx+1)
    flush(len(pages))
    return chunks

def load_manifest() -> Dict[str, Dict]:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except Exception:
            return {}
    return {}

def save_manifest(m: Dict):
    MANIFEST.write_text(json.dumps(m, indent=2))

def _load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def _get_collection():
    """Return/create Chroma collection (HTTP if configured, else local persistent)."""
    global _client, _collection
    if chromadb is None:
        raise RuntimeError("chromadb is not installed; install it to enable RAG ingestion")
    if _client is None:
        http_url = os.getenv('CHROMA_HTTP_URL')
        host = os.getenv('CHROMA_HOST')
        port = os.getenv('CHROMA_PORT')
        if http_url or host or port:
            # HTTP client (Chroma server)
            if http_url:
                from urllib.parse import urlparse
                parsed = urlparse(http_url)
                h = parsed.hostname or 'localhost'
                p = parsed.port or 8000
            else:
                h = host or 'localhost'
                p = int(port or 8000)
            _client = chromadb.HttpClient(host=h, port=p, settings=Settings(anonymized_telemetry=False))
        else:
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
    if _collection is None:
        # We compute embeddings externally; disable chroma's embedding function
        name = 'icar_advisory'
        try:
            _collection = _client.get_collection(name=name)
        except Exception:
            _collection = _client.create_collection(name=name, metadata={"hnsw:space": "cosine"})
    return _collection

def ingest(pdf_paths: List[str]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    model = _load_model()
    collection = _get_collection()

    # Build set of existing IDs from collection
    try:
        existing = collection.get(limit=1_000_000)  # fetch IDs only (safe for our small sizes)
        existing_ids = set(existing.get('ids', []) or [])
    except Exception:
        existing_ids = set()

    for path_str in pdf_paths:
        # Allow direct HTTP(S) URLs
        temp_file = None
        if path_str.startswith('http://') or path_str.startswith('https://'):
            try:
                resp = requests.get(path_str, timeout=60)
                resp.raise_for_status()
                # Derive filename from URL path
                url_name = path_str.rstrip('/').split('/')[-1] or 'download.pdf'
                if not url_name.lower().endswith('.pdf'):
                    url_name += '.pdf'
                temp_dir = STORE_DIR / 'downloads'
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_file = temp_dir / url_name
                temp_file.write_bytes(resp.content)
                path = temp_file
                print(f"↓ Downloaded {path_str} -> {temp_file}")
            except Exception as e:
                print(f"! Failed to download {path_str}: {e}")
                continue
        else:
            path = Path(path_str)
        if not path.exists():
            print(f"! Missing: {path}")
            continue
        sha = file_sha256(path)
        entry = manifest.get(path.name)
        if entry and entry.get('sha') == sha:
            print(f"= Unchanged: {path.name}")
            continue
        print(f"+ Processing {path.name}")
        pages = extract_pdf(path)
        if sum(len(p) for p in pages) < 500:
            print(f"  Warning: Very little text extracted from {path.name} (maybe scanned).")
        season = 'kharif' if 'kharif' in path.name.lower() else ('rabi' if 'rabi' in path.name.lower() else 'general')
        chunks = split_into_chunks(pages, source=season)
        base = path.stem.lower()
        texts: List[str] = []
        metadatas: List[Dict] = []
        ids: List[str] = []
        for c in chunks:
            cid = f"{base}-{c.id}"
            if cid in existing_ids:
                continue
            ids.append(cid)
            texts.append(c.text)
            metadatas.append({
                'source': c.source,
                'page_start': c.page_start,
                'page_end': c.page_end,
                'heading': c.heading,
                'file': path.name
            })
        if texts:
            print(f"Embedding {len(texts)} chunks for {path.name} ...")
            embs = model.encode(texts, batch_size=16, show_progress_bar=True, normalize_embeddings=True)
            # Add to collection with provided embeddings
            collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embs.tolist())
        manifest[path.name] = { 'sha': sha, 'chunks': len(chunks), 'source': path_str }
        # Clean up temp file if used
        if temp_file and temp_file.exists():
            pass  # keep cached download for repeat runs
    print("Ingestion complete (ChromaDB).")
    save_manifest(manifest)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m rag.ingest <pdf1.pdf> <pdf2.pdf> ...")
        raise SystemExit(1)
    ingest(sys.argv[1:])
