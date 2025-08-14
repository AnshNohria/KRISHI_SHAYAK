"""
FPO (Farmer Producer Organization) Service for Krishi Dhan Sahayak
Enhanced with dual maps API support for accurate geocoding and distance calculation
"""

import json
import math
import os
import asyncio
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Import dual maps API service
try:
    from maps.dual_api_service import geocode_geoapify, calculate_distance as maps_calculate_distance
    MAPS_API_AVAILABLE = True
except ImportError:
    MAPS_API_AVAILABLE = False

@dataclass
class FPO:
    """Farmer Producer Organization with minimal fields (name and location)."""
    name: str
    district: str
    state: str
    lat: float
    lon: float

class FPOService:
    """Service for finding and managing FPO information.

    Enhanced with dual maps API support for accurate geocoding and distance calculation.
    Attempts to load extracted JSON (fpo_data.json) from pdf_extract.py.
    Falls back to bundled sample dataset if JSON missing or invalid.
    """
    def __init__(self):
        self._json_loaded = False
        self.fpos = self._load_external_or_sample()
        self._geocoded_locations = {}  # Cache for geocoded locations
        self._district_coordinates = {}  # Cache for district coordinates
    
    async def get_district_coordinates(self, district: str, state: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a district using geocoding."""
        cache_key = f"{district.lower()}, {state.lower()}"
        
        # Check cache first
        if cache_key in self._district_coordinates:
            return self._district_coordinates[cache_key]
        
        # Geocode the district
        location_query = f"{district}, {state}, India"
        coords = await self.geocode_location_async(location_query)
        
        if coords:
            self._district_coordinates[cache_key] = coords
            return coords
        
        return None
    
    async def ensure_fpo_coordinates(self, fpo: FPO) -> bool:
        """Ensure FPO has coordinates, geocode district if needed."""
        if fpo.lat != 0.0 or fpo.lon != 0.0:
            return True  # Already has coordinates
        
        # Get coordinates for the district
        coords = await self.get_district_coordinates(fpo.district, fpo.state)
        if coords:
            fpo.lat, fpo.lon = coords
            return True
        
        return False
    
    async def geocode_location_async(self, location: str) -> Optional[Tuple[float, float]]:
        """Geocode a location using Geoapify only."""
        if not MAPS_API_AVAILABLE:
            return None
        
        # Check cache first
        if location in self._geocoded_locations:
            return self._geocoded_locations[location]
        
        try:
            result = await geocode_geoapify(location)
            if result:
                coords = (result.lat, result.lon)
                self._geocoded_locations[location] = coords
                return coords
        except Exception as e:
            print(f"Geoapify geocoding error for {location}: {e}")
        
        return None
    
    def geocode_location_sync(self, location: str) -> Optional[Tuple[float, float]]:
        """Synchronous wrapper for geocoding."""
        try:
            return asyncio.run(self.geocode_location_async(location))
        except Exception:
            return None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance using maps API if available, otherwise fallback to Haversine."""
        if MAPS_API_AVAILABLE:
            return maps_calculate_distance(lat1, lon1, lat2, lon2)
        else:
            # Fallback to original Haversine implementation
            return self._calculate_distance_haversine(lat1, lon1, lat2, lon2)
    
    def _calculate_distance_haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Original Haversine distance calculation as fallback."""
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
    
    def _load_external_or_sample(self) -> List[FPO]:
        json_path = os.path.join(os.path.dirname(__file__), 'fpo_data.json')
        loaded: List[Dict] = []
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for rec in data:
                        if isinstance(rec, dict) and rec.get('name') and rec.get('state'):
                            loaded.append(rec)
                if loaded:
                    self._json_loaded = True
            except Exception:
                loaded = []
        if not loaded:
            print("Warning: No FPO data found. Please ensure fpo_data.json exists in the fpo/ directory.")
            return []  # Return empty list instead of sample data
        fpos: List[FPO] = []
        for rec in loaded:
            # Keep lat/lon only if present and numeric; else set to 0.0 so we can skip for distance calc
            raw_lat = rec.get('lat')
            raw_lon = rec.get('lon')
            try:
                lat_val = float(raw_lat) if raw_lat not in (None, "",) else 0.0
            except (TypeError, ValueError):
                lat_val = 0.0
            try:
                lon_val = float(raw_lon) if raw_lon not in (None, "",) else 0.0
            except (TypeError, ValueError):
                lon_val = 0.0
            fpos.append(FPO(
                name=rec.get('name',''),
                district=rec.get('district',''),
                state=rec.get('state',''),
                lat=lat_val,
                lon=lon_val,
            ))
        return fpos

    def find_nearest_fpos(self, lat: float, lon: float, limit: int = 5) -> List[Tuple[FPO, float]]:
        """Find nearest FPOs to a given location using enhanced distance calculation."""
        fpo_distances = []
        for fpo in self.fpos:
            # Skip entries lacking real coordinates (lat/lon left as 0.0 from missing data)
            if fpo.lat == 0.0 and fpo.lon == 0.0:
                continue
            distance = self.calculate_distance(lat, lon, fpo.lat, fpo.lon)
            fpo_distances.append((fpo, distance))
        
        # Sort by distance and return top results
        fpo_distances.sort(key=lambda x: x[1])
        return fpo_distances[:limit]
    
    async def find_nearest_fpos_with_geocoding(self, location_name: str, state: str = None, limit: int = 5) -> List[Tuple[FPO, float]]:
        """Find nearest FPOs by geocoding user location and calculating distances to state FPOs."""
        # Geocode the user's location using Geoapify
        user_coords = await self.geocode_location_async(f"{location_name}, {state}" if state else location_name)
        if not user_coords:
            return []
        
        user_lat, user_lon = user_coords
        
        # Filter FPOs by state if specified
        if state:
            state_fpos = [fpo for fpo in self.fpos if fpo.state.lower() == state.lower()]
            if not state_fpos:
                return []  # No FPOs in this state
        else:
            state_fpos = self.fpos
        
        # Ensure all FPOs have coordinates (geocode districts as needed)
        fpos_with_coords = []
        for fpo in state_fpos:
            if await self.ensure_fpo_coordinates(fpo):
                fpos_with_coords.append(fpo)
        
        if not fpos_with_coords:
            return []  # No FPOs with coordinates
        
        # Calculate distances to all FPOs
        fpo_distances = []
        for fpo in fpos_with_coords:
            # Calculate distance using dual API
            distance = self.calculate_distance(user_lat, user_lon, fpo.lat, fpo.lon)
            fpo_distances.append((fpo, distance))
        
        # Sort by distance and return top results
        fpo_distances.sort(key=lambda x: x[1])
        return fpo_distances[:limit]
    
    def enhance_fpo_with_coordinates(self, fpo: FPO) -> FPO:
        """FPO coordinates are now auto-assigned on initialization, so this is mostly a no-op."""
        return fpo  # Coordinates already assigned in __init__
    
    def find_fpos_by_state(self, state: str) -> List[FPO]:
        """Find all FPOs in a specific state"""
        return [fpo for fpo in self.fpos if fpo.state.lower() == state.lower()]
    def json_source_loaded(self) -> bool:
        return self._json_loaded
    def total_fpos(self) -> int:
        return len(self.fpos)
