# Testing Approach, Root-Cause Analysis & Assumptions

## Part 1 — Flaky Login Test

### Issues identified
1. No auto-waiting on navigation — assertion runs before redirect/dynamic content finishes loading.
2. `.is_visible()` used as a one-shot check instead of a retrying assertion.
3. Hardcoded credentials, no 2FA handling (some accounts require it).
4. No fixtures / no guaranteed browser teardown on failure — resource leaks affect later tests.
5. No CI-appropriate timeouts (default timeouts assume a fast environment).
6. Strict string equality on URL (breaks on trailing slash / query params).
7. No fixed viewport — CI runs different browsers/screen sizes than local.
8. `.locator(...).all()` is a snapshot, not a retrying query — can read a partial list while multi-tenant data is still loading.
9. No wait for network/loading state before asserting tenant-scoped data.
10. No retry strategy to absorb legitimately transient infra issues.

### Why this is worse in CI than locally
CI runners are shared/slower, run cold (no warm cache), typically default to headless with a different viewport than local dev, may run tests in parallel against shared test accounts, and often hit a different (higher latency) network path to staging. None of these are present when a developer manually runs (and effectively "retries") a test locally.

### Fix summary
See `tests/ui/test_login.py`: pytest fixtures with guaranteed teardown, `expect()` retrying assertions instead of one-shot checks, explicit 2FA branch, fixed viewport, credentials from environment variables, generous CI-tuned timeouts, `wait_for_url` instead of raw equality checks.

## Part 2 — Framework Design

See `test-plan.md`.

## Part 3 — API + UI + Mobile Integration

### Strategy
1. **API-first setup.** The project is created via the API (fast, deterministic) rather than driven through the UI, to isolate what the test is actually verifying (rendering/access), not setup timing.
2. **UI verification** uses `expect()` retrying assertions against a loading-spinner-hidden state before reading content.
3. **Mobile verification** runs against a real device via BrowserStack (not a resized desktop viewport), and explicitly handles a collapsed mobile nav before searching for the project card.
4. **Tenant isolation is checked at the API layer**, at two levels: direct object access (`GET /projects/{id}` with the wrong tenant's token) and list enumeration (`GET /projects` must not include the other tenant's project). Checking only "is it hidden in the UI" is not sufficient evidence of a secure backend — a UI-only check can pass even if the API itself leaks data to a client that queries it directly.
5. **Cleanup** happens in a fixture teardown (`yield` pattern), so it runs even if an assertion earlier in the test fails, preventing orphaned test data in staging.

### Assumptions
1. Test accounts have a supported "test OTP" path, or 2FA can be disabled for automation accounts.
2. "Mobile accessibility" refers to responsive web (tested via BrowserStack real-device browsers), not a separate native app. If a native app is in scope, the mobile layer would switch to Appium against native screen objects instead.
3. A session-bootstrap or token-injection mechanism exists (or could be added) to authenticate a UI session without repeating a full login flow on every integration test, keeping runtime reasonable.
4. Staging environments per tenant are stable enough for CI to hit directly and aren't shared with manual QA in a way that causes data collisions.
5. `403` and `404` are both acceptable "no access" responses for isolation checks; exact status code semantics would be confirmed with the backend team in a real engagement.

### Required environment variables
```
WFP_BASE_URL
WFP_API_BASE_URL
WFP_ADMIN_COMPANY1_EMAIL / WFP_ADMIN_COMPANY1_PASSWORD
WFP_COMPANY1_ADMIN_EMAIL / WFP_COMPANY1_ADMIN_PASSWORD
WFP_COMPANY2_ADMIN_EMAIL / WFP_COMPANY2_ADMIN_PASSWORD
WFP_USER_COMPANY2_EMAIL / WFP_USER_COMPANY2_PASSWORD
WFP_TEST_OTP_CODE
BROWSERSTACK_USERNAME / BROWSERSTACK_ACCESS_KEY
```
