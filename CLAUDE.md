# CLAUDE.md — TheraSocial

## What This Is

Monolithic single-page Flask application for a mental health/wellness platform.
No build step — what you see is what ships.

## Architecture

### Backend
- **app.py** (~16,800 lines, ~131 API routes) — Flask + SQLAlchemy, the entire backend
- **models.py** — SQLAlchemy ORM models (User, Follow, Profile, Message, Post, Alert, etc.)
- **config.py** — Environment-based config, reads from env vars
- **auth.py** — AuthManager class, JWT + session auth
- **messaging.py** — Private messaging logic
- **security.py** — Encryption (Fernet), sanitization (bleach), CSRF
- **social.py** — Following, feeds, posts
- **tracking.py** — User activity and parameter tracking

### Frontend
- **templates/index.html** (~14,300 lines) — The entire SPA: HTML + CSS + inline JS
- **static/css/style.css** (~19KB) — External stylesheet
- **static/js/** — External JS modules:
  - `parameters-social.js` (155KB) — Parameter and social features
  - `circles-messages.js` (100KB) — Circle and messaging UI
  - `i18n.js` (271KB) — All translation strings
  - `feed-calendar.js` (20KB) — Feed calendar UI
  - `feed-updates.js` (5KB) — Feed update logic
  - `follow-requests.js` (17KB) — Follow request handling
  - `onboarding.js` (12KB) — User onboarding flow
  - `profile.js` (16KB) — Profile management
  - `triggers.js` (13KB) — Trigger alert logic
  - `utilities.js` (14KB) — Common utility functions

### Database
- PostgreSQL (psycopg2-binary) with connection pooling
- Flask-Migrate for schema migrations
- Redis for caching and sessions

## Languages / i18n

English, Hebrew (RTL), Arabic (RTL), Russian. All strings live in `static/js/i18n.js`.
RTL is handled via `dir="rtl"` attribute and CSS logical properties / directional overrides.

## Deployment

- Hosted on **Render**, auto-deploys from the `main` branch
- `render.yaml` defines the service; `Procfile` runs `gunicorn app:app`
- `init_db.py` runs as the release command
- Python 3.11 (see `runtime.txt`)
- No build step — static files served directly by Flask

## Key Dependencies

Flask 2.3, SQLAlchemy 2.0, Flask-Migrate, Flask-Limiter, Flask-Session,
Redis, psycopg2-binary, PyJWT, bcrypt, cryptography (Fernet), bleach,
SendGrid (email), WeasyPrint (PDF generation), gunicorn.

## Current Work Focus

**CSS, HTML structure, inline style cleanup, and JS-generated HTML for mobile width consistency.**

The branch `fix/mobile-width-consistency` is the active working branch.

## DO NOT Touch

- Database schema or migrations
- Authentication logic (auth.py, JWT, sessions)
- GDPR/privacy endpoints or consent flows
- Trigger logic (triggers.py, trigger-related routes)
- Email sending (SendGrid integration)
- Backend API routes in app.py

## Working in This Codebase

- **Read before editing.** Files are large. Use line offsets to read relevant sections.
- **index.html is the SPA.** All views are `<div>` sections toggled by JS. CSS is both
  inline (in index.html `<style>` blocks) and external (style.css).
- **JS-generated HTML** is scattered across the JS files in `static/js/`. Many elements
  get their styles from inline `style=` attributes set in JS string templates. These
  are a primary target for cleanup.
- **No framework.** Vanilla JS, no React/Vue/Angular. DOM manipulation is direct
  (`document.getElementById`, `innerHTML`, template literals).
- **No bundler/transpiler.** Edit the files directly. Changes are live on next deploy.
- **Test by opening in a browser.** There is no automated frontend test suite.
  Backend tests exist as standalone scripts (`backend_test.py`, `alerttest.py`, etc.)
  but there is no formal test runner.
- When fixing mobile width issues, check all four languages — Hebrew and Arabic
  flip the layout direction and can cause overflow differently than LTR languages.
