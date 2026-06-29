# IkaManager

Ikariam automation platform with web interface. Manage multiple accounts with proxy support, resource automation, piracy, donations, and more.

## Como Usar (Simples)

### Requisitos

1. Instalar o **Docker Desktop**: https://docs.docker.com/desktop/install/windows-install/
2. Instalar o **Git**: https://git-scm.com/download/win

### Passo a Passo

```bash
# 1. Baixar o projeto
git clone https://github.com/SAGIEV007/ikamanager.git
cd ikamanager

# 2. Iniciar (Windows: duplo-clique em start.bat)
docker compose up --build -d

# 3. Abrir no navegador
# http://localhost:3000
```

**Windows:** Depois de instalar Docker Desktop e Git, basta dar **duplo-clique** no arquivo `start.bat`.

**Para parar:** `docker compose down`

### Como funciona o Login

1. Abra http://localhost:3000 no navegador
2. Vá em **Accounts** e clique em **Add Account**
3. Coloque email, senha, country (BR/US/GB), world (nome do mundo)
4. Clique no botao de Login (play verde)
5. O sistema gera automaticamente o token de autenticacao do seu navegador

## Features

- **Multi-Account Management** — Add and manage multiple Ikariam accounts
- **Proxy Support** — HTTPS/SOCKS5 proxy per account for security
- **Anti-Ban** — Human-like delays, rate limiting, realistic headers
- **Web Dashboard** — Modern React interface (inspired by Higgs)
- **Quick Actions** — Bulk operations across accounts
- **Automation** — Resource collection, donations, piracy, building, research
- **Real-time Status** — WebSocket updates for all operations
- **Alerts** — Telegram/Discord notifications

## Development (sem Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
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
- Blackbox token generated automatically by your browser (proves legitimate access)

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
├── start.bat               # Windows: duplo-clique para iniciar
├── start.sh                # Linux/Mac: ./start.sh
└── README.md
```

## Roadmap

- [x] Core: Login, session, proxy, account management
- [x] Dashboard with real-time status
- [x] Quick Actions (bulk operations)
- [x] Blackbox token auto-generation (browser fingerprint)
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
