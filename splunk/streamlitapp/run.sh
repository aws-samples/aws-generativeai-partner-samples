#!/bin/bash

# Ensure we're in the correct directory
cd "$(dirname "$0")"

# Export environment variables from .env file if it exists
if [ -f .env ]; then
  echo "Loading environment variables from .env file"
  export $(grep -v '^#' .env | xargs)
else
  echo "Warning: .env file not found"
fi

# Run the Streamlit app
streamlit run app.py