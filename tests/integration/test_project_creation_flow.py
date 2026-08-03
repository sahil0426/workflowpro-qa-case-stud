"""
Part 3 — API + UI + Mobile integration test.

Strategy:
  1. API layer creates the source-of-truth project (fast, deterministic
     setup — avoids doing UI-driven creation just to reach the assertion we
     actually care about).
  2. Desktop UI (Playwright) verifies the project renders correctly for the
     correct tenant, using retrying expect() calls to absorb dynamic-loading
     timing rather than fixed sleeps.
  3. Mobile web (BrowserStack real device) repeats the visibility check to
     catch responsive-layout-only bugs (e.g., project card hidden behind a
     mobile nav collapse).
  4. Security check re-uses the API layer with Company2's token to assert
     the backend itself enforces tenant isolation — checked at the API
     level (not just "hidden in UI"), since UI-only checks can pass even if
     the API leaks data to any client that queries it directly.
"""

import os
import time
import pytest
import requests
from playwright.sync_api import sync_playwright, expect

API_BASE_URL = os.environ.get("WFP_API_BASE_URL", "https://api.workflowpro.com")
UI_BASE_URL_TEMPLATE = "https://{tenant}.workflowpro.com"
DEFAULT_TIMEOUT_MS = 15000


# ---------- Fixtures ----------

@pytest.fixture(scope="function")
def tenant_a_token():
    """API auth token for Company1 (the tenant that should be able to see the project)."""
    resp = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={
            "email": os.environ["WFP_COMPANY1_ADMIN_EMAIL"],
            "password": os.environ["WFP_COMPANY1_ADMIN_PASSWORD"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


@pytest.fixture(scope="function")
def tenant_b_token():
    """API auth token for Company2 — used purely to prove tenant isolation."""
    resp = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={
            "email": os.environ["WFP_COMPANY2_ADMIN_EMAIL"],
            "password": os.environ["WFP_COMPANY2_ADMIN_PASSWORD"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


@pytest.fixture(scope="function")
def created_project(tenant_a_token):
    """Creates a project for Company1 via the API and guarantees cleanup,
    even if the test body fails partway through."""
    payload = {
        "name": f"QA Automation Project {int(time.time())}",
        "description": "Created by integration test — safe to delete",
        "team_members": [],
    }
    headers = {
        "Authorization": f"Bearer {tenant_a_token}",
        "X-Tenant-ID": "company1",
    }

    create_resp = requests.post(
        f"{API_BASE_URL}/api/v1/projects", json=payload, headers=headers, timeout=10
    )
    assert create_resp.status_code == 201, (
        f"Project creation failed: {create_resp.status_code} {create_resp.text}"
    )
    project = create_resp.json()

    yield project

    # Cleanup regardless of test outcome
    requests.delete(
        f"{API_BASE_URL}/api/v1/projects/{project['id']}", headers=headers, timeout=10
    )


# ---------- Test ----------

def test_project_creation_flow(created_project, tenant_a_token, tenant_b_token):
    project_id = created_project["id"]
    project_name = created_project["name"]

    # ---- 2. Web UI verification (Chromium desktop) ----
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            base_url=UI_BASE_URL_TEMPLATE.format(tenant="company1"),
        )
        context.set_default_timeout(DEFAULT_TIMEOUT_MS)
        page = context.new_page()

        # Bootstrap an authenticated session directly instead of re-running a
        # full UI login flow for every integration test.
        page.goto("/session/bootstrap", wait_until="commit")
        page.evaluate(f"window.localStorage.setItem('wfp_token', '{tenant_a_token}')")

        page.goto("/projects")
        expect(page.locator(".loading-spinner")).to_be_hidden(timeout=DEFAULT_TIMEOUT_MS)

        project_card = page.locator(f".project-card:has-text('{project_name}')")
        expect(project_card).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

        context.close()
        browser.close()

    # ---- 3. Mobile web verification (BrowserStack real device) ----
    bstack_capabilities = {
        "browserName": "Safari",
        "bstack:options": {
            "deviceName": "iPhone 14",
            "osVersion": "16",
            "realMobile": "true",
            "userName": os.environ["BROWSERSTACK_USERNAME"],
            "accessKey": os.environ["BROWSERSTACK_ACCESS_KEY"],
            "sessionName": f"project_creation_mobile_{project_id}",
            "networkLogs": "true",
        },
    }
    bstack_ws_endpoint = (
        "wss://cdp.browserstack.com/playwright?caps="
        + requests.utils.quote(str(bstack_capabilities))
    )

    with sync_playwright() as p:
        mobile_browser = p.chromium.connect(bstack_ws_endpoint)
        mobile_context = mobile_browser.new_context(
            base_url=UI_BASE_URL_TEMPLATE.format(tenant="company1")
        )
        mobile_context.set_default_timeout(DEFAULT_TIMEOUT_MS)
        mobile_page = mobile_context.new_page()

        mobile_page.goto("/session/bootstrap", wait_until="commit")
        mobile_page.evaluate(f"window.localStorage.setItem('wfp_token', '{tenant_a_token}')")
        mobile_page.goto("/projects")

        # On mobile, the project list may be behind a collapsed nav / tab.
        mobile_nav_toggle = mobile_page.locator("[data-testid='mobile-nav-toggle']")
        if mobile_nav_toggle.is_visible():
            mobile_nav_toggle.click()
            mobile_page.locator("text=Projects").click()

        expect(mobile_page.locator(".loading-spinner")).to_be_hidden(timeout=DEFAULT_TIMEOUT_MS)
        mobile_project_card = mobile_page.locator(f".project-card:has-text('{project_name}')")
        expect(mobile_project_card).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

        mobile_context.close()
        mobile_browser.close()

    # ---- 4. Tenant isolation — enforced at the API, not just hidden in UI ----
    isolation_check = requests.get(
        f"{API_BASE_URL}/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {tenant_b_token}", "X-Tenant-ID": "company2"},
        timeout=10,
    )
    assert isolation_check.status_code in (403, 404), (
        f"Tenant isolation breach: Company2 token got status "
        f"{isolation_check.status_code} for a Company1 project"
    )

    company2_list = requests.get(
        f"{API_BASE_URL}/api/v1/projects",
        headers={"Authorization": f"Bearer {tenant_b_token}", "X-Tenant-ID": "company2"},
        timeout=10,
    )
    company2_ids = {p["id"] for p in company2_list.json().get("projects", [])}
    assert project_id not in company2_ids, "Project leaked into Company2's project list"
