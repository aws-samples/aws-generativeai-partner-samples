#!/usr/bin/env python3
"""
Script to generate synthetic data for the Travel Advisory Application
and load it into Elasticsearch.
"""

import json
import random
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import faker
import argparse
from elasticsearch_schemas import schemas
from dotenv import load_dotenv
import os
from real_world_data import (
    REAL_DESTINATIONS, 
    DESTINATION_ATTRACTIONS, 
    DESTINATION_EVENTS, 
    DESTINATION_HOTELS,
    COUNTRY_ADVISORIES,
    DESTINATION_WEATHER
)

# Initialize Faker
fake = faker.Faker()

# Configuration
DEFAULT_NUM_DESTINATIONS = 20  # Reduced to match real-world data
DEFAULT_NUM_ATTRACTIONS_PER_DEST = 5
DEFAULT_NUM_HOTELS_PER_DEST = 5
DEFAULT_NUM_ADVISORIES_PER_DEST = 1
DEFAULT_NUM_WEATHER_RECORDS_PER_DEST = 30
DEFAULT_NUM_EVENTS_PER_DEST = 3

# Constants for data generation
CONTINENTS = ["Asia", "Europe", "North America", "South America", "Africa", "Oceania"]
CLIMATES = ["Tropical", "Dry", "Temperate", "Continental", "Polar", "Mediterranean"]
LANGUAGES = ["English", "Spanish", "French", "German", "Chinese", "Japanese", "Arabic", "Russian", "Portuguese", "Italian"]
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "SGD"]
COST_LEVELS = ["Budget", "Moderate", "Luxury"]
TAGS = ["Beach", "Mountain", "Cultural", "Historical", "Adventure", "Relaxation", "Urban", "Rural", "Island", "Desert", "Tropical", "Winter", "Family-friendly", "Romantic", "Nightlife"]
ATTRACTION_TYPES = ["Museum", "Park", "Monument", "Beach", "Mountain", "Temple", "Castle", "Zoo", "Aquarium", "Theme Park", "Historical Site", "Natural Wonder", "Market", "Theater", "Stadium"]
PRICE_RANGES = ["Free", "$", "$$", "$$$", "$$$$"]
CROWD_LEVELS = ["Low", "Moderate", "High"]
HOTEL_BRANDS = ["Marriott", "Hilton", "Hyatt", "InterContinental", "Accor", "Best Western", "Wyndham", "Choice Hotels", "Radisson", "Four Seasons", "Local Boutique"]
HOTEL_AMENITIES = ["Pool", "Spa", "Gym", "Restaurant", "Bar", "Room Service", "Concierge", "Business Center", "Airport Shuttle", "Laundry Service", "Free Breakfast", "Pet Friendly"]
ROOM_TYPES = ["Single", "Double", "Twin", "Suite", "Deluxe", "Executive", "Family", "Penthouse", "Villa", "Bungalow"]
ADVISORY_LEVELS = ["Low", "Medium", "High", "Extreme"]
ISSUING_AUTHORITIES = ["State Department", "Foreign Office", "Ministry of Foreign Affairs", "Department of Foreign Affairs", "Travel Security Agency"]
VACCINATIONS = ["None", "Yellow Fever", "Hepatitis A", "Hepatitis B", "Typhoid", "Malaria Prophylaxis", "COVID-19"]
WEATHER_CONDITIONS = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorm", "Snowy", "Foggy", "Windy", "Hail", "Clear"]
EVENT_TYPES = ["Festival", "Concert", "Sports", "Exhibition", "Conference", "Fair", "Parade", "Cultural Celebration", "Food Event", "Art Show"]
SIGNIFICANCE_LEVELS = ["Low", "Medium", "High"]

def generate_destinations(num_destinations):
    """Generate destination data based on real-world locations."""
    destinations = []
    
    # Use real-world destination data
    for i, real_dest in enumerate(REAL_DESTINATIONS[:num_destinations]):
        destination_id = f"DEST{i+1:04d}"
        
        destinations.append({
            "destination_id": destination_id,
            "name": f"{real_dest['city']}, {real_dest['country']}",
            "city": real_dest['city'],
            "country": real_dest['country'],
            "continent": real_dest['continent'],
            "latitude": real_dest['latitude'],
            "longitude": real_dest['longitude'],
            "description": real_dest['description'],
            "best_season": real_dest['best_season'],
            "climate": real_dest['climate'],
            "language": real_dest['language'],
            "currency": real_dest['currency'],
            "timezone": real_dest['timezone'],
            "safety_rating": real_dest['safety_rating'],
            "popularity_score": real_dest['popularity_score'],
            "cost_level": real_dest['cost_level'],
            "tags": real_dest['tags']
        })
    
    # If we need more destinations than we have real data for, generate some synthetic ones
    if num_destinations > len(REAL_DESTINATIONS):
        for i in range(len(REAL_DESTINATIONS), num_destinations):
            destination_id = f"DEST{i+1:04d}"
            city = fake.city()
            country = fake.country()
            
            destinations.append({
                "destination_id": destination_id,
                "name": f"{city}, {country}",
                "city": city,
                "country": country,
                "continent": random.choice(CONTINENTS),
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude()),
                "description": fake.paragraph(nb_sentences=5),
                "best_season": random.choice(["Spring", "Summer", "Fall", "Winter", "Year-round"]),
                "climate": random.choice(CLIMATES),
                "language": random.choice(LANGUAGES),
                "currency": random.choice(CURRENCIES),
                "timezone": fake.timezone(),
                "safety_rating": random.randint(1, 10),
                "popularity_score": random.randint(1, 100),
                "cost_level": random.choice(COST_LEVELS),
                "tags": random.sample(TAGS, random.randint(1, 5))
            })
    
    return destinations

def generate_attractions(destinations, num_per_destination):
    """Generate attraction data based on real-world attractions."""
    attractions = []
    
    for destination in destinations:
        dest_id = destination["destination_id"]
        city = destination["city"]
        base_lat = destination["latitude"]
        base_lon = destination["longitude"]
        
        # Check if we have predefined attractions for this city
        if city in DESTINATION_ATTRACTIONS:
            real_attractions = DESTINATION_ATTRACTIONS[city]
            
            # Use predefined attractions first
            for i, attr in enumerate(real_attractions[:num_per_destination]):
                attraction_id = f"{dest_id}_ATTR{i+1:03d}"
                
                # Slightly adjust lat/lon to be near the destination
                lat_offset = random.uniform(-0.01, 0.01)
                lon_offset = random.uniform(-0.01, 0.01)
                
                attractions.append({
                    "attraction_id": attraction_id,
                    "destination_id": dest_id,
                    "name": attr["name"],
                    "type": attr["type"],
                    "description": attr["description"],
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lon + lon_offset,
                    "address": fake.address().replace('\n', ', '),
                    "opening_hours": f"{random.randint(7, 11)}:00",
                    "closing_hours": f"{random.randint(16, 22)}:00",
                    "price_range": attr["price_range"],
                    "duration_minutes": attr["duration_minutes"],
                    "accessibility": random.choice([True, False]),
                    "rating": round(random.uniform(3.5, 5.0), 1),  # Higher ratings for famous attractions
                    "tags": attr["tags"],
                    "best_time_to_visit": random.choice(["Morning", "Afternoon", "Evening", "Any time"]),
                    "crowd_level": random.choice(CROWD_LEVELS)
                })
            
            # If we need more attractions than we have real data for
            if num_per_destination > len(real_attractions):
                for i in range(len(real_attractions), num_per_destination):
                    attraction_id = f"{dest_id}_ATTR{i+1:03d}"
                    
                    # Slightly adjust lat/lon to be near the destination
                    lat_offset = random.uniform(-0.05, 0.05)
                    lon_offset = random.uniform(-0.05, 0.05)
                    
                    attractions.append({
                        "attraction_id": attraction_id,
                        "destination_id": dest_id,
                        "name": fake.company() + " " + random.choice(["Museum", "Park", "Monument", "Castle", "Garden", "Tower", "Cathedral"]),
                        "type": random.choice(ATTRACTION_TYPES),
                        "description": fake.paragraph(nb_sentences=3),
                        "latitude": base_lat + lat_offset,
                        "longitude": base_lon + lon_offset,
                        "address": fake.address().replace('\n', ', '),
                        "opening_hours": f"{random.randint(7, 11)}:00",
                        "closing_hours": f"{random.randint(16, 22)}:00",
                        "price_range": random.choice(PRICE_RANGES),
                        "duration_minutes": random.choice([30, 60, 90, 120, 180, 240]),
                        "accessibility": random.choice([True, False]),
                        "rating": round(random.uniform(2.0, 5.0), 1),
                        "tags": random.sample(TAGS, random.randint(1, 3)),
                        "best_time_to_visit": random.choice(["Morning", "Afternoon", "Evening", "Any time"]),
                        "crowd_level": random.choice(CROWD_LEVELS)
                    })
        else:
            # Generate synthetic attractions for destinations without predefined data
            for i in range(1, num_per_destination + 1):
                attraction_id = f"{dest_id}_ATTR{i:03d}"
                
                # Slightly adjust lat/lon to be near the destination
                lat_offset = random.uniform(-0.05, 0.05)
                lon_offset = random.uniform(-0.05, 0.05)
                
                attractions.append({
                    "attraction_id": attraction_id,
                    "destination_id": dest_id,
                    "name": fake.company() + " " + random.choice(["Museum", "Park", "Monument", "Castle", "Garden", "Tower", "Cathedral"]),
                    "type": random.choice(ATTRACTION_TYPES),
                    "description": fake.paragraph(nb_sentences=3),
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lon + lon_offset,
                    "address": fake.address().replace('\n', ', '),
                    "opening_hours": f"{random.randint(7, 11)}:00",
                    "closing_hours": f"{random.randint(16, 22)}:00",
                    "price_range": random.choice(PRICE_RANGES),
                    "duration_minutes": random.choice([30, 60, 90, 120, 180, 240]),
                    "accessibility": random.choice([True, False]),
                    "rating": round(random.uniform(2.0, 5.0), 1),
                    "tags": random.sample(TAGS, random.randint(1, 3)),
                    "best_time_to_visit": random.choice(["Morning", "Afternoon", "Evening", "Any time"]),
                    "crowd_level": random.choice(CROWD_LEVELS)
                })
    
    return attractions

def generate_hotels(destinations, num_per_destination):
    """Generate hotel data based on real-world hotels."""
    hotels = []
    
    for destination in destinations:
        dest_id = destination["destination_id"]
        city = destination["city"]
        base_lat = destination["latitude"]
        base_lon = destination["longitude"]
        currency = destination["currency"]
        
        # Check if we have predefined hotels for this city
        if city in DESTINATION_HOTELS:
            real_hotels = DESTINATION_HOTELS[city]
            
            # Use predefined hotels first
            for i, hotel_data in enumerate(real_hotels[:num_per_destination]):
                hotel_id = f"{dest_id}_HOTEL{i+1:03d}"
                
                # Slightly adjust lat/lon to be near the destination
                lat_offset = random.uniform(-0.02, 0.02)
                lon_offset = random.uniform(-0.02, 0.02)
                
                # Calculate price based on star rating
                base_price = hotel_data["star_rating"] * 100
                price_variation = random.uniform(0.8, 1.2)
                price = round(base_price * price_variation, 2)
                
                hotels.append({
                    "hotel_id": hotel_id,
                    "destination_id": dest_id,
                    "name": hotel_data["name"],
                    "brand": hotel_data["brand"],
                    "address": fake.address().replace('\n', ', '),
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lon + lon_offset,
                    "star_rating": hotel_data["star_rating"],
                    "user_rating": round(random.uniform(3.5, 5.0), 1),  # Higher ratings for famous hotels
                    "price_per_night": price,
                    "currency": currency,
                    "amenities": hotel_data["amenities"],
                    "room_types": random.sample(ROOM_TYPES, random.randint(3, 6)),
                    "breakfast_included": random.choice([True, False]),
                    "free_wifi": True,  # Most luxury hotels have free WiFi
                    "parking_available": random.choice([True, False]),
                    "distance_to_center_km": round(random.uniform(0.1, 3.0), 1),  # Closer to center
                    "pet_friendly": random.choice([True, False]),
                    "check_in_time": f"{random.randint(12, 16)}:00",
                    "check_out_time": f"{random.randint(10, 12)}:00"
                })
            
            # If we need more hotels than we have real data for
            if num_per_destination > len(real_hotels):
                for i in range(len(real_hotels), num_per_destination):
                    hotel_id = f"{dest_id}_HOTEL{i+1:03d}"
                    
                    # Slightly adjust lat/lon to be near the destination
                    lat_offset = random.uniform(-0.05, 0.05)
                    lon_offset = random.uniform(-0.05, 0.05)
                    
                    brand = random.choice(HOTEL_BRANDS)
                    name = f"{brand} {city}" if brand != "Local Boutique" else f"{fake.last_name()}'s {random.choice(['Inn', 'Hotel', 'Suites', 'Lodge'])}"
                    
                    hotels.append({
                        "hotel_id": hotel_id,
                        "destination_id": dest_id,
                        "name": name,
                        "brand": brand,
                        "address": fake.address().replace('\n', ', '),
                        "latitude": base_lat + lat_offset,
                        "longitude": base_lon + lon_offset,
                        "star_rating": random.randint(1, 5),
                        "user_rating": round(random.uniform(2.0, 5.0), 1),
                        "price_per_night": round(random.uniform(50, 1000), 2),
                        "currency": currency,
                        "amenities": random.sample(HOTEL_AMENITIES, random.randint(2, 8)),
                        "room_types": random.sample(ROOM_TYPES, random.randint(2, 6)),
                        "breakfast_included": random.choice([True, False]),
                        "free_wifi": random.choice([True, False, True]),  # More likely to have free WiFi
                        "parking_available": random.choice([True, False]),
                        "distance_to_center_km": round(random.uniform(0.1, 10.0), 1),
                        "pet_friendly": random.choice([True, False, False, False]),  # Less likely to be pet friendly
                        "check_in_time": f"{random.randint(12, 16)}:00",
                        "check_out_time": f"{random.randint(10, 12)}:00"
                    })
        else:
            # Generate synthetic hotels for destinations without predefined data
            for i in range(1, num_per_destination + 1):
                hotel_id = f"{dest_id}_HOTEL{i:03d}"
                
                # Slightly adjust lat/lon to be near the destination
                lat_offset = random.uniform(-0.05, 0.05)
                lon_offset = random.uniform(-0.05, 0.05)
                
                brand = random.choice(HOTEL_BRANDS)
                name = f"{brand} {city}" if brand != "Local Boutique" else f"{fake.last_name()}'s {random.choice(['Inn', 'Hotel', 'Suites', 'Lodge'])}"
                
                hotels.append({
                    "hotel_id": hotel_id,
                    "destination_id": dest_id,
                    "name": name,
                    "brand": brand,
                    "address": fake.address().replace('\n', ', '),
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lon + lon_offset,
                    "star_rating": random.randint(1, 5),
                    "user_rating": round(random.uniform(2.0, 5.0), 1),
                    "price_per_night": round(random.uniform(50, 1000), 2),
                    "currency": currency,
                    "amenities": random.sample(HOTEL_AMENITIES, random.randint(2, 8)),
                    "room_types": random.sample(ROOM_TYPES, random.randint(2, 6)),
                    "breakfast_included": random.choice([True, False]),
                    "free_wifi": random.choice([True, False, True]),  # More likely to have free WiFi
                    "parking_available": random.choice([True, False]),
                    "distance_to_center_km": round(random.uniform(0.1, 10.0), 1),
                    "pet_friendly": random.choice([True, False, False, False]),  # Less likely to be pet friendly
                    "check_in_time": f"{random.randint(12, 16)}:00",
                    "check_out_time": f"{random.randint(10, 12)}:00"
                })
    
    return hotels

def generate_advisories(destinations, num_per_destination):
    """Generate travel advisory data based on real-world information."""
    advisories = []
    
    for destination in destinations:
        dest_id = destination["destination_id"]
        country = destination["country"]
        
        for i in range(1, num_per_destination + 1):
            advisory_id = f"{dest_id}_ADV{i:03d}"
            
            issue_date = datetime.now() - timedelta(days=random.randint(1, 60))
            expiry_date = issue_date + timedelta(days=random.randint(30, 180))
            
            # Use real advisory data if available
            if country in COUNTRY_ADVISORIES:
                advisory_data = COUNTRY_ADVISORIES[country]
                
                advisories.append({
                    "advisory_id": advisory_id,
                    "destination_id": dest_id,
                    "country": country,
                    "advisory_level": advisory_data["advisory_level"],
                    "description": advisory_data["description"],
                    "issue_date": issue_date.strftime("%Y-%m-%d"),
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "issuing_authority": random.choice(ISSUING_AUTHORITIES),
                    "health_risks": advisory_data["health_risks"],
                    "safety_risks": advisory_data["safety_risks"],
                    "entry_requirements": advisory_data["entry_requirements"],
                    "visa_required": advisory_data["visa_required"],
                    "vaccination_required": advisory_data["vaccination_required"],
                    "currency_restrictions": fake.sentence(),
                    "local_laws": fake.paragraph(nb_sentences=1),
                    "emergency_contacts": f"Police: {fake.phone_number()}, Hospital: {fake.phone_number()}"
                })
            else:
                # Generate synthetic advisory data
                advisories.append({
                    "advisory_id": advisory_id,
                    "destination_id": dest_id,
                    "country": country,
                    "advisory_level": random.choice(ADVISORY_LEVELS),
                    "description": fake.paragraph(nb_sentences=2),
                    "issue_date": issue_date.strftime("%Y-%m-%d"),
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "issuing_authority": random.choice(ISSUING_AUTHORITIES),
                    "health_risks": fake.paragraph(nb_sentences=1),
                    "safety_risks": fake.paragraph(nb_sentences=1),
                    "entry_requirements": fake.paragraph(nb_sentences=1),
                    "visa_required": random.choice([True, False]),
                    "vaccination_required": random.sample(VACCINATIONS, random.randint(0, 3)),
                    "currency_restrictions": fake.sentence(),
                    "local_laws": fake.paragraph(nb_sentences=1),
                    "emergency_contacts": f"Police: {fake.phone_number()}, Hospital: {fake.phone_number()}"
                })
    
    return advisories

def generate_weather(destinations, num_records_per_destination):
    """Generate weather data based on realistic seasonal patterns."""
    weather_records = []
    
    for destination in destinations:
        dest_id = destination["destination_id"]
        city = destination["city"]
        climate = destination["climate"]
        
        # Generate weather for the next X days
        for i in range(num_records_per_destination):
            weather_id = f"{dest_id}_WTHR{i+1:03d}"
            forecast_date = datetime.now() + timedelta(days=i)
            date_str = forecast_date.strftime("%Y-%m-%d")
            
            # Determine season based on month and hemisphere
            month = forecast_date.month
            is_northern = destination["latitude"] > 0
            
            if is_northern:
                if 3 <= month <= 5:
                    season = "Spring"
                elif 6 <= month <= 8:
                    season = "Summer"
                elif 9 <= month <= 11:
                    season = "Fall"
                else:
                    season = "Winter"
            else:  # Southern hemisphere
                if 3 <= month <= 5:
                    season = "Fall"
                elif 6 <= month <= 8:
                    season = "Winter"
                elif 9 <= month <= 11:
                    season = "Spring"
                else:
                    season = "Summer"
            
            # Use real weather data if available
            if city in DESTINATION_WEATHER and season in DESTINATION_WEATHER[city]:
                weather_data = DESTINATION_WEATHER[city][season]
                
                # Add some randomness to make it realistic
                temp_variation = random.uniform(-3, 3)
                precip_variation = random.uniform(-5, 10)
                
                temp_high = weather_data["high_celsius"] + temp_variation
                temp_low = weather_data["low_celsius"] + temp_variation
                precipitation = max(0, weather_data["precipitation_mm"] + precip_variation)
                condition = weather_data["condition"]
                
                # Adjust condition based on precipitation
                if precipitation > 20 and "Rainy" not in condition:
                    condition = "Rainy"
                elif precipitation > 40:
                    condition = random.choice(["Rainy", "Thunderstorm"])
                
                weather_records.append({
                    "weather_id": weather_id,
                    "destination_id": dest_id,
                    "date": date_str,
                    "temperature_high_celsius": round(temp_high, 1),
                    "temperature_low_celsius": round(temp_low, 1),
                    "precipitation_mm": round(precipitation, 1),
                    "humidity_percent": random.randint(30, 95),
                    "wind_speed_kmh": round(random.uniform(0, 50), 1),
                    "weather_condition": condition,
                    "uv_index": random.randint(1, 11),
                    "air_quality_index": random.randint(1, 300),
                    "forecast_accuracy": round(random.uniform(0.7, 1.0), 2)
                })
            else:
                # Generate synthetic weather based on climate
                base_temp = {
                    "Tropical": random.uniform(25, 35),
                    "Dry": random.uniform(20, 40),
                    "Temperate": random.uniform(10, 25),
                    "Continental": random.uniform(0, 20),
                    "Polar": random.uniform(-20, 5),
                    "Mediterranean": random.uniform(15, 30)
                }.get(climate, random.uniform(10, 30))
                
                # Seasonal adjustments
                if season == "Summer":
                    base_temp += 5
                elif season == "Winter":
                    base_temp -= 5
                
                # Add some randomness
                temp_high = base_temp + random.uniform(0, 5)
                temp_low = base_temp - random.uniform(3, 8)
                
                weather_records.append({
                    "weather_id": weather_id,
                    "destination_id": dest_id,
                    "date": date_str,
                    "temperature_high_celsius": round(temp_high, 1),
                    "temperature_low_celsius": round(temp_low, 1),
                    "precipitation_mm": round(random.uniform(0, 30), 1),
                    "humidity_percent": random.randint(30, 95),
                    "wind_speed_kmh": round(random.uniform(0, 50), 1),
                    "weather_condition": random.choice(WEATHER_CONDITIONS),
                    "uv_index": random.randint(1, 11),
                    "air_quality_index": random.randint(1, 300),
                    "forecast_accuracy": round(random.uniform(0.7, 1.0), 2)
                })
    
    return weather_records

def generate_events(destinations, num_per_destination):
    """Generate event data based on real-world events."""
    events = []
    
    for destination in destinations:
        dest_id = destination["destination_id"]
        city = destination["city"]
        base_lat = destination["latitude"]
        base_lon = destination["longitude"]
        
        # Check if we have predefined events for this city
        if city in DESTINATION_EVENTS:
            real_events = DESTINATION_EVENTS[city]
            
            # Use predefined events first
            for i, event_data in enumerate(real_events[:num_per_destination]):
                event_id = f"{dest_id}_EVT{i+1:03d}"
                
                # Slightly adjust lat/lon to be near the destination
                lat_offset = random.uniform(-0.02, 0.02)
                lon_offset = random.uniform(-0.02, 0.02)
                
                # Parse event dates and create realistic dates
                current_year = datetime.now().year
                
                # Handle date strings like "July 14" or date ranges like "Late March to Early April"
                if "to" in event_data["start_date"] or "-" in event_data["start_date"]:
                    # For date ranges, pick a random date within the range
                    start_month = random.randint(1, 12)
                    start_day = random.randint(1, 28)
                else:
                    # Try to parse specific dates
                    try:
                        date_parts = event_data["start_date"].split()
                        if len(date_parts) >= 2:
                            month_name = date_parts[-2]
                            month_dict = {
                                "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                                "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
                            }
                            start_month = month_dict.get(month_name, random.randint(1, 12))
                            try:
                                start_day = int(''.join(filter(str.isdigit, date_parts[-1])))
                                if start_day < 1 or start_day > 28:
                                    start_day = random.randint(1, 28)
                            except:
                                start_day = random.randint(1, 28)
                        else:
                            start_month = random.randint(1, 12)
                            start_day = random.randint(1, 28)
                    except:
                        start_month = random.randint(1, 12)
                        start_day = random.randint(1, 28)
                
                # If the event date is in the past for this year, use next year
                event_year = current_year
                if datetime(current_year, start_month, start_day) < datetime.now():
                    event_year = current_year + 1
                
                # Create start and end dates
                start_date = datetime(event_year, start_month, start_day)
                
                # Determine event duration (1-7 days)
                duration_days = random.randint(1, 7)
                if event_data["start_date"] == event_data["end_date"]:
                    duration_days = 1
                
                end_date = start_date + timedelta(days=duration_days - 1)
                
                events.append({
                    "event_id": event_id,
                    "destination_id": dest_id,
                    "name": event_data["name"],
                    "type": event_data["type"],
                    "description": event_data["description"],
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "venue": fake.company() + " " + random.choice(["Arena", "Center", "Stadium", "Hall", "Theater", "Park", "Square"]),
                    "address": fake.address().replace('\n', ', '),
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lon + lon_offset,
                    "price_range": random.choice(PRICE_RANGES),
                    "ticket_required": random.choice([True, False]),
                    "booking_url": f"https://tickets.{fake.domain_name()}/event/{event_id}",
                    "local_significance": event_data["local_significance"],
                    "crowd_expectation": random.choice(CROWD_LEVELS)
                })
            
            # If we need more events than we have real data for
            if num_per_destination > len(real_events):
                for i in range(len(real_events), num_per_destination):
                    event_id = f"{dest_id}_EVT{i+1:03d}"
                    
                    # Slightly adjust lat/lon to be near the destination
                    lat_offset = random.uniform(-0.05, 0.05)
                    lon_offset = random.uniform(-0.05, 0.05)
                    
                    # Random dates in the next 6 months
                    start_date = datetime.now() + timedelta(days=random.randint(1, 180))
                    duration_days = random.randint(1, 7)
                    end_date = start_date + timedelta(days=duration_days - 1)
                    
                    events.append({
                        "event_id": event_id,
                        "destination_id": dest_id,
                        "name": fake.catch_phrase(),
                        "type": random.choice(EVENT_TYPES),
                        "description": fake.paragraph(nb_sentences=2),
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "venue": fake.company() + " " + random.choice(["Arena", "Center", "Stadium", "Hall", "Theater", "Park", "Square"]),
                        "address": fake.address().replace('\n', ', '),
                        "latitude": base_lat + lat_offset,
                        "longitude": base_lon + lon_offset,
                        "price_range": random.choice(PRICE_RANGES),
                        "ticket_required": random.choice([True, False]),
                        "booking_url": f"https://tickets.{fake.domain_name()}/event/{event_id}",
                        "local_significance": random.choice(SIGNIFICANCE_LEVELS),
                        "crowd_expectation": random.choice(CROWD_LEVELS)
                    })
        else:
            # Generate synthetic events for destinations without predefined data
            for i in range(1, num_per_destination + 1):
                event_id = f"{dest_id}_EVT{i:03d}"
                
                # Slightly adjust lat/lon to be near the destination
                lat_offset = random.uniform(-0.05, 0.05)
                lon_offset = random.uniform(-0.05, 0.05)
                
                # Random dates in the next 6 months
                start_date = datetime.now() + timedelta(days=random.randint(1, 180))
                duration_days = random.randint(1, 7)
                end_date = start_date + timedelta(days=duration_days - 1)
                
                events.append({
                    "event_id": event_id,
                    "destination_id": dest_id,
                    "name": fake.catch_phrase(),
                    "type": random.choice(EVENT_TYPES),
                    "description": fake.paragraph(nb_sentences=2),
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "venue": fake.company() + " " + random.choice(["Arena", "Center", "Stadium", "Hall", "Theater", "Park", "Square"]),
                    "address": fake.address().replace('\n', ', '),
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lon + lon_offset,
                    "price_range": random.choice(PRICE_RANGES),
                    "ticket_required": random.choice([True, False]),
                    "booking_url": f"https://tickets.{fake.domain_name()}/event/{event_id}",
                    "local_significance": random.choice(SIGNIFICANCE_LEVELS),
                    "crowd_expectation": random.choice(CROWD_LEVELS)
                })
    
    return events

def create_index(es_client, index_name, schema):
    """Create an Elasticsearch index with the given schema."""
    try:
        es_client.indices.create(index=index_name, body=schema)
        print(f"Created index: {index_name}")
    except Exception as e:
        if "resource_already_exists_exception" in str(e):
            print(f"Index {index_name} already exists. Skipping creation.")
        else:
            print(f"Error creating index {index_name}: {e}")

def index_documents(es_client, index_name, documents):
    """Index documents into Elasticsearch."""
    actions = [
        {
            "_index": index_name,
            "_source": document
        }
        for document in documents
    ]
    
    success, failed = bulk(es_client, actions, refresh=True)
    print(f"Indexed {success} documents into {index_name}. Failed: {failed}")

def save_to_json(data, filename):
    """Save data to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved data to {filename}")

def delete_indices(es_client, indices=None):
    """Delete specified Elasticsearch indices or all indices if none specified."""
    if indices is None:
        # Get all indices from schemas
        indices = list(schemas.keys())
    
    for index_name in indices:
        try:
            if es_client.indices.exists(index=index_name):
                es_client.indices.delete(index=index_name)
                print(f"Deleted index: {index_name}")
            else:
                print(f"Index {index_name} does not exist. Skipping deletion.")
        except Exception as e:
            print(f"Error deleting index {index_name}: {e}")

def connect_to_elasticsearch(args):
    """Connect to Elasticsearch using either local connection or cloud credentials."""
    try:
        # Try to load environment variables for cloud connection
        load_dotenv()
        es_api_key = os.getenv("ES_API_KEY")
        es_cloud_id = os.getenv("ES_CLOUD_ID")
        
        if es_api_key and es_cloud_id:
            print("Connecting to Elasticsearch Cloud...")
            return Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)
        else:
            print(f"Connecting to Elasticsearch at {args.es_host}:{args.es_port}...")
            return Elasticsearch([{'host': args.es_host, 'port': args.es_port, 'scheme': 'http'}])
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic travel data for Elasticsearch')
    parser.add_argument('--es-host', default='localhost', help='Elasticsearch host')
    parser.add_argument('--es-port', default=9200, type=int, help='Elasticsearch port')
    parser.add_argument('--destinations', default=DEFAULT_NUM_DESTINATIONS, type=int, help='Number of destinations to generate')
    parser.add_argument('--attractions', default=DEFAULT_NUM_ATTRACTIONS_PER_DEST, type=int, help='Number of attractions per destination')
    parser.add_argument('--hotels', default=DEFAULT_NUM_HOTELS_PER_DEST, type=int, help='Number of hotels per destination')
    parser.add_argument('--advisories', default=DEFAULT_NUM_ADVISORIES_PER_DEST, type=int, help='Number of advisories per destination')
    parser.add_argument('--weather', default=DEFAULT_NUM_WEATHER_RECORDS_PER_DEST, type=int, help='Number of weather records per destination')
    parser.add_argument('--events', default=DEFAULT_NUM_EVENTS_PER_DEST, type=int, help='Number of events per destination')
    parser.add_argument('--save-json', action='store_true', help='Save generated data to JSON files')
    parser.add_argument('--load-es', action='store_true', help='Load data into Elasticsearch')
    parser.add_argument('--cleanup', action='store_true', help='Delete all indices before loading data')
    parser.add_argument('--delete-indices', action='store_true', help='Only delete indices without loading new data')
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch if needed for cleanup or loading
    if args.cleanup or args.load_es or args.delete_indices:
        es = connect_to_elasticsearch(args)
        if es is None:
            print("Failed to connect to Elasticsearch. Exiting.")
            return
        
        # Delete indices if requested
        if args.cleanup or args.delete_indices:
            print("Cleaning up Elasticsearch indices...")
            delete_indices(es)
            
            if args.delete_indices:
                print("Indices deletion complete!")
                return
    
    # Generate data
    print(f"Generating data for {args.destinations} destinations1...")
    destinations = generate_destinations(args.destinations)
    attractions = generate_attractions(destinations, args.attractions)
    hotels = generate_hotels(destinations, args.hotels)
    advisories = generate_advisories(destinations, args.advisories)
    weather = generate_weather(destinations, args.weather)
    events = generate_events(destinations, args.events)
    
    # Save to JSON if requested
    if args.save_json:
        save_to_json(destinations, 'destinations.json')
        save_to_json(attractions, 'attractions.json')
        save_to_json(hotels, 'hotels.json')
        save_to_json(advisories, 'advisories.json')
        save_to_json(weather, 'weather.json')
        save_to_json(events, 'events.json')
    
    # Load into Elasticsearch if requested
    if args.load_es:
        if 'es' not in locals():
            es = connect_to_elasticsearch(args)
            if es is None:
                print("Failed to connect to Elasticsearch. Exiting.")
                return
        
        # Create indices
        create_index(es, 'destinations', schemas['destinations'])
        create_index(es, 'attractions', schemas['attractions'])
        create_index(es, 'hotels', schemas['hotels'])
        create_index(es, 'advisories', schemas['advisories'])
        create_index(es, 'weather', schemas['weather'])
        create_index(es, 'events', schemas['events'])
        
        # Index documents
        index_documents(es, 'destinations', destinations)
        index_documents(es, 'attractions', attractions)
        index_documents(es, 'hotels', hotels)
        index_documents(es, 'advisories', advisories)
        index_documents(es, 'weather', weather)
        index_documents(es, 'events', events)
        
        print("Data loading complete!")

if __name__ == "__main__":
    main()