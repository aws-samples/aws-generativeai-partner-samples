"""
Real-world destination data for the Travel Advisory Application.
This module contains realistic destination information that will be used
to generate correlated data across all indices.
"""

# Real-world destinations with accurate information
REAL_DESTINATIONS = [
    {
        "city": "Paris",
        "country": "France",
        "continent": "Europe",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "description": "Known as the City of Light, Paris is famous for its iconic Eiffel Tower, world-class museums like the Louvre, and charming boulevards. The city offers exceptional cuisine, fashion, and a romantic atmosphere along the Seine River.",
        "best_season": "Spring",
        "climate": "Temperate",
        "language": "French",
        "currency": "EUR",
        "timezone": "Europe/Paris",
        "safety_rating": 8,
        "popularity_score": 95,
        "cost_level": "Luxury",
        "tags": ["Cultural", "Historical", "Romantic", "Urban", "Culinary"]
    },
    {
        "city": "Tokyo",
        "country": "Japan",
        "continent": "Asia",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "description": "Tokyo is a dynamic metropolis that blends ultramodern and traditional elements. From neon-lit skyscrapers and anime culture to historic temples and cherry blossoms, Tokyo offers visitors a unique blend of innovation and tradition.",
        "best_season": "Spring",
        "climate": "Temperate",
        "language": "Japanese",
        "currency": "JPY",
        "timezone": "Asia/Tokyo",
        "safety_rating": 9,
        "popularity_score": 90,
        "cost_level": "Luxury",
        "tags": ["Urban", "Cultural", "Culinary", "Shopping", "Technology"]
    },
    {
        "city": "New York",
        "country": "United States",
        "continent": "North America",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "description": "The Big Apple is a global center for media, culture, art, fashion, and finance. With iconic landmarks like Times Square, Central Park, and the Statue of Liberty, New York City offers endless entertainment options and diverse neighborhoods to explore.",
        "best_season": "Fall",
        "climate": "Continental",
        "language": "English",
        "currency": "USD",
        "timezone": "America/New_York",
        "safety_rating": 7,
        "popularity_score": 92,
        "cost_level": "Luxury",
        "tags": ["Urban", "Cultural", "Shopping", "Nightlife", "Culinary"]
    },
    {
        "city": "Rome",
        "country": "Italy",
        "continent": "Europe",
        "latitude": 41.9028,
        "longitude": 12.4964,
        "description": "The Eternal City is a living museum of ancient ruins, Renaissance art, and vibrant street life. From the Colosseum and Vatican City to charming piazzas and trattorias, Rome offers visitors a journey through history while enjoying la dolce vita.",
        "best_season": "Spring",
        "climate": "Mediterranean",
        "language": "Italian",
        "currency": "EUR",
        "timezone": "Europe/Rome",
        "safety_rating": 7,
        "popularity_score": 88,
        "cost_level": "Moderate",
        "tags": ["Historical", "Cultural", "Culinary", "Religious", "Urban"]
    },
    {
        "city": "Sydney",
        "country": "Australia",
        "continent": "Oceania",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "description": "Sydney is a vibrant harbor city known for its iconic Opera House, Harbour Bridge, and beautiful beaches. With a perfect blend of urban sophistication and natural beauty, Sydney offers visitors world-class dining, cultural experiences, and outdoor adventures.",
        "best_season": "Summer",
        "climate": "Temperate",
        "language": "English",
        "currency": "AUD",
        "timezone": "Australia/Sydney",
        "safety_rating": 9,
        "popularity_score": 85,
        "cost_level": "Luxury",
        "tags": ["Beach", "Urban", "Cultural", "Outdoor", "Relaxation"]
    },
    {
        "city": "Cape Town",
        "country": "South Africa",
        "continent": "Africa",
        "latitude": -33.9249,
        "longitude": 18.4241,
        "description": "Cape Town is a stunning coastal city nestled between mountains and the sea. With attractions like Table Mountain, Cape of Good Hope, and Robben Island, it offers a mix of natural beauty, wildlife, cultural diversity, and historical significance.",
        "best_season": "Summer",
        "climate": "Mediterranean",
        "language": "English",
        "currency": "ZAR",
        "timezone": "Africa/Johannesburg",
        "safety_rating": 6,
        "popularity_score": 80,
        "cost_level": "Moderate",
        "tags": ["Beach", "Mountain", "Cultural", "Outdoor", "Wildlife"]
    },
    {
        "city": "Rio de Janeiro",
        "country": "Brazil",
        "continent": "South America",
        "latitude": -22.9068,
        "longitude": -43.1729,
        "description": "Rio de Janeiro is famous for its stunning landscapes, vibrant culture, and festive atmosphere. From the iconic Christ the Redeemer statue and Copacabana Beach to samba music and Carnival celebrations, Rio offers visitors a lively and unforgettable experience.",
        "best_season": "Summer",
        "climate": "Tropical",
        "language": "Portuguese",
        "currency": "BRL",
        "timezone": "America/Sao_Paulo",
        "safety_rating": 5,
        "popularity_score": 82,
        "cost_level": "Moderate",
        "tags": ["Beach", "Mountain", "Cultural", "Nightlife", "Outdoor"]
    },
    {
        "city": "Bangkok",
        "country": "Thailand",
        "continent": "Asia",
        "latitude": 13.7563,
        "longitude": 100.5018,
        "description": "Bangkok is a vibrant city known for its ornate shrines, bustling street life, and boat-filled canals. The city offers a fascinating mix of traditional Thai culture, modern skyscrapers, exotic food, and vibrant nightlife.",
        "best_season": "Winter",
        "climate": "Tropical",
        "language": "Thai",
        "currency": "THB",
        "timezone": "Asia/Bangkok",
        "safety_rating": 7,
        "popularity_score": 85,
        "cost_level": "Budget",
        "tags": ["Cultural", "Urban", "Culinary", "Shopping", "Nightlife"]
    },
    {
        "city": "Barcelona",
        "country": "Spain",
        "continent": "Europe",
        "latitude": 41.3851,
        "longitude": 2.1734,
        "description": "Barcelona is a vibrant city known for its unique architecture, Mediterranean beaches, and rich cultural heritage. From Gaudí's masterpieces like Sagrada Familia to the Gothic Quarter and lively Las Ramblas, Barcelona offers a perfect blend of history, art, and coastal charm.",
        "best_season": "Spring",
        "climate": "Mediterranean",
        "language": "Spanish",
        "currency": "EUR",
        "timezone": "Europe/Madrid",
        "safety_rating": 7,
        "popularity_score": 87,
        "cost_level": "Moderate",
        "tags": ["Beach", "Cultural", "Historical", "Urban", "Culinary"]
    },
    {
        "city": "Dubai",
        "country": "United Arab Emirates",
        "continent": "Asia",
        "latitude": 25.2048,
        "longitude": 55.2708,
        "description": "Dubai is a city of superlatives, known for its ultramodern architecture, luxury shopping, and vibrant nightlife. From the world's tallest building, Burj Khalifa, to artificial islands and indoor ski slopes, Dubai showcases human innovation in the middle of the desert.",
        "best_season": "Winter",
        "climate": "Dry",
        "language": "Arabic",
        "currency": "AED",
        "timezone": "Asia/Dubai",
        "safety_rating": 9,
        "popularity_score": 86,
        "cost_level": "Luxury",
        "tags": ["Urban", "Shopping", "Luxury", "Desert", "Beach"]
    },
    {
        "city": "Kyoto",
        "country": "Japan",
        "continent": "Asia",
        "latitude": 35.0116,
        "longitude": 135.7681,
        "description": "Kyoto is Japan's cultural heart, famous for its classical Buddhist temples, gardens, imperial palaces, and traditional wooden houses. The city offers visitors a glimpse into Japan's rich history and traditions, from tea ceremonies to geisha culture.",
        "best_season": "Spring",
        "climate": "Temperate",
        "language": "Japanese",
        "currency": "JPY",
        "timezone": "Asia/Tokyo",
        "safety_rating": 9,
        "popularity_score": 84,
        "cost_level": "Moderate",
        "tags": ["Cultural", "Historical", "Religious", "Traditional", "Nature"]
    },
    {
        "city": "Amsterdam",
        "country": "Netherlands",
        "continent": "Europe",
        "latitude": 52.3676,
        "longitude": 4.9041,
        "description": "Amsterdam is known for its artistic heritage, elaborate canal system, and narrow houses with gabled facades. The city offers world-class museums like the Van Gogh Museum, historic sites like Anne Frank House, and a laid-back atmosphere with bicycle-friendly streets.",
        "best_season": "Spring",
        "climate": "Temperate",
        "language": "Dutch",
        "currency": "EUR",
        "timezone": "Europe/Amsterdam",
        "safety_rating": 8,
        "popularity_score": 83,
        "cost_level": "Moderate",
        "tags": ["Cultural", "Historical", "Urban", "Nightlife", "Romantic"]
    },
    {
        "city": "Marrakech",
        "country": "Morocco",
        "continent": "Africa",
        "latitude": 31.6295,
        "longitude": -7.9811,
        "description": "Marrakech is a magical place known for its medina, a medieval walled city with mazelike alleys. The city offers vibrant souks, stunning palaces, beautiful gardens, and a unique blend of Berber, Arab, and French cultural influences.",
        "best_season": "Spring",
        "climate": "Dry",
        "language": "Arabic",
        "currency": "MAD",
        "timezone": "Africa/Casablanca",
        "safety_rating": 7,
        "popularity_score": 79,
        "cost_level": "Budget",
        "tags": ["Cultural", "Historical", "Shopping", "Desert", "Exotic"]
    },
    {
        "city": "Vancouver",
        "country": "Canada",
        "continent": "North America",
        "latitude": 49.2827,
        "longitude": -123.1207,
        "description": "Vancouver is a bustling seaport known for its stunning natural beauty and cultural diversity. Surrounded by mountains and water, the city offers outdoor activities year-round, from skiing to kayaking, along with vibrant neighborhoods, parks, and cultural attractions.",
        "best_season": "Summer",
        "climate": "Temperate",
        "language": "English",
        "currency": "CAD",
        "timezone": "America/Vancouver",
        "safety_rating": 9,
        "popularity_score": 82,
        "cost_level": "Moderate",
        "tags": ["Outdoor", "Mountain", "Urban", "Nature", "Cultural"]
    },
    {
        "city": "Singapore",
        "country": "Singapore",
        "continent": "Asia",
        "latitude": 1.3521,
        "longitude": 103.8198,
        "description": "Singapore is a global financial center with a tropical climate and multicultural population. The city-state offers visitors futuristic architecture, lush gardens, luxury shopping, diverse cuisine, and a perfect blend of Chinese, Malay, Indian, and Western influences.",
        "best_season": "Year-round",
        "climate": "Tropical",
        "language": "English",
        "currency": "SGD",
        "timezone": "Asia/Singapore",
        "safety_rating": 10,
        "popularity_score": 84,
        "cost_level": "Luxury",
        "tags": ["Urban", "Cultural", "Culinary", "Shopping", "Modern"]
    },
    {
        "city": "Prague",
        "country": "Czech Republic",
        "continent": "Europe",
        "latitude": 50.0755,
        "longitude": 14.4378,
        "description": "Prague is a fairytale city known for its well-preserved medieval center. With its stunning castle, Charles Bridge, astronomical clock, and Gothic churches, the city offers visitors a journey through European history while enjoying Czech beer and culture.",
        "best_season": "Spring",
        "climate": "Continental",
        "language": "Czech",
        "currency": "CZK",
        "timezone": "Europe/Prague",
        "safety_rating": 8,
        "popularity_score": 85,
        "cost_level": "Budget",
        "tags": ["Historical", "Cultural", "Urban", "Romantic", "Architectural"]
    },
    {
        "city": "Bali",
        "country": "Indonesia",
        "continent": "Asia",
        "latitude": -8.3405,
        "longitude": 115.0920,
        "description": "Bali is a tropical paradise known for its forested volcanic mountains, iconic rice paddies, beaches, and coral reefs. The island offers visitors spiritual experiences at ancient temples, wellness retreats, surf spots, and a vibrant arts scene.",
        "best_season": "Summer",
        "climate": "Tropical",
        "language": "Indonesian",
        "currency": "IDR",
        "timezone": "Asia/Makassar",
        "safety_rating": 7,
        "popularity_score": 86,
        "cost_level": "Budget",
        "tags": ["Beach", "Cultural", "Spiritual", "Nature", "Relaxation"]
    },
    {
        "city": "Cairo",
        "country": "Egypt",
        "continent": "Africa",
        "latitude": 30.0444,
        "longitude": 31.2357,
        "description": "Cairo is a bustling city on the Nile River, known for its ancient Egyptian treasures. From the pyramids of Giza and the Sphinx to the Egyptian Museum and Islamic architecture, Cairo offers visitors a journey through thousands of years of human history.",
        "best_season": "Winter",
        "climate": "Dry",
        "language": "Arabic",
        "currency": "EGP",
        "timezone": "Africa/Cairo",
        "safety_rating": 6,
        "popularity_score": 78,
        "cost_level": "Budget",
        "tags": ["Historical", "Cultural", "Ancient", "Desert", "Religious"]
    },
    {
        "city": "Buenos Aires",
        "country": "Argentina",
        "continent": "South America",
        "latitude": -34.6037,
        "longitude": -58.3816,
        "description": "Buenos Aires is a sophisticated city known for its European atmosphere, passionate tango dancing, and vibrant cultural scene. With its wide boulevards, distinct neighborhoods, steakhouses, and soccer enthusiasm, the city offers a unique South American experience.",
        "best_season": "Spring",
        "climate": "Temperate",
        "language": "Spanish",
        "currency": "ARS",
        "timezone": "America/Argentina/Buenos_Aires",
        "safety_rating": 6,
        "popularity_score": 79,
        "cost_level": "Budget",
        "tags": ["Cultural", "Urban", "Culinary", "Nightlife", "Historical"]
    },
    {
        "city": "Istanbul",
        "country": "Turkey",
        "continent": "Europe",
        "latitude": 41.0082,
        "longitude": 28.9784,
        "description": "Istanbul is a transcontinental city straddling Europe and Asia across the Bosphorus Strait. With its Byzantine and Ottoman architecture, vibrant bazaars, and rich history as Constantinople, Istanbul offers visitors a unique blend of Eastern and Western influences.",
        "best_season": "Spring",
        "climate": "Mediterranean",
        "language": "Turkish",
        "currency": "TRY",
        "timezone": "Europe/Istanbul",
        "safety_rating": 6,
        "popularity_score": 83,
        "cost_level": "Budget",
        "tags": ["Historical", "Cultural", "Religious", "Shopping", "Culinary"]
    }
]

# Famous attractions for each destination
DESTINATION_ATTRACTIONS = {
    "Paris": [
        {"name": "Eiffel Tower", "type": "Monument", "description": "Iconic iron lattice tower on the Champ de Mars, named after engineer Gustave Eiffel.", "price_range": "$$", "duration_minutes": 120, "tags": ["Iconic", "Historical", "Romantic"]},
        {"name": "Louvre Museum", "type": "Museum", "description": "World's largest art museum and historic monument housing the Mona Lisa and Venus de Milo.", "price_range": "$$", "duration_minutes": 180, "tags": ["Art", "Historical", "Cultural"]},
        {"name": "Notre-Dame Cathedral", "type": "Religious Site", "description": "Medieval Catholic cathedral on the Île de la Cité known for its French Gothic architecture.", "price_range": "Free", "duration_minutes": 60, "tags": ["Religious", "Historical", "Architectural"]},
        {"name": "Montmartre", "type": "District", "description": "Hilltop district known for its artistic history, the Sacré-Cœur Basilica, and stunning city views.", "price_range": "Free", "duration_minutes": 120, "tags": ["Cultural", "Artistic", "Scenic"]},
        {"name": "Palace of Versailles", "type": "Palace", "description": "Opulent royal château that was the seat of power until the French Revolution.", "price_range": "$$", "duration_minutes": 240, "tags": ["Historical", "Royal", "Gardens"]}
    ],
    "Tokyo": [
        {"name": "Tokyo Skytree", "type": "Tower", "description": "Tallest tower in Japan offering panoramic views of the city.", "price_range": "$$", "duration_minutes": 90, "tags": ["Modern", "Scenic", "Architectural"]},
        {"name": "Senso-ji Temple", "type": "Temple", "description": "Ancient Buddhist temple in Asakusa, Tokyo's oldest temple.", "price_range": "Free", "duration_minutes": 60, "tags": ["Religious", "Historical", "Cultural"]},
        {"name": "Shibuya Crossing", "type": "Landmark", "description": "Famous scramble crossing known as the busiest intersection in the world.", "price_range": "Free", "duration_minutes": 30, "tags": ["Urban", "Iconic", "Photography"]},
        {"name": "Meiji Shrine", "type": "Shrine", "description": "Shinto shrine dedicated to Emperor Meiji and Empress Shoken, set in a forested area.", "price_range": "Free", "duration_minutes": 90, "tags": ["Religious", "Nature", "Peaceful"]},
        {"name": "Tokyo Disneyland", "type": "Theme Park", "description": "Disney theme park featuring attractions, entertainment, and Disney characters.", "price_range": "$$$", "duration_minutes": 480, "tags": ["Family-friendly", "Entertainment", "Fun"]}
    ],
    "New York": [
        {"name": "Statue of Liberty", "type": "Monument", "description": "Iconic neoclassical sculpture on Liberty Island, a symbol of freedom and democracy.", "price_range": "$$", "duration_minutes": 180, "tags": ["Iconic", "Historical", "Patriotic"]},
        {"name": "Central Park", "type": "Park", "description": "Urban park spanning 843 acres in the heart of Manhattan.", "price_range": "Free", "duration_minutes": 120, "tags": ["Nature", "Recreation", "Relaxation"]},
        {"name": "Empire State Building", "type": "Skyscraper", "description": "Iconic 102-story skyscraper offering panoramic views of the city.", "price_range": "$$$", "duration_minutes": 90, "tags": ["Iconic", "Scenic", "Architectural"]},
        {"name": "Metropolitan Museum of Art", "type": "Museum", "description": "One of the world's largest and finest art museums with over 2 million works.", "price_range": "$$", "duration_minutes": 180, "tags": ["Art", "Cultural", "Historical"]},
        {"name": "Broadway", "type": "Theater", "description": "Theater district known for its numerous theaters and world-class performances.", "price_range": "$$$", "duration_minutes": 180, "tags": ["Entertainment", "Cultural", "Performing Arts"]}
    ]
}

# Notable events for each destination
DESTINATION_EVENTS = {
    "Paris": [
        {"name": "Bastille Day", "type": "Festival", "description": "French National Day commemorating the Storming of the Bastille with fireworks and parades.", "start_date": "July 14", "end_date": "July 14", "local_significance": "High"},
        {"name": "Paris Fashion Week", "type": "Fashion", "description": "Major fashion event showcasing the latest collections from top designers.", "start_date": "Late September", "end_date": "Early October", "local_significance": "High"},
        {"name": "Roland-Garros French Open", "type": "Sports", "description": "Major tennis tournament held at the Stade Roland-Garros.", "start_date": "Late May", "end_date": "Early June", "local_significance": "High"}
    ],
    "Tokyo": [
        {"name": "Cherry Blossom Festival", "type": "Festival", "description": "Celebration of cherry blossoms with viewing parties and special events.", "start_date": "Late March", "end_date": "Early April", "local_significance": "High"},
        {"name": "Tokyo Game Show", "type": "Exhibition", "description": "Annual video game expo showcasing the latest games and technology.", "start_date": "Mid-September", "end_date": "Late September", "local_significance": "Medium"},
        {"name": "Sumida River Fireworks Festival", "type": "Festival", "description": "One of Tokyo's oldest and most famous fireworks displays.", "start_date": "Late July", "end_date": "Late July", "local_significance": "High"}
    ],
    "New York": [
        {"name": "New Year's Eve in Times Square", "type": "Celebration", "description": "Famous ball drop celebration attracting millions of visitors.", "start_date": "December 31", "end_date": "January 1", "local_significance": "High"},
        {"name": "Macy's Thanksgiving Day Parade", "type": "Parade", "description": "Annual parade featuring giant balloons, floats, and performances.", "start_date": "Thanksgiving Day", "end_date": "Thanksgiving Day", "local_significance": "High"},
        {"name": "US Open Tennis Championships", "type": "Sports", "description": "Major tennis tournament held at the USTA Billie Jean King National Tennis Center.", "start_date": "Late August", "end_date": "Early September", "local_significance": "High"}
    ]
}

# Famous hotels for each destination
DESTINATION_HOTELS = {
    "Paris": [
        {"name": "The Ritz Paris", "brand": "The Ritz", "star_rating": 5, "amenities": ["Pool", "Spa", "Restaurant", "Bar", "Concierge", "Room Service"]},
        {"name": "Four Seasons Hotel George V", "brand": "Four Seasons", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Business Center"]},
        {"name": "Hôtel Plaza Athénée", "brand": "Dorchester Collection", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Gym"]},
        {"name": "Le Meurice", "brand": "Dorchester Collection", "star_rating": 5, "amenities": ["Restaurant", "Bar", "Spa", "Room Service", "Concierge", "Business Center"]},
        {"name": "Hôtel de Crillon", "brand": "Rosewood", "star_rating": 5, "amenities": ["Pool", "Spa", "Restaurant", "Bar", "Room Service", "Concierge"]}
    ],
    "Tokyo": [
        {"name": "Park Hyatt Tokyo", "brand": "Hyatt", "star_rating": 5, "amenities": ["Pool", "Spa", "Restaurant", "Bar", "Gym", "Room Service"]},
        {"name": "The Ritz-Carlton Tokyo", "brand": "The Ritz-Carlton", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Business Center"]},
        {"name": "Mandarin Oriental Tokyo", "brand": "Mandarin Oriental", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Gym"]},
        {"name": "Aman Tokyo", "brand": "Aman", "star_rating": 5, "amenities": ["Pool", "Spa", "Restaurant", "Bar", "Room Service", "Concierge"]},
        {"name": "The Peninsula Tokyo", "brand": "Peninsula", "star_rating": 5, "amenities": ["Pool", "Spa", "Restaurant", "Bar", "Room Service", "Concierge"]}
    ],
    "New York": [
        {"name": "The Plaza", "brand": "Fairmont", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Business Center"]},
        {"name": "The St. Regis New York", "brand": "St. Regis", "star_rating": 5, "amenities": ["Restaurant", "Bar", "Spa", "Room Service", "Concierge", "Business Center"]},
        {"name": "Four Seasons Hotel New York", "brand": "Four Seasons", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Business Center"]},
        {"name": "The Ritz-Carlton New York, Central Park", "brand": "The Ritz-Carlton", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Room Service", "Concierge", "Business Center"]},
        {"name": "Mandarin Oriental, New York", "brand": "Mandarin Oriental", "star_rating": 5, "amenities": ["Spa", "Restaurant", "Bar", "Pool", "Room Service", "Concierge"]}
    ]
}

# Travel advisories for each country
COUNTRY_ADVISORIES = {
    "France": {
        "advisory_level": "Low",
        "description": "Exercise normal precautions in France. Some areas have increased risk.",
        "health_risks": "No major health risks. Healthcare system is excellent.",
        "safety_risks": "Petty crime in tourist areas. Occasional protests in major cities.",
        "entry_requirements": "Valid passport required. Visa not required for stays under 90 days for most nationalities.",
        "visa_required": False,
        "vaccination_required": ["None"]
    },
    "Japan": {
        "advisory_level": "Low",
        "description": "Exercise normal precautions in Japan.",
        "health_risks": "No major health risks. Healthcare system is excellent.",
        "safety_risks": "Low crime rate. Natural disasters such as earthquakes and typhoons may occur.",
        "entry_requirements": "Valid passport required. Visa requirements vary by nationality.",
        "visa_required": True,
        "vaccination_required": ["None"]
    },
    "United States": {
        "advisory_level": "Low",
        "description": "Exercise normal precautions in the United States.",
        "health_risks": "No major health risks. Healthcare system is excellent but expensive.",
        "safety_risks": "Crime rates vary by location. Check local advisories for specific cities.",
        "entry_requirements": "Valid passport required. ESTA or visa required depending on nationality.",
        "visa_required": True,
        "vaccination_required": ["None"]
    },
    "Italy": {
        "advisory_level": "Low",
        "description": "Exercise normal precautions in Italy.",
        "health_risks": "No major health risks. Healthcare system is good.",
        "safety_risks": "Petty crime in tourist areas. Occasional strikes affecting transportation.",
        "entry_requirements": "Valid passport required. Visa not required for stays under 90 days for most nationalities.",
        "visa_required": False,
        "vaccination_required": ["None"]
    },
    "Australia": {
        "advisory_level": "Low",
        "description": "Exercise normal precautions in Australia.",
        "health_risks": "Sun exposure and dehydration in summer months. Healthcare system is excellent.",
        "safety_risks": "Wildlife hazards in certain areas. Strong ocean currents at some beaches.",
        "entry_requirements": "Valid passport and visa or ETA required for all visitors.",
        "visa_required": True,
        "vaccination_required": ["None"]
    }
}

# Seasonal weather patterns for each destination
DESTINATION_WEATHER = {
    "Paris": {
        "Spring": {"high_celsius": 18, "low_celsius": 8, "precipitation_mm": 25, "condition": "Partly Cloudy"},
        "Summer": {"high_celsius": 25, "low_celsius": 15, "precipitation_mm": 20, "condition": "Sunny"},
        "Fall": {"high_celsius": 16, "low_celsius": 8, "precipitation_mm": 30, "condition": "Partly Cloudy"},
        "Winter": {"high_celsius": 8, "low_celsius": 2, "precipitation_mm": 25, "condition": "Cloudy"}
    },
    "Tokyo": {
        "Spring": {"high_celsius": 20, "low_celsius": 10, "precipitation_mm": 120, "condition": "Partly Cloudy"},
        "Summer": {"high_celsius": 30, "low_celsius": 22, "precipitation_mm": 150, "condition": "Rainy"},
        "Fall": {"high_celsius": 22, "low_celsius": 14, "precipitation_mm": 180, "condition": "Partly Cloudy"},
        "Winter": {"high_celsius": 12, "low_celsius": 2, "precipitation_mm": 60, "condition": "Sunny"}
    },
    "New York": {
        "Spring": {"high_celsius": 18, "low_celsius": 8, "precipitation_mm": 100, "condition": "Partly Cloudy"},
        "Summer": {"high_celsius": 29, "low_celsius": 20, "precipitation_mm": 110, "condition": "Sunny"},
        "Fall": {"high_celsius": 18, "low_celsius": 10, "precipitation_mm": 100, "condition": "Partly Cloudy"},
        "Winter": {"high_celsius": 5, "low_celsius": -3, "precipitation_mm": 90, "condition": "Snowy"}
    }
}
