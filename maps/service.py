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

"""Keyword to Geoapify category mapping.

Geoapify categories reference: https://apidocs.geoapify.com/docs/places/#categories
We approximate agricultural inputs with a combination of commercial/agricultural,
shop/garden, shop/agrarian, and service/misc where relevant.
"""
_KEYWORD_CATEGORIES = {
    # Candidate categories; some may be ignored or cause 400; we will retry individually.
    'fertilizer shop': ['commercial.agricultural', 'shop.farm', 'shop.garden'],
    'seed shop': ['commercial.agricultural', 'shop.farm'],
    'pesticide shop': ['commercial.agricultural', 'shop.farm'],
    'farm machinery dealer': ['commercial.agricultural'],
    'tractor dealer': ['commercial.agricultural'],
    'agricultural supply store': ['commercial.agricultural', 'shop.farm']
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
                            fallback_radius_m: int = 50000) -> List[Dict[str, Any]]:
    """Search nearby agricultural shops using Geoapify Places.

    Args:
        keyword: normalized shop keyword (e.g., 'fertilizer shop').
        lat/lon: center coordinates.
        api_key: Geoapify API key.
        radius_m: initial search radius (meters).
        max_results: maximum number of results.
    Returns: list of dicts with name, address, distance_km, rating (None), maps_url.
    """
    categories = _KEYWORD_CATEGORIES.get(keyword, ['commercial.agricultural'])
    categories = _sanitize_categories(categories)
    # Geoapify radius cap: keep within fallback_radius_m
    use_radius = min(radius_m, fallback_radius_m)
    cat_param = ','.join(categories)
    cache_key = (cat_param, round(lat,4), round(lon,4), use_radius)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    base_params = {
        'filter': f"circle:{lon},{lat},{use_radius}",
        'bias': f"proximity:{lon},{lat}",
        'limit': max_results,
        'apiKey': api_key,
    }
    out: List[Dict[str, Any]] = []
    if not _rate_allow(api_key, cat_param):  # rate limited path
        return [{
            'name': 'Rate limit reached (local safeguard)',
            'address': f'Max {_RATE_MAX} calls / {_RATE_WINDOW}s for these categories',
            'distance_km': 0.0,
            'rating': None,
            'maps_url': f"https://www.openstreetmap.org/search?query={keyword.replace(' ', '+')}"
        }]
    try:
        async with httpx.AsyncClient() as client:
            # 1. Text search first (resilient to category taxonomy mismatch)
            text_params = base_params.copy()
            text_params['text'] = keyword
            try:
                data = await _fetch_json(client, GEOAPIFY_PLACES_URL, text_params)
            except httpx.HTTPStatusError as e_text:
                # If even text fails, fall back to category attempts
                data = {'features': []}
            features = data.get('features', [])
            if not features:
                # 2. Category batch attempt
                cat_params = base_params.copy()
                cat_params['categories'] = cat_param
                try:
                    data_cat = await _fetch_json(client, GEOAPIFY_PLACES_URL, cat_params)
                    features = data_cat.get('features', [])
                except httpx.HTTPStatusError as e_cat:
                    if e_cat.response.status_code == 400:
                        # 3. Individual category retries
                        combined: List[Dict[str, Any]] = []
                        for single in categories:
                            single_params = base_params.copy()
                            single_params['categories'] = single
                            try:
                                d_single = await _fetch_json(client, GEOAPIFY_PLACES_URL, single_params)
                                combined.extend(d_single.get('features', []))
                            except httpx.HTTPStatusError:
                                continue
                        features = combined
                    else:
                        raise
            if not features:
                # 4. Overpass fallback (OSM direct) if still empty
                osm = await _overpass_fallback(lat, lon, use_radius, max_results, keyword)
                if osm:
                    _cache_set(cache_key, osm)
                    return osm
        if not features:
            return []
        if not features:
            return []
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
                'name': props.get('name') or keyword.title(),
                'address': address,
                'distance_km': dist,
                'rating': None,
                'maps_url': maps_url,
                'lat': glat,
                'lon': glon,
            })
        out.sort(key=lambda r: r['distance_km'])
        _cache_set(cache_key, out)
        return out[:max_results]
    except Exception as e:  # pragma: no cover - network failure path
        # Attempt Overpass as last-ditch fallback
        try:
            osm = await _overpass_fallback(lat, lon, use_radius, max_results, keyword)
            if osm:
                return osm
        except Exception:
            pass
        return [{
            'name': 'Geoapify request failed',
            'address': str(e),
            'distance_km': 0.0,
            'rating': None,
            'maps_url': f"https://www.openstreetmap.org/search?query={keyword.replace(' ','+')}"
        }]

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
                               fallback_radius_m: int = 50000) -> List[Dict[str, Any]]:
    """Natural language shop search using text-first, then category, then OSM fallback."""
    normalized = query.lower().strip()
    for k in _KEYWORD_CATEGORIES:
        if k in normalized:
            keyword = k
            break
    else:
        keyword = query
    # Reuse underlying logic by calling category search path with mapped keyword
    return await search_agri_shops(keyword, lat, lon, api_key, radius_m=radius_m, max_results=max_results, fallback_radius_m=fallback_radius_m)

__all__ = ['search_agri_shops', 'search_agri_shops_nl']
async def search_kvk(lat: float, lon: float, api_key: str, radius_m: int = 50000, limit: int = 3) -> List[Dict[str, Any]]:
    """Search for Krishi Vigyan Kendra (KVK) near a location using Geoapify.

    Strategy: text search 'Krishi Vigyan Kendra' biased to user location.
    Falls back to empty list if key missing or request fails.
    """
    if not api_key:
        return []
    cache_key = ("kvk", round(lat,4), round(lon,4), radius_m)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {
        'text': 'Krishi Vigyan Kendra',
        'filter': f"circle:{lon},{lat},{radius_m}",
        'bias': f"proximity:{lon},{lat}",
        'limit': limit,
        'apiKey': api_key
    }
    try:
        async with httpx.AsyncClient() as client:
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
        out.sort(key=lambda r: r['distance_km'])
        _cache_set(cache_key, out)
        return out
    except Exception:
        return []

__all__.append('search_kvk')
