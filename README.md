# Automated Verification of a Financial Notification Dispatcher

**Name:** Ahmed Atif Abdalla

**Registration Number:** 24454/2024

**Module:** Software Verification & Validation

A Software Verification & Validation (V&V) practical exam project demonstrating a layered testing strategy 
— unit tests, integration tests, and CI automation — for a financial SMS notification system.

## Overview

`NotificationEngine` dispatches SMS notifications with:
- E.164 phone number validation
- Idempotency checks (prevents duplicate sends)
- Primary gateway delivery with automatic retry
- Backup gateway failover
- Persistent status tracking (`SENT`, `SENT_BACKUP`, `FAILED`)

## Project Structure
├── notification_engine.py # Core business logic under test
├── sqlite_repository.py # Real + intentionally broken SQLite repositories
├── tests/
│ ├── test_unit.py # 7 isolated unit tests (Mock-based)
│ └── test_integration.py # 3 integration tests (real in-memory SQLite)
├── .github/workflows/ci.yml # GitHub Actions CI pipeline
└── requirements.txt

## Testing Strategy

### Unit Tests (`tests/test_unit.py`) — 7 tests
Fully isolated using `unittest.mock.Mock()` — zero database or network interaction. Covers:
- Phone number validation boundaries (valid vs. invalid E.164 formats)
- Idempotency (`ALREADY_SENT` short-circuit)
- Retry logic (primary fails once, succeeds on retry)
- Fallback gateway failover (primary fails twice, backup succeeds)
- Complete failure handling (both gateways fail)

### Integration Tests (`tests/test_integration.py`) — 3 tests
Uses a real in-memory SQLite database (`:memory:`) via a Pytest fixture. Covers:
- Successful dispatch actually persisted to the database
- Idempotency verified against real SQL state
- **The "Mock Lie" demonstration** — a deliberately broken repository (`BrokenSQLiteWalletRepository`) writes to a nonexistent table. 
This proves a bug invisible to mock-based unit tests is caught immediately by integration tests as a real `sqlite3.OperationalError`.

## CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs automatically on every push:
- **Matrix strategy** — tests run in parallel on Python 3.10 and 3.11
- **Fail-fast ordering** — unit tests run first, integration tests second
- **Coverage gate** — enforces ≥90% coverage via `pytest-cov` (`--cov-fail-under=90`); current suite achieves **95.54%**

## Running Locally

```bash
pip install -r requirements.txt
python -m pytest tests/test_unit.py -v
python -m pytest tests/test_integration.py -v
python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=90
```

## Key Concept: The Mock Lie

Unit tests using mocks verify that code *calls* dependencies correctly, but cannot verify those dependencies actually behave as assumed in production. This project includes a deliberate demonstration: a broken repository implementation passes all mock-based unit tests but fails immediately under integration testing against a real database — illustrating why both testing layers are necessary.
