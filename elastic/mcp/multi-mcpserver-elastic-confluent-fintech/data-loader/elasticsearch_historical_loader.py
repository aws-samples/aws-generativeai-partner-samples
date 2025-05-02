# elasticsearch_historical_loader.py

from datetime import datetime, timedelta
from typing import Dict, List
import random
import json
from faker import Faker
from elasticsearch import Elasticsearch, helpers, exceptions
import yfinance as yf
import pandas as pd
import numpy as np

class HistoricalDataLoader:
    def __init__(self):
        self.faker = Faker()
        
        # Elasticsearch configuration
        self.es = Elasticsearch(
            cloud_id="SecondDeployment:dXMtZWFzdC0xLmF3cy5mb3VuZC5pbyRiZWZmMTljZDdjMTQ0YzlmYjc3MWQzMjZjNjRiMWM4NyQwNTEwOTBiYTlkNzQ0ZDYyOTU1ZTkzMjJmZmNjYTAzMw==",
            api_key="elo5anc1RUI1Sm9wUklaYW5IX3A6ZnRpV2oxVVNRNE9NQU44VGljTFFSdw=="
        )
        
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA','ESTC']
        self.exchanges = ['NYSE', 'NASDAQ', 'LSE', 'TSE']
        
    def create_indices(self):
        """Create required indices with mappings"""
        mappings = {
            "market-data": {
                "properties": {
                    "symbol": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "price": {"type": "float"},
                    "volume": {"type": "long"},
                    "high": {"type": "float"},
                    "low": {"type": "float"},
                    "open": {"type": "float"},
                    "close": {"type": "float"},
                    "exchange": {"type": "keyword"},
                    "adjusted-close": {"type": "float"}
                }
            },
            "trading-metrics": {
                "properties": {
                    "symbol": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "volatility": {"type": "float"},
                    "rsi": {"type": "float"},
                    "ma-20": {"type": "float"},
                    "ma-50": {"type": "float"},
                    "volume-ma": {"type": "float"}
                }
            }
        }
        
        for index_name, mapping in mappings.items():
            try:
                # Check if the index exists
                self.es.indices.get(index=index_name)
                print(f"Index '{index_name}' already exists.")
            except exceptions.NotFoundError:
                # If the index doesn't exist, create it
                self.es.indices.create(
                    index=index_name,
                    mappings={"properties": mapping["properties"]},
                    settings={
                        "number_of_shards": 3,
                        "number_of_replicas": 1
                    }
                )
                print(f"Created index '{index_name}'.")
            except Exception as e:
                print(f"An error occurred while creating index '{index_name}': {e}")

    def fetch_historical_data(self, symbol: str, start_date: datetime) -> pd.DataFrame:
        """Fetch historical data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=datetime.now())
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Calculate Moving Averages
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        
        # Calculate Volatility (20-day standard deviation)
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        return df

    def generate_bulk_data(self, symbol: str, start_date: datetime) -> List[Dict]:
        """Generate bulk data for Elasticsearch"""
        df = self.fetch_historical_data(symbol, start_date)
        if df.empty:
            return []
        
        df = self.calculate_technical_indicators(df)
        
        bulk_data = []
        
        for index, row in df.iterrows():
            # Market Data
            market_data = {
                "_index": "market-data",
                "_source": {
                    "symbol": symbol,
                    "timestamp": index.isoformat(),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']),
                    "adjusted-close": float(row['Close']),
                    "exchange": random.choice(self.exchanges)
                }
            }
            
            # Trading Metrics
            trading_metrics = {
                "_index": "trading-metrics",
                "_source": {
                    "symbol": symbol,
                    "timestamp": index.isoformat(),
                    "volatility": float(row['Volatility']) if not np.isnan(row['Volatility']) else 0,
                    "rsi": float(row['RSI']) if not np.isnan(row['RSI']) else 50,
                    "ma-20": float(row['MA20']) if not np.isnan(row['MA20']) else float(row['Close']),
                    "ma-50": float(row['MA50']) if not np.isnan(row['MA50']) else float(row['Close']),
                    "volume-ma": float(row['Volume_MA']) if not np.isnan(row['Volume_MA']) else float(row['Volume'])
                }
            }
            
            bulk_data.extend([market_data, trading_metrics])
        
        return bulk_data

    def load_historical_data(self):
        """Main method to load historical data"""
        # Create indices if they don't exist
        self.create_indices()
        
        # Start date for historical data (e.g., 3 years ago)
        start_date = datetime.now() - timedelta(days=1095)
        
        for symbol in self.symbols:
            print(f"Processing historical data for {symbol}")
            bulk_data = self.generate_bulk_data(symbol, start_date)
            
            if bulk_data:
                try:
                    helpers.bulk(self.es, bulk_data)
                    print(f"Successfully loaded data for {symbol}")
                except Exception as e:
                    print(f"Error loading data for {symbol}: {e}")

if __name__ == "__main__":
    loader = HistoricalDataLoader()
    loader.load_historical_data()
