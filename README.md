<p align="center">
  <img src="https://raw.githubusercontent.com/EdenH1234/CrowsNest/development/frontend/public/logo.svg" alt="CrowsNest" width="120" />
</p>

# CrowsNest

[![CI](https://github.com/EdenH1234/CrowsNest/actions/workflows/ci.yml/badge.svg)](https://github.com/EdenH1234/CrowsNest/actions/workflows/ci.yml)

A lightweight Docker log monitor built for single-host Docker Compose applications. CrowsNest tails logs from all your containers in real time and persists them to a local SQLite database — so you always have the full log history, even across container restarts and redeployments.

## Why CrowsNest

If you run a small production stack on a single server, the built-in `docker logs` command loses history every time a container restarts. Cloud log aggregators are overkill and add cost and complexity. CrowsNest sits alongside your Compose stack, captures everything, and gives you a fast searchable UI — with no external dependencies.

## Features

- **Persistent logs** — logs survive container restarts, redeploys, and service crashes
- **Live streaming** — real-time log tail via WebSocket
- **Full-text search** — SQLite FTS5 search across all container logs
- **Compose-aware** — groups containers by Docker Compose project and service
- **Time range filtering** — filter logs from the last 30 minutes up to all time
- **Lightweight** — a single Docker container, SQLite database, no external services

## Quick Start

Add CrowsNest to your existing `docker-compose.yml`:

```yaml
services:
  crowsnest:
    image: ghcr.io/edenh1234/crowsnest:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./crowsnest-data:/data
    environment:
      - SECRET_KEY=your-secret-key-here
      - ADMIN_PASSWORD=your-password-here
```

Then open [http://localhost:8080](http://localhost:8080) and log in.

Or clone and run standalone:

```bash
git clone https://github.com/EdenH1234/CrowsNest.git
cd CrowsNest
cp .env.example .env   # set SECRET_KEY and ADMIN_PASSWORD
docker compose up -d
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **change this** |
| `ADMIN_USER` | `admin` | Login username |
| `ADMIN_PASSWORD` | `admin` | Login password — **change this** |
| `LOG_RETENTION_DAYS` | `30` | How many days of logs to keep |
| `PORT` | `8080` | Host port to expose |
| `DB_PATH` | `/data/logs.db` | Path to the SQLite database inside the container |

## Running Tests

```bash
cd backend
../.venv/bin/python3 -m pytest -v
```

Or via Docker:

```bash
docker build --target test -t crowsnest:test .
docker run --rm crowsnest:test python -m pytest -v
```

## Tech Stack

- **Backend** — Python, FastAPI, SQLite (FTS5), Docker SDK
- **Frontend** — Vue 3, Vite, PrimeVue
- **Auth** — JWT (8-hour tokens), bcrypt

## License

MIT
