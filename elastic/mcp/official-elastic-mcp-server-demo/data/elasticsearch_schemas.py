"""
Elasticsearch schemas for Travel Advisory Application.
These schemas are intentionally flat (non-nested) for easier querying.
"""

# Destinations index schema
destinations_schema = {
    "mappings": {
        "properties": {
            "destination_id": {"type": "keyword"},
            "name": {"type": "text"},
            "city": {"type": "keyword"},
            "country": {"type": "keyword"},
            "continent": {"type": "keyword"},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "description": {"type": "text"},
            "best_season": {"type": "keyword"},
            "climate": {"type": "keyword"},
            "language": {"type": "keyword"},
            "currency": {"type": "keyword"},
            "timezone": {"type": "keyword"},
            "safety_rating": {"type": "integer"},  # 1-10 scale
            "popularity_score": {"type": "integer"},  # 1-100 scale
            "cost_level": {"type": "keyword"},  # Budget, Moderate, Luxury
            "tags": {"type": "keyword"}  # Beach, Mountain, Cultural, etc.
        }
    }
}

# Attractions index schema
attractions_schema = {
    "mappings": {
        "properties": {
            "attraction_id": {"type": "keyword"},
            "destination_id": {"type": "keyword"},  # Reference to destination
            "name": {"type": "text"},
            "type": {"type": "keyword"},  # Museum, Park, Monument, etc.
            "description": {"type": "text"},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "address": {"type": "text"},
            "opening_hours": {"type": "text"},
            "closing_hours": {"type": "text"},
            "price_range": {"type": "keyword"},  # Free, $, $$, $$$
            "duration_minutes": {"type": "integer"},
            "accessibility": {"type": "boolean"},
            "rating": {"type": "float"},  # 0-5 scale
            "tags": {"type": "keyword"},
            "best_time_to_visit": {"type": "keyword"},
            "crowd_level": {"type": "keyword"}  # Low, Moderate, High
        }
    }
}

# Hotels index schema
hotels_schema = {
    "mappings": {
        "properties": {
            "hotel_id": {"type": "keyword"},
            "destination_id": {"type": "keyword"},  # Reference to destination
            "name": {"type": "text"},
            "brand": {"type": "keyword"},
            "address": {"type": "text"},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "star_rating": {"type": "integer"},  # 1-5 stars
            "user_rating": {"type": "float"},  # 0-5 scale
            "price_per_night": {"type": "float"},
            "currency": {"type": "keyword"},
            "amenities": {"type": "keyword"},  # Pool, Spa, Restaurant, etc.
            "room_types": {"type": "keyword"},  # Single, Double, Suite, etc.
            "breakfast_included": {"type": "boolean"},
            "free_wifi": {"type": "boolean"},
            "parking_available": {"type": "boolean"},
            "distance_to_center_km": {"type": "float"},
            "pet_friendly": {"type": "boolean"},
            "check_in_time": {"type": "keyword"},
            "check_out_time": {"type": "keyword"}
        }
    }
}

# Travel advisories index schema
advisories_schema = {
    "mappings": {
        "properties": {
            "advisory_id": {"type": "keyword"},
            "destination_id": {"type": "keyword"},  # Reference to destination
            "country": {"type": "keyword"},
            "advisory_level": {"type": "keyword"},  # Low, Medium, High, Extreme
            "description": {"type": "text"},
            "issue_date": {"type": "date"},
            "expiry_date": {"type": "date"},
            "issuing_authority": {"type": "keyword"},
            "health_risks": {"type": "text"},
            "safety_risks": {"type": "text"},
            "entry_requirements": {"type": "text"},
            "visa_required": {"type": "boolean"},
            "vaccination_required": {"type": "keyword"},
            "currency_restrictions": {"type": "text"},
            "local_laws": {"type": "text"},
            "emergency_contacts": {"type": "text"}
        }
    }
}

# Weather data index schema
weather_schema = {
    "mappings": {
        "properties": {
            "weather_id": {"type": "keyword"},
            "destination_id": {"type": "keyword"},  # Reference to destination
            "date": {"type": "date"},
            "temperature_high_celsius": {"type": "float"},
            "temperature_low_celsius": {"type": "float"},
            "precipitation_mm": {"type": "float"},
            "humidity_percent": {"type": "integer"},
            "wind_speed_kmh": {"type": "float"},
            "weather_condition": {"type": "keyword"},  # Sunny, Cloudy, Rainy, etc.
            "uv_index": {"type": "integer"},
            "air_quality_index": {"type": "integer"},
            "forecast_accuracy": {"type": "float"}  # 0-1 scale
        }
    }
}

# Events index schema
events_schema = {
    "mappings": {
        "properties": {
            "event_id": {"type": "keyword"},
            "destination_id": {"type": "keyword"},  # Reference to destination
            "name": {"type": "text"},
            "type": {"type": "keyword"},  # Festival, Concert, Sports, etc.
            "description": {"type": "text"},
            "start_date": {"type": "date"},
            "end_date": {"type": "date"},
            "venue": {"type": "text"},
            "address": {"type": "text"},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "price_range": {"type": "keyword"},  # Free, $, $$, $$$
            "ticket_required": {"type": "boolean"},
            "booking_url": {"type": "keyword"},
            "local_significance": {"type": "keyword"},  # Low, Medium, High
            "crowd_expectation": {"type": "keyword"}  # Low, Moderate, High
        }
    }
}

# Users index schema
users_schema = {
    "mappings": {
        "properties": {
            "user_id": {"type": "keyword"},
            "email": {"type": "keyword"},
            "first_name": {"type": "text"},
            "last_name": {"type": "text"},
            "phone": {"type": "keyword"},
            "date_of_birth": {"type": "date"},
            "nationality": {"type": "keyword"},
            "preferred_language": {"type": "keyword"},
            "preferred_currency": {"type": "keyword"},
            "loyalty_tier": {"type": "keyword"},  # Standard, Silver, Gold, Platinum
            "loyalty_points": {"type": "integer"},
            "account_created": {"type": "date"},
            "last_login": {"type": "date"},
            "preferences": {"type": "keyword"},  # Room preferences, amenities, etc.
            "dietary_restrictions": {"type": "keyword"},
            "special_needs": {"type": "text"}
        }
    }
}

# Reservations index schema
reservations_schema = {
    "mappings": {
        "properties": {
            "reservation_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},  # Reference to user
            "hotel_id": {"type": "keyword"},  # Reference to hotel
            "room_type": {"type": "keyword"},
            "check_in_date": {"type": "date"},
            "check_out_date": {"type": "date"},
            "num_guests": {"type": "integer"},
            "num_rooms": {"type": "integer"},
            "total_price": {"type": "float"},
            "currency": {"type": "keyword"},
            "payment_status": {"type": "keyword"},  # Pending, Paid, Refunded, etc.
            "payment_method": {"type": "keyword"},  # Credit Card, PayPal, etc.
            "booking_date": {"type": "date"},
            "booking_source": {"type": "keyword"},  # Direct, OTA, Travel Agent, etc.
            "status": {"type": "keyword"},  # Confirmed, Cancelled, Completed, etc.
            "special_requests": {"type": "text"},
            "breakfast_included": {"type": "boolean"},
            "is_refundable": {"type": "boolean"},
            "cancellation_deadline": {"type": "date"},
            "confirmation_code": {"type": "keyword"}
        }
    }
}

# Room availability index schema
room_availability_schema = {
    "mappings": {
        "properties": {
            "availability_id": {"type": "keyword"},
            "hotel_id": {"type": "keyword"},  # Reference to hotel
            "room_type": {"type": "keyword"},
            "date": {"type": "date"},
            "available_rooms": {"type": "integer"},
            "total_rooms": {"type": "integer"},
            "price": {"type": "float"},
            "currency": {"type": "keyword"},
            "promotion_code": {"type": "keyword"},
            "discount_percentage": {"type": "float"},
            "minimum_stay": {"type": "integer"},  # Minimum nights required
            "is_closed": {"type": "boolean"},  # Whether the hotel is closed on this date
            "last_updated": {"type": "date"}
        }
    }
}

# All schemas in a dictionary for easy access
schemas = {
    "destinations": destinations_schema,
    "attractions": attractions_schema,
    "hotels": hotels_schema,
    "advisories": advisories_schema,
    "weather": weather_schema,
    "events": events_schema,
    "users": users_schema,
    "reservations": reservations_schema,
    "room_availability": room_availability_schema
}
