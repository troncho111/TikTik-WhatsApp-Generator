# TikTik WhatsApp Generator 🎫

  A Flask web application that generates formatted WhatsApp messages for Real Madrid ticket orders from Google Sheets data.

  ## Features

  - **User Authentication** - Login system with admin/user roles
  - **Google Sheets Integration** - Real-time ticket data retrieval via OAuth
  - **WhatsApp Message Generation** - Three formats:
    - Hebrew (עברית) - Full customer message
    - English - Full customer message
    - Supplier - Condensed format
  - **Seat Adjacency Detection** - Validates if seats are consecutive
  - **Admin Panel** - User management and Google Sheets connection monitoring
  - **Mark as Sent** - Updates both tickets and orders spreadsheets
  - **Already Sent Warning** - Alerts when tickets were previously sent
  - **Quick Copy Links** - Individual and bulk ticket link copying
  - **Direct Ticket Downloads** - Open ticket links directly in browser
  - **Stadium Map** - Optional stadium map attachment
  - **Mobile Responsive** - RTL Hebrew interface optimized for all devices

  ## Tech Stack

  - **Backend:** Python / Flask
  - **Frontend:** HTML, CSS, JavaScript (vanilla)
  - **Data:** Google Sheets API (OAuth)
  - **Styling:** Custom CSS with Real Madrid branding (#004C99 / #FFD700)

  ## Setup

  1. Clone the repository
  2. Install dependencies:
     ```
     pip install -r requirements.txt
     ```
  3. Set environment variables:
     - `GOOGLE_CREDENTIALS` - Google Cloud Service Account JSON
     - `SPREADSHEET_ID` - Tickets Google Sheet ID
     - `ORDERS_SPREADSHEET_ID` - Orders Google Sheet ID
     - `SHEET_NAME` - Sheet tab name (default: "real madrid tickets")
     - `ADMIN_USERNAME` - Admin login username
     - `ADMIN_PASSWORD` - Admin login password
     - `SESSION_SECRET` - Flask session secret key

  4. Run the server:
     ```
     python main.py
     ```

  ## Project Structure

  ```
  ├── main.py                 # Flask application (routes, API, Google Sheets)
  ├── requirements.txt        # Python dependencies
  ├── pyproject.toml          # Project configuration
  ├── static/
  │   ├── style.css           # RTL Hebrew styling
  │   ├── script.js           # Client-side functionality
  │   └── stadium_map.png     # Stadium map image
  └── templates/
      ├── login.html          # Authentication page
      ├── index.html          # Main search & message interface
      └── admin.html          # Admin user management
  ```

  ## License

  Private project - TikTik © 2025
  