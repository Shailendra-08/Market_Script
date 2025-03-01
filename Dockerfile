# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port (optional, if required for webhooks)
EXPOSE 8080

# Define environment variables (optional, if needed)
# ENV PROXY_URL="http://your_proxy_here:8080"

# Run the script when the container launches
CMD ["python", "deploy.py"]
