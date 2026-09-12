# AgriQueue — SIH PS26032

**Farmer Slot Booking & Queue Management System**
Smart India Hackathon — Problem Statement 26032

## Live Demo

🔗 **[sih-ps26032-production.up.railway.app/login](https://sih-ps26032-production.up.railway.app/login)**

## Problem

Farmers arriving at mandis (agricultural procurement centers) often face long, unstructured queues with no way to know how long they'll wait or whether a counter can even take their produce that day. **AgriQueue** lets farmers book a specific time slot in advance, check in with a QR code on arrival, and track their live position in the queue — while giving procurement officers a real-time dashboard to manage slots, check-ins, and the live queue at their counter.

## Features

**For farmers**
- Book a slot at a nearby procurement center for a specific date and time
- See real-time slot availability (X of 20 booked) before choosing
- Straight-line distance to the selected center, computed from live device geolocation
- Confirmation screen with a unique QR code and token number
- Live queue tracking — position, farmers ahead, estimated wait time, and a visual status timeline (booked → checked in → waiting → in service)
- Full English / Hindi language toggle
- No-smartphone fallback path (in-person booking + SMS/voice queue updates)

**For officers**
- Add, view, and delete upcoming slots per counter
- Scan a farmer's QR code to check them in instantly
- Live queue dashboard, auto-refreshing
- "Awaiting check-in" list for bookings that haven't arrived yet

**Under the hood**
- JWT-based authentication with role-based access control (farmer / officer)
- Concurrency-safe slot booking (row-level locking prevents double-booking the last seat)
- QR code generation and token-based check-in
- MySQL with foreign-key constraints protecting booking history from accidental deletion

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI (Python) |
| Database | MySQL |
| Templating | Jinja2 |
| Frontend interactivity | htmx |
| Auth | JWT (cookie-based sessions) |
| QR codes | `qrcode` (Python) |
| Deployment | Railway |

## Getting Started

```powershell
# clone and enter the backend
cd backend

# create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# set up the database
mysql -u root -p < ../db/schema.sql

# configure environment variables (see .env.example)
# DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, JWT_SECRET, PUBLIC_BASE_URL

# run the server
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` and sign up as either a farmer or an officer to get started.

## Version History

| Version | Change |
|---|---|
| 0.1.0 | Added initial MySQL schema for slot booking system |
| 0.2.0 | Added FastAPI backend skeleton with MySQL connection |
| 0.3.0 | Added JWT auth with signup/login endpoints |
| 0.4.0 | Added Role Based Access Control (RBAC) |
| 0.5.0 | Added slots and bookings endpoints with concurrency-safe booking |
| 1.6.0 | Added queue check-in and live status tracking |
| 2.0.0 | Added frontend |
| 1.1.0 | Added QR code generation and check-in window for officer |
| 3.1.0 | Deployed locally using VS Code's Port Forwarding |
| 3.1.1 | Removed comments and made minor changes |
| 3.1.2 | Changed QR-scanned website URL from localhost to deployed URL |
| 3.1.3 | Moved `requirements.txt` out |
| 3.1.4 | Moved `requirements.txt` back |
| 4.1.4 | Deployed to Railway.app |
| 5.1.4 | Updated the frontend and added QR code and booking history |
| 5.2.4 | Added Live Queue |
| 5.3.4 | Added notification display after booking |
| 5.3.5 | Minor changes |
| 5.4.5 | Optimized the code — removed dead code blocks, improved efficiency |
| 5.5.5 | Centered nav, larger farmer-facing UI, produce quick-select shortcuts |
| 5.6.5 | Added subtle motion/animations |

## License

Built for Smart India Hackathon 2026. All rights reserved by the team unless otherwise noted.
