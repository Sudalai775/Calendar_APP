from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import os
import json

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for all routes

# ==============================
# Google Sheets Configuration
# ==============================

SPREADSHEET_ID = '1scnaCYJZaVFFy3WldSbzjxMR4eZVRuWr3ibR1sN_r7U'
RANGE_NAME = 'Sheet1!A:F'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Load Google Service Account credentials from environment variable
credentials_info = json.loads(os.environ['GOOGLE_CREDENTIALS_JSON'])
credentials = service_account.Credentials.from_service_account_info(
    credentials_info, scopes=SCOPES
)

# Initialize Sheets API
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

# ==============================
# Routes
# ==============================

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/timetable')
def get_timetable():
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()

    values = result.get('values', [])
    if not values or len(values) < 2:
        return jsonify({})

    header = values[0]
    rows = values[1:]
    timetable = {}

    for row in rows:
        row += [''] * (len(header) - len(row))
        data = dict(zip(header, row))

        raw_date = data.get('Date', '')
        try:
            parsed_date = datetime.strptime(raw_date, '%Y-%m-%d')
        except ValueError:
            try:
                parsed_date = datetime.strptime(raw_date, '%d/%m/%Y')
            except ValueError:
                continue

        date_key = parsed_date.strftime('%Y-%m-%d')

        if date_key not in timetable:
            timetable[date_key] = {
                'holiday': data.get('Holiday', ''),
                'day_order': data.get('Day Order', ''),
                'periods': []
            }

        period = data.get('Period')
        timing = data.get('Timing')
        subject = data.get('Subject')

        if period and timing and subject:
            timetable[date_key]['periods'].append({
                'period': period,
                'timing': timing,
                'subject': subject
            })

    return jsonify(timetable)

# ==============================
# Entry Point
# ==============================

if __name__ == '__main__':
    app.run(debug=True)
