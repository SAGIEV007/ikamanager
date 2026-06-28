# IkaManager

Ikariam automation platform with web interface. Manage multiple accounts with proxy support, resource automation, piracy, donations, and more.

## Features

- **Multi-Account Management** — Add and manage multiple Ikariam accounts
- **Proxy Support** — HTTPS/SOCKS5 proxy per account for security
- **Anti-Ban** — Human-like delays, rate limiting, realistic headers
- **Web Dashboard** — Modern React interface (inspired by Higgs)
- **Quick Actions** — Bulk operations across accounts
- **Automation** — Resource collection, donations, piracy, building, research
- **Real-time Status** — WebSocket updates for all operations
- **Alerts** — Telegram/Discord notifications

## Quick Start

### Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install aiosqlite
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Docker

```bash
docker-compose up --build
```

Open http://localhost:3000

## Architecture

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, aiohttp
- **Frontend**: React 18, TailwindCSS, Vite, Zustand
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Real-time**: WebSocket
- **Proxy**: aiohttp-socks (SOCKS5/HTTPS)

## API Documentation

Once running, visit http://localhost:8000/docs for Swagger UI.

## Security

- All Ikariam passwords are encrypted with AES-256 (Fernet) before storage
- Each account uses a dedicated proxy (never shared IP per world)
- Human-like delays between actions (configurable)
- Rate limiting per account
- Realistic browser headers/fingerprints

## Project Structure

```
ikamanager/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Settings
│   │   ├── database.py       # DB connection
│   │   ├── models/           # SQLAlchemy models
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   │   └── ikariam/      # Game interaction
│   │   └── utils/            # Helpers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── pages/            # Page views
│   │   ├── stores/           # State management
│   │   └── services/         # API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Roadmap

- [x] Core: Login, session, proxy, account management
- [x] Dashboard with real-time status
- [x] Quick Actions (bulk operations)
- [ ] Resource automation (collect, distribute, send)
- [ ] Donation automation (daily, scheduled)
- [ ] Piracy automation with captcha solving
- [ ] Building queue
- [ ] Research queue
- [ ] Marketplace (buy/sell)
- [ ] Military (train, move)
- [ ] Map visualization
- [ ] Telegram bot integration
- [ ] Workflow system (complex automation chains)
