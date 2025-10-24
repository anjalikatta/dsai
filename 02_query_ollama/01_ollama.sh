#!/bin/bash

# 00_ollama.sh - Ollama Startup Script
# Serves Ollama on a specific port, pulls a small model, runs it, and provides stop controls
# 🛑🌐🤖📡🚀
# Load your local paths and variables
source .bashrc

# Configuration
PORT=11434  # Default Ollama port (change as needed)
# Set environment variable for port
export OLLAMA_HOST="0.0.0.0:$PORT"
MODEL="gemma3:latest"  # Small, reputable model (3.3GB)
SERVER_PID=""
MODEL_PID=""

# Start server in background, and assign the process ID to the SERVER_PID variable
ollama serve > /dev/null 2>&1 & SERVER_PID=$!
# View the process ID of ollama
echo $SERVER_PID

# Pull model of interest
# ollama pull $MODEL

# run model of interest interactively -- usually I don't want this
# ollama run $MODEL & MODEL_PID=$!
# echo $MODEL_PID

# Need to kill the server and model if they are running? These might help.
# kill $SERVER_PID 2>/dev/null
# pkill -f "ollama serve" 2>/dev/null
# pkill -f "ollama run" 2>/dev/null


# Test query the model
echo "Testing the model..."
test=$(curl -s -X POST http://localhost:$PORT/api/generate \
    -H "Content-Type: application/json" \
    -d '{
        "model": "'$MODEL'",
        "prompt": "Hello! Please respond with just: Model is working.",
        "stream": false
    }' 2>/dev/null)


# install jq for json parsing
# choco install jq 
# or for other systems... sudo apt-get install jq

# Use jq to extract the response text
echo "$test" | jq '.'

# Extract just some parts
echo "$test" | jq '.model, .response'


