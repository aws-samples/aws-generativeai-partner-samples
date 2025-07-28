#!/usr/bin/env python3
"""
Script to generate user profiles and their hotel reservations.
This script creates sample users with reservation history and loads them into Elasticsearch.
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

# Initialize Faker
fake = faker.Faker()

# Sample user data
SAMPLE_USERS = [
    {
        "user_id": "USER001",
        "email": "john.smith@example.com",
        "first_name": "John",
        "last_name": "Smith",
        "phone": "+1-555-123-4567",
        "date_of_birth": "1985-06-15",
        "nationality": "United States",
        "preferred_language": "English",
        "preferred_currency": "USD",
        "loyalty_tier": "Gold",
        "loyalty_points": 5000,
        "account_created": "2020-03-10",
        "last_login": "2025-05-01",
        "preferences": ["Non-smoking", "High floor", "King bed"],
        "dietary_restrictions": ["None"],
        "special_needs": ""
    },
    {
        "user_id": "USER002",
        "email": "maria.garcia@example.com",
        "first_name": "Maria",
        "last_name": "Garcia",
        "phone": "+34-611-234-567",
        "date_of_birth": "1990-11-22",
        "nationality": "Spain",
        "preferred_language": "Spanish",
        "preferred_currency": "EUR",
        "loyalty_tier": "Silver",
        "loyalty_points": 2500,
        "account_created": "2021-07-15",
        "last_login": "2025-05-05",
        "preferences": ["Quiet room", "Twin beds", "Near elevator"],
        "dietary_restrictions": ["Vegetarian"],
        "special_needs": ""
    },
    {
        "user_id": "USER003",
        "email": "akira.tanaka@example.com",
        "first_name": "Akira",
        "last_name": "Tanaka",
        "phone": "+81-90-1234-5678",
        "date_of_birth": "1978-09-03",
        "nationality": "Japan",
        "preferred_language": "Japanese",
        "preferred_currency": "JPY",
        "loyalty_tier": "Platinum",
        "loyalty_points": 12000,
        "account_created": "2019-01-20",
        "last_login": "2025-05-07",
        "preferences": ["Non-smoking", "Japanese breakfast", "Late check-out"],
        "dietary_restrictions": ["No pork"],
        "special_needs": "Accessible bathroom"
    }
]

def load_hotels(es_client):
    """Load hotels from Elasticsearch to use in reservations."""
    query = {
        "query": {
            "match_all": {}
        },
        "size": 100
    }
    
    response = es_client.search(index="hotels", body=query)
    return [hit["_source"] for hit in response["hits"]["hits"]]

def generate_past_reservations(user, hotels, num_reservations=3):
    """Generate past hotel reservations for a user."""
    reservations = []
    
    # Get current date
    now = datetime.now()
    
    for i in range(num_reservations):
        # Select a random hotel
        hotel = random.choice(hotels)
        
        # Generate a random past date (between 30 and 365 days ago)
        days_ago = random.randint(30, 365)
        check_in_date = now - timedelta(days=days_ago)
        
        # Stay duration between 1 and 7 days
        stay_duration = random.randint(1, 7)
        check_out_date = check_in_date + timedelta(days=stay_duration)
        
        # Booking date (1-30 days before check-in)
        booking_days_before = random.randint(1, 30)
        booking_date = check_in_date - timedelta(days=booking_days_before)
        
        # Generate reservation
        reservation_id = f"{user['user_id']}_RES{i+1:03d}"
        room_type = random.choice(hotel.get("room_types", ["Standard"]))
        num_guests = random.randint(1, 4)
        price_per_night = hotel.get("price_per_night", 100)
        total_price = round(price_per_night * stay_duration * (1 + 0.1 * num_guests), 2)  # Simple price calculation
        
        reservation = {
            "reservation_id": reservation_id,
            "user_id": user["user_id"],
            "hotel_id": hotel["hotel_id"],
            "room_type": room_type,
            "check_in_date": check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": check_out_date.strftime("%Y-%m-%d"),
            "num_guests": num_guests,
            "num_rooms": 1,
            "total_price": total_price,
            "currency": hotel.get("currency", "USD"),
            "payment_status": "Paid",
            "payment_method": random.choice(["Credit Card", "PayPal", "Bank Transfer"]),
            "booking_date": booking_date.strftime("%Y-%m-%d"),
            "booking_source": random.choice(["Direct", "Expedia", "Booking.com", "Travel Agent"]),
            "status": "Completed",
            "special_requests": random.choice(["", "Late check-in", "Extra pillows", "Quiet room"]),
            "breakfast_included": hotel.get("breakfast_included", False),
            "is_refundable": random.choice([True, False]),
            "cancellation_deadline": (check_in_date - timedelta(days=1)).strftime("%Y-%m-%d"),
            "confirmation_code": f"CONF{random.randint(10000, 99999)}"
        }
        
        reservations.append(reservation)
    
    return reservations

def generate_future_reservations(user, hotels, num_reservations=1):
    """Generate future hotel reservations for a user."""
    reservations = []
    
    # Get current date
    now = datetime.now()
    
    for i in range(num_reservations):
        # Select a random hotel
        hotel = random.choice(hotels)
        
        # Generate a random future date (between 7 and 180 days from now)
        days_ahead = random.randint(7, 180)
        check_in_date = now + timedelta(days=days_ahead)
        
        # Stay duration between 1 and 10 days
        stay_duration = random.randint(1, 10)
        check_out_date = check_in_date + timedelta(days=stay_duration)
        
        # Booking date (between now and 30 days ago)
        booking_days_ago = random.randint(0, 30)
        booking_date = now - timedelta(days=booking_days_ago)
        
        # Generate reservation
        reservation_id = f"{user['user_id']}_RES{i+4:03d}"  # Start from 4 to avoid overlap with past reservations
        room_type = random.choice(hotel.get("room_types", ["Standard"]))
        num_guests = random.randint(1, 4)
        price_per_night = hotel.get("price_per_night", 100)
        total_price = round(price_per_night * stay_duration * (1 + 0.1 * num_guests), 2)  # Simple price calculation
        
        reservation = {
            "reservation_id": reservation_id,
            "user_id": user["user_id"],
            "hotel_id": hotel["hotel_id"],
            "room_type": room_type,
            "check_in_date": check_in_date.strftime("%Y-%m-%d"),
            "check_out_date": check_out_date.strftime("%Y-%m-%d"),
            "num_guests": num_guests,
            "num_rooms": 1,
            "total_price": total_price,
            "currency": hotel.get("currency", "USD"),
            "payment_status": random.choice(["Paid", "Pending"]),
            "payment_method": random.choice(["Credit Card", "PayPal", "Bank Transfer"]),
            "booking_date": booking_date.strftime("%Y-%m-%d"),
            "booking_source": random.choice(["Direct", "Expedia", "Booking.com", "Travel Agent"]),
            "status": "Confirmed",
            "special_requests": random.choice(["", "Early check-in", "Airport shuttle", "Birthday decoration"]),
            "breakfast_included": hotel.get("breakfast_included", False),
            "is_refundable": random.choice([True, False]),
            "cancellation_deadline": (check_in_date - timedelta(days=1)).strftime("%Y-%m-%d"),
            "confirmation_code": f"CONF{random.randint(10000, 99999)}"
        }
        
        reservations.append(reservation)
    
    return reservations

def generate_room_availability(hotels, days_ahead=90):
    """Generate room availability data for hotels."""
    availability_records = []
    
    # Get current date
    now = datetime.now()
    
    for hotel in hotels:
        hotel_id = hotel["hotel_id"]
        room_types = hotel.get("room_types", ["Standard"])
        base_price = hotel.get("price_per_night", 100)
        
        for room_type in room_types:
            # Determine total rooms of this type
            total_rooms = random.randint(5, 30)
            
            # Generate availability for each day
            for day in range(days_ahead):
                date = now + timedelta(days=day)
                date_str = date.strftime("%Y-%m-%d")
                
                # Determine available rooms (some might be booked)
                available_rooms = max(0, total_rooms - random.randint(0, total_rooms // 2))
                
                # Price variations based on day of week and seasonality
                day_of_week = date.weekday()
                is_weekend = day_of_week >= 5  # Saturday or Sunday
                is_high_season = 5 <= date.month <= 8  # Summer months
                
                price_multiplier = 1.0
                if is_weekend:
                    price_multiplier *= 1.2
                if is_high_season:
                    price_multiplier *= 1.3
                
                # Room type price adjustment
                if "Deluxe" in room_type:
                    price_multiplier *= 1.5
                elif "Suite" in room_type:
                    price_multiplier *= 2.0
                
                price = round(base_price * price_multiplier, 2)
                
                # Generate availability record
                availability_id = f"{hotel_id}_{room_type.replace(' ', '_')}_{date_str}"
                
                availability_record = {
                    "availability_id": availability_id,
                    "hotel_id": hotel_id,
                    "room_type": room_type,
                    "date": date_str,
                    "available_rooms": available_rooms,
                    "total_rooms": total_rooms,
                    "price": price,
                    "currency": hotel.get("currency", "USD"),
                    "promotion_code": "" if random.random() > 0.1 else f"PROMO{random.randint(100, 999)}",
                    "discount_percentage": 0 if random.random() > 0.1 else random.choice([5, 10, 15, 20]),
                    "minimum_stay": 1 if random.random() > 0.2 else random.randint(2, 3),
                    "is_closed": False if random.random() > 0.05 else True,  # 5% chance hotel is closed
                    "last_updated": datetime.now().strftime("%Y-%m-%d")
                }
                
                availability_records.append(availability_record)
    
    return availability_records

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

def connect_to_elasticsearch(args):
    """Connect to Elasticsearch using either local connection or cloud credentials."""
    try:
        # Try to load environment variables for cloud connection
        load_dotenv()
        es_api_key = os.getenv("ES_API_KEY")
        es_url = os.getenv("ES_URL")
        #es_cloud_id = os.getenv("ES_CLOUD_ID")
        if es_api_key and es_url:
            print("Connecting to Elasticsearch Serverless...")
            return Elasticsearch(hosts=[es_url],
            api_key=es_api_key,
            verify_certs=True,
            request_timeout=30)
            
        else:
            print(f"Connecting to Elasticsearch at {args.es_host}:{args.es_port}...")
            return Elasticsearch([{'host': args.es_host, 'port': args.es_port, 'scheme': 'http'}])
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate user profiles and reservations for Travel Advisory Application')
    parser.add_argument('--es-host', default='localhost', help='Elasticsearch host')
    parser.add_argument('--es-port', default=9200, type=int, help='Elasticsearch port')
    parser.add_argument('--save-json', action='store_true', help='Save generated data to JSON files')
    parser.add_argument('--load-es', action='store_true', help='Load data into Elasticsearch')
    parser.add_argument('--cleanup', action='store_true', help='Delete user indices before loading data')
    parser.add_argument('--delete-indices', action='store_true', help='Only delete user indices without loading new data')
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch if needed for cleanup or loading
    if args.cleanup or args.load_es or args.delete_indices:
        #load_dotenv()
        es = connect_to_elasticsearch(args)
        #es_api_key = os.getenv("ES_API_KEY")
        #es_cloud_id = os.getenv("ES_CLOUD_ID")
        
        #if es_api_key and es_cloud_id:
        #    print("Connecting to Elasticsearch Cloud...")
        #    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)
        #else:
        #    print(f"Connecting to Elasticsearch at {args.es_host}:{args.es_port}...")
        #    es = Elasticsearch([{'host': args.es_host, 'port': args.es_port, 'scheme': 'http'}])
        
        # Delete indices if requested
        if args.cleanup or args.delete_indices:
            print("Cleaning up user-related Elasticsearch indices...")
            delete_user_indices(es)
            
            if args.delete_indices:
                print("User indices deletion complete!")
                return
    
    # Connect to Elasticsearch to load hotels
    if args.load_es:
        if 'es' not in locals():
            es = connect_to_elasticsearch(args)
            #load_dotenv()
            #es_api_key = os.getenv("ES_API_KEY")
            #es_cloud_id = os.getenv("ES_CLOUD_ID")
            
            #if es_api_key and es_cloud_id:
            #    print("Connecting to Elasticsearch Cloud...")
            #    es = Elasticsearch(cloud_id=es_cloud_id, api_key=es_api_key)
            #else:
            #    print(f"Connecting to Elasticsearch at {args.es_host}:{args.es_port}...")
            #    es = Elasticsearch([{'host': args.es_host, 'port': args.es_port, 'scheme': 'http'}])
        
        # Load hotels to use in reservations
        hotels = load_hotels(es)
        if not hotels:
            print("No hotels found in Elasticsearch. Please load hotel data first.")
            return
    else:
        # Dummy hotels for JSON output
        hotels = [
            {
                "hotel_id": "DUMMY_HOTEL001",
                "name": "Grand Hotel",
                "room_types": ["Standard", "Deluxe", "Suite"],
                "price_per_night": 150,
                "currency": "USD",
                "breakfast_included": True
            },
            {
                "hotel_id": "DUMMY_HOTEL002",
                "name": "Beach Resort",
                "room_types": ["Standard", "Ocean View", "Villa"],
                "price_per_night": 200,
                "currency": "USD",
                "breakfast_included": True
            },
            {
                "hotel_id": "DUMMY_HOTEL003",
                "name": "City Center Hotel",
                "room_types": ["Standard", "Business", "Executive Suite"],
                "price_per_night": 120,
                "currency": "EUR",
                "breakfast_included": False
            }
        ]
    
    # Generate reservations for each user
    all_reservations = []
    for user in SAMPLE_USERS:
        past_reservations = generate_past_reservations(user, hotels, 3)
        future_reservations = generate_future_reservations(user, hotels, 1)
        all_reservations.extend(past_reservations)
        all_reservations.extend(future_reservations)
    
    # Generate room availability data
    room_availability = generate_room_availability(hotels[:10], 90)  # Generate for first 10 hotels, 90 days ahead
    
    # Save to JSON if requested
    if args.save_json:
        save_to_json(SAMPLE_USERS, 'users.json')
        save_to_json(all_reservations, 'reservations.json')
        save_to_json(room_availability, 'room_availability.json')
    
    # Load into Elasticsearch if requested
    if args.load_es:
        if 'es' not in locals():
            es = connect_to_elasticsearch(args)
            #load_dotenv()
            #es_api_key = os.getenv("ES_API_KEY")
            #es_url = os.getenv("ES_URL")
        
            #not needed for serverless
            #es_cloud_id = os.getenv("ES_CLOUD_ID")
        
            #if es_api_key and es_url:
            #    print("Connecting to Elasticsearch Cloud...")
            #    return Elasticsearch(hosts=[es_url],
            #    api_key=es_api_key,
            #    verify_certs=True,
            #    request_timeout=30)
            #else:
            #    print(f"Connecting to Elasticsearch at {args.es_host}:{args.es_port}...")
            #    es = Elasticsearch([{'host': args.es_host, 'port': args.es_port, 'scheme': 'http'}])
        
        # Create indices
        create_index(es, 'app_users', schemas['users'])
        create_index(es, 'reservations', schemas['reservations'])
        create_index(es, 'room_availability', schemas['room_availability'])
        
        # Index documents
        index_documents(es, 'app_users', SAMPLE_USERS)
        index_documents(es, 'reservations', all_reservations)
        index_documents(es, 'room_availability', room_availability)
        
        print("User data loading complete!")


def delete_user_indices(es_client, indices=None):
    """Delete user-related Elasticsearch indices."""
    if indices is None:
        indices = ['app_users', 'reservations', 'room_availability']
    
    for index_name in indices:
        try:
            if es_client.indices.exists(index=index_name):
                es_client.indices.delete(index=index_name)
                print(f"Deleted index: {index_name}")
            else:
                print(f"Index {index_name} does not exist. Skipping deletion.")
        except Exception as e:
            print(f"Error deleting index {index_name}: {e}")

if __name__ == "__main__":
    main()
