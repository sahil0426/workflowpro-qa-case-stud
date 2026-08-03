# Sample Test Execution Report

This repo was built without access to a live WorkFlow Pro staging
environment or real BrowserStack/API credentials, so this document
describes the expected execution report format and results, rather than an
actual run log. Once pointed at a real environment (`pytest
--html=reports/report.html --self-contained-html`), this file would be
replaced by the generated HTML report.

## Expected suite

| Test                                                   | Layer        | Purpose                                            |
|---------------------------------------------------------|--------------|-------------------------------------------------------|
| `tests/ui/test_login.py::test_user_login`                | UI           | Verifies successful login + dashboard render        |
| `tests/ui/test_login.py::test_multi_tenant_access`       | UI           | Verifies tenant-scoped data on login                |
| `tests/integration/test_project_creation_flow.py::test_project_creation_flow` | API + UI + Mobile | Full create → verify (desktop) → verify (mobile) → isolation check |

## Reporting strategy in CI

- `pytest-html` generates a self-contained HTML report per run, uploaded as
  a CI artifact (see `ci/github-actions-ci.yml`).
- Failures include Playwright trace/screenshot capture (`--tracing=retain-on-failure`
  recommended once wired into a real environment) to speed up triage.
- `pytest-rerunfailures` retries tests marked `@pytest.mark.flaky_known`
  once, to absorb known-transient infra issues without masking real bugs
  (unmarked failing tests do NOT get an automatic retry).
- Nightly scheduled run (see CI config) catches regressions independent of
  code changes, e.g. due to environment drift.
