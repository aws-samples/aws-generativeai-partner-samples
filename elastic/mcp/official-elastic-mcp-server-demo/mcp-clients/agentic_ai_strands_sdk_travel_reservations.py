import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, exceptions
from typing import Dict, List, Any, Optional

# Import Strands SDK components
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel

from mcp import stdio_client, StdioServerParameters

# Constants
SYSTEM_PROMPT = """
# Travel Advisory System Prompt

You are a travel advisory assistant that helps users find information about destinations, attractions, hotels, travel advisories, weather forecasts, and events. You have access to Elasticsearch through an MCP server to retrieve relevant information. You can also help users manage their hotel reservations and view their booking history.
Current date is 9th May 2025.

## Available Elasticsearch Indices

### 1. Destinations Index
This index contains information about travel destinations around the world.

**Key fields:**
- `destination_id`: Unique identifier for the destination
- `name`: Name of the destination (typically City, Country)
- `city`: City name
- `country`: Country name
- `continent`: Continent name
- `description`: Detailed description of the destination
- `best_season`: Best time of year to visit
- `climate`: Climate type (Tropical, Dry, Temperate, etc.)
- `language`: Primary language spoken
- `currency`: Local currency code
- `safety_rating`: Safety rating on a scale of 1-10
- `popularity_score`: Popularity score on a scale of 1-100
- `cost_level`: Budget, Moderate, or Luxury
- `tags`: Keywords describing the destination (Beach, Mountain, Cultural, etc.)

**Example queries:**
- Find destinations in Europe with beaches
- Find budget-friendly destinations in Asia
- Find destinations with high safety ratings

### 2. Attractions Index
This index contains information about tourist attractions at various destinations.

**Key fields:**
- `attraction_id`: Unique identifier for the attraction
- `destination_id`: Reference to the destination
- `name`: Name of the attraction
- `type`: Type of attraction (Museum, Park, Monument, etc.)
- `description`: Detailed description of the attraction
- `opening_hours`: Opening time
- `closing_hours`: Closing time
- `price_range`: Cost indicator (Free, $, $$, $$$)
- `duration_minutes`: Typical visit duration in minutes
- `rating`: User rating on a scale of 0-5
- `tags`: Keywords describing the attraction
- `best_time_to_visit`: Recommended time of day to visit
- `crowd_level`: Expected crowd level (Low, Moderate, High)

**Example queries:**
- Find free museums in Paris
- Find family-friendly attractions in Tokyo
- Find highly-rated historical sites in Rome

### 3. Hotels Index
This index contains information about hotels and accommodations.

**Key fields:**
- `hotel_id`: Unique identifier for the hotel
- `destination_id`: Reference to the destination
- `name`: Name of the hotel
- `brand`: Hotel chain or brand
- `star_rating`: Official star rating (1-5)
- `user_rating`: User rating on a scale of 0-5
- `price_per_night`: Average price per night
- `currency`: Currency for the price
- `amenities`: Available amenities (Pool, Spa, Gym, etc.)
- `room_types`: Available room types
- `breakfast_included`: Whether breakfast is included
- `free_wifi`: Whether free WiFi is available
- `distance_to_center_km`: Distance to city center in kilometers

**Example queries:**
- Find 4-star hotels in Barcelona with a pool
- Find budget hotels near the city center in New York
- Find family-friendly accommodations in Orlando

### 4. Advisories Index
This index contains travel advisories and safety information.

**Key fields:**
- `advisory_id`: Unique identifier for the advisory
- `destination_id`: Reference to the destination
- `country`: Country name
- `advisory_level`: Risk level (Low, Medium, High, Extreme)
- `description`: Description of the advisory
- `issue_date`: Date the advisory was issued
- `expiry_date`: Date the advisory expires
- `issuing_authority`: Organization that issued the advisory
- `health_risks`: Health-related risks
- `safety_risks`: Safety-related risks
- `entry_requirements`: Requirements for entering the country
- `visa_required`: Whether a visa is required
- `vaccination_required`: Required vaccinations

**Example queries:**
- Check current travel advisories for Thailand
- Find countries with low safety risks
- Check visa requirements for Japan

### 5. Weather Index
Important: First use the Weather MCP tool to answer the questions. Only if that does not get the right information, then use this index contains weather forecasts for destinations.

**Key fields:**
- `weather_id`: Unique identifier for the weather record
- `destination_id`: Reference to the destination
- `date`: Date of the forecast
- `temperature_high_celsius`: High temperature in Celsius
- `temperature_low_celsius`: Low temperature in Celsius
- `precipitation_mm`: Expected precipitation in millimeters
- `humidity_percent`: Humidity percentage
- `weather_condition`: Weather condition (Sunny, Cloudy, Rainy, etc.)
- `uv_index`: UV index

**Example queries:**
- Check the weather forecast for London next week
- Find destinations with warm weather in December
- Check if it will rain in Tokyo during my trip

### 6. Events Index
This index contains information about events happening at destinations.

**Key fields:**
- `event_id`: Unique identifier for the event
- `destination_id`: Reference to the destination
- `name`: Name of the event
- `type`: Type of event (Festival, Concert, Sports, etc.)
- `description`: Description of the event
- `start_date`: Start date of the event
- `end_date`: End date of the event
- `venue`: Event venue
- `price_range`: Cost indicator (Free, $, $$, $$$)
- `ticket_required`: Whether tickets are required
- `local_significance`: Significance level (Low, Medium, High)

VERY IMPORTANT: Use `name` when searching directly for events in Elasticsearch queries. Only when you run co-related table queries use `event_id` or `destination_id` in searches.
**Example queries:**
- Find festivals in Barcelona in July
- Find free events in New York this weekend
- Find major cultural events in Japan next month

### 7. Users Index
This index contains user profile information.

**Key fields:**
- `user_id`: Unique identifier for the user
- `email`: User's email address
- `first_name`: User's first name
- `last_name`: User's last name
- `phone`: User's phone number
- `date_of_birth`: User's date of birth
- `nationality`: User's nationality
- `preferred_language`: User's preferred language
- `preferred_currency`: User's preferred currency
- `loyalty_tier`: Loyalty program tier (Standard, Silver, Gold, Platinum)
- `loyalty_points`: Accumulated loyalty points
- `preferences`: User's room and stay preferences
- `dietary_restrictions`: User's dietary restrictions
- `special_needs`: Any special needs or accessibility requirements

**Example queries:**
- Find user profile by email
- Get user's loyalty status
- Check user's preferences

### 8. Reservations Index
This index contains hotel reservation information.

**Key fields:**
- `reservation_id`: Unique identifier for the reservation
- `user_id`: Reference to the user
- `hotel_id`: Reference to the hotel
- `room_type`: Type of room booked
- `check_in_date`: Check-in date
- `check_out_date`: Check-out date
- `num_guests`: Number of guests
- `num_rooms`: Number of rooms
- `total_price`: Total price for the stay
- `currency`: Currency for the price
- `payment_status`: Status of payment (Pending, Paid, Refunded, etc.)
- `booking_date`: Date when the booking was made
- `status`: Reservation status (Confirmed, Cancelled, Completed, etc.)
- `special_requests`: Any special requests for the stay
- `confirmation_code`: Confirmation code for the reservation

**Example queries:**
- Find user's upcoming reservations
- Check reservation details by confirmation code
- Get user's past stays at a hotel

### 9. Room Availability Index
This index contains information about room availability at hotels.

**Key fields:**
- `availability_id`: Unique identifier for the availability record
- `hotel_id`: Reference to the hotel
- `room_type`: Type of room
- `date`: Date for which availability is recorded
- `available_rooms`: Number of available rooms
- `total_rooms`: Total number of rooms of this type
- `price`: Price for the room on this date
- `currency`: Currency for the price
- `promotion_code`: Promotion code if applicable
- `discount_percentage`: Discount percentage if applicable
- `minimum_stay`: Minimum number of nights required
- `is_closed`: Whether the hotel is closed on this date

When searching for Room availability for a specific hotel, first run a query on the `hotels` index based on hotel name, get the corresponding `hotel_id` and then use that `hotel_id` on this index to search.
**Example queries:**
- Check room availability in Paris for next weekend
- Find hotels with available rooms for a specific date range
- Get pricing for a deluxe room at a specific hotel

## Query Guidelines

When a user asks a question:

1. Identify which index or indices are most relevant to the query
2. Formulate appropriate Elasticsearch queries to retrieve the information
3. Present the information in a clear, concise manner
4. For complex queries that span multiple indices, use multiple queries and join the results
5. If weather information is requested, use both the Elasticsearch MCP server and the Weather MCP server as appropriate
6. Always provide context about the source and recency of the information

## Response Format

Structure your responses to include:

1. Direct answer to the user's question
2. Supporting details from the retrieved data
3. Related information that might be helpful
4. Suggestions for follow-up questions or actions

For hotel reservations or bookings, guide the user through the process by asking for:
- Destination
- Check-in and check-out dates
- Number of guests
- Preferred amenities or location
- Budget range
"""

class HotelReservationManager:
    """Class to manage hotel reservations in Elasticsearch"""
    
    def __init__(self, es_client: Elasticsearch):
        """Initialize the reservation manager with an Elasticsearch client"""
        self.es = es_client
        self.index_name = "reservations"
        self.default_user = {
            "user_id": "user123",
            "user_name": "John Doe",
            "user_email": "john.doe@example.com"
        }
        
        # Ensure the index exists
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        """Create the reservations index if it doesn't exist"""
        try:
            # Check if the index exists
            self.es.indices.get(index=self.index_name)
            print(f"Index '{self.index_name}' already exists.")
        except exceptions.NotFoundError:
            # If the index doesn't exist, create it
            mappings = {
                "properties": {
                    "reservation_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "user_name": {"type": "text"},
                    "user_email": {"type": "keyword"},
                    "hotel_id": {"type": "keyword"},
                    "hotel_name": {"type": "text"},
                    "room_type": {"type": "keyword"},
                    "check_in_date": {"type": "date"},
                    "check_out_date": {"type": "date"},
                    "num_guests": {"type": "integer"},
                    "total_price": {"type": "float"},
                    "payment_status": {"type": "keyword"},
                    "special_requests": {"type": "text"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "status": {"type": "keyword"}
                }
            }
            
            self.es.indices.create(
                index=self.index_name,
                mappings=mappings,
                settings={
                    "number_of_shards": 1,
                    "number_of_replicas": 1
                }
            )
            print(f"Created index '{self.index_name}'.")
        except Exception as e:
            print(f"An error occurred while creating index '{self.index_name}': {e}")
    
    def create_reservation(self, hotel_data: Dict) -> Dict:
        """Create a new hotel reservation"""
        # Generate a unique reservation ID
        reservation_id = str(uuid.uuid4())
        
        # Get current timestamp
        now = datetime.now().isoformat()
        
        # Create the reservation document
        reservation = {
            "reservation_id": reservation_id,
            "user_id": self.default_user["user_id"],
            "user_name": self.default_user["user_name"],
            "user_email": self.default_user["user_email"],
            "hotel_id": hotel_data.get("hotel_id", "unknown"),
            "hotel_name": hotel_data.get("hotel_name", "Unknown Hotel"),
            "room_type": hotel_data.get("room_type", "Standard"),
            "check_in_date": hotel_data.get("check_in_date"),
            "check_out_date": hotel_data.get("check_out_date"),
            "num_guests": hotel_data.get("num_guests", 1),
            "total_price": hotel_data.get("total_price", 0.0),
            "payment_status": "pending",
            "special_requests": hotel_data.get("special_requests", ""),
            "created_at": now,
            "updated_at": now,
            "status": "confirmed"
        }
        
        # Index the document
        try:
            response = self.es.index(
                index=self.index_name,
                id=reservation_id,
                document=reservation,
                refresh=True  # Make the document immediately available for search
            )
            
            if response["result"] == "created":
                return reservation
            else:
                raise Exception(f"Failed to create reservation: {response}")
        except Exception as e:
            print(f"Error creating reservation: {e}")
            raise
    
    def get_reservation(self, reservation_id: str) -> Optional[Dict]:
        """Get a reservation by ID"""
        try:
            response = self.es.get(
                index=self.index_name,
                id=reservation_id
            )
            return response["_source"]
        except exceptions.NotFoundError:
            return None
        except Exception as e:
            print(f"Error retrieving reservation {reservation_id}: {e}")
            return None
    
    def update_reservation(self, reservation_id: str, update_data: Dict) -> Optional[Dict]:
        """Update an existing reservation"""
        try:
            # First, get the current reservation
            current = self.get_reservation(reservation_id)
            if not current:
                return None
            
            # Update the fields
            for key, value in update_data.items():
                if key in current:
                    current[key] = value
            
            # Update the timestamp
            current["updated_at"] = datetime.now().isoformat()
            
            # Update the document
            response = self.es.index(
                index=self.index_name,
                id=reservation_id,
                document=current,
                refresh=True
            )
            
            if response["result"] in ["updated", "created"]:
                return current
            else:
                raise Exception(f"Failed to update reservation: {response}")
        except Exception as e:
            print(f"Error updating reservation {reservation_id}: {e}")
            return None
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        """Cancel a reservation"""
        try:
            # Update the status to cancelled
            update_data = {"status": "cancelled"}
            result = self.update_reservation(reservation_id, update_data)
            return result is not None
        except Exception as e:
            print(f"Error cancelling reservation {reservation_id}: {e}")
            return False
    
    def list_user_reservations(self, user_id: Optional[str] = None) -> List[Dict]:
        """List all reservations for a user"""
        if user_id is None:
            user_id = self.default_user["user_id"]
        
        try:
            # Query for all reservations for this user
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user_id": user_id}}
                        ]
                    }
                },
                "sort": [
                    {"created_at": {"order": "desc"}}
                ]
            }
            
            response = self.es.search(
                index=self.index_name,
                body=query,
                size=100  # Limit to 100 reservations
            )
            
            # Extract the reservations from the response
            reservations = [hit["_source"] for hit in response["hits"]["hits"]]
            return reservations
        except Exception as e:
            print(f"Error listing reservations for user {user_id}: {e}")
            return []

# Define custom tools for reservation management
@tool
def book_hotel(hotel_name: str, check_in_date: str = None, check_out_date: str = None, 
                    num_guests: int = 2, room_type: str = "Deluxe") -> str:
    """Book a hotel reservation.
    
    Args:
        hotel_name: Name of the hotel to book
        check_in_date: Check-in date in YYYY-MM-DD format (defaults to 7 days from now)
        check_out_date: Check-out date in YYYY-MM-DD format (defaults to 10 days from now)
        num_guests: Number of guests
        room_type: Type of room to book
    
    Returns:
        Confirmation message with reservation details
    """
    # Get default dates if not provided
    today = datetime.now()
    if not check_in_date:
        check_in_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    if not check_out_date:
        check_out_date = (today + timedelta(days=10)).strftime("%Y-%m-%d")
    
    # Create a reservation with provided values
    hotel_data = {
        "hotel_id": f"hotel_{uuid.uuid4().hex[:8]}",
        "hotel_name": hotel_name,
        "room_type": room_type,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "num_guests": num_guests,
        "total_price": 450.00,
        "special_requests": "Late check-in, room with ocean view if possible"
    }
    
    try:
        reservation =  reservation_manager.create_reservation(hotel_data)
        
        return f"""✅ Hotel reservation confirmed!

Reservation ID: {reservation['reservation_id']}
Hotel: {reservation['hotel_name']}
Room Type: {reservation['room_type']}
Check-in: {reservation['check_in_date']}
Check-out: {reservation['check_out_date']}
Guests: {reservation['num_guests']}
Total Price: ${reservation['total_price']:.2f}
Status: {reservation['status'].capitalize()}

Your reservation has been confirmed. You can view or modify this reservation using the reservation ID.
"""
    except Exception as e:
        return f"❌ Failed to create reservation: {str(e)}"

@tool
def view_reservation(reservation_id: str) -> str:
    """View details of a specific reservation.
    
    Args:
        reservation_id: ID of the reservation to view
    
    Returns:
        Reservation details
    """
    try:
        reservation =  reservation_manager.get_reservation(reservation_id)
        
        if not reservation:
            return f"❌ Reservation with ID {reservation_id} not found."
        
        return f"""📋 Reservation Details:

Reservation ID: {reservation['reservation_id']}
Hotel: {reservation['hotel_name']}
Room Type: {reservation['room_type']}
Check-in: {reservation['check_in_date']}
Check-out: {reservation['check_out_date']}
Guests: {reservation['num_guests']}
Total Price: ${reservation['total_price']:.2f}
Status: {reservation['status'].capitalize()}
Payment Status: {reservation['payment_status'].capitalize()}
Special Requests: {reservation['special_requests'] or 'None'}
"""
    except Exception as e:
        return f"❌ Error retrieving reservation: {str(e)}"

@tool
def update_reservation(reservation_id: str, room_type: str = None, 
                           special_requests: str = None, total_price: float = None) -> str:
    """Update an existing reservation.
    
    Args:
        reservation_id: ID of the reservation to update
        room_type: New room type (optional)
        special_requests: New special requests (optional)
        total_price: New total price (optional)
    
    Returns:
        Updated reservation details
    """
    update_data = {}
    if room_type:
        update_data["room_type"] = room_type
    if special_requests:
        update_data["special_requests"] = special_requests
    if total_price:
        update_data["total_price"] = total_price
    
    try:
        updated =  reservation_manager.update_reservation(reservation_id, update_data)
        
        if not updated:
            return f"❌ Reservation with ID {reservation_id} not found or could not be updated."
        
        return f"""✅ Reservation Updated:

Reservation ID: {updated['reservation_id']}
Hotel: {updated['hotel_name']}
Room Type: {updated['room_type']} (Updated)
Check-in: {updated['check_in_date']}
Check-out: {updated['check_out_date']}
Guests: {updated['num_guests']}
Total Price: ${updated['total_price']:.2f} (Updated)
Status: {updated['status'].capitalize()}
Special Requests: {updated['special_requests']} (Updated)
"""
    except Exception as e:
        return f"❌ Error updating reservation: {str(e)}"

@tool
def cancel_reservation(reservation_id: str) -> str:
    """Cancel a reservation.
    
    Args:
        reservation_id: ID of the reservation to cancel
    
    Returns:
        Confirmation message
    """
    try:
        success =  reservation_manager.cancel_reservation(reservation_id)
        
        if not success:
            return f"❌ Reservation with ID {reservation_id} not found or could not be cancelled."
        
        return f"✅ Reservation {reservation_id} has been successfully cancelled."
    except Exception as e:
        return f"❌ Error cancelling reservation: {str(e)}"

@tool
def list_reservations() -> str:
    """List all reservations for the current user.
    
    Returns:
        List of reservations
    """
    try:
        reservations =  reservation_manager.list_user_reservations()
        
        if not reservations:
            return "You don't have any reservations yet."
        
        result = "📋 Your Reservations:\n\n"
        
        for i, res in enumerate(reservations, 1):
            result += f"{i}. {res['hotel_name']} - {res['check_in_date']} to {res['check_out_date']} - {res['status'].capitalize()}\n"
            result += f"   ID: {res['reservation_id']} | Room: {res['room_type']} | ${res['total_price']:.2f}\n\n"
        
        return result
    except Exception as e:
        return f"❌ Error retrieving reservations: {str(e)}"

@tool
def send_email(to_address: str, subject: str, body: str) -> str:
    """Send a plain text email using Amazon SES via boto3.
    
    Args:
        to_address: Email address of the recipient
        subject: Subject line of the email
        body: Plain text content of the email
    
    Returns:
        Confirmation message with the email status
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Create a new SES client
        ses_client = boto3.client(
            'ses',
            region_name=os.getenv('AWS_REGION', 'us-west-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Format the text body for better readability
        formatted_body = body.strip()
        
        # Ensure sections are properly separated with blank lines
        formatted_body = formatted_body.replace('\n\n\n', '\n\n')  # Remove excessive blank lines
        formatted_body = formatted_body.replace('\n', '\n\n')  # Add proper spacing between lines
        
        # Prepare the email message (plain text only)
        message = {
            'Subject': {
                'Data': subject
            },
            'Body': {
                'Text': {
                    'Data': formatted_body
                }
            }
        }
        
        # Send the email
        response = ses_client.send_email(
            Source=os.getenv('SENDER_EMAIL_ADDRESS'),
            Destination={
                'ToAddresses': [to_address]
            },
            Message=message,
            ReplyToAddresses=[os.getenv('REPLY_TO_EMAIL_ADDRESSES', os.getenv('SENDER_EMAIL_ADDRESS'))]
        )
        
        return f"✅ Email sent successfully to {to_address}! Message ID: {response['MessageId']}"
            
    except ClientError as e:
        error_message = e.response['Error']['Message']
        return f"❌ Failed to send email: {error_message}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

async def main():
    load_dotenv()
        
    # Get environment variables
    es_url = os.getenv("ES_URL")
    es_api_key = os.getenv("ES_API_KEY")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-west-2")
    sender_email = os.getenv("SENDER_EMAIL_ADDRESS")
    reply_to_email = os.getenv("REPLY_TO_EMAIL_ADDRESSES")
    aws_ses_mcp_server_path = os.getenv("AWS_SES_MCP_SERVER_PATH")
    weather_mcp_server_script_path = os.getenv("WEATHER_MCP_SERVER_SCRIPT_PATH")

    # Validate required environment variables
    if not es_url or not es_api_key:
        print("Error: ES_URL and ES_API_KEY must be set in the .env file")
        sys.exit(1)
    
    if not all([aws_access_key_id, aws_secret_access_key, sender_email]):
        print("Error: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and SENDER_EMAIL_ADDRESS must be set in the .env file")
        sys.exit(1)
    
    # Initialize Elasticsearch client
    es = Elasticsearch(
        hosts=[es_url],
        api_key=es_api_key
    )
    
    # Initialize the reservation manager (global for tools to use)
    global reservation_manager
    reservation_manager = HotelReservationManager(es)
    
    # Set up MCP clients
    weather_mcp = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="python",
                args=[weather_mcp_server_script_path]
            )
        )
    )
    
    elasticsearch_mcp = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="npx",
                args=["-y", "@elastic/mcp-server-elasticsearch"],
                env={
                    "ES_URL": es_url,
                    "ES_API_KEY": es_api_key
                }
            )
        )
    )

    aws_ses_mcp = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="node",
                args=[aws_ses_mcp_server_path],
                env={
                    "AWS_ACCESS_KEY_ID": aws_access_key_id,
                    "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
                    "AWS_REGION": aws_region,
                    "SENDER_EMAIL_ADDRESS": sender_email,
                    "REPLY_TO_EMAIL_ADDRESSES": reply_to_email or sender_email
                }
            )
        )
    )
    
    # Define custom reservation tools
    reservation_tools = [
        book_hotel,
        view_reservation,
        update_reservation,
        cancel_reservation,
        list_reservations,
        send_email
    ]
    MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0" # Using Claude 3.5 Sonnet
    
    model = BedrockModel (
        model_id=MODEL_ID,
        max_tokens=8000
    )

    # Initialize the MCP clients
    try:
        with weather_mcp, elasticsearch_mcp, aws_ses_mcp:
            #Get all the tools together here
            weather_tools = weather_mcp.list_tools_sync()
            elasticsearch_tools = elasticsearch_mcp.list_tools_sync()
            #ses_tools = aws_ses_mcp.list_tools_sync()
            all_tools = weather_tools + elasticsearch_tools + reservation_tools

            # Create the agent
            agent = Agent(
                system_prompt=SYSTEM_PROMPT,
                tools=all_tools,
                model=model
            )
        
            # Define exit command checker
            def is_exit_command(user_input: str) -> bool:
                # Clean up input
                cleaned_input = user_input.lower().strip()
                
                # Direct commands
                exit_commands = {'quit', 'exit'}
                
                # Semantic variations
                semantic_phrases = {
                    'i am done', 
                    'i am finished',
                    "i'm done",
                    "i'm finished"
                }
                
                return cleaned_input in exit_commands or cleaned_input in semantic_phrases
            
            print("\nWelcome to the Travel Advisory Assistant!")
            print("To exit, type 'quit', 'exit', 'I am done', or 'I am finished'")
            print("\n\nTravel Reservation and Advisory Prompts you can ask: ")
            print("- I am planning a trip to New York in 2 weeks. What's the weather like and are there any travel advisories?")
            print("- Which destinations in France can I consider to visit?") 
            print("- Are there any upcoming events in France that are interesting to consider for my travel?")
            print("- Any interesting events in Paris around next year.")
            print("- Can you give precise details of when Paris Fashion Week is happening?")
            print("- Find me some hotels in Paris that offer free breakfast")
            print("- When are rooms available for the Hôtel de Crillon (Rosewood) in Paris")
            print("- Book a hotel at Hôtel de Crillon (Rosewood)")
            print("- View my reservations")
            print("- Cancel my reservation")
            
            # Chat loop
            while True:
                try:
                    query = input("\nYou: ").strip()
                    if is_exit_command(query):
                        print("\nThank you for using the Travel Advisory Assistant. Goodbye!")
                        break
                    
                    print("\nAssistant:", end=" ")
                    response = agent(query)
                    print(response)
                    quit
                        
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    import traceback
                    traceback.print_exc()
    finally:
        # Clean up MCP clients
        print(" Thank You For Using Agentic AI capabilities from Amazon and Elastic")


if __name__ == "__main__":
    asyncio.run(main())
