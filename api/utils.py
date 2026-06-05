import requests
from decimal import Decimal
import time

def get_location_details(location_query):
    """
    Get location details from OpenStreetMap Nominatim API in English
    """
    if not location_query:
        return None
        
    try:
        # print(f"Geocoding location: {location_query}")  # Comment out
        
        # For plus codes, try a different approach
        if '+' in location_query and len(location_query.split('+')[0]) >= 4:
            # print("Plus code detected, processing...")  # Comment out
            parts = location_query.split(',')
            if len(parts) >= 2:
                location_query = ','.join(parts[1:]).strip()
                # print(f"Converted to area name: {location_query}")  # Comment out
        
        params = {
            'q': location_query,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
            'accept-language': 'en'
        }
        
        headers = {
            'User-Agent': 'NFCApp/1.0 (contact@nfc.com)'
        }
        
        time.sleep(1)
        
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params=params,
            headers=headers,
            timeout=10
        )
        
        # print(f"Response status: {response.status_code}")  # Comment out
        
        if response.status_code == 200:
            data = response.json()
            # print(f"Response data: {data}")  # Comment out - this causes the error
            
            if data and len(data) > 0:
                location = data[0]
                address = location.get('address', {})
                
                # print(f"Full address object: {address}")  # Comment out
                
                city = (
                    address.get('city') or 
                    address.get('town') or 
                    address.get('village') or
                    address.get('municipality') or
                    address.get('suburb') or
                    ''
                )
                
                district = (
                    address.get('county') or
                    address.get('district') or
                    address.get('municipality') or
                    address.get('city_district') or
                    ''
                )
                
                province = (
                    address.get('state') or
                    address.get('province') or
                    address.get('region') or
                    ''
                )
                
                province = province.replace("Bagamati", "Bagmati")
                
                postal_code = address.get('postcode', '')
                
                result = {
                    'latitude': Decimal(str(location.get('lat', 0))),
                    'longitude': Decimal(str(location.get('lon', 0))),
                    'city': city,
                    'district': district,
                    'province': province,
                    'postal_code': postal_code,
                    'display_name': location.get('display_name', '')
                }
                
                # print(f"Geocoding successful (English): {result}")  # Comment out
                return result
            else:
                print("No results found")
        else:
            print(f"API request failed: {response.status_code}")
        
        return None
        
    except Exception as e:
        print(f"Geocoding error: {e}")
        import traceback
        traceback.print_exc()
        return None