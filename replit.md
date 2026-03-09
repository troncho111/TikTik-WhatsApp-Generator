# TikTik WhatsApp Generator

## Overview
A Flask web application that generates formatted WhatsApp messages for Real Madrid ticket orders from Google Sheets data. The system includes user authentication, admin management, and automated Hebrew message generation.

## Project Architecture

### Backend (Python/Flask)
- `main.py` - Main Flask application with all routes and Google Sheets integration

### Frontend (HTML/CSS/JS)
- `templates/` - Jinja2 HTML templates
  - `login.html` - User authentication page
  - `index.html` - Main search and message generation interface
  - `admin.html` - User management for admins
- `static/` - Static assets
  - `style.css` - RTL Hebrew styling with TikTik branding
  - `script.js` - Client-side functionality for search and clipboard

### Key Features
1. **User Authentication** - Login system with admin/user roles
2. **Google Sheets Integration** - Real-time ticket data retrieval
3. **WhatsApp Message Generation** - Formatted Hebrew messages
4. **Seat Adjacency Detection** - Validates if seats are consecutive
5. **Admin Panel** - User management (add/delete representatives)

## Configuration

### Required Environment Secrets
| Key | Description |
|-----|-------------|
| `GOOGLE_CREDENTIALS` | Full JSON content from Google Cloud Service Account |
| `SPREADSHEET_ID` | Google Sheets document ID |
| `SHEET_NAME` | Sheet tab name (default: "real madrid tickets") |
| `ADMIN_USERNAME` | Admin username for login |
| `ADMIN_PASSWORD` | Admin password for login |

### Google Sheets Column Mapping
| Column | Field | Description |
|--------|-------|-------------|
| A | sector | Stadium sector/block |
| B | row | Row number |
| C | seat | Seat number |
| E | order_number | Order number (search key) |
| K | customer_name | Customer name (format: "ID - Name") |
| L | link | Ticket download link |

## Development Commands
- **Run server**: `python main.py`
- **Default port**: 5000

## User Preferences
- Interface language: Hebrew (RTL)
- Target platform: WhatsApp Web integration
- Branding colors: Real Madrid blue (#004C99) and gold (#FFD700)

## Recent Changes
- 2025-12-10: Initial project setup with Flask backend and Hebrew interface
