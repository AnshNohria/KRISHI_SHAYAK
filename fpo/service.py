"""
FPO (Farmer Producer Organization) Service for Krishi Dhan Sahayak
Helps farmers find nearby FPOs and learn about registration benefits
"""

import json
import math
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class FPO:
    """Farmer Producer Organization data structure"""
    name: str
    district: str
    state: str
    lat: float
    lon: float
    contact_person: str
    phone: str
    email: str = ""
    crops: List[str] = None
    services: List[str] = None
    registration_year: int = None
    members_count: int = None

    def __post_init__(self):
        if self.crops is None:
            self.crops = []
        if self.services is None:
            self.services = []

class FPOService:
    """Service for finding and managing FPO information.

    Attempts to load extracted JSON (fpo_data.json) from pdf_extract.py.
    Falls back to bundled sample dataset if JSON missing or invalid.
    """
    def __init__(self):
        self._json_loaded = False
        self.fpos = self._load_external_or_sample()
    
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
            # Keep lat/lon only if present and numeric; else set to None so we can skip for distance calc
            raw_lat = rec.get('lat')
            raw_lon = rec.get('lon')
            try:
                lat_val = float(raw_lat) if raw_lat not in (None, "",) else None
            except (TypeError, ValueError):
                lat_val = None
            try:
                lon_val = float(raw_lon) if raw_lon not in (None, "",) else None
            except (TypeError, ValueError):
                lon_val = None
            fpos.append(FPO(
                name=rec.get('name',''),
                district=rec.get('district',''),
                state=rec.get('state',''),
                lat=lat_val or 0.0,
                lon=lon_val or 0.0,
                contact_person=rec.get('contact_person','(unknown)'),
                phone=rec.get('phone',''),
                email=rec.get('email',''),
                crops=rec.get('crops') or [],
                services=rec.get('services') or [],
                registration_year=rec.get('registration_year'),
                members_count=rec.get('members_count')
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
                contact_person=d["contact_person"],
                phone=d["phone"],
                email=d.get("email", ""),
                crops=d.get("crops", []),
                services=d.get("services", []),
                registration_year=d.get("registration_year"),
                members_count=d.get("members_count")
            ))
        return fpos
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
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
    
    def find_nearest_fpos(self, lat: float, lon: float, limit: int = 5) -> List[Tuple[FPO, float]]:
        """Find nearest FPOs to a given location"""
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
    
    def find_fpos_by_state(self, state: str) -> List[FPO]:
        """Find all FPOs in a specific state"""
        return [fpo for fpo in self.fpos if fpo.state.lower() == state.lower()]
    
    def find_fpos_by_crop(self, crop: str) -> List[FPO]:
        """Find FPOs that deal with a specific crop"""
        crop_lower = crop.lower()
        return [fpo for fpo in self.fpos if any(crop_lower in c.lower() for c in fpo.crops)]
    def find_fpos_by_service(self, service: str) -> List[FPO]:
        s = service.lower()
        return [fpo for fpo in self.fpos if any(s in serv.lower() for serv in fpo.services)]
    def json_source_loaded(self) -> bool:
        return self._json_loaded
    def total_fpos(self) -> int:
        return len(self.fpos)

def get_fpo_registration_benefits() -> List[str]:
    """Get comprehensive list of FPO registration benefits"""
    return [
        "🏦 **Financial Benefits:**",
        "   • Access to institutional credit at lower interest rates",
        "   • Government subsidies and grants up to ₹15 lakhs per FPO",
        "   • Easier loan approval with FPO as collateral",
        "   • Reduced transaction costs through collective bargaining",
        "",
        "💰 **Market Access:**", 
        "   • Direct access to wholesale and retail markets",
        "   • Elimination of middlemen, leading to better prices",
        "   • Contract farming opportunities with companies",
        "   • Export opportunities for quality produce",
        "",
        "🌱 **Input Supply:**",
        "   • Bulk purchase of seeds, fertilizers at discounted rates",
        "   • Quality assurance of inputs through collective procurement",
        "   • Access to latest agricultural technologies and machinery",
        "   • Reduced input costs by 10-20% on average",
        "",
        "📚 **Knowledge & Training:**",
        "   • Regular training on modern farming techniques",
        "   • Workshops on crop diversification and value addition",
        "   • Technical support from agricultural experts",
        "   • Digital literacy and technology adoption programs",
        "",
        "🏭 **Processing & Value Addition:**",
        "   • Collective processing facilities (mills, storage, packaging)",
        "   • Brand development and marketing support",
        "   • Quality certification (organic, FSSAI, etc.)",
        "   • Cold storage and post-harvest management",
        "",
        "⚖️ **Legal & Regulatory:**",
        "   • Legal entity status with limited liability",
        "   • Tax benefits and exemptions under various schemes",
        "   • Professional management and governance structure",
        "   • Dispute resolution mechanisms",
        "",
        "🌾 **Agricultural Support:**",
        "   • Crop insurance at group rates",
        "   • Weather-based advisory services",
        "   • Soil testing and farm advisory services",
        "   • Integrated pest management programs"
    ]

def get_fpo_registration_process() -> List[str]:
    """Get step-by-step FPO registration process"""
    return [
        "📋 **FPO Registration Process:**",
        "",
        "**Step 1: Formation & Planning**",
        "   • Form a group of minimum 10 farmers (300+ for Primary Agricultural Credit Societies)",
        "   • Conduct awareness meetings in your village/cluster",
        "   • Identify common crops/activities for collective action",
        "   • Elect interim leadership (President, Secretary, Treasurer)",
        "",
        "**Step 2: Legal Registration**",
        "   • Choose registration type: Producer Company under Companies Act 2013",
        "   • Prepare required documents (see document list below)",
        "   • Apply through ROC (Registrar of Companies) online portal",
        "   • Obtain Certificate of Incorporation (15-30 days)",
        "",
        "**Step 3: Required Documents**",
        "   • Memorandum and Articles of Association",
        "   • Form INC-7 (Application for incorporation)",
        "   • Identity & address proof of all directors/members",
        "   • Land records/farming evidence of members",
        "   • Consent letters from all founding members",
        "",
        "**Step 4: Post-Registration Setup**",
        "   • Open bank account with incorporation certificate",
        "   • Register for GST if annual turnover expected > ₹40 lakhs",
        "   • Apply for relevant licenses (FSSAI, Organic certification)",
        "   • Conduct first General Body meeting and elect Board",
        "",
        "**Step 5: Government Support & Funding**",
        "   • Apply for government schemes through SFAC (Small Farmers' Agri-Business Consortium)",
        "   • Submit business plan for ₹15 lakh matching grant",
        "   • Register on GeM portal for government procurement",
        "   • Connect with NABARD for credit linkage",
        "",
        "**Step 6: Operational Setup**",
        "   • Hire professional CEO/Manager if required",
        "   • Set up basic infrastructure (office, storage, etc.)",
        "   • Start collective procurement and marketing activities",
        "   • Maintain proper books of accounts and records",
        "",
        "⏰ **Timeline:** Complete process takes 2-6 months",
        "💰 **Cost:** ₹15,000 - ₹50,000 (including professional help)",
        "📞 **Support:** Contact your nearest KVK (Krishi Vigyan Kendra) or District Collector office"
    ]

def get_government_schemes_for_fpos() -> List[str]:
    """Get list of government schemes supporting FPOs"""
    return [
        "🏛️ **Major Government Schemes for FPOs:**",
        "",
        "**1. Formation and Promotion of FPOs Scheme (2020-21 to 2027-28)**",
        "   • Central Sector Scheme with ₹6,865 crore budget",
        "   • Formation of 10,000 new FPOs across India",
        "   • ₹18.50 lakh support per FPO over 5 years",
        "   • Cluster-based approach for better sustainability",
        "",
        "**2. NABARD - Producer Organization Development Fund**",
        "   • Credit support up to ₹100 crore per FPO",
        "   • Interest subvention schemes",
        "   • Capacity building and training programs",
        "   • Infrastructure development support",
        "",
        "**3. SFAC (Small Farmers' Agri-Business Consortium) Support**",
        "   • Matching equity grant up to ₹15 lakh per FPO",
        "   • Credit guarantee fund coverage",
        "   • Market linkage and handholding support",
        "   • Business development services",
        "",
        "**4. Mission for Integrated Development of Horticulture (MIDH)**",
        "   • Support for horticulture-focused FPOs",
        "   • Infrastructure development grants",
        "   • Processing and value addition support",
        "   • Market infrastructure development",
        "",
        "**5. National Food Security Mission (NFSM)**",
        "   • Support for FPOs in rice, wheat, pulses, coarse cereals",
        "   • Seed production and processing support",
        "   • Technology demonstration and training",
        "   • Custom hiring centers establishment",
        "",
        "**6. Paramparagat Krishi Vikas Yojana (PKVY)**",
        "   • Support for organic farming FPOs",
        "   • Cluster approach with ₹50,000 per hectare support",
        "   • Organic certification and marketing support",
        "   • Premium price realization for organic produce",
        "",
        "**7. PM-KISAN FPO Scheme**",
        "   • Direct benefit transfer to FPO members",
        "   • Priority in government procurement",
        "   • Preferential treatment in various schemes",
        "   • Digital platform integration"
    ]
