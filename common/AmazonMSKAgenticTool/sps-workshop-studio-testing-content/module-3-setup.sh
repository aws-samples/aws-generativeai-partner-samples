#!/bin/bash

# Exit on error
set -e

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements from mod3_requirements.txt..."
pip install --no-cache-dir -r mod3_requirements.txt

echo "Deactivating virtual environment..."
deactivate

echo "Setup complete! Virtual environment created in './venv'"
echo "To activate it later, run: source venv/bin/activate"