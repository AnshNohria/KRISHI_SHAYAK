"""Geoapify based agricultural shop search service.

Replaced Google Places usage with Geoapify Places API so the project no longer
depends on Google Maps billing requirements.

API Docs: https://www.geoapify.com/api/places-api

Endpoint pattern:
    https://api.geoapify.com/v2/places?categories=<cats>&filter=circle:lon,lat,radius&bias=proximity:lon,lat&limit=N&apiKey=KEY

We map internal keywords to Geoapify categories and build simple result cards.
If an error occurs we return a single pseudo result entry describing it.
"""
from __future__ import annotations
import os, math, time, json
from typing import List, Dict, Any, Optional, Tuple
import httpx

GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"
_CACHE: Dict[Tuple[str, float, float, int], Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL = 300  # seconds (5 min) basic response cache

# Simple rate limiting (token bucket style) per (api_key, category bundle)
_RATE_LOG: Dict[Tuple[str, str], List[float]] = {}
_RATE_WINDOW = 60  # seconds
_RATE_MAX = 20  # max calls per window per key+category set (can be tuned)

def _rate_allow(api_key: str, categories: str) -> bool:
    """Return True if request allowed under simple rate limiting.

    We store timestamps of recent calls and prune outside the window.
    If limit exceeded, return False. This intentionally does NOT raise
    so caller can decide fallback messaging.
    """
    if not api_key:  # if no key we don't rate limit network (will fail earlier)
        return True
    key = (api_key, categories)
    now = time.time()
    arr = _RATE_LOG.setdefault(key, [])
    # prune
    cutoff = now - _RATE_WINDOW
    while arr and arr[0] < cutoff:
        arr.pop(0)
    if len(arr) >= _RATE_MAX:
        return False
    arr.append(now)
    return True

def _cache_get(key):
    rec = _CACHE.get(key)
    if not rec:
        return None
    ts, data = rec
    if time.time() - ts > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return data

def _cache_set(key, data):
    _CACHE[key] = (time.time(), data)

"""Text search variants for agricultural inputs.

Per Geoapify Places quick-start, text= is robust and category taxonomy for
agri inputs is inconsistent. We'll rely on text search with multiple variants
instead of fragile categories that often return 400.
"""
_KEYWORD_TEXT_VARIANTS = {
    'fertilizer shop': ['fertilizer shop', 'fertiliser shop', 'agro dealer', 'agri input dealer', 'agro chemical', 'agriculture supply'],
    'seed shop': ['seed shop', 'seed store', 'seed dealer', 'agri input dealer'],
    'pesticide shop': ['pesticide shop', 'agro chemical', 'agro dealer', 'agri input dealer'],
    'farm machinery dealer': ['farm machinery dealer', 'agriculture machinery', 'tractor dealer'],
    'tractor dealer': ['tractor dealer', 'tractor showroom'],
    'agricultural supply store': ['agricultural supply', 'agriculture supply', 'agri input dealer']
}

def _sanitize_categories(cats):
    cleaned = []
    for c in cats:
        c2 = c.replace('/', '.').strip().lower()
        # keep only allowed chars (alnum and dot)
        if all(ch.isalnum() or ch == '.' for ch in c2):
            cleaned.append(c2)
    # de-duplicate preserving order
    seen = set()
    out = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out

async def _fetch_json(client: httpx.AsyncClient, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = await client.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

async def search_agri_shops(keyword: str, lat: float, lon: float, api_key: str,
                            radius_m: int = 20000, max_results: int = 5,
                            fallback_radius_m: int = 100000) -> Tuple[List[Dict[str, Any]], int]:
    """Search nearby agricultural shops using Geoapify Places.

    Args:
        keyword: normalized shop keyword (e.g., 'fertilizer shop').
        lat/lon: center coordinates.
        api_key: Geoapify API key.
        radius_m: initial search radius (meters).
        max_results: maximum number of results.
    Returns: (results, used_radius_m)
      - results: list of dicts with name, address, distance_km, rating (None), maps_url.
      - used_radius_m: last radius attempted in meters.
    """
    # Build radius attempts (progressively widen up to cap)
    first = max(1000, int(radius_m))
    cap = max(first, int(fallback_radius_m))
    radii = []
    r = first
    while True:
        radii.append(r)
        if r >= cap:
            break
        r = min(cap, int(r * 2))

    # Prepare alternative keyword attempts for agri inputs
    kwl = keyword.lower().strip()
    alt_keywords = [kwl]
    if 'fertilizer' in kwl:
        alt_keywords += ['seed shop', 'pesticide shop']
    elif 'seed' in kwl:
        alt_keywords += ['fertilizer shop', 'pesticide shop']
    elif 'pesticide' in kwl:
        alt_keywords += ['fertilizer shop', 'seed shop']

    last_radius_used = radii[-1]
    try:
        async with httpx.AsyncClient() as client:
            for use_radius in radii:
                for kw_try in alt_keywords:
                    # Cache by keyword+radius
                    cache_key = (kw_try, round(lat,4), round(lon,4), use_radius)
                    cached = _cache_get(cache_key)
                    if cached is not None:
                        return cached[:max_results], use_radius
                    base_params = {
                        'filter': f"circle:{lon},{lat},{use_radius}",
                        'bias': f"proximity:{lon},{lat}",
                        'limit': max_results,
                        'apiKey': api_key,
                        'categories': 'commercial',
                    }
                    out: List[Dict[str, Any]] = []
                    # Light local rate guard (per kw)
                    if not _rate_allow(api_key, kw_try):
                        return ([{
                            'name': 'Rate limit reached (local safeguard)',
                            'address': f'Max ' + str(_RATE_MAX) + f" calls / {_RATE_WINDOW}s",
                            'distance_km': 0.0,
                            'rating': None,
                            'maps_url': f"https://www.openstreetmap.org/search?query={kw_try.replace(' ', '+')}"
                        }], use_radius)
                    # 1. Text search (primary per docs)
                    text_params = base_params.copy()
                    text_params['text'] = kw_try
                    try:
                        data = await _fetch_json(client, GEOAPIFY_PLACES_URL, text_params)
                    except httpx.HTTPStatusError:
                        data = {'features': []}
                    features = data.get('features', [])
                    if not features:
                        last_radius_used = use_radius
                        continue
                    for feat in features:
                        props = feat.get('properties', {})
                        glat = props.get('lat') or feat.get('geometry', {}).get('coordinates', [None, None])[1]
                        glon = props.get('lon') or feat.get('geometry', {}).get('coordinates', [None, None])[0]
                        if glat is None or glon is None:
                            continue
                        dist = _haversine(lat, lon, glat, glon)
                        address_parts = [
                            props.get('name'),
                            props.get('street'),
                            props.get('housenumber'),
                            props.get('district'),
                            props.get('city'),
                            props.get('state'),
                        ]
                        address = ', '.join([str(p) for p in address_parts if p])
                        maps_url = f"https://www.openstreetmap.org/?mlat={glat}&mlon={glon}#map=16/{glat}/{glon}"
                        out.append({
                            'name': props.get('name') or kw_try.title(),
                            'address': address,
                            'distance_km': dist,
                            'rating': None,
                            'maps_url': maps_url,
                            'lat': glat,
                            'lon': glon,
                        })
                    if out:
                        out.sort(key=lambda r: r['distance_km'])
                        _cache_set(cache_key, out)
                        return out[:max_results], use_radius
                    last_radius_used = use_radius
        # If still nothing, try OSM fallback once with the last radius
        osm = await _overpass_fallback(lat, lon, last_radius_used, max_results, keyword)
        if osm:
            return osm, last_radius_used
        return [], last_radius_used
    except Exception as e:  # pragma: no cover - network failure path
        try:
            osm = await _overpass_fallback(lat, lon, last_radius_used, max_results, keyword)
            if osm:
                return osm, last_radius_used
        except Exception:
            pass
        return ([{
            'name': 'Geoapify request failed',
            'address': str(e),
            'distance_km': 0.0,
            'rating': None,
            'maps_url': f"https://www.openstreetmap.org/search?query={keyword.replace(' ','+')}"
        }], last_radius_used)

async def _overpass_fallback(lat: float, lon: float, radius_m: int, max_results: int, keyword: str) -> List[Dict[str, Any]]:
    """Query Overpass API for agricultural-related shops if Geoapify yields nothing.

    We approximate radius with bounding box for performance; Overpass has its own
    internal optimizations. Tags targeted: agricultural_supplies, garden_centre, farm.
    """
    # convert radius to degree deltas
    dlat = radius_m / 111000.0
    dlon = radius_m / (111000.0 * max(0.1, math.cos(math.radians(lat))))
    south, north = lat - dlat, lat + dlat
    west, east = lon - dlon, lon + dlon
    query = f"""[out:json][timeout:20];(
  node["shop"="agricultural_supplies"]({south},{west},{north},{east});
  node["shop"="garden_centre"]({south},{west},{north},{east});
  node["shop"="farm"]({south},{west},{north},{east});
  way["shop"="agricultural_supplies"]({south},{west},{north},{east});
  way["shop"="garden_centre"]({south},{west},{north},{east});
);out center {max_results};"""
    url = "https://overpass-api.de/api/interpreter"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, data=query, timeout=30, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        r.raise_for_status()
        data = r.json()
    elements = data.get('elements', [])
    out: List[Dict[str, Any]] = []
    for el in elements:
        if len(out) >= max_results:
            break
        if 'lat' in el:
            glat, glon = el['lat'], el['lon']
        else:
            center = el.get('center') or {}
            glat, glon = center.get('lat'), center.get('lon')
        if glat is None or glon is None:
            continue
        dist = _haversine(lat, lon, glat, glon)
        tags = el.get('tags', {})
        name = tags.get('name') or keyword.title()
        address = ', '.join([tags.get(k) for k in ['addr:street','addr:city','addr:state'] if tags.get(k)])
        maps_url = f"https://www.openstreetmap.org/?mlat={glat}&mlon={glon}#map=16/{glat}/{glon}"
        out.append({
            'name': name + ' (OSM)',
            'address': address,
            'distance_km': dist,
            'rating': None,
            'maps_url': maps_url,
            'lat': glat,
            'lon': glon,
        })
    out.sort(key=lambda r: r['distance_km'])
    return out[:max_results]

async def search_agri_shops_nl(query: str, lat: float, lon: float, api_key: str,
                               radius_m: int = 20000, max_results: int = 5,
                               fallback_radius_m: int = 100000) -> Tuple[List[Dict[str, Any]], int]:
    """Natural language shop search using text-first, then category, then OSM fallback."""
    normalized = query.lower().strip()
    for k in _KEYWORD_TEXT_VARIANTS:
        if k in normalized:
            keyword = k
            break
    else:
        keyword = query
    # Reuse underlying logic by calling category search path with mapped keyword
    return await search_agri_shops(keyword, lat, lon, api_key, radius_m=radius_m, max_results=max_results, fallback_radius_m=fallback_radius_m)

__all__ = ['search_agri_shops', 'search_agri_shops_nl']
async def search_kvk(lat: float, lon: float, api_key: str, radius_m: int = 50000, limit: int = 3,
                     fallback_radius_m: int = 150000) -> Tuple[List[Dict[str, Any]], int]:
    """Search for Krishi Vigyan Kendra (KVK) near a location using Geoapify.

    Strategy: text search 'Krishi Vigyan Kendra' biased to user location.
    Falls back to empty list if key missing or request fails.
    """
    if not api_key:
        return [], radius_m
    first = max(5000, int(radius_m))
    cap = max(first, int(fallback_radius_m))
    radii = []
    r = first
    while True:
        radii.append(r)
        if r >= cap:
            break
        r = min(cap, int(r * 2))
    last_radius_used = radii[-1]
    try:
        async with httpx.AsyncClient() as client:
            for use_radius in radii:
                cache_key = ("kvk", round(lat,4), round(lon,4), use_radius)
                cached = _cache_get(cache_key)
                if cached is not None:
                    return cached, use_radius
                params = {
                    'text': 'Krishi Vigyan Kendra',
                    'filter': f"circle:{lon},{lat},{use_radius}",
                    'bias': f"proximity:{lon},{lat}",
                    'limit': limit,
                    'apiKey': api_key,
                    'categories': 'education'
                }
                data = await _fetch_json(client, GEOAPIFY_PLACES_URL, params)
                feats = data.get('features', [])
                out: List[Dict[str, Any]] = []
                for feat in feats:
                    props = feat.get('properties', {})
                    glat = props.get('lat') or feat.get('geometry', {}).get('coordinates', [None, None])[1]
                    glon = props.get('lon') or feat.get('geometry', {}).get('coordinates', [None, None])[0]
                    if glat is None or glon is None:
                        continue
                    dist = _haversine(lat, lon, glat, glon)
                    address_parts = [
                        props.get('name'),
                        props.get('housenumber'),
                        props.get('street'),
                        props.get('district'),
                        props.get('city'),
                        props.get('state'),
                        props.get('postcode')
                    ]
                    address = ', '.join([str(p) for p in address_parts if p])
                    maps_url = f"https://www.openstreetmap.org/?mlat={glat}&mlon={glon}#map=16/{glat}/{glon}"
                    out.append({
                        'name': props.get('name') or 'Krishi Vigyan Kendra',
                        'address': address,
                        'distance_km': dist,
                        'lat': glat,
                        'lon': glon,
                        'maps_url': maps_url
                    })
                if out:
                    out.sort(key=lambda r: r['distance_km'])
                    _cache_set(cache_key, out)
                    return out, use_radius
                last_radius_used = use_radius
        return [], last_radius_used
    except Exception:
        return [], last_radius_used

__all__.append('search_kvk')
