FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY givenergy-optimizer-final.py optimizer.py

# Set environment variables (these will be overridden by Docker run command)
ENV GIVENERGY_API_KEY=""
ENV GIVENERGY_SYSTEM_ID=""
ENV WEATHER_API_KEY=""
ENV LOCATION_LAT=""
ENV LOCATION_LON=""
ENV TIMEZONE="Europe/London"
ENV MIN_BATTERY_LEVEL="20.0"
ENV CHARGE_THRESHOLD="3.0"

# Run the application
CMD ["python", "optimizer.py"]