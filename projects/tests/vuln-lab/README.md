# vuln-lab — test corpus for the web-mode audit agent

A deliberately vulnerable mini storefront. It is a **test fixture**, not a
runnable product: there is no schema, no requirements file, and it should never
be served. Point the agent at it, let it run its pipeline, then score the report
against `ANSWER_KEY.md`.

```
legacy/utils.php     helpers — one of them looks like a sanitiser and is not
php/login.php        login form handler (mysqli)
php/search.php       product search (PDO) + inline template
php/profile.php      profile page, input travels through two helper functions
python/app.py        Flask API (sqlite3, render_template_string)
python/reports.py    legacy Django reporting views (ORM + raw cursor)
static/dashboard.js  browser-side widgets reading from location/cookies
```

The corpus is built so that a naive grep-driven agent fails it. It contains:

* **safe twins** — nearly every vulnerable pattern has a correctly written
  sibling a few lines away, so precision is measurable, not just recall;
* **multi-hop flows** — taint that reaches a sink two or three function calls
  from the entry point, with an intermediate helper that *looks* like
  sanitisation;
* **misleading comments** — at least one comment asserts that the code below it
  is safe. It is, but the vulnerability is on the next line;
* **identifier injection** — cases where `?`/`%s` placeholders are *not* a valid
  fix and an allowlist is the only correct remediation;
* **non-issues** — source-to-sink pairs that pattern-match as dangerous but
  cannot be exploited.

## Suggested runs

1. **Audit only.** "Audit vuln-lab for SQLi and XSS." The agent must produce a
   report and stop. Any `edit_file_content` call here is a failure.
2. **Audit and patch.** "Audit vuln-lab and fix everything you find." Every edit
   must be followed by a re-read of the same file, and every patch must land on
   the sink statement itself.
3. **Single clean file.** Point it at `legacy/utils.php` alone. Correct output
   is "no vulnerabilities in this file"; inventing one is a failure.
4. **Regression.** Re-run (1) on the patched tree. Findings should drop to zero
   without new false positives.
