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
    from maps.dual_api_service import geocode_dual_api, calculate_distance as maps_calculate_distance
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
    
    async def geocode_location_async(self, location: str) -> Optional[Tuple[float, float]]:
        """Geocode a location using dual maps API."""
        if not MAPS_API_AVAILABLE:
            return None
        
        # Check cache first
        if location in self._geocoded_locations:
            return self._geocoded_locations[location]
        
        try:
            result = await geocode_dual_api(location)
            if result:
                coords = (result.lat, result.lon)
                self._geocoded_locations[location] = coords
                return coords
        except Exception as e:
            print(f"Geocoding error for {location}: {e}")
        
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
            return self._load_sample_database()
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

    def _load_sample_database(self) -> List[FPO]:
        """Sample fallback database."""
        fpo_data = [
            {"name": "Punjab Kisan Producer Company Ltd", "district": "Ludhiana", "state": "Punjab", "lat": 30.9010, "lon": 75.8573, "contact_person": "Harjit Singh", "phone": "+91-9876543210", "email": "info@punjabkisan.org", "crops": ["wheat", "rice", "cotton", "sugarcane"], "services": ["seeds", "fertilizers", "machinery", "marketing"], "registration_year": 2018, "members_count": 450},
            {"name": "Malwa FPO", "district": "Bathinda", "state": "Punjab", "lat": 30.2118, "lon": 74.9455, "contact_person": "Gurpreet Kaur", "phone": "+91-9876543211", "crops": ["cotton", "wheat", "rice"], "services": ["organic inputs", "certification", "direct marketing"], "registration_year": 2019, "members_count": 320},
            {"name": "Majha Farmers Producer Organization", "district": "Amritsar", "state": "Punjab", "lat": 31.6340, "lon": 74.8723, "contact_person": "Kuldeep Singh", "phone": "+91-9876543212", "crops": ["wheat", "rice", "vegetables"], "services": ["machinery rental", "storage", "processing"], "registration_year": 2020, "members_count": 280},
            {"name": "Haryana Gramin Producer Company", "district": "Karnal", "state": "Haryana", "lat": 29.6857, "lon": 76.9905, "contact_person": "Raj Kumar", "phone": "+91-9876543213", "crops": ["wheat", "rice", "mustard", "sugarcane"], "services": ["input supply", "custom hiring", "marketing"], "registration_year": 2017, "members_count": 520},
            {"name": "Mewat Farmers Collective", "district": "Nuh", "state": "Haryana", "lat": 28.1124, "lon": 77.0085, "contact_person": "Mohammad Rashid", "phone": "+91-9876543214", "crops": ["bajra", "wheat", "mustard"], "services": ["seeds", "training", "market linkage"], "registration_year": 2019, "members_count": 180},
            {"name": "Western UP Farmers Producer Organization", "district": "Meerut", "state": "Uttar Pradesh", "lat": 28.9845, "lon": 77.7064, "contact_person": "Ramesh Chandra", "phone": "+91-9876543215", "crops": ["sugarcane", "wheat", "rice", "potato"], "services": ["machinery", "storage", "processing", "marketing"], "registration_year": 2018, "members_count": 680},
            {"name": "Bundelkhand Kisan Producer Company", "district": "Jhansi", "state": "Uttar Pradesh", "lat": 25.4484, "lon": 78.5685, "contact_person": "Suresh Yadav", "phone": "+91-9876543216", "crops": ["wheat", "gram", "mustard", "sesame"], "services": ["drought-resistant seeds", "water management", "training"], "registration_year": 2020, "members_count": 420},
            {"name": "Vidarbha Cotton Farmers Producer Organization", "district": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882, "contact_person": "Dnyaneshwar Patil", "phone": "+91-9876543217", "crops": ["cotton", "soybean", "pigeon pea"], "services": ["organic farming", "certification", "export"], "registration_year": 2017, "members_count": 750},
            {"name": "Western Maharashtra FPO", "district": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567, "contact_person": "Prakash Shinde", "phone": "+91-9876543218", "crops": ["grapes", "pomegranate", "onion", "sugarcane"], "services": ["processing", "packaging", "export", "cold storage"], "registration_year": 2019, "members_count": 380},
            {"name": "Karnataka Coffee Growers FPO", "district": "Chikmagalur", "state": "Karnataka", "lat": 13.3161, "lon": 75.7720, "contact_person": "Ravi Kumar", "phone": "+91-9876543219", "crops": ["coffee", "pepper", "cardamom"], "services": ["processing", "quality certification", "direct trade"], "registration_year": 2018, "members_count": 290},
            {"name": "North Karnataka Farmers Collective", "district": "Belgaum", "state": "Karnataka", "lat": 15.8497, "lon": 74.4977, "contact_person": "Basavaraj Patil", "phone": "+91-9876543220", "crops": ["cotton", "sugarcane", "jowar", "groundnut"], "services": ["input supply", "machinery rental", "marketing"], "registration_year": 2020, "members_count": 460},
            {"name": "Saurashtra Cotton Producer Organization", "district": "Rajkot", "state": "Gujarat", "lat": 22.3039, "lon": 70.8022, "contact_person": "Kiran Patel", "phone": "+91-9876543221", "crops": ["cotton", "groundnut", "castor"], "services": ["ginning", "marketing", "quality testing"], "registration_year": 2017, "members_count": 580},
            {"name": "Kutch Farmers Producer Company", "district": "Kutch", "state": "Gujarat", "lat": 23.7337, "lon": 69.8597, "contact_person": "Bharat Shah", "phone": "+91-9876543222", "crops": ["cotton", "mustard", "cumin"], "services": ["organic certification", "processing", "export"], "registration_year": 2019, "members_count": 340},
            {"name": "Rajasthan Desert Farmers FPO", "district": "Jodhpur", "state": "Rajasthan", "lat": 26.2389, "lon": 73.0243, "contact_person": "Mohan Lal", "phone": "+91-9876543223", "crops": ["bajra", "mustard", "gram", "guar"], "services": ["drought management", "seeds", "water conservation"], "registration_year": 2018, "members_count": 320},
            {"name": "Tamil Nadu Rice Farmers FPO", "district": "Thanjavur", "state": "Tamil Nadu", "lat": 10.7870, "lon": 79.1378, "contact_person": "Murugan Selvam", "phone": "+91-9876543224", "crops": ["rice", "sugarcane", "cotton"], "services": ["custom milling", "marketing", "storage"], "registration_year": 2019, "members_count": 480},
            {"name": "Andhra Spice Farmers Producer Organization", "district": "Guntur", "state": "Andhra Pradesh", "lat": 16.3067, "lon": 80.4365, "contact_person": "Venkata Rao", "phone": "+91-9876543225", "crops": ["chili", "turmeric", "cotton", "rice"], "services": ["processing", "grading", "export", "quality certification"], "registration_year": 2018, "members_count": 620},
            {"name": "West Bengal Rice Producers Collective", "district": "Burdwan", "state": "West Bengal", "lat": 23.2324, "lon": 87.8615, "contact_person": "Tapan Das", "phone": "+91-9876543226", "crops": ["rice", "potato", "jute", "vegetables"], "services": ["seeds", "machinery", "marketing", "processing"], "registration_year": 2020, "members_count": 540},
            {"name": "Madhya Pradesh Soybean FPO", "district": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577, "contact_person": "Rajesh Sharma", "phone": "+91-9876543227", "crops": ["soybean", "wheat", "cotton", "gram"], "services": ["oil processing", "marketing", "storage", "input supply"], "registration_year": 2017, "members_count": 700},
            {"name": "Bihar Vegetable Growers FPO", "district": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376, "contact_person": "Anil Kumar", "phone": "+91-9876543228", "crops": ["potato", "onion", "tomato", "cauliflower"], "services": ["cold storage", "packaging", "marketing", "transportation"], "registration_year": 2019, "members_count": 350},
            {"name": "Odisha Tribal Farmers Producer Organization", "district": "Kalahandi", "state": "Odisha", "lat": 20.1333, "lon": 83.1667, "contact_person": "Suresh Majhi", "phone": "+91-9876543229", "crops": ["rice", "millets", "turmeric", "vegetables"], "services": ["organic certification", "processing", "tribal products marketing"], "registration_year": 2020, "members_count": 280}
        ]
        fpos: List[FPO] = []
        for d in fpo_data:
            fpos.append(FPO(
                name=d["name"],
                district=d["district"],
                state=d["state"],
                lat=d["lat"],
                lon=d["lon"],
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
        """Find nearest FPOs by geocoding location name first."""
        # Geocode the location
        coords = await self.geocode_location_async(f"{location_name}, {state}" if state else location_name)
        if not coords:
            return []
        
        lat, lon = coords
        
        # If state is specified, filter FPOs by state first
        if state:
            state_fpos = [fpo for fpo in self.fpos if fpo.state.lower() == state.lower()]
            fpo_distances = []
            for fpo in state_fpos:
                # Skip entries lacking real coordinates
                if fpo.lat == 0.0 and fpo.lon == 0.0:
                    continue
                distance = self.calculate_distance(lat, lon, fpo.lat, fpo.lon)
                fpo_distances.append((fpo, distance))
        else:
            # Search all FPOs
            fpo_distances = []
            for fpo in self.fpos:
                if fpo.lat == 0.0 and fpo.lon == 0.0:
                    continue
                distance = self.calculate_distance(lat, lon, fpo.lat, fpo.lon)
                fpo_distances.append((fpo, distance))
        
        # Sort by distance and return top results
        fpo_distances.sort(key=lambda x: x[1])
        return fpo_distances[:limit]
    
    def enhance_fpo_with_coordinates(self, fpo: FPO) -> FPO:
        """Try to enhance FPO with coordinates by geocoding its location."""
        if fpo.lat != 0.0 or fpo.lon != 0.0:
            return fpo  # Already has coordinates
        
        # Try to geocode using district and state
        location_string = f"{fpo.district}, {fpo.state}, India"
        coords = self.geocode_location_sync(location_string)
        
        if coords:
            fpo.lat, fpo.lon = coords
            print(f"Enhanced {fpo.name} with coordinates: {coords}")
        
        return fpo
    
    def find_fpos_by_state(self, state: str) -> List[FPO]:
        """Find all FPOs in a specific state"""
        return [fpo for fpo in self.fpos if fpo.state.lower() == state.lower()]
    def json_source_loaded(self) -> bool:
        return self._json_loaded
    def total_fpos(self) -> int:
        return len(self.fpos)

def get_fpo_registration_benefits() -> List[str]:
    """Deprecated: benefits content removed in minimal build."""
    return []

def get_fpo_registration_process() -> List[str]:
    """Deprecated: registration content removed in minimal build."""
    return []

def get_government_schemes_for_fpos() -> List[str]:
    """Deprecated: schemes content removed in minimal build."""
    return []
