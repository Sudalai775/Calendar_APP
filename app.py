from flask import Flask, jsonify
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_caching import Cache

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Configuration
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '1scnaCYJZaVFFy3WldSbzjxMR4eZVRuWr3ibR1sN_r7U')
RANGE_NAME = os.getenv('RANGE_NAME', 'Sheet1!A:F')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'credentials.json')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Initialize Google Sheets API
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
except Exception as e:
    print(f"Failed to initialize Google Sheets API: {str(e)}")
    raise

def parse_date(date_str):
    """Parse date string in multiple formats"""
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

@app.route('/api/timetable')
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_timetable():
    try:
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()

        values = result.get('values', [])
        if not values or len(values) < 2:
            return jsonify({"error": "No data available"}), 404

        header = [h.strip() for h in values[0]]
        rows = values[1:]
        timetable = {}

        for row in rows:
            # Pad row with empty strings if shorter than header
            row += [''] * (len(header) - len(row))
            data = dict(zip(header, row))

            # Parse date
            raw_date = data.get('Date', '')
            parsed_date = parse_date(raw_date)
            if not parsed_date:
                continue

            date_key = parsed_date.strftime('%Y-%m-%d')

            # Initialize date entry if not exists
            if date_key not in timetable:
                timetable[date_key] = {
                    'holiday': data.get('Holiday', '').strip(),
                    'day_order': data.get('Day Order', '').strip(),
                    'periods': []
                }

            # Add period if all fields exist
            period = data.get('Period', '').strip()
            timing = data.get('Timing', '').strip()
            subject = data.get('Subject', '').strip()

            if period and timing and subject:
                timetable[date_key]['periods'].append({
                    'period': period,
                    'timing': timing,
                    'subject': subject
                })

        return jsonify(timetable)

    except Exception as e:
        app.logger.error(f"Error fetching timetable: {str(e)}")
        return jsonify({
            "error": "Failed to fetch timetable data",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    # Run in development mode
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True, port=5000)
    else:
        # Run in production mode
        from waitress import serve
        serve(app, host="0.0.0.0", port=8080)