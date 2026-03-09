"""
TikTik WhatsApp Message Generator
Flask application for generating formatted WhatsApp messages from Google Sheets
"""

import os
import json
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import zipfile
import io
from functools import wraps
import gspread
from google.oauth2.credentials import Credentials
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.environ.get('SESSION_SECRET', 'tiktik_default_secret_key_change_me'))

def extract_spreadsheet_id(value):
    if not value:
        return None
    if '/spreadsheets/d/' in value:
        parts = value.split('/spreadsheets/d/')
        if len(parts) > 1:
            id_part = parts[1].split('/')[0].split('?')[0].split('#')[0]
            return id_part
    return value

SPREADSHEET_ID = extract_spreadsheet_id(os.environ.get('SPREADSHEET_ID'))
ORDERS_SPREADSHEET_ID = extract_spreadsheet_id(os.environ.get('ORDERS_SPREADSHEET_ID'))
SHEET_NAME = os.environ.get('SHEET_NAME', 'real madrid tickets')
STADIUM_MAP_URL = os.environ.get('STADIUM_MAP_URL', '')

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))

users_db = {
    ADMIN_USERNAME: {
        'password': ADMIN_PASSWORD_HASH,
        'role': 'admin'
    }
}

def get_connection_settings():
    """Get fresh connection settings each time to avoid stale tokens"""
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
    
    if repl_identity:
        x_replit_token = f'repl {repl_identity}'
    elif web_repl_renewal:
        x_replit_token = f'depl {web_repl_renewal}'
    else:
        raise Exception('X_REPLIT_TOKEN not found for repl/depl')
    
    response = requests.get(
        f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-sheet',
        headers={
            'Accept': 'application/json',
            'X_REPLIT_TOKEN': x_replit_token
        }
    )
    
    data = response.json()
    settings = data.get('items', [{}])[0] if data.get('items') else None
    
    if not settings:
        raise Exception('Google Sheet not connected')
    
    return settings

def get_google_sheets_client():
    try:
        settings = get_connection_settings()
        oauth_creds = settings.get('settings', {}).get('oauth', {}).get('credentials', {})
        
        if not oauth_creds:
            raise Exception('No OAuth credentials found in connection settings')
        
        access_token = oauth_creds.get('access_token')
        refresh_token = oauth_creds.get('refresh_token')
        client_id = oauth_creds.get('client_id')
        client_secret = oauth_creds.get('client_secret')
        
        if not access_token:
            raise Exception('No access token found')
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Error initializing Google Sheets client: {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        username = session['username']
        if users_db.get(username, {}).get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/check_google_connection')
@admin_required
def check_google_connection():
    try:
        global connection_settings
        connection_settings = None
        
        client = get_google_sheets_client()
        if not client:
            return jsonify({
                'connected': False,
                'error': 'לא ניתן להתחבר לגוגל שיטס'
            })
        
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        row_count = len(sheet.get_all_values())
        
        return jsonify({
            'connected': True,
            'message': f'מחובר בהצלחה! נמצאו {row_count} שורות בגיליון'
        })
    except Exception as e:
        return jsonify({
            'connected': False,
            'error': f'שגיאת התחברות: {str(e)}'
        })

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = users_db.get(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='שם משתמש או סיסמה שגויים')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    users_list = [
        {
            'username': username,
            'role': data['role']
        }
        for username, data in users_db.items()
    ]
    return render_template('admin.html', users=users_list, username=session['username'])

@app.route('/api/add_user', methods=['POST'])
@admin_required
def add_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'חסרים שם משתמש או סיסמה'}), 400
    
    if username in users_db:
        return jsonify({'error': 'שם המשתמש כבר קיים'}), 400
    
    users_db[username] = {
        'password': generate_password_hash(password),
        'role': 'user'
    }
    
    return jsonify({'message': 'משתמש נוסף בהצלחה'})

@app.route('/api/delete_user', methods=['POST'])
@admin_required
def delete_user():
    data = request.json
    username = data.get('username')
    
    if username == ADMIN_USERNAME:
        return jsonify({'error': 'לא ניתן למחוק את חשבון האדמין'}), 400
    
    if username not in users_db:
        return jsonify({'error': 'משתמש לא נמצא'}), 404
    
    del users_db[username]
    return jsonify({'message': 'משתמש נמחק בהצלחה'})

@app.route('/api/search_order', methods=['POST'])
@login_required
def search_order():
    try:
        data = request.json
        order_number = data.get('order_number', '').strip()
        custom_name = data.get('custom_name', '').strip()
        include_map = data.get('include_map', False)
        language = data.get('language', 'he')
        
        if not order_number:
            return jsonify({'error': 'אנא הזן מספר הזמנה'}), 400
        
        order_data = get_order_data(order_number)
        
        if not order_data:
            return jsonify({'error': f'הזמנה מספר {order_number} לא נמצאה'}), 404
        
        if custom_name:
            order_data['display_name'] = custom_name
        else:
            order_data['display_name'] = order_data['customer_name']
        
        if include_map:
            if STADIUM_MAP_URL:
                map_url = STADIUM_MAP_URL
            else:
                map_url = request.host_url.rstrip('/') + url_for('static', filename='stadium_map.png')
        else:
            map_url = ''
        message = generate_whatsapp_message(order_data, include_map=include_map, map_url=map_url, language=language)
        
        return jsonify({
            'message': message,
            'customer_name': order_data['customer_name'],
            'game_name': order_data.get('game_name', ''),
            'tickets': order_data['tickets'],
            'order_data': order_data,
            'already_sent': order_data.get('already_sent', False)
        })
        
    except Exception as e:
        print(f"Error in search_order: {e}")
        return jsonify({'error': f'שגיאה בחיפוש: {str(e)}'}), 500

@app.route('/api/mark_sent', methods=['POST'])
@login_required
def mark_sent():
    try:
        data = request.json
        row_indices = data.get('row_indices', [])
        order_number = data.get('order_number', '')
        
        if not row_indices:
            return jsonify({'error': 'לא נמצאו שורות לעדכון'}), 400
        
        client = get_google_sheets_client()
        if not client:
            return jsonify({'error': 'שגיאה בהתחברות ל-Google Sheets'}), 500
        
        from gspread_formatting import CellFormat, Color, format_cell_range
        green_format = CellFormat(backgroundColor=Color(0.85, 0.95, 0.85))
        
        tickets_sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        for row_idx in row_indices:
            tickets_sheet.update_cell(row_idx, 2, 'done!')
            row_range = f"A{row_idx}:Z{row_idx}"
            format_cell_range(tickets_sheet, row_range, green_format)
        
        if ORDERS_SPREADSHEET_ID and order_number:
            try:
                print(f"Updating orders sheet for order: {order_number}")
                print(f"ORDERS_SPREADSHEET_ID: {ORDERS_SPREADSHEET_ID}")
                orders_sheet = client.open_by_key(ORDERS_SPREADSHEET_ID).sheet1
                all_values = orders_sheet.get_all_values()
                print(f"Found {len(all_values)} rows in orders sheet")
                
                found = False
                for idx, row in enumerate(all_values[1:], start=2):
                    if len(row) > 3:
                        cell_value = str(row[3]).strip()
                        if cell_value == str(order_number).strip():
                            print(f"Found match at row {idx}: {cell_value}")
                            orders_sheet.update_cell(idx, 2, 'done!')
                            row_range = f"A{idx}:Z{idx}"
                            format_cell_range(orders_sheet, row_range, green_format)
                            found = True
                
                if not found:
                    print(f"Order number {order_number} not found in orders sheet column D")
                else:
                    print(f"Successfully updated orders sheet!")
            except Exception as e:
                import traceback
                print(f"Error updating orders sheet: {e}")
                traceback.print_exc()
        
        return jsonify({'message': f'עודכנו {len(row_indices)} שורות בהצלחה!', 'success': True})
        
    except Exception as e:
        print(f"Error in mark_sent: {e}")
        return jsonify({'error': f'שגיאה בעדכון: {str(e)}'}), 500

@app.route('/api/download_ticket', methods=['POST'])
@login_required
def download_ticket():
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({'error': 'URL not provided'}), 400
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
        }
        
        response = requests.get(url, timeout=60, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'application/vnd.apple.pkpass')
        
        return Response(
            response.content,
            mimetype=content_type,
            headers={'Content-Disposition': 'attachment; filename=ticket.pkpass'}
        )
        
    except requests.exceptions.Timeout:
        print(f"Timeout downloading ticket from: {url}")
        return jsonify({'error': 'הזמן הקצוב להורדה עבר, נסה שוב'}), 500
    except requests.exceptions.RequestException as e:
        print(f"Error downloading ticket: {e}")
        return jsonify({'error': f'שגיאה בהורדה: {str(e)}'}), 500
    except Exception as e:
        print(f"Error downloading ticket: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_all_zip', methods=['POST'])
@login_required
def download_all_zip():
    try:
        data = request.json
        tickets = data.get('tickets', [])
        order_number = data.get('order_number', 'order')
        
        if not tickets:
            return jsonify({'error': 'No tickets provided'}), 400
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
        }
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for ticket in tickets:
                try:
                    url = ticket.get('url', '')
                    seat = ticket.get('seat', 'unknown')
                    response = requests.get(url, timeout=60, headers=headers, allow_redirects=True)
                    response.raise_for_status()
                    zip_file.writestr(f'{order_number}_seat_{seat}.pkpass', response.content)
                except Exception as e:
                    print(f"Error downloading {url}: {e}")
        
        zip_buffer.seek(0)
        
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': 'attachment; filename=tickets.zip'}
        )
        
    except Exception as e:
        print(f"Error creating zip: {e}")
        return jsonify({'error': str(e)}), 500

def get_order_data(order_number):
    try:
        client = get_google_sheets_client()
        if not client:
            raise Exception("Failed to initialize Google Sheets client")
        
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        all_values = sheet.get_all_values()
        
        headers = all_values[0] if all_values else []
        
        matching_rows = []
        row_indices = []
        already_sent = False
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) > 10 and str(row[10]).strip() == str(order_number).strip():
                matching_rows.append(row)
                row_indices.append(idx)
                if len(row) > 1 and str(row[1]).strip().lower() == 'done!':
                    already_sent = True
        
        if not matching_rows:
            return None
        
        customer_name = order_number
        game_name = matching_rows[0][2].strip() if len(matching_rows[0]) > 2 and matching_rows[0][2] else ''
        
        tickets = []
        for row in matching_rows:
            if len(row) > 12:
                sector_desc = row[3].strip() if len(row) > 3 and row[3] else ''
                sector_num = row[4].strip() if len(row) > 4 and row[4] else ''
                full_sector = f"{sector_desc} {sector_num}".strip()
                
                ticket = {
                    'sector': full_sector,
                    'row': row[5].strip() if len(row) > 5 and row[5] else '',
                    'seat': row[6].strip() if len(row) > 6 and row[6] else '',
                    'link': row[12].strip() if len(row) > 12 and row[12] else ''
                }
                if ticket['sector'] and ticket['link']:
                    tickets.append(ticket)
        
        if not tickets:
            return None
        
        return {
            'order_number': order_number,
            'customer_name': customer_name,
            'game_name': game_name,
            'tickets': tickets,
            'row_indices': row_indices,
            'already_sent': already_sent
        }
        
    except Exception as e:
        print(f"Error fetching order data: {e}")
        raise

def generate_whatsapp_message(order_data, include_map=False, map_url='', language='he'):
    customer_name = order_data.get('display_name', order_data['customer_name'])
    game_name = order_data.get('game_name', '')
    tickets = order_data['tickets']
    
    if language == 'en':
        return generate_english_message(customer_name, game_name, tickets, include_map, map_url)
    elif language == 'supplier':
        return generate_supplier_message(game_name, tickets)
    else:
        return generate_hebrew_message(customer_name, game_name, tickets, include_map, map_url)

def generate_hebrew_message(customer_name, game_name, tickets, include_map, map_url):
    seats_info = ""
    if len(tickets) == 2:
        seat1 = int(tickets[0]['seat']) if tickets[0]['seat'].isdigit() else 0
        seat2 = int(tickets[1]['seat']) if tickets[1]['seat'].isdigit() else 0
        
        if seat1 and seat2:
            if (seat1 % 2 == seat2 % 2) and abs(seat1 - seat2) == 2:
                seats_info = f"\n✅ *כיסאות צמודים!* ({min(seat1, seat2)}, {max(seat1, seat2)})"
            else:
                seats_info = f"\n⚠️ *שים לב:* הכיסאות {min(seat1, seat2)} ו-{max(seat1, seat2)} אינם צמודים"
    
    game_line = f"\n🏆 *{game_name}*\n" if game_name else ""
    
    message = f"""🎉 *שלום {customer_name},*

ברוכים הבאים למשפחת TikTik! 💙
{game_line}
הכרטיסים שלך מוכנים! 🏟️⚽

━━━━━━━━━━━━━━━━━━━━━
📋 *פרטי הכרטיסים:*
"""
    
    for i, ticket in enumerate(tickets, 1):
        message += f"""
🎫 *כרטיס {i}:*
📍 סקטור: {ticket['sector']} | שורה: {ticket['row']} | כיסא: {ticket['seat']}"""
    
    message += seats_info
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

🔗 *הכרטיסים הדיגיטליים שלך:*
"""
    
    for i, ticket in enumerate(tickets, 1):
        message += f"""
🎟️ כרטיס {i} (כיסא {ticket['seat']}):
{ticket['link']}"""
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

📱 *הוראות שימוש:*
1️⃣ לחץ על הלינק של כל כרטיס
2️⃣ שמור את הכרטיסים במכשיר או הדפס
3️⃣ הצג את הברקוד בכניסה לאצטדיון

💡 *טיפ חשוב:* שמור את הכרטיסים במכשיר כבר עכשיו, ווודא שיש לך סוללה מלאה ביום המשחק!"""
    
    if include_map and map_url:
        message += f"""

━━━━━━━━━━━━━━━━━━━━━

🗺️ *מפת האצטדיון:*
{map_url}"""
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

✨ *תהנה מהמשחק ו-Hala Madrid!* 👑⚽

צוות TikTik 💙
🌐 www.tiktik-online.co.il
📧 צריך עזרה? פשוט שלח הודעה!"""
    
    return message

def generate_english_message(customer_name, game_name, tickets, include_map, map_url):
    seats_info = ""
    if len(tickets) == 2:
        seat1 = int(tickets[0]['seat']) if tickets[0]['seat'].isdigit() else 0
        seat2 = int(tickets[1]['seat']) if tickets[1]['seat'].isdigit() else 0
        
        if seat1 and seat2:
            if (seat1 % 2 == seat2 % 2) and abs(seat1 - seat2) == 2:
                seats_info = f"\n✅ *Adjacent seats!* ({min(seat1, seat2)}, {max(seat1, seat2)})"
            else:
                seats_info = f"\n⚠️ *Note:* Seats {min(seat1, seat2)} and {max(seat1, seat2)} are not adjacent"
    
    game_line = f"\n🏆 *{game_name}*\n" if game_name else ""
    
    message = f"""🎉 *Hello {customer_name},*

Welcome to the TikTik family! 💙
{game_line}
Your tickets are ready! 🏟️⚽

━━━━━━━━━━━━━━━━━━━━━
📋 *Ticket Details:*
"""
    
    for i, ticket in enumerate(tickets, 1):
        message += f"""
🎫 *Ticket {i}:*
📍 Sector: {ticket['sector']} | Row: {ticket['row']} | Seat: {ticket['seat']}"""
    
    message += seats_info
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

🔗 *Your Digital Tickets:*
"""
    
    for i, ticket in enumerate(tickets, 1):
        message += f"""
🎟️ Ticket {i} (Seat {ticket['seat']}):
{ticket['link']}"""
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

📱 *Instructions:*
1️⃣ Click on each ticket link
2️⃣ Save the tickets to your device or print them
3️⃣ Show the barcode at the stadium entrance

💡 *Important tip:* Save the tickets to your device now, and make sure you have a full battery on game day!"""
    
    if include_map and map_url:
        message += f"""

━━━━━━━━━━━━━━━━━━━━━

🗺️ *Stadium Map:*
{map_url}"""
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

✨ *Enjoy the game and Hala Madrid!* 👑⚽

TikTik Team 💙
🌐 www.tiktik-online.co.il
📧 Need help? Just send us a message!"""
    
    return message

def generate_supplier_message(game_name, tickets):
    seats_info = ""
    if len(tickets) == 2:
        seat1 = int(tickets[0]['seat']) if tickets[0]['seat'].isdigit() else 0
        seat2 = int(tickets[1]['seat']) if tickets[1]['seat'].isdigit() else 0
        
        if seat1 and seat2:
            if (seat1 % 2 == seat2 % 2) and abs(seat1 - seat2) == 2:
                seats_info = f"\n✅ *Adjacent seats!* ({min(seat1, seat2)}, {max(seat1, seat2)})"
            else:
                seats_info = f"\n⚠️ *Note:* Seats {min(seat1, seat2)} and {max(seat1, seat2)} are not adjacent"
    
    game_line = f"🏆 *{game_name}*\n\n" if game_name else ""
    
    message = f"""{game_line}📋 *Ticket Details:*
"""
    
    for i, ticket in enumerate(tickets, 1):
        message += f"""
🎫 *Ticket {i}:*
📍 Sector: {ticket['sector']} | Row: {ticket['row']} | Seat: {ticket['seat']}"""
    
    message += seats_info
    
    message += """

━━━━━━━━━━━━━━━━━━━━━

🔗 *Your Digital Tickets:*
"""
    
    for i, ticket in enumerate(tickets, 1):
        message += f"""
🎟️ Ticket {i} (Seat {ticket['seat']}):
{ticket['link']}"""
    
    message += """

━━━━━━━━━━━━━━━━━━━━━"""
    
    return message

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
