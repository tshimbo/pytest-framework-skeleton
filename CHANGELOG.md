# Changelog

## 1.0.0 - 2026-09-17
- Test suite runs with warnings treated as errors: replaced deprecated `datetime.utcnow()` and closed leaked sockets in the HTTP integration tests
- mypy now runs in full strict mode
- CI on Python 3.11, 3.12, and 3.13 with current GitHub Actions versions
- Security workflow: gitleaks history scan, committed `.env` guard, and no-emoji check
- Lint fixes (unused imports, f-string without placeholders)
- MIT license

## 0.1.0 - 2026-01
- Initial pytest framework: fixture scopes, conftest hierarchy, parametrized tests, markers, HTML/JSON reports, coverage gate, GitHub Actions
