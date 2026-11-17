# SOC Job Search Automation

Automated SOC Analyst job search system covering the UK, India, Germany, and the Netherlands.

**Current stage: GitHub infrastructure and placeholders only.** No job searching,
applications, networking, Google Sheets writes, or credentials are implemented.
Each placeholder prints its name, UTC and local execution timestamps, and a
successful completion message. This verifies execution infrastructure only.

## Architecture and files

Three independent workflows execute three separate Python entry points. No
workflow depends on another. Each has its own concurrency group and five-minute
timeout, so a failure in one does not cancel or block the other agents.

```text
.github/workflows/{uk,india,eu}-agent.yml
agents/{uk,india,eu}_agent.py
config/settings.yaml
utils/__init__.py
tests/test_infrastructure.py
requirements.txt
.gitignore
LICENSE
README.md
```

## Daily schedule

| Workflow | Coverage | Local times, every day | IANA time zone |
| --- | --- | --- | --- |
| uk-agent.yml | Entire United Kingdom | 08:00, 14:00, 20:00 | Europe/London |
| india-agent.yml | Entire India | 08:00, 14:00, 20:00 | Asia/Kolkata |
| eu-agent.yml | Germany and Netherlands only | 08:00, 14:00, 20:00 | Europe/Berlin |

Each workflow uses `cron: '0 8,14,20 * * *'` with the native `timezone` field.
UK and EU schedules automatically follow daylight saving time; India stays at
UTC+05:30. Setting the job's `TZ` also aligns log context, but the schedule's
`timezone` field is what controls when GitHub triggers it. Manual execution runs
immediately and is not limited to scheduled hours.

Expected UTC equivalents:

| Agent | Winter UTC | Summer UTC |
| --- | --- | --- |
| UK | 08:00, 14:00, 20:00 | 07:00, 13:00, 19:00 |
| India | 02:30, 08:30, 14:30 | 02:30, 08:30, 14:30 |
| EU | 07:00, 13:00, 19:00 | 06:00, 12:00, 18:00 |

GitHub schedules are best effort: runs may be delayed or skipped during high
load, especially at the start of an hour. Scheduled workflows run from the
default branch and are disabled in public repositories after 60 days without
repository activity. Check Actions periodically and re-enable if needed.
See [GitHub scheduling documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## GitHub Actions configuration

Every workflow uses standard `ubuntu-latest`, Python 3.13, a dependency install,
infrastructure validation, its own placeholder, and an always-run status summary.
The checkout and setup-python actions are pinned to full release commit SHAs.
The token has only `contents: read`; checkout does not persist credentials.
Failures propagate to the workflow result (no `continue-on-error`). GitHub retains
step logs and displays a run summary. No artifacts or private data are uploaded.

Concurrency is limited to one running execution per agent, across branches and
manual/scheduled triggers, with `cancel-in-progress: false`. Different agents may
run concurrently. GitHub can replace an older pending run with a newer pending
run; this is not a durable queue for every invocation.

Schedules are maintained in the workflow files. `config/settings.yaml` describes
the same settings, and tests detect drift. It does not dynamically generate cron.

## Run and monitor manually

1. Open this repository's **Actions** tab.
2. Choose **UK SOC Job Search Agent**, **India SOC Job Search Agent**, or
   **EU SOC Job Search Agent**.
3. Select **Run workflow**, choose `main`, then select **Run workflow** again.
4. Open the new run, then the **Run ... placeholder** job.
5. Expand **Execute ... placeholder** to see the agent name and timestamps.
6. Confirm that the run concludes **Success**. Dispatching alone is not proof
   of successful execution.

To monitor failures, filter Actions by failed status, open the failed job and
step, and inspect its error. Fix the underlying configuration before rerunning.
Use **Re-run failed jobs** for a transient failure. For a code fix, commit the fix
and dispatch a new run on `main`; rerunning an old run uses its old commit.
Configure GitHub Actions notifications in personal notification settings if desired.
Scheduled runs and manual smoke tests should be distinguished when reporting
results: smoke tests do not prove a future schedule will start on time.

## Local validation

Use Python 3.13 and run from the repository root:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q agents utils tests
python -m unittest discover -s tests -v
python agents/uk_agent.py
python agents/india_agent.py
python agents/eu_agent.py
```

Tests parse all workflow YAML, check schedule/config consistency, independent
concurrency groups, minimal permissions, runner labels, and Python syntax. They
also exercise the three placeholders and check winter/summer time-zone offsets.
GitHub's actual workflow execution remains the integration validation.

## Security and free operation

This repository is PUBLIC. Never commit passwords, tokens, API keys, Google
credentials, personal CVs, application records, or job-search state. `.gitignore`
excludes common credential files, `.env` files, Python caches and private runtime
directories. Ignore rules are not secret detection: inspect every staged diff.
Never force-add private files. If a secret is committed, revoke it immediately;
removing the current file does not remove it from Git history.

Future credentials belong in **Settings > Secrets and variables > Actions**,
referenced only by the workflow that needs them. Do not echo secrets, dump the
environment, enable verbose authentication logging, or publish private data in
public workflow logs or artifacts. No secrets are needed for this initial setup.

Only standard GitHub-hosted Ubuntu runners are used. Standard runner execution
in public repositories is free; no larger runners, paid cloud servers, paid APIs,
third-party automation services, or Codespaces are required. See
[GitHub billing documentation](https://docs.github.com/en/actions/concepts/billing-and-usage).
Keep the repository public to retain these free execution conditions.

## Future Google Sheets integration

The separate **Test Google Sheets Connection** workflow now tests access to the
existing private workbook. It is manually triggered and does not change the
three agent schedules. The test creates `UK_JOBS`, `INDIA_JOBS`, `EU_JOBS`, and
`EXECUTION_LOGS` if missing, without deleting or changing existing worksheets.
It appends one uniquely identified test row to `EXECUTION_LOGS` and reads it
back. The three job-search placeholders do not yet write jobs.

Before running this test:

1. In Google Cloud, enable the Google Sheets API, create a service account,
   and create a JSON key for that account. Keep the key private.
2. Share the **existing** workbook with the service account's `client_email`
   as **Editor**. Do not change the workbook's general access to public.
3. In this repository, open **Settings > Secrets and variables > Actions**.
   Create `GOOGLE_SERVICE_ACCOUNT_JSON` containing the entire JSON key and
   `GOOGLE_SHEET_ID` containing the existing spreadsheet ID.
4. Open **Actions > Test Google Sheets Connection > Run workflow** on `main`.
   Confirm the run succeeds and locate its `SHEETS_TEST_...` row in
   `EXECUTION_LOGS`.

The test uses only the Sheets API scope and loads credentials from the
environment in memory. A missing secret, disabled API, incorrect spreadsheet
ID, or missing service-account sharing causes the workflow to fail with a
sanitised message. Never paste the JSON key into an issue, log, source file,
or chat. Hosted runner filesystems are temporary and are not durable job-search
memory; durable private state and duplicate-safe writes remain future work.

## License

MIT; see LICENSE.
