"""
Part 1 — Fixed login tests.

Original issues fixed here:
- Race conditions on navigation / dynamic content (now uses expect() retrying
  assertions and wait_for_url instead of one-shot checks).
- Hardcoded credentials (now pulled from environment variables).
- No 2FA handling (login() now branches on whichever screen appears).
- No fixture-based teardown (browser_context fixture guarantees cleanup).
- No fixed viewport (pinned to 1440x900 so CI and local behave the same).
- Strict URL equality (replaced with wait_for_url + expect().to_have_url).
"""

import os
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get("WFP_BASE_URL", "https://app.workflowpro.com")
DEFAULT_TIMEOUT_MS = int(os.environ.get("WFP_TIMEOUT_MS", "15000"))


def _get_credentials(user_key: str):
    """Pull credentials from environment variables / secret store — never
    hardcode credentials in test code."""
    creds = {
        "admin_company1": {
            "email": os.environ["WFP_ADMIN_COMPANY1_EMAIL"],
            "password": os.environ["WFP_ADMIN_COMPANY1_PASSWORD"],
        },
        "user_company2": {
            "email": os.environ["WFP_USER_COMPANY2_EMAIL"],
            "password": os.environ["WFP_USER_COMPANY2_PASSWORD"],
        },
    }
    return creds[user_key]


@pytest.fixture
def browser_context():
    """Shared, properly torn-down browser/context per test, with a fixed
    viewport so behavior is consistent across CI machines and local runs."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            base_url=BASE_URL,
        )
        context.set_default_timeout(DEFAULT_TIMEOUT_MS)
        try:
            yield context
        finally:
            context.close()
            browser.close()


def login(page, email: str, password: str):
    """Reusable login helper that handles the optional 2FA step."""
    page.goto("/login")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click("#login-btn")

    # Some accounts require 2FA — branch on whichever screen actually
    # appears instead of assuming a fixed flow.
    otp_input = page.locator("#otp-code")
    dashboard_marker = page.locator(".welcome-message")

    otp_input.or_(dashboard_marker).first.wait_for(state="visible")

    if otp_input.is_visible():
        test_otp = os.environ["WFP_TEST_OTP_CODE"]
        otp_input.fill(test_otp)
        page.click("#otp-submit-btn")

    # Wait for the actual navigation, not just the click, and allow slower
    # tenants extra time.
    page.wait_for_url("**/dashboard**", timeout=DEFAULT_TIMEOUT_MS)


def test_user_login(browser_context):
    page = browser_context.new_page()
    creds = _get_credentials("admin_company1")

    login(page, creds["email"], creds["password"])

    # expect() auto-retries until the condition is true or times out,
    # instead of checking visibility once.
    expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=DEFAULT_TIMEOUT_MS)
    expect(page.locator(".welcome-message")).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)


def test_multi_tenant_access(browser_context):
    page = browser_context.new_page()
    creds = _get_credentials("user_company2")

    login(page, creds["email"], creds["password"])

    # Wait for the project list container to leave its loading state before
    # reading its contents, rather than trusting a synchronous .all() snapshot.
    project_list = page.locator("[data-testid='project-list']")
    expect(project_list.locator(".loading-spinner")).to_be_hidden(timeout=DEFAULT_TIMEOUT_MS)

    project_cards = page.locator(".project-card")
    expect(project_cards.first).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    count = project_cards.count()
    assert count > 0, "Expected at least one project for company2's user"

    for i in range(count):
        text = project_cards.nth(i).text_content()
        assert "Company1" not in text, f"Tenant isolation breach: saw Company1 data — {text}"
