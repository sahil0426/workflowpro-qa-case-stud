# Test Automation Framework Design — WorkFlow Pro

## 1. Goals

- Support web (Chrome, Firefox, Safari) and mobile (iOS, Android) testing
- Handle multiple tenant environments (company1.workflowpro.com, company2.workflowpro.com, ...)
- Test different user roles (Admin, Manager, Employee) with varying permissions
- API testing for backend services
- BrowserStack integration for cross-platform coverage
- CI/CD pipeline integration

## 2. Folder Structure

```
workflowpro-qa/
├── config/
│   ├── environments/
│   │   ├── company1.staging.yaml
│   │   ├── company2.staging.yaml
│   │   └── production.readonly.yaml
│   ├── browserstack.yaml
│   └── config_loader.py
├── src/
│   ├── api/
│   │   ├── clients/
│   │   │   ├── base_client.py        # auth, headers, retries, tenant header injection
│   │   │   └── projects_client.py
│   │   └── models/                   # request/response schemas
│   ├── ui/
│   │   ├── pages/
│   │   │   ├── base_page.py          # common waits, navigation, screenshot-on-fail
│   │   │   ├── login_page.py
│   │   │   ├── dashboard_page.py
│   │   │   └── project_page.py
│   │   └── components/               # nav bar, modals, toasts
│   ├── mobile/
│   │   ├── ios/
│   │   └── android/                  # Appium-style screen objects, if native app in scope
│   └── utils/
│       ├── test_data_factory.py      # builds/cleans up projects, users, tenants
│       ├── auth_helper.py            # token/session management, 2FA bypass for test accounts
│       └── retry.py
├── tests/
│   ├── ui/
│   ├── api/
│   ├── mobile/
│   └── integration/
├── fixtures/
│   └── conftest.py
├── reports/
├── ci/
└── pytest.ini
```

**Rationale:** API and UI layers are separate and composable so integration
tests (Part 3) can build state via the API and verify via the UI/mobile
layers without duplicating request or selector logic. Page Object Model
(`ui/pages`) keeps one place to update per workflow when the UI changes.
Mobile mirrors the same structure so native and web tests share conventions.

## 3. Configuration Management

Per-tenant YAML config (see `test-data/config/environments/` in this repo)
holds base URLs, tenant IDs, timeouts, and *references* to credentials
(environment variable names), never raw secrets. A `--env=company1.staging`
CLI flag selects which config loads at session start.

Browser/device matrix (Chrome/Firefox/Safari desktop, iOS/Android via
BrowserStack) is defined as data in `config/browserstack.yaml` and consumed
via `pytest.mark.parametrize`, so adding a new device is a config change,
not a code change.

Role-based test data (Admin/Manager/Employee) is created and torn down via
the API layer directly (`test_data_factory.py`) for speed and parallel-safe
isolation — each test gets its own freshly created user/project rather than
relying on shared, hand-maintained accounts.

## 4. Missing Requirements — Questions For The Team

**Test data management**
- Is there a dedicated, resettable staging environment per tenant?
- Who owns seed data for roles/permissions?
- What's the cleanup policy — per-test API delete, or nightly reset job?

**Reporting**
- Existing reporting tooling (Allure, ReportPortal, JUnit XML into a dashboard)?
- Is failure notification (Slack/Teams) expected, or pull-based only?
- Do we need historical flakiness tracking / auto-quarantine of flaky tests?

**Parallel execution**
- Can tests run in parallel across tenants safely (isolated data), or are
  there shared/global resources that would collide?
- What's the CI runtime budget, and does the BrowserStack plan support the
  concurrency needed to hit it?

**Environments & access**
- Is there a stable staging environment mirroring production tenant
  behavior (loading times, 2FA), or must this run against production with
  synthetic accounts?
- Any rate limits on the API or BrowserStack sessions constraining
  parallelization?

**Scope & ownership**
- Which mobile OS/device versions are actually in the supported matrix
  (affects BrowserStack plan cost)?
- Is visual regression testing in scope, or purely functional/flow testing?
- Who maintains 2FA bypass / test-OTP generation for automated accounts?
