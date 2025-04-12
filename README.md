# Weather Application

A comprehensive weather application that provides current weather conditions and forecasts for any location. Built by Aditya for the PM Accelerator assessment.

## Features

- Current weather information for any location
- 5-day weather forecast
- Location-based weather using GPS
- Weather data persistence with CRUD operations
- Data export in multiple formats
- Additional location information through integrated APIs

## Setup Instructions

1. Clone the repository
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add your API keys:
     ```
     OPENWEATHER_API_KEY=your_api_key_here
     GOOGLE_MAPS_API_KEY=your_api_key_here
     YOUTUBE_API_KEY=your_api_key_here
     ```
4. Run the application:
   ```
   python app.py
   ```
5. Open your browser and navigate to `http://localhost:5000`

## API Keys Required

- OpenWeather API (for weather data)
- Google Maps API (for location services)
- YouTube Data API (for location videos)

## About PM Accelerator

PM Accelerator is a program designed to help aspiring product managers develop the skills and knowledge needed to succeed in the field. For more information, visit our [LinkedIn page](https://www.linkedin.com/company/product-manager-accelerator). 