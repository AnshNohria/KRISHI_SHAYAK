import os
from pathlib import Path
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
from statistics import mean
import re

# LangChain + Google Genie wrapper (as in your environment)
#from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
# -------------------------------
# CONFIG (hardcoded for now)
# -------------------------------
AGMARKET_RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
AGMARKET_BASE = f"https://api.data.gov.in/resource/{AGMARKET_RESOURCE}"
AGMARKET_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"  # sample/test key

LOOKBACK_DAYS = 30       # how far back to search for "most recent" data
RECENT_WINDOW_DAYS = 30  # how many recent days to collect for trend (from most recent date)
RECENT_MIN_POINTS = 3    # minimum points to consider a regression
RECENT_PROJECTION_DAYS = 7

# Prefer env var; else use the file in the Krishi Shayak folder (repo root)
HISTORICAL_CSV = os.getenv("HISTORICAL_CSV") or str((Path(__file__).resolve().parent / "historical_prices.csv"))

GEMINI_MODEL_NAME = "gemini-1.5-flash"

load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

state_to_districts = {
    "Andaman and Nicobar Islands": ["Nicobar", "South Andaman", "North and Middle Andaman"],
    "Andhra Pradesh": ["Anantapur", "Cuddapah", "Chittor", "East Godavari", "Guntur", "Krishna", "Kurnool", "Nellore", "Prakasam", "Srikakulam", "Vijayanagaram", "Visakhapatnam", "West Godavari"],
    "Arunachal Pradesh": ["Changlang", "Lohit", "East Siang", "Lower Dibang Valley", "Lower Subansiri", "Papum Pore", "Tawang", "Tirap", "Upper Subansiri", "West Kameng", "West Siang"],
    "Assam": ["BONGAIGAON", "Cachar", "Barpeta", "Darrang", "Dhemaji", "Dhubri", "Dibrugarh", "Goalpara", "Golaghat", "Hailakandi", "Jorhat", "Kamrup", "Karbi Anglong", "Karimganj", "Kokrajhar", "Lakhimpur", "MORIGAON", "Nagaon", "Nalbari", "Sibsagar", "Sonitpur", "Tinsukia"],
    "Bihar": ["Araria", "Aurangabad", "Arwal", "Banka", "Begusarai", "Bhagalpur", "Bhojpur", "Buxar", "Chhapra", "Darbhanga", "East Champaran/ Motihari", "Gaya", "Gopalgang", "Jamui", "Jehanabad", "Kaimur/Bhabhua", "Kaithar", "Khagaria", "Kishanganj", "Luckeesarai", "Madhepura", "Madhubani", "Munghair", "Muzaffarpur", "Nalanda", "Nawada", "Patna", "Purnea", "Rohtas", "Saharsa", "Samastipur", "Saran", "Sheikhpura", "Sheohar", "Sitamarhi", "Siwan", "Supaul", "Vaishali", "West Chambaran"],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": ["Balod", "Balodabazar", "Balrampur", "Bastar", "Bemetara", "Bijapur", "Bilaspur", "Dantewada", "Dhamtari", "Durg", "Gariyaband", "Janjgir", "Jashpur", "Kabirdham", "Kanker", "Kondagaon", "Korba", "Koria", "Mahasamund", "Mungeli", "Narayanpur", "Raigarh", "Raipur", "Rajnandgaon", "Sukma", "Surajpur", "Surguja"],
    "Goa": ["North Goa", "South Goa"],
    "Gujarat": ["Ahmedabad", "Amreli", "Anand", "Banaskanth", "Bharuch", "Bhavnagar", "Botad", "Chhota Udaipur", "Dahod", "Dang", "Devbhumi Dwarka", "Gandhinagar", "Gir Somnath", "Jamnagar", "Junagarh", "Kachchh", "Kheda", "Mehsana", "Morbi", "Narmada", "Navsari", "Panchmahals", "Patan", "Porbandar", "Rajkot", "Sabarkantha", "Surat", "Surendranagar", "The Dangs", "Vadodara(Baroda)", "Valsad"],
    "Haryana": ["Ambala", "Bhiwani", "Faridabad", "Fatehabad", "Gurgaon", "Hissar", "Jhajar", "Jind", "Kaithal", "Karnal", "Kurukshetra", "Mahendragarh-Narnaul", "Mewat", "Palwal", "Panchkula", "Panipat", "Rewari", "Rohtak", "Sirsa", "Sonipat", "Yamuna Nagar"],
    "Himachal Pradesh": ["Bilaspur", "Chamba", "Hamirpur", "Kangra", "Kullu", "Mandi", "Shimla", "Sirmore", "Solan", "Una"],
    "Jammu and Kashmir": ["Anantnag", "Badgam", "Baramulla", "Jammu", "Kathua", "Kupwara", "Pulwama", "Rajouri", "Srinagar", "Udhampur"],
    "Jharkhand": ["Bokaro", "Deogarh", "Dhanbad", "Dumka", "East Singhbhum", "Garhwa", "Giridih", "Godda", "Gumla", "Hazaribagh", "Jamtara", "Koderma", "Latehar", "Lohardaga", "Pakur", "Palamu", "Ranchi", "Sahebgang", "Saraikela(Kharsanwa)", "Simdega", "West Singbhum"],
    "Karnataka": ["Bagalkot", "Bangalore", "Belgaum", "Bellary", "Bidar", "Bijapur", "Chamrajnagar", "Chikmagalur", "Chitradurga", "Davangere", "Dharwad", "Gadag", "Hassan", "Haveri", "Kalburgi", "Karwar(Uttar Kannad)", "Kolar", "Koppal", "Madikeri(Kodagu)", "Mandya", "Mangalore(Dakshin Kannad)", "Mysore", "Raichur", "Shimoga", "Tumkur", "Udupi", "Yadgiri"],
    "Kerala": ["Alappuzha", "Alleppey", "Ernakulam", "Idukki", "Kannur", "Kasargod", "Kollam", "Kottayam", "Kozhikode(Calicut)", "Malappuram", "Palakad", "Pathanamthitta", "Thirssur", "Thiruvananthapuram", "Wayanad"],
    "Madhya Pradesh": ["Agar Malwa", "Alirajpur", "Anupur", "Ashoknagar", "Badwani", "Balaghat", "Betul", "Bhind", "Bhopal", "Burhanpur", "Chhatarpur", "Chhindwara", "Damoh", "Datia", "Dewas", "Dhar", "Dindori", "Guna", "Gwalior", "Harda", "Hoshangabad", "Indore", "Jabalpur", "Jhabua", "Katni", "Khandwa", "Khargone", "Mandla", "Mandsaur", "Morena", "Narsinghpur", "Neemuch", "Panna", "Raisen", "Rajgarh", "Ratlam", "Rewa", "Sagar", "Satna", "Sehore", "Seoni", "Shajapur", "Shehdol", "Sheopur", "Shivpuri", "Sidhi", "Singroli", "Tikamgarh", "Ujjain", "Umariya", "Vidisha"],
    "Maharashtra": ["Ahmednagar", "Akola", "Amarawati", "Beed", "Bhandara", "Buldhana", "Chandrapur", "Chattrapati Sambhajinagar", "Dharashiv(Usmanabad)", "Dhule", "Gadchiroli", "Gondiya", "Hingoli", "Jalana", "Jalgaon", "Kolhapur", "Latur", "Mumbai", "Murum", "Nagpur", "Nanded", "Nandurbar", "Nashik", "Parbhani", "Pune", "Raigad", "Ratnagiri", "Sangli", "Satara", "Sholapur", "Thane", "Vashim", "Wardha", "Yavatmal"],
    "Manipur": ["Bishnupur", "Imphal East", "Imphal West", "Kakching", "Thoubal"],
    "Meghalaya": ["East Garo Hills", "East Jaintia Hills", "East Khasi Hills", "Nongpoh (R-Bhoi)", "South Garo Hills", "South West Garo Hills", "South West Khasi Hills", "West Garo Hills", "West Jaintia Hills", "West Khasi Hills"],
    "Mizoram": ["Aizawl", "Lungli"],
    "Delhi": ["Delhi"],
    "Nagaland": ["Dimapur", "Kiphire", "Kohima", "Longleng", "Mokokchung", "Mon", "Peren", "Phek", "Tsemenyu", "Tuensang", "Wokha", "Zunheboto"],
    "Odisha": ["Angul", "Balasore", "Bargarh", "Bhadrak", "Bolangir", "Boudh", "Cuttack", "Deogarh", "Dhenkanal", "Gajapati", "Ganjam", "Jagatsinghpur", "Jajpur", "Jharsuguda", "Kalahandi", "Kandhamal", "Kendrapara", "Keonjhar", "Khurda", "Koraput", "Malkangiri", "Mayurbhanja", "Nayagarh", "Nowarangpur", "Nuapada", "Puri", "Rayagada", "Sambalpur", "Sonepur", "Sundergarh"],
    "Puducherry": ["Karaikal", "Pondicherry"],
    "Punjab": ["Amritsar", "Barnala", "Bhatinda", "Faridkot", "Fatehgarh", "Fazilka", "Ferozpur", "Gurdaspur", "Hoshiarpur", "Jalandhar", "Ludhiana", "Mansa", "Moga", "Mohali", "Muktsar", "Nawanshahr", "Pathankot", "Patiala", "Ropar (Rupnagar)", "Sangrur", "Tarntaran", "kapurthala"],
    "Rajasthan": ["Jhunjhunu", "Ajmer", "Alwar", "Anupgarh", "Balotra", "Banswara", "Baran", "Barmer", "Beawar", "Bharatpur", "Bhilwara", "Bikaner", "Bundi", "Chittorgarh", "Churu", "Dausa", "Deedwana Kuchaman", "Deeg", "Dholpur", "Dudu", "Dungarpur", "Ganganagar", "Gangapur City", "Hanumangarh", "Jaipur", "Jaipur Rural", "Jaisalmer", "Jalore", "Jhalawar", "Jhunjunu", "Jodhpur", "Jodhpur Rural", "Karauli", "Kekri", "Khairthal Tijara", "Kota", "Kotputli- Behror", "Nagaur", "Neem Ka Thana", "Pali", "Phalodi", "Pratapgarh", "Rajasamand", "Rajsamand", "Sanchore", "Sikar", "Sirohi", "Swai Madhopur", "Tonk", "Udaipur"],
    "Sikkim": ["East", "South Sikkim (Namchi)", "West Sikkim (Gyalsing)"],
    "Tamil Nadu": ["Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul", "Erode", "Kallakuruchi", "Kancheepuram", "Karur", "Krishnagiri", "Madurai", "Nagapattinam", "Nagercoil (Kannyiakumari)", "Namakkal", "Perambalur", "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "The Nilgiris", "Theni", "Thiruchirappalli", "Thirunelveli", "Thirupathur", "Thirupur", "Thiruvannamalai", "Thiruvarur", "Thiruvellore", "Tuticorin", "Vellore", "Villupuram", "Virudhunagar"],
    "Telangana": ["Adilabad", "Hyderabad", "Jagityal", "Karimnagar", "Khammam", "Mahbubnagar", "Medak", "Nalgonda", "Nizamabad", "Ranga Reddy", "Warangal"],
    "Tripura": ["Dhalai", "Gomati", "Khowai", "North Tripura", "Sepahijala", "South District", "Unokoti", "West District"],
    "Uttar Pradesh": ["Agra", "Aligarh", "Ambedkarnagar", "Amethi", "Amroha", "Auraiya", "Ayodhya", "Azamgarh", "Badaun", "Baghpat", "Bahraich", "Ballia", "Balrampur", "Banda", "Barabanki", "Bareilly", "Basti", "Bhadohi(Sant Ravi Nagar)", "Bijnor", "Bulandshahar", "Chandauli", "Chitrakut", "Deoria", "Etah", "Etawah", "Farukhabad", "Fatehpur", "Firozabad", "Gautam Budh Nagar", "Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur", "Hapur", "Hardoi", "Hathras", "Jalaun (Orai)", "Jaunpur", "Jhansi", "Kannuj", "Kanpur", "Kanpur Dehat", "Kasganj", "Kaushambi", "Khiri (Lakhimpur)", "Kushinagar", "Lakhimpur", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri", "Mathura", "Mau(Maunathbhanjan)", "Meerut", "Mirzapur", "Muzaffarnagar", "Pillibhit", "Pratapgarh", "Prayagraj", "Raebarelli", "Rampur", "Saharanpur", "Sambhal", "Sant Kabir Nagar", "Shahjahanpur", "Shamli", "Shravasti", "Siddharth Nagar", "Sitapur", "Sonbhadra", "Unnao", "Varanasi"],
    "Uttarakhand": ["Champawat", "Dehradoon", "Garhwal (Pauri)", "Haridwar", "Nanital", "UdhamSinghNagar"],
    "West Bengal": ["Alipurduar", "Bankura", "Birbhum", "Burdwan", "Coochbehar", "Dakshin Dinajpur", "Darjeeling", "Hooghly", "Howrah", "Jalpaiguri", "Jhargram", "Kalimpong", "Kolkata", "Malda", "Medinipur(E)", "Medinipur(W)", "Murshidabad", "Nadia", "North 24 Parganas", "Paschim Bardhaman", "Purba Bardhaman", "Puruliya", "Sounth 24 Parganas", "Uttar Dinajpur"]
}
# -------------------------------
# Helpers
# -------------------------------
def to_float_safe(x):
    try:
        if x is None:
            return None
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None

def parse_date_safe(s):
    if s is None:
        return None
    s = str(s).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    # try splitting and guessing DD/MM/YYYY
    parts = s.replace("-", "/").split("/")
    if len(parts) == 3:
        try:
            d, m, y = parts
            return datetime(int(y), int(m), int(d))
        except Exception:
            pass
    return None

def get_record_field(record, key_predicate):
    """Return the first matching value from a record where key_predicate(lower_key) is True."""
    # exact keys first
    for k, v in record.items():
        try:
            if key_predicate(k):
                return v
        except Exception:
            pass
    # lowercased keys
    for k, v in record.items():
        try:
            if key_predicate(k.lower()):
                return v
        except Exception:
            pass
    return None

def extract_modal_price(record):
    """Try multiple heuristics to find the modal price in a record dict."""
    # direct candidates
    keys_to_try = [
        "modal_price", "modalprice", "modal price", "modal_price (rs./quintal)",
        "modal_price (rs/quintal)", "modal_price_rs", "modal_price_rs/quintal",
        "min_price", "max_price", "modal", "modalprice", "Modal_Price", "ModalPrice", "Modal Price"
    ]
    for cand in keys_to_try:
        val = get_record_field(record, lambda k: k.lower() == cand.lower())
        if val is not None and str(val).strip() != "":
            f = to_float_safe(val)
            if f is not None:
                return f
    # contains both modal and price
    val = get_record_field(record, lambda k: ("modal" in k.lower() and "price" in k.lower()))
    if val is not None:
        f = to_float_safe(val)
        if f is not None:
            return f
    # any numeric under 'price'
    val = get_record_field(record, lambda k: "price" in k.lower())
    if val is not None:
        f = to_float_safe(val)
        if f is not None:
            return f
    return None

def extract_arrival_date(record):
    """Get arrival/report date from record (various key names)."""
    val = get_record_field(record, lambda k: "arrival" in k.lower() or "arrival_date" in k.lower() or "report" in k.lower())
    if val:
        parsed = parse_date_safe(val)
        return parsed
    return None

def extract_market_name(record):
    return get_record_field(record, lambda k: "market" in k.lower() or "market_center" in k.lower() or "market center" in k.lower())

# -------------------------------
# Gemini LLM for crop name normalization
# -------------------------------
def init_gemini():
    if not GOOGLE_API_KEY:
        print("⚠️  No GEMINI_API_KEY/GOOGLE_API_KEY set; proceeding without LLM normalization.")
        return None
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        return genai.GenerativeModel(model_name=GEMINI_MODEL_NAME)
    except Exception as e:
        print(f"⚠️  Gemini init failed: {e}; continuing without LLM normalization.")
        return None


def gemini_map_input(llm, user_input: str, field_name: str, candidate_list: list) -> str:
    """
    Use Gemini to map a fuzzy/incorrect user input to one of the valid candidates.
    """
    prompt = f"""
You are given a user-provided {field_name} name: "{user_input}"

Here is the valid list of {field_name}s:
{candidate_list}

Choose the closest matching item from the list above.
Respond with ONLY the corrected {field_name} (must be exactly one from the list).
    """.strip()

    if llm is None:
        # Simple heuristic fallback: case-insensitive exact or prefix match
        lower = user_input.strip().lower()
        for cand in candidate_list:
            if cand.lower() == lower:
                return cand
        for cand in candidate_list:
            if cand.lower().startswith(lower[:3]):
                return cand
        return user_input.strip().title()
    resp = llm.generate_content(contents=prompt)
    return (resp.text or user_input).strip()

def gemini_map_all_inputs(llm, user_inputs: dict, csv_path: str = HISTORICAL_CSV) -> dict:
    """
    Map free-text crop/state/district to canonical dataset values.
    Uses gemini_map_input for each field separately (3 Gemini calls).
    """
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as e:
        print(f"Warning: failed to read {csv_path}: {e}")
        return {k: v.strip().title() for k, v in user_inputs.items()}

    # Candidate lists from dataset
    commodity_list = sorted(df["commodity"].dropna().unique())
    state_list = sorted(df["state_name"].dropna().unique())

    mapped = {}
    mapped["commodity"] = gemini_map_input(llm, user_inputs.get("commodity",""), "commodity", commodity_list)
    mapped["state_name"] = gemini_map_input(llm, user_inputs.get("state_name",""), "state", state_list)
    district_list = sorted(state_to_districts[mapped["state_name"]])
    mapped["district_name"] = gemini_map_input(llm, user_inputs.get("district_name",""), "district", district_list)

    return mapped

# -------------------------------
# Fetch data for a single date from Agmarknet API
# -------------------------------
def fetch_for_date(commodity: str, state: str, district: str, date_obj: datetime):
    arrival_str = date_obj.strftime("%d/%m/%Y")
    params = {
        "api-key": AGMARKET_API_KEY,
        "format": "json",
        "filters[State]": state,
        "filters[District]": district,
        "filters[Commodity]": commodity,
        "filters[Arrival_Date]": arrival_str,
        "limit": 500
    }
    try:
        resp = requests.get(AGMARKET_BASE, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        # debug raw response snippet when records found
        if data.get("records"):
            print(f"DEBUG: raw response (truncated) for {arrival_str}:")
            try:
                print(str(resp.text)[:600] + ("\n... (truncated)\n" if len(resp.text) > 600 else "\n"))
            except Exception:
                pass
        return data.get("records", [])
    except Exception as e:
        print(f"Agmarket API error for date {arrival_str}: {e}")
        return []

# -------------------------------
# Find most recent available date within LOOKBACK_DAYS
# -------------------------------
def find_most_recent_data_date(commodity, state, district, lookback=LOOKBACK_DAYS):
    today = datetime.now()
    for delta in range(0, lookback):
        check_date = today - timedelta(days=delta)
        print(f"Checking prices for date: {check_date.strftime('%d/%m/%Y')}")
        recs = fetch_for_date(commodity, state, district, check_date)
        if recs:
            # attempt parse arrival date from first record
            rec0 = recs[0]
            rec_date = parse_date_safe(
                (rec0.get("arrival_date") or rec0.get("Arrival_Date") or
                 get_record_field(rec0, lambda k: "arrival" in k.lower() or "report" in k.lower()))
            )
            if rec_date:
                print(f"  Found records for {rec_date.strftime('%d/%m/%Y')} ({len(recs)} records)")
                return rec_date, recs
            else:
                print("  Found records but couldn't parse arrival date; treating as found.")
                return check_date, recs
    return None, None

# -------------------------------
# Fetch recent days (up to 'days') starting from start_date and going backward
# -------------------------------
def fetch_recent_days_prices(commodity, state, district, days=RECENT_WINDOW_DAYS, start_date=None):
    all_records = []
    if start_date is None:
        start_date = datetime.now()
    days_checked = 0
    max_checks = days  # check up to 'days' calendar days backwards

    while len(all_records) < days and days_checked < max_checks:
        date_check = start_date - timedelta(days=days_checked)
        recs = fetch_for_date(commodity, state, district, date_check)
        if recs:
            # collect modal prices from each record on that day
            for r in recs:
                mp = extract_modal_price(r)
                if mp is not None and mp > 0:
                    arrival_dt = extract_arrival_date(r)
                    arrival_raw = (r.get("arrival_date") or r.get("Arrival_Date") or
                                   get_record_field(r, lambda k: "arrival" in k.lower() or "report" in k.lower()) or "")
                    market_name = extract_market_name(r) or r.get("market") or r.get("Market") or r.get("market_center") or ""
                    all_records.append({
                        "arrival_raw": arrival_raw,
                        "arrival_date": arrival_dt,
                        "arrival_date_str": arrival_raw,
                        "modal_price": mp,
                        "market": market_name,
                        "raw_record": r
                    })
                    print(f"    Price: {mp} for {arrival_raw} @ {market_name}")
        else:
            print("  No data found")
        days_checked += 1

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    # Normalize arrival datetime
    df["arrival_date_dt"] = df["arrival_date"].apply(lambda x: x if isinstance(x, datetime) else parse_date_safe(x))
    df = df.dropna(subset=["arrival_date_dt"])
    df = df.sort_values("arrival_date_dt").drop_duplicates(subset=["arrival_date_dt"], keep="last")
    df = df[["arrival_date_dt", "arrival_date_str", "modal_price", "market", "raw_record"]].rename(
        columns={"arrival_date_str": "arrival_date"}
    )
    return df

# -------------------------------
# Predict price using historical CSV and seasonality ± window days (today-based)
# -------------------------------
def predict_from_history(commodity: str, csv_path=HISTORICAL_CSV, window_days=15):
    if not os.path.exists(csv_path):
        return None, "Historical CSV not found."

    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as e:
        return None, f"Failed loading historical CSV: {e}"

    df.columns = [c.strip() for c in df.columns]
    columns_lower = {c.lower(): c for c in df.columns}
    col_report_date = columns_lower.get("report_date") or columns_lower.get("arrival_date")
    col_commodity = columns_lower.get("commodity")
    col_modal = columns_lower.get("modal_price") or columns_lower.get("modal price")
    col_unit = columns_lower.get("price_unit")

    if not col_report_date or not col_commodity or not col_modal:
        return None, "Historical CSV missing required columns (report_date/commodity/modal_price)."

    # filter commodity rows (case-insensitive)
    df_comp = df[df[col_commodity].str.strip().str.lower() == commodity.strip().lower()]
    if df_comp.empty:
        return None, "No historical records for this commodity."

    # parse dates safely
    df_comp = df_comp.copy()
    df_comp["__date"] = df_comp[col_report_date].apply(parse_date_safe)
    df_comp = df_comp.dropna(subset=["__date"])

    today = datetime.now()
    today_doy = today.timetuple().tm_yday
    window = window_days

    df_comp["__doy"] = df_comp["__date"].apply(lambda d: d.timetuple().tm_yday)

    def within_window(doy):
        diff = min((doy - today_doy) % 365, (today_doy - doy) % 365)
        return diff <= window

    df_season = df_comp[df_comp["__doy"].apply(within_window)].copy()
    if df_season.empty:
        return None, "No seasonal historical records in the ±{} day window.".format(window)

    df_season.loc[:, "modal_f"] = df_season[col_modal].apply(to_float_safe)
    df_season = df_season.dropna(subset=["modal_f"])
    if df_season.empty:
        return None, "Seasonal records exist but modal_price values are unusable."

    seasonal_avg = df_season["modal_f"].mean()

    df_season["year"] = df_season["__date"].dt.year
    year_avg = df_season.groupby("year")["modal_f"].mean().reset_index().sort_values("year")
    trend_note = "stable"
    if len(year_avg) >= 2:
        if year_avg["modal_f"].iloc[-1] > year_avg["modal_f"].iloc[-2]:
            trend_note = "upward"
        elif year_avg["modal_f"].iloc[-1] < year_avg["modal_f"].iloc[-2]:
            trend_note = "downward"

    price_unit = df_season[col_unit].iloc[0] if col_unit and col_unit in df_season.columns else "Rs/Quintal"

    explanation = (
        f"Seasonal average (±{window}d) across years: {round(seasonal_avg,2)} {price_unit}. "
        f"Recent year trend: {trend_note}. Data points used: {len(df_season)}."
    )

    return round(seasonal_avg, 2), explanation

# -------------------------------
# Main tool function
# -------------------------------


def get_market_info_for_crop(user_crop_input: str, user_state_input: str, user_district_input: str):
    # 1) initialize Gemini LLM and map crop
    try:
        llm = init_gemini()
    except Exception as e:
        print("Gemini init failed; using naive mapping. Error:", e)
        resolved = {
            "commodity": user_crop_input.strip().title(),
            "state_name": user_state_input.strip().title(),
            "district_name": user_district_input.strip().title()
        }
    else:
        resolved = gemini_map_all_inputs(llm, {
            "commodity": user_crop_input,
            "state_name": user_state_input,
            "district_name": user_district_input
        })

    english_crop = resolved["commodity"]
    state = resolved["state_name"]
    district = resolved["district_name"]

    print(f"Resolved inputs: {resolved}")

    # 2) Find most recent available date (search back LOOKBACK_DAYS)
    recent_date, recent_records = find_most_recent_data_date(english_crop, state, district, LOOKBACK_DAYS)
    print("RECENT RECORDS\n", recent_records)
    if recent_date:
        # 3) Fetch recent points backward from the most recent date
        df_recent = fetch_recent_days_prices(english_crop, state, district, RECENT_WINDOW_DAYS, start_date=recent_date)
    else:
        df_recent = pd.DataFrame()

    # Compute recent statistics
    recent_price = None
    recent_price_date = None
    recent_average = None
    recent_trend = "stable"
    regression_debug = None
    recent_count = 0
    recent_projection = None

    if not df_recent.empty:
        recent_count = len(df_recent)
        # most recent price = price on the most recent date
        # match by date only
        if recent_date:
            mask = df_recent["arrival_date_dt"].dt.date == recent_date.date()
            recs_on_recent = df_recent[mask]
            if not recs_on_recent.empty:
                recent_price = recs_on_recent["modal_price"].mean()
                recent_price_date = recent_date.strftime("%d/%m/%Y")
        # recent average
        recent_average = df_recent["modal_price"].mean()

        # regression/trend (simple linear regression on index)
        n = len(df_recent)
        ys = list(df_recent["modal_price"].values)
        xs = list(range(n))
        # compute least-squares slope & intercept (no numpy)
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_x2 = sum(x*x for x in xs)
        sum_xy = sum(x*y for x, y in zip(xs, ys))
        denom = (n * sum_x2 - sum_x * sum_x)
        if denom != 0:
            slope = (n * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n
            # interpret slope
            if slope > 0.01:
                recent_trend = "upward"
            elif slope < -0.01:
                recent_trend = "downward"
            else:
                recent_trend = "stable"
            # projection
            recent_projection = None
            last_index = n - 1
            last_value = ys[-1]
            proj_value = last_value + slope * RECENT_PROJECTION_DAYS
            recent_projection = round(proj_value, 2)
            regression_debug = {"slope_per_day": slope, "intercept": intercept, "n_points": n}
        else:
            regression_debug = {"reason": "not enough variance in x"}
            recent_trend = "stable"

    # 4) Seasonal prediction (based on TODAY's day-of-year)
    seasonal_pred, seasonal_explanation = predict_from_history(english_crop)

    # 5) Blend recent and seasonal (weighted toward recent if enough recent points)
    final_prediction = None
    blend_debug = {}

    # dynamic weight: more recent points => more weight to recent
    if recent_average is not None and seasonal_pred is not None:
        if recent_count >= 10:
            w_recent = 0.75
        elif recent_count >= 5:
            w_recent = 0.65
        elif recent_count >= 3:
            w_recent = 0.55
        else:
            w_recent = 0.45
        w_seasonal = 1.0 - w_recent
        final_prediction = round(w_recent * recent_average + w_seasonal * seasonal_pred, 2)
        blend_debug = {"w_recent": w_recent, "w_seasonal": w_seasonal, "recent_count": recent_count}
    elif recent_average is not None:
        final_prediction = round(recent_average, 2)
        blend_debug = {"w_recent": 1.0, "reason": "no seasonal"}
    elif seasonal_pred is not None:
        final_prediction = round(seasonal_pred, 2)
        blend_debug = {"w_seasonal": 1.0, "reason": "no recent"}
    else:
        final_prediction = None

    # 6) PRINT debug sections (console)
    print("\nSEASONAL INFO:")
    if seasonal_pred is None:
        print("  Seasonal data unavailable:", seasonal_explanation)
    else:
        print(f"  Seasonal average: {seasonal_pred}")
        print(f"  {seasonal_explanation}")

    print("\nRECENT / REGRESSION INFO:")
    if df_recent.empty:
        print("  No recent API data found (within lookup window).")
    else:
        print(f"  Recent points collected: {recent_count}")
        if recent_price is not None:
            print(f"  Most recent available price: {recent_price} on {recent_price_date}")
        else:
            print("  Most recent available price: (parsed missing)")

        print(f"  Recent average (collected): {recent_average}")
        print(f"  Recent trend: {recent_trend}")
        if regression_debug:
            print(f"  Regression debug: {regression_debug}")
        if recent_projection is not None:
            print(f"  Recent projection ({RECENT_PROJECTION_DAYS}d ahead): {recent_projection}")

    print("\nFINAL SUMMARY:")
    print(f"  Commodity: {english_crop}")
    print(f"  Most recent price (if any): {recent_price} on {recent_price_date}")
    print(f"  Recent average over collected days: {recent_average}")
    print(f"  Recent trend: {recent_trend}")
    print(f"  Recent projection ({RECENT_PROJECTION_DAYS}d ahead): {recent_projection}")
    print(f"  Seasonal average: {seasonal_pred}")
    print(f"  Final blended prediction: {final_prediction}")
    print(f"  Blend debug: {blend_debug}")

    # 7) Final JSON
    if recent_price is not None or recent_average is not None:
        status = "recent_available"
    elif seasonal_pred is not None:
        status = "seasonal_only"
    else:
        status = "no_data"

    out = {
        "status": status,
        "commodity_requested": english_crop,
        "district": district,
        "state": state,
        "recent_price": recent_price,
        "recent_price_date": recent_price_date,
        "recent_average": recent_average,
        "recent_trend": recent_trend,
        "recent_projection_days": RECENT_PROJECTION_DAYS,
        "recent_projection": recent_projection,
        "seasonal_average": seasonal_pred,
        "seasonal_explanation": seasonal_explanation,
        "final_prediction": final_prediction,
        "blend_debug": blend_debug,
        "regression_debug": regression_debug
    }
    print(out)

    prompt = f"""
You are advising a farmer about selling his crop. Use the following data:

{out}

Explain the situation in simple language so a farmer with little education can understand. Include key prices: recent price, usual seasonal average, and predicted price for the next few days. Then give a clear suggestion: should the farmer hold or sell in the next 7 days. Avoid jargon, formulas, or technical details. Keep it short and practical.

Example outputs:

1. Upward trend:
"Hello! Today, tomato price in Bangalore is 2500 Rs/Quintal. Usually, at this season, the price is around 2290 Rs/Quintal. For the next week, the price may go up to around 2620 Rs/Quintal. It looks like the price will rise, so you should hold your tomatoes a few days before selling."

2. Downward trend:
"Hello! Today, onion price in Pune is 1800 Rs/Quintal. Usually, at this season, the price is around 2000 Rs/Quintal. For the next week, the price may drop to about 1700 Rs/Quintal. Since prices are falling, it's better to sell your onions soon."

3. Stable prices:
"Hello! Today, wheat price in Ludhiana is 2100 Rs/Quintal. Usually, at this season, the price is about 2120 Rs/Quintal. For the next week, prices are expected to stay around 2110 Rs/Quintal. Prices look steady, so you can sell now or wait a little, it won't make much difference."
"""
    resp = llm.generate_content(contents=prompt)

    return resp.text.strip()

def price_predict_tool(query: str):
    try:
        llm = init_gemini()
    except Exception as e:
        print("Gemini init failed; using naive mapping. Error:", e)
    EXTRACTION_PROMPT = f"""
You are an information extraction assistant.
Given a user request about agricultural markets, extract the following fields:

- "district": the district name (string)
- "state": the state name (string)
- "crop": the crop/commodity name (string)

Always respond in *valid JSON* with exactly these three keys.
Do not include explanations, only JSON.

Examples:

Input: "What's the price of tamatar in Bangalore, Karnataka?"
Output: {{"district": "Bangalore", "state": "Karnataka", "crop": "tamatar"}}

Input: "Need latest Bhindi price from Pune Maharashtra"
Output: {{"district": "Pune", "state": "Maharashtra", "crop": "Bhindi"}}

Input: "How much for onions in Jaipur, Rajasthan?"
Output: {{"district": "Jaipur", "state": "Rajasthan", "crop": "onions"}}

Now extract from this input and output ONLY JSON:
{query}
"""
    obj = llm.generate_content(contents = EXTRACTION_PROMPT).text.strip()
    try:
        mapping = json.loads(obj)
    except json.JSONDecodeError:
        # Try to recover just the JSON substring
        match = re.search(r"\{.*\}", obj, re.DOTALL)
        if match:
            mapping = json.loads(match.group(0))
        else:
            raise  # re-raise if no JSON found
    state = mapping.get("state")
    district = mapping.get("district")
    crop = mapping.get("crop")
    return get_market_info_for_crop(crop, state, district)

def current_price_tool(query: str):
    try:
        llm = init_gemini()
    except Exception as e:
        print("Gemini init failed; using naive mapping. Error:", e)
        return "Sorry, I am unable to connect to my AI model to process this request at the moment."

    EXTRACTION_PROMPT = f"""
You are an information extraction assistant.
Given a user request about agricultural markets, extract the following fields:

- "district_name": the district name (string)
- "state_name": the state name (string)
- "commodity": the crop/commodity name (string)

Always respond in *valid JSON* with exactly these three keys.
Do not include explanations, only JSON.

Examples:

Input: "What's the price of tamatar in Bangalore, Karnataka?"
Output: {{"district_name": "Bangalore", "state_name": "Karnataka", "commodity": "tamatar"}}

Input: "Need latest Bhindi price from Pune Maharashtra"
Output: {{"district_name": "Pune", "state_name": "Maharashtra", "commodity": "Bhindi"}}

Input: "How much for onions in Jaipur, Rajasthan?"
Output: {{"district_name": "Jaipur", "state_name": "Rajasthan", "commodity": "onions"}}

Now extract from this input and output ONLY JSON:
{query}
"""
    try:
        obj = llm.generate_content(contents = EXTRACTION_PROMPT).text.strip()
        mapping = json.loads(obj)
    except json.JSONDecodeError:
        try:
            match = re.search(r"\{.*\}", obj, re.DOTALL)
            if match:
                mapping = json.loads(match.group(0))
            else:
                return "I couldn't understand the crop, state, or district from your request. Please be more specific."
        except (json.JSONDecodeError, AttributeError):
            return "I couldn't parse the necessary information from your request. Please check the format."
    except Exception as e:
        print(f"Error during LLM invocation or parsing: {e}")
        return "An unexpected error occurred while processing your request."
    
    mapping = gemini_map_all_inputs(llm, mapping)
    state = mapping.get("state_name")
    district = mapping.get("district_name")
    crop = mapping.get("commodity")
    print(mapping)
    recent_date, recent_records = find_most_recent_data_date(crop, state, district, LOOKBACK_DAYS)
    print("RECENT RECORDS\n", recent_date, "\n" ,recent_records)
    if not recent_records:
        return (
            f"I couldn't find recent market price data for {crop} in {district}, {state} in the last {LOOKBACK_DAYS} days. "
            "Please try another district/nearby market or a different crop."
        )
    total = 0
    c = 0
    for r in recent_records:
        try:
            total += float(r.get("Modal_Price") or r.get("modal_price") or 0)
            c += 1
        except Exception:
            continue
    mean_price = total / c if c > 0 else 0
    FINAL_PROMPT = f"""
    You are an agricultural assistant. 
    Given the following data, generate a clear and farmer-friendly answer in 2-4 sentences.

    Crop: {crop}
    District: {district}
    State: {state}
    Date: {recent_date.strftime('%d %b %Y')}

    Market Prices:
    {recent_records}

    Mean Modal Price across markets: {mean_price:.2f} Rs/Quintal

    Answer requirements:
    - Speak in plain, supportive language.
    - Mention the crop, district, and state.
    - List the date and modal market prices in all the markets.
    - Mention the average price as a useful reference.
    - Do not just repeat the table, but explain it in sentences, crisply.
    - Note that the date might not be today's, and data of a few days ago might be used.
        """
        
    try:
        return llm.generate_content(contents=FINAL_PROMPT).text.strip()
    except Exception as e:
        print(f"Error generating final response: {e}")
        return "An error occurred while generating the final response. Please try again."
    

if __name__ == "__main__":
    print("=== Market Price Agent (single-file) ===")
    print(current_price_tool("I am from Bangalore, Karnataka. what is the price of tamatar currently?"))
