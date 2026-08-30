# Contributing to TelePlay

First off, thank you for considering contributing to TelePlay! 🎉

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs what actually happened
- **Logs** from `docker-compose logs backend`
- **Environment** (OS, Docker version, etc.)

### Suggesting Features

Feature requests are welcome! Please:

- Check if the feature has already been suggested
- Explain why it would be useful
- Consider if it fits the project scope

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests if available
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn app.main:app --reload
```

### Web

```bash
cd web
npm install
npm run dev
```

### Android TV

Open `/android` in Android Studio and build normally.

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions focused and small

### TypeScript/React (Web)

- Use functional components with hooks
- Follow existing patterns in the codebase
- Use TypeScript types, avoid `any`

### Kotlin (Android TV)

- Follow Kotlin conventions
- Use Compose best practices
- Keep composables focused

## Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep first line under 72 characters
- Reference issues when applicable (`Fix #123`)

## Questions?

Feel free to open an issue for any questions about contributing!
