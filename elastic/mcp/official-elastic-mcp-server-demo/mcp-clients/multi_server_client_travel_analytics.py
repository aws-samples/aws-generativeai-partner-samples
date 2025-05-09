import asyncio
import sys
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack
from dataclasses import dataclass
import os
import uuid
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# to interact with MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# to interact with Amazon Bedrock
import boto3

# to interact with Elasticsearch directly
from elasticsearch import Elasticsearch, helpers, exceptions

# Constants
MAX_TOKENS = 2000
MAX_TURNS = 15

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

## Example Interactions

**User:** "I'm planning a trip to Bali next month. What's the weather like and are there any travel advisories?"

**Assistant:** *[Uses Elasticsearch to query the weather and advisories indices for Bali]*

"Bali is expected to have average temperatures between 24-31°C next month with occasional afternoon showers. The current travel advisory level is Low, with some precautions recommended for certain areas. The Indonesian government requires a visa on arrival for most visitors, and it's recommended to have travel insurance that covers medical evacuation. Popular activities during this season include visiting temples, rice terraces, and beaches, though some beach areas may have stronger currents this time of year."

**User:** "Can you recommend some hotels in Paris with a view of the Eiffel Tower?"

**Assistant:** *[Uses Elasticsearch to query the hotels index for Paris hotels, possibly filtering by location or amenities]*

"I found several hotels in Paris with views of the Eiffel Tower:

1. Hotel Le Meurice (5-star) - $450/night, exceptional 4.8/5 rating
2. Shangri-La Hotel (5-star) - $520/night, with 4.7/5 rating
3. Hotel Balzac (4-star) - $320/night, with 4.3/5 rating
4. Citadines Tour Eiffel (3-star) - $210/night, with 4.0/5 rating

Would you like more details about any of these hotels or help with booking?"

**User:** "Show me my upcoming reservations"

**Assistant:** *[Uses Elasticsearch to query the reservations index for the user's upcoming reservations]*

"I found the following upcoming reservation for you:

Reservation at Shangri-La Hotel, Paris
Confirmation Code: CONF45678
Check-in: June 15, 2025
Check-out: June 20, 2025
Room Type: Deluxe Room with Eiffel Tower View
Guests: 2
Total Price: €2,600 (Paid)

Would you like to modify this reservation or see more details?"

**User:** "I'd like to book a hotel in Barcelona for next month"

**Assistant:** *[Uses Elasticsearch to check room availability in Barcelona]*

"I'd be happy to help you book a hotel in Barcelona. To find the best options for you, I need a few details:

1. What are your check-in and check-out dates?
2. How many guests will be staying?
3. Do you have any preferences for location (beach area, city center, etc.)?
4. What's your budget range per night?
5. Any specific amenities you're looking for (pool, spa, etc.)?

Once you provide these details, I can search for available hotels that match your criteria."

"""


@dataclass
class Message:
    role: str
    content: List[Dict[str, Any]]

    @classmethod
    def user(cls, text: str) -> 'Message':
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant(cls, text: str) -> 'Message':
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def tool_result(cls, tool_use_id: str, content: List[Dict]) -> 'Message':
        return cls(
            role="user",
            content=[{
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": content
                }
            }]
        )

    @classmethod
    def tool_request(cls, tool_use_id: str, name: str, input_data: dict) -> 'Message':
        return cls(
            role="assistant",
            content=[{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": name,
                    "input": input_data
                }
            }]
        )

    @staticmethod
    def to_bedrock_format(tools_list: List[Dict]) -> List[Dict]:
        return [{
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": tool["input_schema"]["properties"],
                        "required": tool["input_schema"].get("required", [])
                    }
                }
            }
        } for tool in tools_list]


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
    
    async def create_reservation(self, hotel_data: Dict) -> Dict:
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
    
    async def get_reservation(self, reservation_id: str) -> Optional[Dict]:
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
    
    async def update_reservation(self, reservation_id: str, update_data: Dict) -> Optional[Dict]:
        """Update an existing reservation"""
        try:
            # First, get the current reservation
            current = await self.get_reservation(reservation_id)
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
    
    async def cancel_reservation(self, reservation_id: str) -> bool:
        """Cancel a reservation"""
        try:
            # Update the status to cancelled
            update_data = {"status": "cancelled"}
            result = await self.update_reservation(reservation_id, update_data)
            return result is not None
        except Exception as e:
            print(f"Error cancelling reservation {reservation_id}: {e}")
            return False
    
    async def list_user_reservations(self, user_id: Optional[str] = None) -> List[Dict]:
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


class MultiServerMCPClient:
    MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')
        self.all_tools = {}
        self.server_configs = {}
        
        # Initialize Elasticsearch client
        es_url = os.getenv("ES_URL")
        es_api_key = os.getenv("ES_API_KEY")
        
        if not es_url or not es_api_key:
            raise ValueError("ES_URL and ES_API_KEY must be set in the .env file")
        
        self.es = Elasticsearch(
            hosts=[es_url],
            api_key=es_api_key
        )
        
        # Initialize the reservation manager
        self.reservation_manager = HotelReservationManager(self.es)

    async def connect_to_servers(self, server_configs: Dict[str, Dict]):
        """Connect to multiple MCP servers"""
        self.server_configs = server_configs
        for server_name, config in server_configs.items():
            await self.connect_to_server(server_name, config)
        
        print(f"\nConnected to {len(self.sessions)} servers with {len(self.all_tools)} total tools")
        for server, tools in self.all_tools.items():
            print(f"- {server}: {[tool.name for tool in tools]}")

    async def connect_to_server(self, server_name: str, config: Dict):
        """Connect to an MCP server using the provided configuration"""
        if "command" not in config:
            raise ValueError(f"Invalid server configuration for {server_name}: missing 'command'")

        server_params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env", None)
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        response = await session.list_tools()
        print(f"\nConnected to {server_name} with tools:", [tool.name for tool in response.tools])
        
        self.sessions[server_name] = session
        self.all_tools[server_name] = response.tools

    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return self.bedrock.converse(
            modelId=self.MODEL_ID,
            messages=messages,
            inferenceConfig={
                "maxTokens": MAX_TOKENS,
                "temperature": 0.7,
                "topP": 0.9,
            },
            toolConfig={"tools": tools}
        )

    async def process_query(self, query: str) -> str:
        # Check if this is a reservation-related command
        if query.lower().startswith("book hotel"):
            return await self._handle_book_hotel(query)
        elif query.lower().startswith("view reservation"):
            return await self._handle_view_reservation(query)
        elif query.lower().startswith("update reservation"):
            return await self._handle_update_reservation(query)
        elif query.lower().startswith("cancel reservation"):
            return await self._handle_cancel_reservation(query)
        elif query.lower() == "my reservations":
            return await self._handle_list_reservations()
        
        # If not a reservation command, process normally with the LLM
        messages = [
            Message.user(SYSTEM_PROMPT).__dict__,
            Message.user(query).__dict__
        ]
        
        available_tools = []
        for server_name, tools in self.all_tools.items():
            for tool in tools:
                tool_info = {
                    "name": f"{tool.name}",
                    "server": server_name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                
                if "required" not in tool_info["input_schema"]:
                    tool_info["input_schema"]["required"] = []
                    if tool_info["input_schema"]["properties"]:
                        first_param = next(iter(tool_info["input_schema"]["properties"]))
                        tool_info["input_schema"]["required"] = [first_param]
                
                available_tools.append(tool_info)

        bedrock_tools = Message.to_bedrock_format(available_tools)
        response = self._make_bedrock_request(messages, bedrock_tools)
        
        return await self._process_response(response, messages, bedrock_tools, available_tools)

    async def _handle_book_hotel(self, query: str) -> str:
        """Handle the book hotel command"""
        # Parse the query to extract hotel booking details
        # For demo purposes, we'll use some default values
        today = datetime.now()
        check_in = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        check_out = (today + timedelta(days=10)).strftime("%Y-%m-%d")
        
        # Extract hotel name from query if provided
        hotel_name = "Seaside Resort"  # Default
        if "at" in query.lower():
            parts = query.lower().split("at")
            if len(parts) > 1 and parts[1].strip():
                hotel_name = parts[1].strip().title()
        
        # Create a reservation with default values
        hotel_data = {
            "hotel_id": f"hotel_{uuid.uuid4().hex[:8]}",
            "hotel_name": hotel_name,
            "room_type": "Deluxe",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "num_guests": 2,
            "total_price": 450.00,
            "special_requests": "Late check-in, room with ocean view if possible"
        }
        
        try:
            reservation = await self.reservation_manager.create_reservation(hotel_data)
            
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

    async def _handle_view_reservation(self, query: str) -> str:
        """Handle the view reservation command"""
        # Extract reservation ID from query
        parts = query.split()
        if len(parts) < 3:
            return "❌ Please provide a reservation ID. Example: view reservation abc123"
        
        reservation_id = parts[2]
        
        try:
            reservation = await self.reservation_manager.get_reservation(reservation_id)
            
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

    async def _handle_update_reservation(self, query: str) -> str:
        """Handle the update reservation command"""
        # Extract reservation ID from query
        parts = query.split()
        if len(parts) < 3:
            return "❌ Please provide a reservation ID. Example: update reservation abc123"
        
        reservation_id = parts[2]
        
        # For demo purposes, we'll update the room type and special requests
        update_data = {
            "room_type": "Premium Suite",
            "special_requests": "Early check-in, champagne in room",
            "total_price": 650.00  # Updated price for the premium suite
        }
        
        try:
            updated = await self.reservation_manager.update_reservation(reservation_id, update_data)
            
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

    async def _handle_cancel_reservation(self, query: str) -> str:
        """Handle the cancel reservation command"""
        # Extract reservation ID from query
        parts = query.split()
        if len(parts) < 3:
            return "❌ Please provide a reservation ID. Example: cancel reservation abc123"
        
        reservation_id = parts[2]
        
        try:
            success = await self.reservation_manager.cancel_reservation(reservation_id)
            
            if not success:
                return f"❌ Reservation with ID {reservation_id} not found or could not be cancelled."
            
            return f"✅ Reservation {reservation_id} has been successfully cancelled."
        except Exception as e:
            return f"❌ Error cancelling reservation: {str(e)}"

    async def _handle_list_reservations(self) -> str:
        """Handle the my reservations command"""
        try:
            reservations = await self.reservation_manager.list_user_reservations()
            
            if not reservations:
                return "You don't have any reservations yet."
            
            result = "📋 Your Reservations:\n\n"
            
            for i, res in enumerate(reservations, 1):
                result += f"{i}. {res['hotel_name']} - {res['check_in_date']} to {res['check_out_date']} - {res['status'].capitalize()}\n"
                result += f"   ID: {res['reservation_id']} | Room: {res['room_type']} | ${res['total_price']:.2f}\n\n"
            
            return result
        except Exception as e:
            return f"❌ Error retrieving reservations: {str(e)}"

    async def _process_response(
        self, 
        response: Dict, 
        messages: List[Dict], 
        bedrock_tools: List[Dict],
        available_tools: List[Dict]
    ) -> str:
        final_text = []
        turn_count = 0
        tool_to_server = {tool["name"]: tool["server"] for tool in available_tools}
        
        try:
            while turn_count < MAX_TURNS:
                if response['stopReason'] == 'tool_use':
                    for item in response['output']['message']['content']:
                        if 'text' in item:
                            thinking_text = item['text']
                            final_text.append(f"[Thinking: {thinking_text}]")
                        
                        elif 'toolUse' in item:
                            tool_info = item['toolUse']
                            tool_name = tool_info['name']
                            
                            server_name = tool_to_server.get(tool_name)
                            if not server_name:
                                error_msg = f"Tool {tool_name} not found in any connected server"
                                final_text.append(f"[ERROR: {error_msg}]")
                                return "\n".join(final_text)
                            
                            tool_result, messages = await self._handle_tool_call(
                                server_name, 
                                tool_info, 
                                messages
                            )
                            final_text.extend(tool_result)
                            
                            response = self._make_bedrock_request(messages, bedrock_tools)
                            turn_count += 1
                            break
                    
                else:  # For non-tool_use responses
                    if 'output' in response and 'message' in response['output']:
                        response_text = response['output']['message']['content'][0]['text']
                        final_text.append(response_text)
                    return "\n".join(final_text)

            if turn_count >= MAX_TURNS:
                final_text.append("\n[Maximum conversation turns reached.]")
                
            return "\n".join(final_text)
            
        except Exception as e:
            import traceback
            final_text.append(f"\n[Error processing response: {str(e)}]")
            final_text.append(traceback.format_exc())
            return "\n".join(final_text)

    async def _handle_tool_call(
        self, 
        server_name: str, 
        tool_info: Dict, 
        messages: List[Dict]
    ) -> tuple[List[str], List[Dict]]:
        """Handle a tool call and return the results and updated messages"""
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        session = self.sessions[server_name]
        result = await session.call_tool(tool_name, tool_args)

        tool_result_content = [{"json": {"text": content.text}} for content in result.content if content.text]

        tool_request = Message.tool_request(tool_use_id, tool_name, tool_args)
        tool_result = Message.tool_result(tool_use_id, tool_result_content)
        
        messages.append(tool_request.__dict__)
        messages.append(tool_result.__dict__)
        
        formatted_result = [
            f"[Calling tool {tool_name} on server {server_name} with args {tool_args}]",
            f"[Tool {tool_name} returned: {result.content[0].text if result.content else 'No content'}]"
        ]
        
        return formatted_result, messages

    async def chat_loop(self):
        print("\nWelcome to the Multi-Server MCP Chat!")
        print("Type 'quit' to exit or your query.")
        print("\nReservation Commands:")
        print("- book hotel: Create a new hotel reservation")
        print("- view reservation [id]: View details of a specific reservation")
        print("- update reservation [id]: Update an existing reservation")
        print("- cancel reservation [id]: Cancel a reservation")
        print("- my reservations: List all reservations for the current user")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                if query.lower() == 'quit':
                    break
                
                print("\nAssistant:", end=" ")
                response = await self.process_query(query)
                print(response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python multi_server_client.py <weather_server_script>")
        sys.exit(1)

    weather_script = sys.argv[1]
    
    es_url = os.getenv("ES_URL")
    es_api_key = os.getenv("ES_API_KEY")

    if not es_url or not es_api_key:
        print("Error: ES_URL and ES_API_KEY must be set in the .env file")
        sys.exit(1)

    server_configs = {
        "weather": {
            "command": "python",
            "args": [weather_script],
            "env": None
        },
        "elasticsearch-mcp-server": {
            "command": "npx",
            "args": ["-y", "@elastic/mcp-server-elasticsearch"],
            "env": {
                "ES_URL": es_url,
                "ES_API_KEY": es_api_key
            }
        }
    }

    client = MultiServerMCPClient()
    try:
        await client.connect_to_servers(server_configs)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())