#!/bin/bash

echo "Setting up a new virtual environment with compatible packages..."

# Create a new virtual environment
python -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt

echo "Setup complete! Activate the new environment with: source venv_new/bin/activate"
