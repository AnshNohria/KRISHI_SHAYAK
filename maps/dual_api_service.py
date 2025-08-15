"""
Krishi Dhan Sahayak - Dual Maps API Service
Enhanced maps service with Geoapify + Foursquare support for geocoding and places search
"""

import httpx
import os
import math
import time
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# API Configuration
GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
FOURSQUARE_PLACES_URL = "https://places-api.foursquare.com/places/search"
FOURSQUARE_GEOCODE_URL = "https://places-api.foursquare.com/places/search"

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")

# Cache configuration
_CACHE: Dict[Tuple[str, float, float, int], Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL = 300  # 5 minutes

# Rate limiting
_RATE_LOG: Dict[Tuple[str, str], List[float]] = {}
_RATE_WINDOW = 60  # seconds
_RATE_MAX = 20  # max calls per window

class MapsServiceError(Exception):
    """Custom exception for maps service errors."""
    pass

class GeocodeResult:
    """Geocoding result container."""
    def __init__(self, lat: float, lon: float, display_name: str, country: str = None, 
                 state: str = None, district: str = None, source: str = ""):
        self.lat = lat
        self.lon = lon
        self.display_name = display_name
        self.country = country
        self.state = state
        self.district = district
        self.source = source

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def _rate_allow(api_key: str, endpoint: str) -> bool:
    """Simple rate limiting."""
    if not api_key:
        return True
    key = (api_key, endpoint)
    now = time.time()
    arr = _RATE_LOG.setdefault(key, [])
    cutoff = now - _RATE_WINDOW
    while arr and arr[0] < cutoff:
        arr.pop(0)
    if len(arr) >= _RATE_MAX:
        return False
    arr.append(now)
    return True

def _cache_get(key):
    """Get cached result."""
    rec = _CACHE.get(key)
    if not rec:
        return None
    ts, data = rec
    if time.time() - ts > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return data

def _cache_set(key, data):
    """Set cache result."""
    _CACHE[key] = (time.time(), data)

async def geocode_geoapify(location: str, country: str = "IN") -> Optional[GeocodeResult]:
    """Geocode using Geoapify API."""
    if not GEOAPIFY_API_KEY:
        logger.warning("Geoapify API key not configured")
        return None
    
    if not _rate_allow(GEOAPIFY_API_KEY, "geocode"):
        logger.warning("Geoapify geocoding rate limit exceeded")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            params = {
                'text': location,
                'apiKey': GEOAPIFY_API_KEY,
                'limit': 1,
                'country': country
            }
            
            response = await client.get(GEOAPIFY_GEOCODE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if not features:
                return None
            
            feature = features[0]
            geometry = feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            properties = feature.get('properties', {})
            
            if len(coordinates) >= 2:
                lon, lat = coordinates[0], coordinates[1]
                return GeocodeResult(
                    lat=lat,
                    lon=lon,
                    display_name=properties.get('formatted', location),
                    country=properties.get('country'),
                    state=properties.get('state'),
                    district=properties.get('district'),
                    source="geoapify"
                )
    except Exception as e:
        logger.error(f"Geoapify geocoding error: {e}")
        return None

async def geocode_foursquare(location: str, country: str = "IN") -> Optional[GeocodeResult]:
    """Geocode using Foursquare Places API v3."""
    if not FOURSQUARE_API_KEY:
        logger.warning("Foursquare API key not configured")
        return None
    
    if not _rate_allow(FOURSQUARE_API_KEY, "geocode"):
        logger.warning("Foursquare geocoding rate limit exceeded")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                'accept': 'application/json',
                'X-Places-Api-Version': '2025-06-17',
                'authorization': f'Bearer {FOURSQUARE_API_KEY}'
            }
            params = {
                'query': f"{location}, {country}",
                'limit': 1
            }
            
            response = await client.get(FOURSQUARE_GEOCODE_URL, 
                                      headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            if not results:
                return None
            
            result = results[0]
            # Updated: coordinates are directly in result, not nested in geocodes
            latitude = result.get('latitude')
            longitude = result.get('longitude')
            location_info = result.get('location', {})
            
            if latitude is not None and longitude is not None:
                return GeocodeResult(
                    lat=latitude,
                    lon=longitude,
                    display_name=result.get('name', location),
                    country=location_info.get('country'),
                    state=location_info.get('region'),
                    district=location_info.get('locality'),
                    source="foursquare"
                )
    except Exception as e:
        logger.error(f"Foursquare geocoding error: {e}")
        return None

async def geocode_dual_api(location: str, country: str = "IN") -> Optional[GeocodeResult]:
    """Geocode using both APIs with fallback."""
    # Try Geoapify first (primary)
    result = await geocode_geoapify(location, country)
    if result:
        return result
    
    # Fallback to Foursquare
    logger.info("Geoapify geocoding failed, trying Foursquare...")
    result = await geocode_foursquare(location, country)
    return result

async def search_places_geoapify(query: str, lat: float, lon: float, 
                                radius_m: int = 20000, limit: int = 5) -> List[Dict[str, Any]]:
    """Search places using Geoapify."""
    if not GEOAPIFY_API_KEY:
        return []
    
    if not _rate_allow(GEOAPIFY_API_KEY, "places"):
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            params = {
                'text': query,
                'filter': f"circle:{lon},{lat},{radius_m}",
                'bias': f"proximity:{lon},{lat}",
                'limit': limit,
                'apiKey': GEOAPIFY_API_KEY,
                'categories': 'commercial'
            }
            
            response = await client.get(GEOAPIFY_PLACES_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates', [None, None])
                
                if len(coordinates) >= 2 and coordinates[0] is not None:
                    place_lon, place_lat = coordinates[0], coordinates[1]
                    distance = calculate_distance(lat, lon, place_lat, place_lon)
                    
                    results.append({
                        'name': props.get('name', query.title()),
                        'address': props.get('formatted', ''),
                        'distance_km': round(distance, 1),
                        'lat': place_lat,
                        'lon': place_lon,
                        'source': 'geoapify',
                        'maps_url': f"https://www.openstreetmap.org/?mlat={place_lat}&mlon={place_lon}#map=16/{place_lat}/{place_lon}"
                    })
            
            results.sort(key=lambda x: x['distance_km'])
            return results
    except Exception as e:
        logger.error(f"Geoapify places search error: {e}")
        return []

async def search_places_foursquare(query: str, lat: float, lon: float, 
                                  radius_m: int = 20000, limit: int = 5) -> List[Dict[str, Any]]:
    """Search places using Foursquare Places API v3."""
    if not FOURSQUARE_API_KEY:
        return []
    
    if not _rate_allow(FOURSQUARE_API_KEY, "places"):
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                'accept': 'application/json',
                'X-Places-Api-Version': '2025-06-17',
                'authorization': f'Bearer {FOURSQUARE_API_KEY}'
            }
            # Use broader search terms for better results
            search_query = query
            if 'fertilizer' in query.lower():
                search_query = 'shop'  # Broader term
            elif 'seed' in query.lower():
                search_query = 'shop'
            elif 'agricultural' in query.lower():
                search_query = 'shop'
                
            params = {
                'query': search_query,
                'll': f"{lat},{lon}",
                'radius': min(radius_m, 100000),
                'limit': limit
            }
            
            response = await client.get(FOURSQUARE_PLACES_URL, 
                                      headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get('results', []):
                # Updated: coordinates are directly in result
                place_lat = result.get('latitude')
                place_lon = result.get('longitude')
                location_info = result.get('location', {})
                
                if place_lat is not None and place_lon is not None:
                    distance = calculate_distance(lat, lon, place_lat, place_lon)
                    
                    # Build address from location info
                    address_parts = [
                        location_info.get('address'),
                        location_info.get('locality'),
                        location_info.get('region'),
                        location_info.get('country')
                    ]
                    address = ', '.join([str(p) for p in address_parts if p])
                    
                    results.append({
                        'name': result.get('name', query.title()),
                        'address': address,
                        'distance_km': round(distance, 1),
                        'lat': place_lat,
                        'lon': place_lon,
                        'source': 'foursquare',
                        'maps_url': f"https://www.openstreetmap.org/?mlat={place_lat}&mlon={place_lon}#map=16/{place_lat}/{place_lon}"
                    })
            
            results.sort(key=lambda x: x['distance_km'])
            return results
    except Exception as e:
        logger.error(f"Foursquare places search error: {e}")
        return []
        logger.error(f"Foursquare places search error: {e}")
        return []

async def search_places_dual_api(query: str, lat: float, lon: float, 
                                radius_m: int = 20000, limit: int = 5) -> List[Dict[str, Any]]:
    """Search places using both APIs and combine results."""
    # Get results from both APIs
    geoapify_results = await search_places_geoapify(query, lat, lon, radius_m, limit)
    foursquare_results = await search_places_foursquare(query, lat, lon, radius_m, limit)
    
    # Combine results 
    all_results = geoapify_results + foursquare_results
    
    # If no results from either, try alternative search terms for agricultural queries
    if not all_results and query in ['fertilizer', 'fertilizer shop']:
        alt_results = await search_places_geoapify('agro dealer', lat, lon, radius_m, limit//2)
        alt_results.extend(await search_places_geoapify('agriculture supply', lat, lon, radius_m, limit//2))
        all_results = alt_results
    
    # Simple deduplication based on name similarity and proximity
    unique_results = []
    for result in all_results:
        is_duplicate = False
        for existing in unique_results:
            # Check if names are similar and locations are very close (< 100m)
            name_similar = (result['name'].lower() in existing['name'].lower() or 
                          existing['name'].lower() in result['name'].lower())
            distance_close = calculate_distance(result['lat'], result['lon'], 
                                              existing['lat'], existing['lon']) < 0.1  # 100m
            
            if name_similar and distance_close:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_results.append(result)
    
    # Sort by distance and return top results
    unique_results.sort(key=lambda x: x['distance_km'])
    return unique_results[:limit]

# Agricultural shop search with dual API
async def search_agri_shops_dual(keyword: str, lat: float, lon: float,
                                radius_m: int = 20000, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search agricultural shops using dual API approach."""
    # Map agricultural keywords
    agri_keywords = {
        'fertilizer shop': ['fertilizer', 'fertiliser', 'agro dealer', 'agri input'],
        'seed shop': ['seed store', 'seed dealer', 'agri input'],
        'pesticide shop': ['pesticide', 'agro chemical', 'agro dealer'],
        'farm machinery': ['tractor dealer', 'farm equipment', 'agriculture machinery']
    }
    
    # Get search terms
    search_terms = agri_keywords.get(keyword.lower(), [keyword])
    
    all_results = []
    for term in search_terms[:2]:  # Limit to avoid too many API calls
        results = await search_places_dual_api(term, lat, lon, radius_m, max_results)
        all_results.extend(results)
        
        if len(all_results) >= max_results:
            break
    
    # Remove duplicates and sort
    unique_results = []
    for result in all_results:
        is_duplicate = False
        for existing in unique_results:
            if calculate_distance(result['lat'], result['lon'], existing['lat'], existing['lon']) < 0.1:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_results.append(result)
    
    unique_results.sort(key=lambda x: x['distance_km'])
    return unique_results[:max_results]

__all__ = [
    'geocode_dual_api', 'geocode_geoapify', 'geocode_foursquare',
    'search_places_dual_api', 'search_agri_shops_dual', 'calculate_distance',
    'GeocodeResult', 'MapsServiceError'
]
