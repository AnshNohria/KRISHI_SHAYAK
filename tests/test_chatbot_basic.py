import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
chatbot_path = ROOT / 'chatbot.py'
spec = importlib.util.spec_from_file_location('chatbot_module', chatbot_path)
chatbot_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chatbot_mod)  # type: ignore
KrishiChatbot = chatbot_mod.KrishiChatbot

def test_non_agri_query_guard():
    bot = KrishiChatbot()
    resp = bot.get_response("Tell me a joke")
    assert "not related to farming" in resp.lower()

def test_weather_parsing_no_state():
    import os, pathlib
    prof = pathlib.Path(__file__).resolve().parent.parent / 'user_profile.json'
    if prof.exists():
        prof.unlink()
    bot = KrishiChatbot()
    resp = bot.get_response("weather now")
    assert "don't have enough verified data" in resp.lower()

def test_handler_precedence_shop_over_fpo(monkeypatch):
    bot = KrishiChatbot()
    async def fake_geocode(village, state):
        return {'lat': 30.0, 'lon': 75.0}
    import weather.service as ws
    monkeypatch.setattr(ws, 'geocode_openweather', fake_geocode)
    async def fake_search(keyword, lat, lon, key, radius_m=20000, max_results=5, fallback_radius_m=50000):
        return [{'name': 'Test Fertilizer Store', 'address': 'Main Bazaar', 'distance_km': 2.3, 'rating': 4.5, 'maps_url': 'http://maps.test'}]
    import maps.service as ms
    monkeypatch.setattr(ms, 'search_agri_shops', fake_search)
    monkeypatch.setenv('GEOAPIFY_API_KEY', 'dummy')
    resp = bot.get_response("nearest fertilizer shop in Moga, Punjab also fpo")
    assert ("fertilizer" in resp.lower())

def test_fpo_lookup_requires_location():
    # Ensure no saved profile interferes
    import os, pathlib
    prof = pathlib.Path(__file__).resolve().parent.parent / 'user_profile.json'
    if prof.exists():
        prof.unlink()
    bot = KrishiChatbot()
    resp = bot.get_response("nearest fpo for seeds")
    assert "don't have enough verified data" in resp.lower()

def test_geoapify_missing_key_fallback(monkeypatch):
    # Ensure key absence
    monkeypatch.delenv('GEOAPIFY_API_KEY', raising=False)
    monkeypatch.delenv('GEOAPIFY_MAPS_API', raising=False)
    bot = KrishiChatbot()
    async def fake_geocode(village, state):
        return {'lat': 30.0, 'lon': 75.0}
    import weather.service as ws
    monkeypatch.setattr(ws, 'geocode_openweather', fake_geocode)
    async def fake_visual(village, state):
        return {'lat': 30.0, 'lon': 75.0}
    monkeypatch.setattr(ws, 'geocode_visual_crossing', fake_visual)
    resp = bot.get_response("nearest fertilizer shop in Moga, Punjab")
    assert "don't have enough verified data" in resp.lower()

def test_natural_language_queries_list(monkeypatch):
    queries = [
        "nearest fertilizer shop in Moga, Punjab",
        "nearest seed shop in Moga, Punjab",
        "nearest fpo for seeds in Moga, Punjab",
        "weather in Moga, Punjab",
        "fertilizer advice",
        "pest management",
    ]
    bot = KrishiChatbot()
    # Provide deterministic geocode
    async def fake_geocode(village, state):
        return {'lat': 30.0, 'lon': 75.0}
    import weather.service as ws
    monkeypatch.setattr(ws, 'geocode_openweather', fake_geocode)
    async def fake_visual(village, state):
        return {'lat': 30.0, 'lon': 75.0}
    monkeypatch.setattr(ws, 'geocode_visual_crossing', fake_visual)
    # Monkeypatch shop search to avoid network when key present
    async def fake_search(keyword, lat, lon, key, radius_m=20000, max_results=5, fallback_radius_m=50000):
        return [{'name': 'Demo Shop', 'address': 'Bazaar', 'distance_km': 1.2, 'rating': None, 'maps_url': 'http://osm'}]
    import maps.service as ms
    monkeypatch.setattr(ms, 'search_agri_shops', fake_search)
    monkeypatch.setenv('GEOAPIFY_API_KEY', 'dummy')
    outputs = [bot.get_response(q) for q in queries]
    # Basic sanity expectations
    assert any('fertilizer' in o.lower() for o in outputs)
    assert any('fpo' in o.lower() for o in outputs)
    assert any('weather' in o or '🌤️' in o for o in outputs)
