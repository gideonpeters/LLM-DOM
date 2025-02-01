# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Install Node.js and npm
RUN apt-get update && apt-get install -y nodejs npm chromium

# Install Lighthouse globally using npm
RUN npm install -g lighthouse

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# # Copy the entrypoint script into the container
# COPY entrypoint.sh /app/entrypoint.sh

# # Make the entrypoint script executable
# RUN chmod +x /app/entrypoint.sh

# # Use the entrypoint script to start the HTTP server and run report_generator.py
# ENTRYPOINT ["/app/entrypoint.sh"]