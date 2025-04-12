from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import pandas as pd
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import sqlite3

# Load environment variables
load_dotenv()

# Check for required API keys
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
if not OPENWEATHER_API_KEY:
    raise ValueError("OpenWeather API key is required. Please add it to your .env file.")

# Optional API keys
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class WeatherRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    date = db.Column(db.DateTime, nullable=False)
    temperature = db.Column(db.Float)
    description = db.Column(db.String(100))
    humidity = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize database
with app.app_context():
    db.create_all()

# Helper Functions
def get_coordinates(location):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode(location)
    if location:
        return location.latitude, location.longitude
    return None, None

def get_weather_data(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json()

def get_forecast_data(lat, lon, days=5):
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json()

def get_google_maps_data(lat, lon, count=5):
    if not GOOGLE_MAPS_API_KEY:
        return None
    
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=5000&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if 'results' in data:
        return {'results': data['results'][:count]}
    return None

def init_db():
    conn = sqlite3.connect('weather.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            date TEXT,
            temperature REAL,
            description TEXT,
            humidity INTEGER,
            wind_speed REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html', 
                         has_maps_api=bool(GOOGLE_MAPS_API_KEY))

@app.route('/api/weather', methods=['POST'])
def get_weather():
    data = request.get_json()
    location = data.get('location')
    forecast_days = int(data.get('forecastDays', 5))
    places_count = int(data.get('placesCount', 5))
    
    if not location:
        return jsonify({'error': 'Location is required'}), 400
    
    lat, lon = get_coordinates(location)
    if not lat or not lon:
        return jsonify({'error': 'Could not find location'}), 404
    
    try:
        current_weather = get_weather_data(lat, lon)
        forecast = get_forecast_data(lat, lon, forecast_days)
        places = get_google_maps_data(lat, lon, places_count)
        
        record = WeatherRecord(
            location=location,
            latitude=lat,
            longitude=lon,
            date=datetime.utcnow(),
            temperature=current_weather['main']['temp'],
            description=current_weather['weather'][0]['description'],
            humidity=current_weather['main']['humidity'],
            wind_speed=current_weather['wind']['speed']
        )
        db.session.add(record)
        db.session.commit()
        
        return jsonify({
            'current': current_weather,
            'forecast': forecast,
            'places': places
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/records', methods=['GET'])
def get_records():
    records = WeatherRecord.query.order_by(WeatherRecord.created_at.desc()).all()
    return jsonify([{
        'id': record.id,
        'location': record.location,
        'date': record.date.isoformat(),
        'temperature': record.temperature,
        'description': record.description,
        'humidity': record.humidity,
        'wind_speed': record.wind_speed
    } for record in records])

@app.route('/api/records/<int:id>', methods=['PUT'])
def update_record(id):
    record = WeatherRecord.query.get_or_404(id)
    data = request.get_json()
    
    if 'location' in data:
        record.location = data['location']
    if 'temperature' in data:
        record.temperature = data['temperature']
    if 'description' in data:
        record.description = data['description']
    
    db.session.commit()
    return jsonify({'message': 'Record updated successfully'})

@app.route('/api/records/<int:id>', methods=['DELETE'])
def delete_record(id):
    record = WeatherRecord.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'Record deleted successfully'})

@app.route('/api/export/<format>', methods=['GET'])
def export_data(format):
    records = WeatherRecord.query.order_by(WeatherRecord.created_at.desc()).all()
    data = [{
        'Location': record.location,
        'Date': record.date.strftime('%Y-%m-%d %H:%M:%S'),
        'Temperature (°C)': record.temperature,
        'Description': record.description,
        'Humidity (%)': record.humidity,
        'Wind Speed (m/s)': record.wind_speed
    } for record in records]
    
    if format == 'json':
        return jsonify(data)
    elif format == 'csv':
        df = pd.DataFrame(data)
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return output.getvalue(), 200, {'Content-Type': 'text/csv'}
    elif format == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        table_data = [list(data[0].keys())] + [list(record.values()) for record in data]
        table = Table(table_data)
        
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.grey),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.white)
        ])
        
        table.setStyle(style)
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue(), 200, {'Content-Type': 'application/pdf'}
    else:
        return jsonify({'error': 'Invalid format'}), 400

if __name__ == '__main__':
    app.run(debug=True) 