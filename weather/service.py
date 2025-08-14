"""
Krishi Dhan Sahayak - Complete Weather Service
All-in-one weather service with dual API support for Indian farmers
"""

import httpx
import os
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# API Configuration
OPENWEATHER_GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"
OPENWEATHER_WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
VISUAL_CROSSING_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
VISUAL_CROSSING_API_KEY = os.getenv("VISUAL_CROSSING_API_KEY")

class WeatherServiceError(Exception):
    """Custom exception for weather service errors."""
    pass

class WeatherData:
    """Simple weather data container."""
    def __init__(self, location_name: str, lat: float, lon: float, 
                 temperature: float, feels_like: float = None, 
                 description: str = "", humidity: int = None,
                 pressure: int = None, visibility: float = None,
                 wind_speed: float = 0, wind_direction: int = 0,
                 precipitation_prob: float = None, precipitation_amount: float = None,
                 uv_index: int = None, cloud_cover: int = None,
                 data_sources: List[str] = None):
        self.location_name = location_name
        self.lat = lat
        self.lon = lon
        self.temperature = temperature
        self.feels_like = feels_like
        self.description = description
        self.humidity = humidity
        self.pressure = pressure
        self.visibility = visibility
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
        self.precipitation_prob = precipitation_prob
        self.precipitation_amount = precipitation_amount
        self.uv_index = uv_index
        self.cloud_cover = cloud_cover
        self.data_sources = data_sources or []

async def geocode_openweather(village: str, state: str) -> Optional[Dict[str, Any]]:
    """Geocode using OpenWeatherMap."""
    if not OPENWEATHER_API_KEY:
        return None
    
    query = f"{village},{state},IN"
    params = {"q": query, "limit": 1, "appid": OPENWEATHER_API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(OPENWEATHER_GEOCODE_URL, params=params)
            r.raise_for_status()
            data = r.json()
            
        if data:
            result = data[0]
            return {
                "name": result.get("name", village),
                "lat": result.get("lat"),
                "lon": result.get("lon"),
                "state": result.get("state", state)
            }
    except Exception as e:
        logger.warning(f"OpenWeatherMap geocoding failed: {e}")
    
    return None

async def geocode_visual_crossing(village: str, state: str) -> Optional[Dict[str, Any]]:
    """Fallback geocode using Visual Crossing timeline endpoint (approx)."""
    if not VISUAL_CROSSING_API_KEY:
        return None
    # Visual Crossing accepts location string; we'll parse back lat/lon
    location_str = f"{village},{state},India"
    params = {
        "key": VISUAL_CROSSING_API_KEY,
        "contentType": "json",
        "include": "days",
        "elements": "temp"
    }
    try:
        url = f"{VISUAL_CROSSING_URL}/{location_str}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        loc = data.get('latitude'), data.get('longitude')
        if loc[0] is not None and loc[1] is not None:
            return {"name": village.title(), "lat": loc[0], "lon": loc[1], "state": state.title()}
    except Exception as e:
        logger.warning(f"Visual Crossing geocoding fallback failed: {e}")
    return None

async def get_openweather_data(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Get weather data from OpenWeatherMap."""
    if not OPENWEATHER_API_KEY:
        return None
    
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "appid": OPENWEATHER_API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(OPENWEATHER_WEATHER_URL, params=params)
            r.raise_for_status()
            data = r.json()
        
        main = data.get("main", {})
        wind = data.get("wind", {})
        weather = data.get("weather", [{}])[0]
        
        return {
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "description": weather.get("description", ""),
            "wind_speed": wind.get("speed", 0),
            "wind_direction": wind.get("deg", 0),
            "visibility": data.get("visibility", 0) / 1000 if data.get("visibility") else None,
            "cloud_cover": data.get("clouds", {}).get("all"),
            "precipitation_amount": data.get("rain", {}).get("1h", 0) + data.get("snow", {}).get("1h", 0)
        }
    except Exception as e:
        logger.warning(f"OpenWeatherMap weather failed: {e}")
    
    return None

async def get_visual_crossing_data(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Get weather data from Visual Crossing."""
    if not VISUAL_CROSSING_API_KEY:
        return None
    
    location_str = f"{lat},{lon}"
    params = {
        "key": VISUAL_CROSSING_API_KEY,
        "contentType": "json",
        "include": "current",
        "elements": "temp,feelslike,humidity,precip,precipprob,windspeed,winddir,visibility,uvindex,cloudcover,conditions"
    }
    
    try:
        url = f"{VISUAL_CROSSING_URL}/{location_str}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        
        current = data.get("currentConditions", {})
        
        return {
            "temperature": current.get("temp"),
            "feels_like": current.get("feelslike"),
            "humidity": current.get("humidity"),
            "description": current.get("conditions", ""),
            "wind_speed": current.get("windspeed", 0) * 0.277778,  # km/h to m/s
            "wind_direction": current.get("winddir", 0),
            "visibility": current.get("visibility"),
            "uv_index": current.get("uvindex"),
            "cloud_cover": current.get("cloudcover"),
            "precipitation_prob": current.get("precipprob"),
            "precipitation_amount": current.get("precip", 0)
        }
    except Exception as e:
        logger.warning(f"Visual Crossing weather failed: {e}")
    
    return None

def average_values(val1: Optional[float], val2: Optional[float]) -> Optional[float]:
    """Average two values, handling None."""
    if val1 is None and val2 is None:
        return None
    if val1 is None:
        return val2
    if val2 is None:
        return val1
    return (val1 + val2) / 2

async def get_weather(village: str, state: str) -> WeatherData:
    """Get comprehensive weather data using dual APIs."""
    # Try geocoding
    location = await geocode_openweather(village, state)
    if not location:
        location = await geocode_visual_crossing(village, state)
    if not location:
        raise WeatherServiceError(f"Could not find location: {village}, {state}")
    
    lat, lon = location["lat"], location["lon"]
    location_name = f"{location['name']}, {location['state']}"
    
    # Get data from both APIs
    openweather_data = await get_openweather_data(lat, lon)
    visual_crossing_data = await get_visual_crossing_data(lat, lon)
    
    if not openweather_data and not visual_crossing_data:
        raise WeatherServiceError("No weather data available from any source")
    
    # Merge data
    sources = []
    if openweather_data:
        sources.append("OpenWeatherMap")
    if visual_crossing_data:
        sources.append("Visual Crossing")
    
    # Use data from available sources
    ow_data = openweather_data or {}
    vc_data = visual_crossing_data or {}
    
    return WeatherData(
        location_name=location_name,
        lat=lat,
        lon=lon,
        temperature=average_values(ow_data.get("temperature"), vc_data.get("temperature")),
        feels_like=average_values(ow_data.get("feels_like"), vc_data.get("feels_like")),
        description=ow_data.get("description") or vc_data.get("description") or "",
        humidity=average_values(ow_data.get("humidity"), vc_data.get("humidity")),
        pressure=ow_data.get("pressure"),  # Only available in OpenWeatherMap
        visibility=average_values(ow_data.get("visibility"), vc_data.get("visibility")),
        wind_speed=average_values(ow_data.get("wind_speed"), vc_data.get("wind_speed")),
        wind_direction=average_values(ow_data.get("wind_direction"), vc_data.get("wind_direction")),
        precipitation_prob=vc_data.get("precipitation_prob"),  # Only in Visual Crossing
        precipitation_amount=average_values(ow_data.get("precipitation_amount"), vc_data.get("precipitation_amount")),
        uv_index=vc_data.get("uv_index"),  # Only in Visual Crossing
        cloud_cover=average_values(ow_data.get("cloud_cover"), vc_data.get("cloud_cover")),
        data_sources=sources
    )

def generate_agricultural_advice(weather: WeatherData) -> List[str]:
    """Generate agricultural advice based on weather conditions."""
    advice = []
    
    # Temperature advice
    if weather.temperature:
        if weather.temperature < 10:
            advice.append("❄️ Cold conditions - protect sensitive crops from frost")
        elif weather.temperature > 35:
            advice.append("🌡️ Hot conditions - ensure adequate irrigation and shade")
        else:
            advice.append(f"🌡️ Temperature {weather.temperature:.1f}°C - suitable for most crops")
    
    # Humidity advice
    if weather.humidity:
        if weather.humidity > 80:
            advice.append("💧 High humidity - monitor for fungal diseases")
        elif weather.humidity < 40:
            advice.append("🌵 Low humidity - increase irrigation frequency")
        else:
            advice.append(f"💧 Humidity {weather.humidity:.0f}% - good for crop growth")
    
    # Rain advice
    if weather.precipitation_prob and weather.precipitation_prob > 60:
        advice.append(f"🌧️ High rain chance ({weather.precipitation_prob:.0f}%) - delay spraying")
    elif weather.precipitation_prob and weather.precipitation_prob < 20:
        advice.append("☀️ Low rain chance - good for field operations")
    
    # Wind advice
    if weather.wind_speed and weather.wind_speed > 15:
        advice.append("💨 Strong winds - avoid pesticide spraying")
    elif weather.wind_speed and weather.wind_speed > 8:
        advice.append("🍃 Moderate winds - use drift-reducing nozzles")
    
    # UV advice
    if weather.uv_index and weather.uv_index > 8:
        advice.append("☀️ High UV - protect workers and livestock")
    elif weather.uv_index and weather.uv_index > 5:
        advice.append("🌞 Moderate UV - good for photosynthesis")
    
    # Pressure advice
    if weather.pressure:
        if weather.pressure < 1000:
            advice.append("⬇️ Low pressure - weather changes expected")
        elif weather.pressure > 1020:
            advice.append("⬆️ High pressure - stable weather expected")
    
    # Data sources
    if weather.data_sources:
        sources_str = ", ".join(weather.data_sources)
        advice.append(f"📊 Data from: {sources_str}")
    
    return advice if advice else ["Weather data available for agricultural planning"]

def check_api_configuration() -> bool:
    """Check if at least one API is configured."""
    if not OPENWEATHER_API_KEY and not VISUAL_CROSSING_API_KEY:
        print("❌ No API keys configured!")
        print("Please add API keys to .env file:")
        print("- OPENWEATHER_API_KEY (free from openweathermap.org)")
        print("- VISUAL_CROSSING_API_KEY (free from visualcrossing.com)")
        return False
    
    apis = []
    if OPENWEATHER_API_KEY:
        apis.append("OpenWeatherMap")
    if VISUAL_CROSSING_API_KEY:
        apis.append("Visual Crossing")
    
    print(f"✅ API keys configured for: {', '.join(apis)}")
    return True
