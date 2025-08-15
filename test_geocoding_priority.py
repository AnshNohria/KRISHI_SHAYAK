#!/usr/bin/env python3
"""
Test the new LocationIQ primary + Geoapify fallback geocoding for FPO service
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append('.')

from fpo.service import FPOService

async def test_geocoding_priority():
    """Test LocationIQ primary and Geoapify fallback"""
    print("🌾 TESTING GEOCODING PRIORITY FOR FPO SERVICE")
    print("=" * 60)
    
    # Initialize FPO service
    fpo_service = FPOService()
    
    # Test locations
    test_locations = [
        "Patna, Bihar",
        "Mumbai, Maharashtra", 
        "Delhi, Delhi",
        "Araria, Bihar",
        "Banka, Bihar"
    ]
    
    print("📍 Testing geocoding priority (LocationIQ → Geoapify):")
    print("=" * 60)
    
    for location in test_locations:
        print(f"\n🔍 Testing: {location}")
        try:
            coords = await fpo_service.geocode_location_async(location)
            if coords:
                print(f"✅ Success: {coords[0]:.6f}, {coords[1]:.6f}")
            else:
                print(f"❌ Failed to geocode: {location}")
        except Exception as e:
            print(f"💥 Error geocoding {location}: {e}")
    
    # Test FPO search with new geocoding
    print("\n🏢 TESTING FPO SEARCH WITH NEW GEOCODING")
    print("=" * 60)
    
    try:
        print("🔍 Searching for nearest FPOs to Patna, Bihar...")
        nearest_fpos = await fpo_service.find_nearest_fpos_with_geocoding(
            location_name="Patna", 
            state="Bihar", 
            limit=3
        )
        
        if nearest_fpos:
            print(f"✅ Found {len(nearest_fpos)} nearest FPOs:")
            for i, (fpo, distance) in enumerate(nearest_fpos, 1):
                print(f"{i}. {fpo.name}")
                print(f"   📍 District: {fpo.district}, State: {fpo.state}")
                print(f"   📏 Distance: {distance:.2f} km")
                print()
        else:
            print("❌ No FPOs found")
            
    except Exception as e:
        print(f"💥 Error in FPO search: {e}")
    
    print("=" * 60)
    print("✅ Geocoding priority test completed!")

if __name__ == "__main__":
    asyncio.run(test_geocoding_priority())
