# GivEnergy Weather-Based Battery Optimizer

This application is designed to optimize your GivEnergy battery charging based on weather forecasts. It checks the weather forecast and your current battery level, then decides whether to schedule overnight charging during off-peak hours.

## How It Works

The application follows this workflow:

1. **Retrieves your inverter details** using your GivEnergy communication device ID
2. **Checks your battery's current status** (charge level, power flow)
3. **Gets weather forecast data** for your location
4. **Estimates potential solar generation** based on cloud cover and time of day
5. **Makes a charging decision**:
   - If expected solar generation is below threshold AND battery level is low: Schedules overnight charging
   - Otherwise: Cancels any scheduled charging to prioritize solar charging

## Requirements

- A GivEnergy battery system with API access
- A GivEnergy API key
- An OpenWeatherMap API key (free tier works fine)
- Docker installed on your Synology NAS

## Configuration

The application uses environment variables for configuration, which are set in the `docker-compose.yml` file:

- `GIVENERGY_API_KEY`: Your GivEnergy API key
- `GIVENERGY_SYSTEM_ID`: Your GivEnergy communication device ID (e.g., WO2227G735)
- `WEATHER_API_KEY`: Your OpenWeatherMap API key
- `LOCATION_LAT`: Your location's latitude
- `LOCATION_LON`: Your location's longitude
- `TIMEZONE`: Your local timezone (e.g., Europe/London)
- `MIN_BATTERY_LEVEL`: Minimum battery level (%) to trigger charging (default: 20.0)
- `CHARGE_THRESHOLD`: Expected solar generation threshold in kWh (default: 3.0)

## Installation

1. Create a directory on your Synology NAS for this application
2. Save these files to the directory:
   - `givenergy-optimizer-final.py` (rename to `optimizer.py`)
   - `Dockerfile`
   - `docker-compose.yml`
   - `requirements.txt`

3. Edit the `docker-compose.yml` file to set your API keys and location

4. Build and start the container:
   ```bash
   docker-compose up -d
   ```

5. Check the logs to ensure it's working:
   ```bash
   docker-compose logs -f
   ```

## Scheduling

By default, the application:
- Runs a check immediately when started
- Runs a daily check at 17:00 to plan for the next night
- When needed, schedules battery charging from 1:30 AM to 5:30 AM (during typical off-peak hours)

You can modify these times in the source code if needed.

## Troubleshooting

Check the logs for detailed information:
```bash
docker-compose logs -f
```

Common issues:
- Incorrect API keys
- Invalid system ID
- Network connectivity issues

## Advanced Configuration

The default thresholds are:
- `MIN_BATTERY_LEVEL`: 20% (will schedule charging if below this level)
- `CHARGE_THRESHOLD`: 3.0 kWh (will schedule charging if expected generation is below this)

Adjust these values in `docker-compose.yml` to match your needs:
- Higher `MIN_BATTERY_LEVEL` ensures more backup capacity but uses more grid power
- Higher `CHARGE_THRESHOLD` will trigger charging more often when weather is less favorable

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
