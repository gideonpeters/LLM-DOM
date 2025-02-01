#!/bin/sh

# Start the HTTP server in the background
cd /app/extracted-doms/llm-modified
python -m http.server 8000 &

# Wait for a few seconds to ensure the server starts
sleep 5

# Change back to the root directory
cd /app

# # Run the report_generator.py script
# python report_generator.py