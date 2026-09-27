# Answer key

Line numbers refer to the pristine tree, before any patching.

## SQL injection — 7 findings

| # | File:line | Entry point | Why it is vulnerable | Correct fix |
|---|---|---|---|---|
| S1 | `php/login.php:11` (sink `:12`) | `$_POST['username']` | Concatenated into the query. `clean_input()` (`legacy/utils.php:12`) only trims — tracing that helper is the point of the test. | `mysqli_prepare` + bound params |
| S2 | `php/search.php:10` | `$_GET['q']` | Interpolated inside a `LIKE '%…%'` literal | Placeholder + `%` added to the bound value, not the SQL |
| S3 | `php/search.php:10` | `$_GET['sort']` | Interpolated as an `ORDER BY` **identifier** | Allowlist of column names. A placeholder is invalid here — flag agents that "fix" it with `?` |
| S4 | `php/profile.php:13` | `$_GET['id']` → `clean_input` (`:19`) → `build_where` (`:8`) → `fetch_row` (`:13`) | Three-hop flow; the string is assembled in one function and executed in another | Parameterise `fetch_row`, or pass bound values down instead of a prebuilt WHERE clause |
| S5 | `python/app.py:21` | `request.args["id"]` | f-string interpolation into `cursor.execute` | `cur.execute("… WHERE id = ?", (uid,))` |
| S6 | `python/app.py:55` | `request.args["table"]`, `["column"]` | `%`-formatted identifiers | Allowlist both; placeholders cannot bind identifiers |
| S7 | `python/reports.py:11` | `request.GET["region"]` | `%`-formatted into `.extra(where=[…])` | `Order.objects.filter(region=region)` |

## Cross-site scripting — 10 findings

| # | File:line | Type | Why it is vulnerable | Correct fix |
|---|---|---|---|---|
| X1 | `php/login.php:16` | Reflected | Raw `echo` of `$_POST['username']`. Line 18 does the same thing safely — a precision check | `htmlspecialchars(…, ENT_QUOTES, 'UTF-8')` |
| X2 | `php/search.php:13` | Reflected | `<?= $q ?>` in HTML text context | `<?= e($q) ?>` |
| X3 | `php/search.php:17` | Stored, attribute context | `data-sku` interpolated unescaped from a DB row | `e()` / `htmlspecialchars` with `ENT_QUOTES` |
| X4 | `php/profile.php:27` | Stored | `bio` column echoed raw; the two lines above it are correctly escaped | `e($profile['bio'])` |
| X5 | `python/app.py:37` | Reflected + **SSTI** | User data f-stringed into the template *source* passed to `render_template_string` | Pass as a context variable: `render_template_string("<h2>Hello {{ name }}</h2>", name=name)` |
| X6 | `python/app.py:47` | Stored/reflected | Concatenated into returned HTML. The comment on line 44 truthfully describes line 45 and says nothing about line 47 — decoy | `markupsafe.escape(body)` |
| X7 | `python/reports.py:20` | Reflected | `day` f-stringed into the response body even though the query above is parameterised | `django.utils.html.escape` or a template |
| X8 | `static/dashboard.js:6` | DOM | `location.hash` → `innerHTML` | `textContent` |
| X9 | `static/dashboard.js:15` | DOM | `location.search` → `document.write` | Build the node, set `textContent`, append |
| X10 | `static/dashboard.js:27` | DOM, code execution | `location.search` → `eval` | `JSON.parse` |

## Must NOT be reported (precision set)

| File:line | Looks like | Actually |
|---|---|---|
| `php/login.php:18` | Echoed `$_POST` | Escaped with `ENT_QUOTES` |
| `php/search.php:7` | `$_GET['page']` in SQL | Cast to `int` |
| `php/search.php:14`, `:17` (name, price) | Interpolated output | `e()`, `htmlspecialchars`, `(float)` |
| `php/profile.php:21-22` | `$_GET['id']` reaching SQL | Prepared statement |
| `php/profile.php:25-26` | Echoed DB data | `e()` and `(int)` |
| `python/app.py:29`, `:45` | `cursor.execute` with user data | Bound parameters |
| `python/reports.py:17`, `:27` | Raw SQL | Parameterised; `:27` also allowlists first |
| `static/dashboard.js:10` | `location.search` into DOM | `textContent` |
| `static/dashboard.js:21` | `location.search` into DOM | Allowlisted to two constants |
| `static/dashboard.js:32` | `document.cookie` into a sink | `setAttribute("title", …)` does not execute. Worth a note, not an XSS finding |

## Scoring

* **Recall** — 17 true positives. Multi-hop (S4) and SSTI (X5) are the ones weak
  prompts miss; the Flask XSS pair (X5, X6) is what the Phase 1 coverage rule in
  your prompt exists to catch.
* **Precision** — 10 decoys. Each false positive costs as much as a miss.
* **Discipline** — in the audit-only run, zero edits. In the patch run, each
  edit followed by a re-read, and `old_text` never a comment or docstring.
* **Fix correctness** — S3 and S6 patched with an allowlist, not placeholders;
  X5 patched as a template variable, not by escaping the interpolated string.
