"""
Gemini Orchestrator: routes user queries to tools (weather, maps, FPO, RAG) and
builds answers strictly from tool-backed data. Optionally merges call-center
transcripts if present. Falls back gracefully if Gemini or APIs are unavailable.

Activation: set GEMINI_API_KEY in environment. Otherwise, this module is idle.
"""
from __future__ import annotations
import os
import glob
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # Optional dependency

from sentence_transformers import SentenceTransformer

# Local tools
import weather.service as ws
from fpo.service import FPOService
from rag.retriever import get_retriever


def _is_agri_query(q: str) -> bool:
    ql = q.lower()
    stems = ['fertil', 'irrig', 'crop', 'seed', 'fpo', 'soil', 'pest', 'tractor', 'harvest', 'kvk', 'krishi', 'weather', 'rain']
    return any(s in ql for s in stems)


@dataclass
class SourceDoc:
    kind: str  # 'weather' | 'maps' | 'fpo' | 'rag' | 'transcript'
    title: str
    text: str
    meta: Dict[str, Any]


class TranscriptIndex:
    def __init__(self):
        self._loaded = False
        self._texts: List[str] = []
        self._metas: List[Dict[str, Any]] = []
        self._embeds = None
        self._model: Optional[SentenceTransformer] = None

    def _load_all(self):
        if self._loaded:
            return
        base = os.path.join('data', 'call_center')
        paths = []
        for pat in ('*.txt', '*.md', '*.jsonl', '*.json'):
            paths.extend(glob.glob(os.path.join(base, pat)))
        if not paths:
            self._loaded = True
            return
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        for p in paths:
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    txt = f.read()
                    if txt and len(txt.strip()) > 20:
                        texts.append(txt[:5000])  # cap per item to keep it light
                        metas.append({'file': os.path.basename(p)})
            except Exception:
                continue
        self._texts = texts
        self._metas = metas
        if texts:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            self._embeds = self._model.encode(texts, normalize_embeddings=True)
        self._loaded = True

    def topk(self, query: str, k: int = 3) -> List[SourceDoc]:
        self._load_all()
        if not self._texts or self._embeds is None or self._model is None:
            return []
        q = self._model.encode([query], normalize_embeddings=True)[0]
        import numpy as np  # local import to avoid hard dep in cold paths
        sims = (self._embeds @ q)  # cosine since normalized
        idxs = np.argsort(-sims)[:k]
        out: List[SourceDoc] = []
        for i in idxs:
            score = float(sims[i])
            if score < 0.25:
                continue
            out.append(SourceDoc(kind='transcript', title=self._metas[i]['file'], text=self._texts[i], meta={'score': score}))
        return out


class GeminiAgent:
    def __init__(self):
        self.enabled = bool(os.getenv('GEMINI_API_KEY')) and genai is not None
        if self.enabled:
            genai.configure(api_key=os.environ['GEMINI_API_KEY'])
            # Light, cheap; we only ask it to summarize sources, not browse
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.transcripts = TranscriptIndex()
        self.rag = get_retriever()

    async def _geocode(self, village: Optional[str], state: Optional[str]) -> Optional[Tuple[float, float]]:
        if not village or not state:
            return None
        g = await ws.geocode_openweather(village, state) or await ws.geocode_visual_crossing(village, state)
        if g:
            return (g['lat'], g['lon'])
        return None

    def _collect_rag(self, query: str) -> List[SourceDoc]:
        docs = self.rag.query(query, k=5)
        out: List[SourceDoc] = []
        for d in docs:
            out.append(SourceDoc(kind='rag', title=d.get('heading') or d.get('source') or 'ICAR Advisory', text=d['text'], meta={'score': d.get('score'), 'source': d.get('source')}))
        return out

    async def _collect_weather(self, village: Optional[str], state: Optional[str]) -> List[SourceDoc]:
        if not village or not state:
            return []
        geo = await self._geocode(village, state)
        if not geo:
            return []
        lat, lon = geo
        try:
            w = await ws.get_weather(lat, lon)
            advice = ws.generate_agricultural_advice(w)
            return [SourceDoc(kind='weather', title=f"Weather for {village}, {state}", text=advice, meta={'lat': lat, 'lon': lon})]
        except Exception:
            return []

    async def _collect_maps(self, query_lower: str, village: Optional[str], state: Optional[str]) -> List[SourceDoc]:
        # Detect shop intent or KVK
        shop_map = {
            'fertilizer shop': 'fertilizer shop', 'seed shop': 'seed shop', 'pesticide shop': 'pesticide shop',
            'tractor dealer': 'tractor dealer', 'farm machinery': 'farm machinery', 'fertilizer': 'fertilizer shop', 'seed': 'seed shop'
        }
        key = os.getenv('GEOAPIFY_API_KEY')
        if not (village and state):
            return []
        geo = await self._geocode(village, state)
        if not geo or not key:
            return []
        # KVK detection first
        if any(k in query_lower for k in ['kvk', 'krishi vigyan kendra', 'vigyan kendra']):
            try:
                from maps.service import search_kvk
                kvks = await search_kvk(geo[0], geo[1], key)
            except Exception:
                kvks = []
            if not kvks:
                return []
            lines = []
            for r in kvks[:5]:
                line = f"{r['name']} - {r.get('address','')} ({r.get('distance_km','?')} km)\n{r.get('maps_url','')}"
                lines.append(line)
            return [SourceDoc(kind='maps', title=f"KVK near {village}, {state}", text='\n'.join(lines), meta={'count': len(kvks)})]
        # Shops
        keyword = None
        for k in shop_map:
            if k in query_lower:
                keyword = shop_map[k]
                break
        if not keyword:
            return []
        # Import at call-time so tests can monkeypatch maps.service.search_agri_shops
        from maps.service import search_agri_shops
        results = await search_agri_shops(keyword, geo[0], geo[1], key)
        if not results:
            return []
        lines = []
        for r in results[:5]:
            line = f"{r['name']} - {r.get('address','')} ({r.get('distance_km','?')} km)"
            if r.get('maps_url'):
                line += f"\n{r['maps_url']}"
            lines.append(line)
        return [SourceDoc(kind='maps', title=f"{keyword.title()} near {village}, {state}", text='\n'.join(lines), meta={'count': len(results)})]

    async def _collect_fpo(self, village: Optional[str], state: Optional[str]) -> List[SourceDoc]:
        if not state:
            return []
        svc = FPOService()
        geo = None
        if village:
            geo = await self._geocode(village, state)
        lines = []
        if geo:
            nearest = svc.find_nearest_fpos(geo[0], geo[1], limit=5)
            for f, d in nearest:
                lines.append(f"{f.name} - {f.district} ({d:.1f} km) | {', '.join(f.services[:6])}")
        else:
            # Fallback: list by state
            count = 0
            for f in svc.fpos:
                if f.state.lower() == state.lower():
                    lines.append(f"{f.name} - {f.district} | {', '.join(f.services[:6])}")
                    count += 1
                    if count >= 5:
                        break
        if not lines:
            return []
        return [SourceDoc(kind='fpo', title=f"FPOs in/near {village+', ' if village else ''}{state}", text='\n'.join(lines), meta={})]

    def _compose_with_gemini(self, query: str, sources: List[SourceDoc]) -> str:
        if not self.enabled:
            return ''
        # Build a strict prompt: must only use provided sources
        src_text = []
        for i, s in enumerate(sources, 1):
            src_text.append(f"[{i}] ({s.kind}) {s.title}\n{s.text[:2000]}")
        system = (
            "You are an agriculture assistant. Answer ONLY using the provided sources. "
            "Do not invent data. If sources are insufficient, say: 'I don't have enough verified data to answer.' "
            "Keep it concise and practical."
        )
        prompt = f"{system}\n\nUser question:\n{query}\n\nSources:\n" + "\n\n".join(src_text)
        try:
            resp = self.model.generate_content(prompt)
            text = getattr(resp, 'text', '') or ''
            return text.strip()
        except Exception:
            return ''

    async def run(self, query: str, village: Optional[str], state: Optional[str]) -> str:
        ql = query.lower()
        if not _is_agri_query(ql):
            return "This query is not related to farming."

        # Collect sources
        sources: List[SourceDoc] = []
        # If FPO is requested but we have no location/state, short-circuit with guard
        if ('fpo' in ql or 'producer' in ql) and not state:
            return "I don't have enough verified data to answer."
        # RAG always
        sources.extend(self._collect_rag(query))
        # Weather if looks like weather/location request
        weather_terms = ['weather', 'rain', 'forecast', 'temperature']
        if any(t in ql for t in weather_terms):
            sources.extend(await self._collect_weather(village, state))
        # Shops/maps
        sources.extend(await self._collect_maps(ql, village, state))
        # FPO
        if 'fpo' in ql or 'producer' in ql:
            sources.extend(await self._collect_fpo(village, state))
        # Transcripts for personalization
        sources.extend(self.transcripts.topk(query, k=2))

        # Gate: if no sources -> return farming-related guard
        if not sources:
            return "I don't have enough verified data to answer."

        # If Gemini available, compose with it, else return stitched summary
        if self.enabled:
            out = self._compose_with_gemini(query, sources)
            if out:
                return out
        # Fallback stitching
        lines = ["Verified information:" ]
        for s in sources[:4]:
            lines.append(f"- {s.title}: {s.text.splitlines()[0][:140]}")
        lines.append("Ask a follow-up to refine location or crop if needed.")
        return "\n".join(lines)
