# 📺 TelePlay

**Your personal, self-hosted media server — powered by Telegram.**

![TelePlay Banner](files/app_banner.png)

Stream and manage your Telegram files on any device — TV, Mobile, or Browser — **without downloading the entire file**. TelePlay uses Telegram as unlimited cloud storage and streams content on-demand at high speed using its **multi-client parallel download** technology. Upload via a Telegram Bot, organize through a Web App, and watch anywhere.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![Kotlin](https://img.shields.io/badge/Kotlin-Compose_TV-7f52ff.svg)

---

## ✨ Features

### 🤖 Telegram Bot — [Full Command List](docs/SETUP.md#part-2-using-the-telegram-bot)

- Upload any file type (video, audio, documents, photos)
- Organize files into folders with inline buttons
- Rename, move, and delete files via chat commands
- Search your library with `/myfiles`
- Get an auto-login web link with `/web`

### 🌐 Web App — [Login Methods](docs/SETUP.md#31-web-interface)

- Full file browser with folder navigation
- Multi-select, batch delete, rename, and move operations
- Context menu (right-click) on files
- Inline video/audio player with seeking
- Three login methods (direct link, login code, [remote authorization](docs/SETUP.md#31-web-interface))
- Responsive — works on desktop and mobile

### 📺 Android TV & Mobile App — [Installation Guide](docs/SETUP.md#32-android-tv--mobile)

- Designed for TV with D-Pad / remote control navigation
- **Continue Watching** and **Recently Added** rows on the home screen
- Full-screen ExoPlayer playback with transport controls
- Download files for offline playback (Mobile)
- Picture-in-Picture mode (Mobile)
- Watch progress automatically synced with the server

### ⚡ Platform — [Architecture Overview](docs/ARCHITECTURE.md)

- **Zero local storage** — all files live on Telegram's unlimited cloud
- **Multi-user** — each Telegram user gets an isolated library
- **High-speed streaming** — optional [multi-bot parallel downloads](docs/ARCHITECTURE.md#multi-client-mode-parallel-downloads)
- **Restricted access** — [whitelist allowed users](docs/SETUP.md#-advanced-features) with `AUTH_USERS`
- **Public sharing** — generate signed, time-limited links
- **One-command deploy** — [Docker Compose, Railway, Render, or CapRover](docs/DEPLOYMENT.md)

---

## 🏗️ How It Works

```
  You                Telegram Cloud              Your Server              Your Devices
  ───                ──────────────              ───────────              ────────────
   │                                                  │
   │  1. Send file to Bot ──────────────────────────► │
   │                         2. Bot forwards to  ───► │ (Private Channel)
   │                            Storage Channel       │
   │                                                  │ 3. Saves metadata
   │                                                  │    to Database
   │                                                  │
   │  4. Open Web / TV App ◄──────────────────────────│
   │                                                  │
   │  5. Press Play ──────────────────────────────► │
   │                         6. Fetches chunks   ◄──  │ (from Telegram)
   │  7. Streams to you ◄────────────────────────── │
   │                                                  │
```

Your files are **never stored on your server** — TelePlay streams them directly from Telegram's cloud on demand.

---

## 📸 Screenshots

### 🌐 Web Interface

<p align="center">
  <img src="files/web_app_home_screen.png" width="32%" />
  <img src="files/web_app_player.png" width="32%" />
  <img src="files/web_app_login_screen.png" width="32%" />
</p>

### 📺 Android TV

<p align="center">
  <img src="files/tv_home_screen.png" width="32%" />
  <img src="files/tv_player_screen.png" width="32%" />
  <img src="files/tv_login_screen.png" width="32%" />
</p>

### 📱 Mobile App

<p align="center">
  <img src="files/mobile_home_screen.png" width="32%" />
  <img src="files/mobile_player_screen.png" width="32%" />
  <img src="files/mobile_downloads_screen.png" width="32%" />
</p>

---

## � Quick Start

### Prerequisites — [Detailed Steps](docs/DEPLOYMENT.md#-step-1-get-telegram-credentials)

| Requirement            | How to get it                                          |
| :--------------------- | :----------------------------------------------------- |
| **Telegram Bot Token** | Create via [@BotFather](https://t.me/BotFather)        |
| **API ID & Hash**      | Register at [my.telegram.org](https://my.telegram.org) |
| **Storage Channel**    | Create a private channel, add your bot as admin        |
| **Docker**             | [Install Docker](https://docs.docker.com/get-docker/)  |

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/teleplay.git
cd teleplay
cp .env.example .env
```

Edit `.env` with your credentials:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_STORAGE_CHANNEL_ID=-100xxxxxxxxxx
JWT_SECRET=your-super-secret-key-at-least-32-characters

# Use PostgreSQL (recommended) or SQLite (no setup needed):
DATABASE_URL=sqlite:///./data/teleplay.db
# DATABASE_URL=postgresql://postgres:password@db:5432/teleplay
```

### 2. Deploy

```bash
docker compose up -d
```

That's it! Your services are now running:

| Service         | URL                   |
| :-------------- | :-------------------- |
| **Web App**     | http://localhost      |
| **Backend API** | http://localhost:8000 |

### 3. Start Using

1. Open Telegram and send a video file to your bot.
2. Send `/web` to get a link to your Web App.
3. Stream your files! 🎬

> **For detailed setup, usage, and login instructions**, see the **[Setup & Usage Guide](docs/SETUP.md)**.
>
> **For VPS, Railway, Render, and CapRover deployments**, see the **[Deployment Guide](docs/DEPLOYMENT.md)**.

---

## 📱 Android TV & Mobile App

**Download the APK** from the [Releases](../../releases) page:

| APK         | Best For                               |
| :---------- | :------------------------------------- |
| `arm64-v8a` | Modern TV boxes, phones, NVIDIA Shield |
| `universal` | Any device (if unsure, use this one)   |

**Setup:**

1. Install the APK on your device.
2. Enter your Server URL (e.g., `http://192.168.1.100`).
3. A 6-digit code will appear — send `/login CODE` to your bot.
4. Done! Browse and stream your library.

> **For APK signing and release automation**, see the **[Releasing Guide](docs/RELEASING.md)**.

---

## ⚙️ Environment Variables

| Variable                      | Required | Description                                                                                          |
| :---------------------------- | :------: | :--------------------------------------------------------------------------------------------------- |
| `TELEGRAM_API_ID`             |    ✅    | From [my.telegram.org](https://my.telegram.org)                                                      |
| `TELEGRAM_API_HASH`           |    ✅    | From [my.telegram.org](https://my.telegram.org)                                                      |
| `TELEGRAM_BOT_TOKEN`          |    ✅    | From [@BotFather](https://t.me/BotFather)                                                            |
| `TELEGRAM_STORAGE_CHANNEL_ID` |    ✅    | Private channel ID (starts with `-100`)                                                              |
| `JWT_SECRET`                  |    ✅    | Secret key for JWT signing (min 32 chars)                                                            |
| `DATABASE_URL`                |    ✅    | Database connection URL (see below)                                                                  |
| `WEB_BASE_URL`                |    ❌    | Public URL of the web app                                                                            |
| `TELEGRAM_HELPER_BOT_TOKENS`  |    ❌    | Extra bot tokens for [parallel downloads](docs/ARCHITECTURE.md#multi-client-mode-parallel-downloads) |
| `AUTH_USERS`                  |    ❌    | Comma-separated Telegram IDs for restricted access                                                   |

> **💡 DATABASE_URL Options:**
>
> - **PostgreSQL (recommended):** `postgresql://postgres:password@localhost:5432/teleplay`
> - **SQLite (no setup needed):** `sqlite:///./data/teleplay.db`
>
> Use SQLite if you don't want to set up PostgreSQL — it works out of the box for small deployments.

---

## 🛠️ Tech Stack

| Layer        | Technology                                       |
| :----------- | :----------------------------------------------- |
| **Backend**  | Python 3.11+, FastAPI, Uvicorn                   |
| **Telegram** | PyroTGFork (MTProto)                             |
| **Database** | PostgreSQL (prod) / SQLite (dev), SQLAlchemy 2.0 |
| **Auth**     | JWT (Access + Refresh Tokens)                    |
| **Web**      | React 18, TypeScript, Vite                       |
| **Android**  | Kotlin, Jetpack Compose for TV, ExoPlayer        |
| **Deploy**   | Docker, Docker Compose, Nginx                    |

---

## 📁 Project Structure — [Full Breakdown](docs/ARCHITECTURE.md#-project-structure)

```
teleplay/
├── backend/                  # Python backend (FastAPI + Bot)
│   ├── app/
│   │   ├── routers/          # API endpoints (auth, files, folders, streaming, tv)
│   │   ├── bot.py            # Telegram bot command handlers
│   │   ├── streaming.py      # Multi-client parallel streaming engine
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── main.py           # FastAPI app entry point
│   ├── Dockerfile
│   └── requirements.txt
├── web/                      # React web interface
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── lib/api.ts        # API client & hooks
│   │   └── App.tsx           # Main app with routing
│   └── Dockerfile
├── android/                  # Android TV & Mobile app
│   └── app/src/main/java/    # Kotlin (Compose + ExoPlayer)
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # Technical deep-dive
│   ├── DEPLOYMENT.md         # Deployment guide
│   ├── SETUP.md              # Setup & usage guide
│   └── RELEASING.md          # APK release process
├── docker-compose.yml
└── .env.example
```

---

## 🔧 Development

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # Edit with your credentials
uvicorn app.main:app --reload
```

### Web App

```bash
cd web
npm install
npm run dev
```

### Android

Open the `android/` folder in Android Studio and build.

---

## 🔒 Security — [Details](docs/ARCHITECTURE.md#-security)

- **JWT Authentication** — Short-lived access tokens with [refresh token rotation](docs/ARCHITECTURE.md#authentication-flow)
- **User Authorization** — Optional [`AUTH_USERS`](docs/SETUP.md#-advanced-features) whitelist
- **Rate Limiting** — SlowAPI middleware on all endpoints
- **CORS Protection** — Restricted to configured origins
- **Input Validation** — Pydantic schemas prevent injection attacks
- **Security Headers** — Standard headers on all responses

---

## 📚 Documentation

| Guide                                    | Description                                                           |
| :--------------------------------------- | :-------------------------------------------------------------------- |
| **[Setup & Usage](docs/SETUP.md)**       | How the app works, bot commands, login methods, and troubleshooting   |
| **[Deployment](docs/DEPLOYMENT.md)**     | Docker, VPS, Railway, Render, and CapRover deployment                 |
| **[Architecture](docs/ARCHITECTURE.md)** | Technical deep-dive: streaming engine, API endpoints, database models |
| **[Releasing](docs/RELEASING.md)**       | APK build automation and signing via GitHub Actions                   |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PyroTGFork](https://github.com/TelegramPlayGround/pyrogram) — Telegram MTProto library
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [React](https://react.dev/) — Frontend library
- [Jetpack Compose for TV](https://developer.android.com/training/tv/compose) — Android TV UI toolkit
- [ExoPlayer](https://github.com/google/ExoPlayer) — Android media player
