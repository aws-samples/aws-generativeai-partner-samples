# kafka_data_simulator.py

import random
from datetime import datetime, timedelta
from typing import Dict, List
import json
import time
import os
from dotenv import load_dotenv
from faker import Faker
from confluent_kafka import Producer
import yfinance as yf
import numpy as np

# Load environment variables from .env file
load_dotenv()

class TradingDataSimulator:
    def __init__(self):
        self.faker = Faker()
        
        # Kafka configuration from environment variables
        SASL_USERNAME = os.getenv("CONFLUENT_CLOUD_API_KEY")
        SASL_PASSWORD = os.getenv("CONFLUENT_CLOUD_API_SECRET")
        SR_URL = os.getenv("SCHEMA_REGISTRY_ENDPOINT")
        SCHEMA_REGISTRY_API_KEY = os.getenv("SCHEMA_REGISTRY_API_KEY")
        SCHEMA_REGISTRY_API_SECRET = os.getenv("SCHEMA_REGISTRY_API_SECRET")
        BASIC_AUTH_USER_INFO = f"{SCHEMA_REGISTRY_API_KEY}:{SCHEMA_REGISTRY_API_SECRET}"
        BOOTSTRAP_URL = os.getenv("BOOTSTRAP_SERVERS")
        
        # Validate required environment variables
        if not all([SASL_USERNAME, SASL_PASSWORD, SR_URL, SCHEMA_REGISTRY_API_KEY, 
                   SCHEMA_REGISTRY_API_SECRET, BOOTSTRAP_URL]):
            raise ValueError("Missing required environment variables. Please check your .env file.")

        self.kafka_config = {
            'client.id': 'trading-data-simulator',
            "bootstrap.servers": BOOTSTRAP_URL,
            "sasl.mechanisms": "PLAIN",
            "security.protocol": "SASL_SSL",
            "session.timeout.ms": "45000",
            "sasl.username": SASL_USERNAME,
            "sasl.password": SASL_PASSWORD,
        }
        
        self.producer = Producer(self.kafka_config)
        
        # Trading data configuration
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA']
        self.exchanges = ['NYSE', 'NASDAQ', 'LSE', 'TSE']
        self.order_types = ['market', 'limit', 'stop', 'stop-limit']
        self.trade_sides = ['buy', 'sell']
        
        # Initialize base prices for symbols
        self.base_prices = self._initialize_base_prices()
        
    def _initialize_base_prices(self) -> Dict[str, float]:
        """Initialize realistic base prices for symbols"""
        base_prices = {}
        for symbol in self.symbols:
            # Get actual last closing price, fallback to random if failed
            try:
                ticker = yf.Ticker(symbol)
                base_prices[symbol] = ticker.info['previousClose']
            except:
                base_prices[symbol] = random.uniform(100, 1000)
        return base_prices

    def generate_market_data(self, symbol: str) -> Dict:
        """Generate realistic market data"""
        base_price = self.base_prices[symbol]
        price_change = random.uniform(-2, 2)
        current_price = base_price * (1 + price_change/100)
        
        return {
            'event_type': 'market-data',
            'symbol': symbol,
            'stampedtime': datetime.now().isoformat(),
            'price': round(current_price, 2),
            'volume': random.randint(100, 10000),
            'bid': round(current_price - 0.01, 2),
            'ask': round(current_price + 0.01, 2),
            'exchange': random.choice(self.exchanges),
            'volatility': abs(price_change),
        }

    def generate_trade_data(self, symbol: str) -> Dict:
        """Generate trade execution data"""
        price = self.base_prices[symbol] * (1 + random.uniform(-1, 1)/100)
        
        return {
            'event_type': 'trade',
            'trade_id': self.faker.uuid4(),
            'symbol': symbol,
            'stampedtime': datetime.now().isoformat(),
            'price': round(price, 2),
            'quantity': random.randint(1, 1000),
            'side': random.choice(self.trade_sides),
            'order_type': random.choice(self.order_types),
            'trader_id': self.faker.uuid4(),
            'execution_venue': random.choice(self.exchanges)
        }

    def generate_order_book_data(self, symbol: str) -> Dict:
        """Generate order book data"""
        base_price = self.base_prices[symbol]
        
        def generate_orders(side: str, base: float) -> List[Dict]:
            orders = []
            price_modifier = 1 if side == 'ask' else -1
            
            for i in range(5):  # Generate 5 levels
                price = base * (1 + (price_modifier * i * 0.001))
                orders.append({
                    'price': round(price, 2),
                    'quantity': random.randint(100, 5000)
                })
            return orders

        return {
            'event_type': 'order-book',
            'symbol': symbol,
            'stampedtime': datetime.now().isoformat(),
            'bids': generate_orders('bid', base_price),
            'asks': generate_orders('ask', base_price)
        }

    def produce_message(self, topic: str, data: Dict):
        """Produce message to Kafka topic"""
        try:
            self.producer.produce(
                topic,
                key=data['symbol'].encode('utf-8'),
                value=json.dumps(data).encode('utf-8'),
                callback=self.delivery_report
            )
            self.producer.poll(0)
        except Exception as e:
            print(f"Error producing message: {e}")

    def delivery_report(self, err, msg):
        """Callback for message delivery reports"""
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def simulate_data(self, interval: float = 1.0):
        """Main simulation loop"""
        try:
            while True:
                for symbol in self.symbols:
                    # Generate and send market data
                    market_data = self.generate_market_data(symbol)
                    self.produce_message('market_data', market_data)

                    # Generate and send trade data (with 30% probability)
                    if random.random() < 0.3:
                        trade_data = self.generate_trade_data(symbol)
                        self.produce_message('trades', trade_data)

                    # Generate and send order book data
                    order_book_data = self.generate_order_book_data(symbol)
                    self.produce_message('order_book', order_book_data)

                self.producer.flush()
                time.sleep(interval)

        except KeyboardInterrupt:
            print("Simulation stopped by user")
        finally:
            self.producer.flush()

if __name__ == "__main__":
    simulator = TradingDataSimulator()
    simulator.simulate_data()