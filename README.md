# WorkFlow Pro — QA Automation Case Study

Solution repository for the Bynry Inc. QA Automation Engineering Intern case study
(B2B SaaS Platform Testing — Multi-Platform Automation).

## Contents

```
.
├── README.md                     <- you are here
├── test-plan.md                  <- Part 2: framework design, config strategy, open questions
├── docs/
│   └── testing-approach.md       <- assumptions + strategy notes for all 3 parts
├── requirements.txt
├── pytest.ini
├── test-data/
│   └── config/environments/      <- sample per-tenant YAML configs
├── tests/
│   ├── ui/
│   │   └── test_login.py         <- Part 1: fixed flaky login test
│   ├── integration/
│   │   └── test_project_creation_flow.py   <- Part 3: API + UI + BrowserStack mobile
│   ├── api/                      <- placeholder for pure API test suite
│   └── mobile/                   <- placeholder for native mobile suite, if needed
├── ci/
│   └── github-actions-ci.yml     <- sample CI pipeline
└── reports/
    └── sample_test_execution_report.md
```

## Setup

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd workflowpro-qa-case-study

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install --with-deps

# 4. Copy the example environment config and fill in real values
cp test-data/config/environments/company1.staging.yaml.example \
   test-data/config/environments/company1.staging.local.yaml

# 5. Set required environment variables (see docs/testing-approach.md for the full list)
export WFP_BASE_URL="https://app.workflowpro.com"
export WFP_ADMIN_COMPANY1_EMAIL="..."
export WFP_ADMIN_COMPANY1_PASSWORD="..."
# ...etc — see docs/testing-approach.md
```

## Running the tests

```bash
# Run everything
pytest -v

# Run just the fixed login test (Part 1)
pytest tests/ui/test_login.py -v

# Run the full API + UI + mobile integration flow (Part 3)
pytest tests/integration/test_project_creation_flow.py -v

# Run with HTML report
pytest --html=reports/report.html --self-contained-html
```

## Notes

This case study was solved without access to a live WorkFlow Pro staging
environment or real BrowserStack/API credentials. The test code is written to
be **runnable as-is against a real environment** once credentials and base
URLs are supplied via environment variables — it is not pseudocode. Where a
live run wasn't possible, `reports/sample_test_execution_report.md` documents
expected behavior and how results would be reported in CI.

See `test-plan.md` for the framework design (Part 2) and
`docs/testing-approach.md` for reasoning, root-cause analysis, and
assumptions across all three parts.
