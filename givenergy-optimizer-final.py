#!/usr/bin/env python3
import os
import logging
import json
import time
from datetime import datetime, timedelta
import requests
import schedule
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('givenergy-optimizer')

# Configuration from environment variables
GIVENERGY_API_KEY = os.environ.get('GIVENERGY_API_KEY')
GIVENERGY_SYSTEM_ID = os.environ.get('GIVENERGY_SYSTEM_ID')  # Communication device ID (e.g., WO2227G735)
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
LOCATION_LAT = os.environ.get('LOCATION_LAT')
LOCATION_LON = os.environ.get('LOCATION_LON')
TIMEZONE = os.environ.get('TIMEZONE', 'Europe/London')
MIN_BATTERY_LEVEL = float(os.environ.get('MIN_BATTERY_LEVEL', '20.0'))
CHARGE_THRESHOLD = float(os.environ.get('CHARGE_THRESHOLD', '3.0'))

# GivEnergy API endpoints
GIVENERGY_BASE_URL = 'https://api.givenergy.cloud/v1'

class GivEnergyWeatherOptimizer:
    def __init__(self):
        self.timezone = pytz.timezone(TIMEZONE)
        self.validate_config()
        self.inverter_serial = None
        self.get_inverter_serial()
        logger.info(f"GivEnergy Weather Optimizer initialized with inverter serial: {self.inverter_serial}")

    def validate_config(self):
        """Validate that all required configuration is present"""
        missing_vars = []
        for var in ['GIVENERGY_API_KEY', 'GIVENERGY_SYSTEM_ID', 'WEATHER_API_KEY', 'LOCATION_LAT', 'LOCATION_LON']:
            if not globals().get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def get_givenergy_headers(self):
        """Get the headers required for GivEnergy API calls"""
        return {
            'Authorization': f'Bearer {GIVENERGY_API_KEY}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def get_inverter_serial(self):
        """Get the inverter serial number from the communication device information"""
        try:
            # Based on API spec, this is the endpoint to get communication device info
            url = f"{GIVENERGY_BASE_URL}/communication-device/{GIVENERGY_SYSTEM_ID}"
            logger.info(f"Getting inverter serial from: {url}")
            
            response = requests.get(url, headers=self.get_givenergy_headers())
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'inverter' in data['data'] and 'serial' in data['data']['inverter']:
                    self.inverter_serial = data['data']['inverter']['serial']
                    logger.info(f"Found inverter serial: {self.inverter_serial}")
                else:
                    logger.error(f"Could not find inverter serial in response: {json.dumps(data)}")
                    raise ValueError("Inverter serial not found in API response")
            else:
                logger.error(f"Error getting communication device info: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to get communication device info: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting inverter serial: {e}")
            raise
    
    def get_battery_status(self):
        """Get the current battery status from the GivEnergy API"""
        if not self.inverter_serial:
            logger.error("Cannot get battery status without inverter serial")
            return None
            
        try:
            # Based on API spec, this is the endpoint to get latest system data
            url = f"{GIVENERGY_BASE_URL}/inverter/{self.inverter_serial}/system-data/latest"
            logger.info(f"Getting battery status from: {url}")
            
            response = requests.get(url, headers=self.get_givenergy_headers())
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                # Extract battery information according to the API spec format
                if 'battery' in data and 'percent' in data['battery']:
                    battery_level = data['battery']['percent']
                    battery_power = data['battery'].get('power', 0)
                    solar_power = data.get('solar', {}).get('power', 0)
                    
                    logger.info(f"Current battery level: {battery_level}%")
                    return {
                        'battery_level': battery_level,
                        'battery_power': battery_power,
                        'solar_power': solar_power,
                        'timestamp': data.get('time')
                    }
                else:
                    logger.error(f"Could not find battery data in response: {json.dumps(data)}")
            else:
                logger.error(f"Error getting battery status: {response.status_code} - {response.text}")
            
            return None
        except Exception as e:
            logger.error(f"Error getting battery status: {e}")
            return None

    def get_weather_forecast(self):
        """Get weather forecast for the next 24 hours"""
        try:
            params = {
                'lat': LOCATION_LAT,
                'lon': LOCATION_LON,
                'appid': WEATHER_API_KEY,
                'units': 'metric'  # Use metric units
            }
            response = requests.get('https://api.openweathermap.org/data/2.5/forecast', params=params)
            response.raise_for_status()
            forecast_data = response.json()
            
            # Process forecast data to extract useful information
            processed_forecast = []
            for item in forecast_data.get('list', [])[:8]:  # Get next 24 hours (3-hour intervals)
                dt = datetime.fromtimestamp(item['dt'], self.timezone)
                clouds = item['clouds']['all']  # Cloud coverage in percentage
                weather_main = item['weather'][0]['main']
                weather_desc = item['weather'][0]['description']
                
                processed_forecast.append({
                    'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'clouds': clouds,
                    'weather': weather_main,
                    'description': weather_desc,
                    'temperature': item['main']['temp'],
                })
            
            logger.info(f"Weather forecast retrieved for next 24 hours")
            return processed_forecast
        except Exception as e:
            logger.error(f"Error getting weather forecast: {e}")
            return None

    def estimate_solar_generation(self, forecast):
        """Estimate potential solar generation based on weather forecast"""
        if not forecast:
            return []
        
        # Simple model: clear sky = good generation, cloudy = reduced generation
        estimates = []
        for entry in forecast:
            dt = datetime.strptime(entry['datetime'], '%Y-%m-%d %H:%M:%S')
            hour = dt.hour
            
            # Adjust for daylight hours (simplified)
            daylight_factor = 0
            if 6 <= hour < 20:  # Daylight hours approximation
                # Peak sun hours are typically around noon
                daylight_factor = 1.0 - (abs(hour - 13) / 7)
            
            # Adjust for cloud coverage
            cloud_factor = 1.0 - (entry['clouds'] / 100.0)
            
            # Estimated kWh for this 3-hour period
            # This would need calibration based on your system's capacity
            estimated_kwh = daylight_factor * cloud_factor * 3.0  # Assuming 3kWh maximum per hour
            
            estimates.append({
                'datetime': entry['datetime'],
                'estimated_kwh': max(0, estimated_kwh),
                'clouds': entry['clouds'],
                'weather': entry['weather']
            })
        
        return estimates

    def decide_charging_strategy(self):
        """Decide on the battery charging strategy based on forecasts"""
        battery_status = self.get_battery_status()
        if not battery_status:
            logger.error("Cannot decide charging strategy without battery status")
            return
        
        forecast = self.get_weather_forecast()
        if not forecast:
            logger.error("Cannot decide charging strategy without weather forecast")
            return
        
        generation_estimates = self.estimate_solar_generation(forecast)
        
        # Calculate total estimated generation for tomorrow
        total_estimated_generation = sum(e['estimated_kwh'] for e in generation_estimates)
        logger.info(f"Estimated solar generation for next 24h: {total_estimated_generation:.2f} kWh")
        
        current_battery_level = battery_status['battery_level']
        
        if total_estimated_generation < CHARGE_THRESHOLD and current_battery_level < MIN_BATTERY_LEVEL:
            logger.info(f"Low solar generation expected ({total_estimated_generation:.2f} kWh) and battery level is low ({current_battery_level}%). Scheduling overnight charge.")
            self.schedule_overnight_charge()
        else:
            logger.info(f"Sufficient solar generation expected ({total_estimated_generation:.2f} kWh) or battery level is sufficient ({current_battery_level}%). No overnight charge needed.")
            self.cancel_overnight_charge()
    
    def schedule_overnight_charge(self):
        """Schedule battery charging during off-peak hours using the preset API"""
        if not self.inverter_serial:
            logger.error("Cannot schedule charging without inverter serial")
            return False
            
        try:
            # Get tomorrow's date in the format expected by the API
            tomorrow = (datetime.now(self.timezone) + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Define charge window (typically during off-peak hours)
            charge_start = "01:30:00"
            charge_end = "05:30:00"
            
            # Based on API spec, we should use the preset API for timed-charge
            url = f"{GIVENERGY_BASE_URL}/inverter/{self.inverter_serial}/presets/timed-charge"
            logger.info(f"Scheduling charge with URL: {url}")
            
            # Prepare the payload according to the API spec format for timed-charge preset
            payload = {
                "enabled": True,
                "slots": [
                    {
                        "start_time": charge_start[:5],  # HH:MM format
                        "end_time": charge_end[:5],      # HH:MM format
                        "percent_limit": 100             # Target battery percentage
                    }
                ]
            }
            
            logger.info(f"Scheduling charge with payload: {json.dumps(payload)}")
            response = requests.post(url, headers=self.get_givenergy_headers(), json=payload)
            
            # Both 200 and 201 are success responses
            if response.status_code in [200, 201]:
                logger.info(f"Successfully scheduled overnight charge from {charge_start} to {charge_end} for tomorrow")
                return True
            else:
                logger.error(f"Error scheduling overnight charge: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error scheduling overnight charge: {e}")
            return False
    
    def cancel_overnight_charge(self):
        """Cancel any scheduled overnight charging"""
        if not self.inverter_serial:
            logger.error("Cannot cancel charging without inverter serial")
            return False
            
        try:
            # Based on API spec, we should use the preset API for timed-charge with enabled=false
            url = f"{GIVENERGY_BASE_URL}/inverter/{self.inverter_serial}/presets/timed-charge"
            logger.info(f"Cancelling charge with URL: {url}")
            
            # Prepare the payload to disable timed charging
            # Note: API requires at least one slot, even when disabled
            payload = {
                "enabled": False,
                "slots": [
                    {
                        "start_time": "00:00",
                        "end_time": "00:00",
                        "percent_limit": 100
                    }
                ]
            }
            
            logger.info(f"Cancelling charge with payload: {json.dumps(payload)}")
            response = requests.post(url, headers=self.get_givenergy_headers(), json=payload)
            
            # Both 200 and 201 are success responses
            if response.status_code in [200, 201]:
                logger.info(f"Successfully cancelled overnight charge for tomorrow")
                return True
            else:
                logger.error(f"Error cancelling overnight charge: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling overnight charge: {e}")
            return False

    def run_daily_check(self):
        """Run the daily check to plan charging for the next night"""
        logger.info("Running daily battery optimization check")
        self.decide_charging_strategy()

    def start(self):
        """Start the optimizer service with scheduled runs"""
        logger.info("Starting GivEnergy Weather Optimizer service")
        
        # Run immediately on startup
        self.run_daily_check()
        
        # Schedule daily runs
        schedule.every().day.at("17:00").do(self.run_daily_check)  # Check in the late afternoon
        
        # Main loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for scheduled tasks


if __name__ == "__main__":
    try:
        optimizer = GivEnergyWeatherOptimizer()
        optimizer.start()
    except Exception as e:
        logger.error(f"Error starting optimizer: {e}")
        raise