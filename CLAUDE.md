# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

myMovieDB is a Flask-based web application for managing movies with comprehensive user authentication, including 2FA support, email validation, and encrypted data storage.

## Development Setup

### Environment Setup
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate.ps1

# Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
1. Copy `moviedb/config.sample.json` to `instance/config.dev.json`
2. Required configuration keys:
   - `SQLALCHEMY_DATABASE_URI`: Database connection string
   - `SECRET_KEY`: Flask secret key for sessions/tokens
   - `DATABASE_ENCRYPTION_KEY`: Key for encrypting sensitive database fields
   - `DATABASE_ENCRYPTION_SALT`: Salt for encryption key derivation
   - `POSTMARK_SERVER_TOKEN`: Email service token (if using email features)
   - `CELERY`: Celery configuration object (broker_url, result_backend, beat_schedule, etc.)
     - Requires Redis running on `broker_url` and `result_backend`

### Database Migration

**First time setup:**
```bash
set FLASK_APP=app.py  # Windows: set, Linux: export
flask db init
```

Edit `migrations/env.py` (around line 30) to add:
```python
from moviedb import db
import moviedb.models  # noqa: F401
target_metadata = db.metadata
```

```bash
flask db migrate -m "Initial migration"
flask db upgrade
```

**Subsequent migrations:**
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Running the Application
```bash
flask run
```

### Running Celery (Background Tasks)

The application uses Celery for asynchronous and scheduled tasks. Redis must be running before starting Celery.

**Start the worker** (processes tasks):
```bash
# Windows
celery -A celery_app:celery_app worker --loglevel=info --pool=gevent --concurrency=10 --without-gossip --without-mingle --without-heartbeat -E

# Linux
celery -A celery_app:celery_app worker --loglevel=info --concurrency=10 --without-gossip --without-mingle --without-heartbeat -E
```

**Start the beat scheduler** (triggers scheduled tasks):
```bash
celery -A celery_app:celery_app beat --loglevel=info
```

**Note:** You need three separate terminals: Flask, Celery Worker, and Celery Beat.

## Architecture

### Application Factory Pattern
- Entry point: `app.py` calls `create_app()` from `moviedb/__init__.py`
- `create_app()` initializes all Flask extensions, registers blueprints, and configures the app
- Configuration loaded from JSON files in `instance/` directory

### Core Components

**Extensions** (`moviedb/infra/modulos.py`):
- `db`: SQLAlchemy database instance
- `migrate`: Flask-Migrate for database migrations
- `login_manager`: Flask-Login for session management
- `bootstrap`: Bootstrap-Flask for UI styling

**Celery Integration** (`moviedb/infra/celery.py`):
- Celery initialized via `celery_init_app()` in `create_app()`
- Uses Flask application context for tasks
- Auto-discovers tasks in `moviedb.tasks` package
- Configuration loaded from `CELERY` key in config JSON
- Entry point: `celery_app.py` for worker/beat processes

**Blueprints** (`moviedb/blueprints/`):
- `auth`: Authentication routes (login, register, 2FA, password reset, profile)
- `root`: Main application routes

**Models** (`moviedb/models/`):
- `User`: User account with email validation, password hashing, 2FA support, and avatar
- `Backup2FA`: 2FA backup codes for account recovery
- `BasicRepositoryMixin`: Common CRUD operations (get_by_id, get_all, count_all, etc.)
- `AuditMixin`: Adds created_at/updated_at timestamps
- `EncryptedType`: Custom SQLAlchemy type for transparent field encryption using Fernet

**Services** (`moviedb/services/`):
- `UserService`: User account operations (creation, validation)
- `User2FAService`: 2FA setup, validation, and backup code management
- `TokenService`: JWT generation/validation for email verification and password resets
- `EmailService`: Email sending via Postmark with template support
- `ImageProcessingService`: Avatar/photo processing and resizing
- `QRCodeService`: QR code generation for 2FA setup

### Key Patterns

**Authentication Flow:**
1. User registers → `User.ativo = False` → email verification token sent
2. User clicks email link → token validated → `User.ativo = True`
3. Login checks password and active status
4. If 2FA enabled (`User.usa_2fa`), requires TOTP code or backup code
5. Flask-Login uses alternative tokens: `user_id = f"{uuid}|{password_hash[-15:]}"` to auto-logout on password change

**Database Encryption:**
- Sensitive fields use `EncryptedType` (e.g., `User._otp_secret`)
- Encryption key derived using PBKDF2 with configurable salt
- Automatic encryption on write, decryption on read

**2FA Implementation:**
- Uses TOTP (pyotp) with QR code provisioning
- Backup codes hashed with werkzeug.security
- Session timeout for 2FA challenges (configurable via `2FA_SESSION_TIMEOUT`)
- Prevents TOTP reuse via `User.ultimo_otp` tracking

**Image Handling:**
- Photos stored as base64 in database
- Automatic avatar generation from uploaded photos
- MIME type validation and dimension constraints

**Celery Tasks** (`moviedb/tasks/`):
- `send_email_task`: Asynchronous email sending with retry logic (max 3 retries, exponential backoff)
- `remover_codigos_expirados_task`: Scheduled task to remove expired 2FA backup codes
- All tasks use `@shared_task` decorator and Flask application context
- Tasks auto-discovered via `celery_init_app()` in `moviedb/infra/celery.py`
- Scheduled tasks configured in `CELERY.beat_schedule` in config JSON

## Code Conventions

Follow PEP 8 and the guidelines in `.github/global-copilot-instructions.md`:
- Type hints on all functions
- Docstrings following PEP 257
- 4-space indentation, max 79 characters per line
- Clear comments explaining complex logic
- Handle edge cases with proper exception handling

## Important Notes

- Always work within the virtual environment
- Database migrations must be applied before running the app
- Email features require `SEND_EMAIL: true` and valid Postmark credentials
- Password validation rules are configurable (min length, character requirements)
- The `anonymous_required` decorator restricts routes to non-authenticated users
- User sessions are invalidated when password changes (via alternative token pattern)
- Redis must be running for Celery to function (default: redis://127.0.0.1:6379/0)
- Celery tasks require both worker and beat processes to be running for scheduled tasks
