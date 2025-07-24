# SEOAuditMachine

> **Automated, developer‑centric SEO auditing from the command line**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)  [![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)  ![Status](https://img.shields.io/badge/status-MVP--in--progress-yellow)

---

## Why SEOAuditMachine?

Modern websites change fast, and so do search‑engine requirements. **SEOAuditMachine** (SAM) gives developers a **mechanical, repeatable way** to track a site’s sitemap integrity, indexing status, internal link coverage, and crawl health—without spreadsheets or manual checks.

*It is **not** an AI assistant. Think of it as a calculator for SEO visibility.*

---

## Key Features (MVP)

|    | Feature                                                                                                       |
| -- | ------------------------------------------------------------------------------------------------------------- |
| ✅  | Parse XML sitemaps & sitemap index files                                                                      |
| ✅  | Compare discovered URLs against the sitemap list                                                              |
| ✅  | Query Google Search Console *URL Inspection API* for index status, referring pages, crawl errors & canonicals |
| ✅  | Store every audit in a **SQLite** database for historical trend analysis                                      |
| ✅  | Export actionable reports as **CSV** or **Markdown**                                                          |
| 🚧 | CLI commands for common workflows (`init-db`, `full-audit`, `url-report`, …)                                  |
| 🚧 | Project‑structured database (websites, URLs, inspections)                                                     |

See the [Roadmap](#roadmap) for planned enhancements.

---

## Quick Start

```bash
# 1  Install (editable mode recommended during development)
$ git clone https://github.com/<you>/seo-audit-machine.git
$ cd seo-audit-machine
$ python -m venv .venv && source .venv/bin/activate
$ pip install -e .[dev]

# 2  Set Google credentials (see below)
$ export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# 3  Initialise the database
$ seo-audit-machine init-db

# 4  Add a site to track
$ seo-audit-machine add-site https://example.com --name "Marketing Site"

# 5  Run your first audit (deep = crawl + index checks)
$ seo-audit-machine full-audit --site-id 1 --deep
```

### Obtaining Google Search Console API access

1. Create a Google Cloud project.
2. Enable the **Search Console API**.
3. Create a *service‑account key* (JSON) and download it.
4. In Search Console, add the service‑account email as a **restricted user** for each property you want to audit.
5. Point `GOOGLE_APPLICATION_CREDENTIALS` to the JSON key file.

> ⚠️ **Respect Google’s API quotas.** SAM throttles requests by default, but you are responsible for staying within your allowance.

---

## CLI Overview

```text
seo-audit-machine <command> [options]

Commands:
  init-db                       Initialise (or migrate) the SQLite database
  add-site <url> --name <str>   Register a site and generate a site‑id
  crawl-site --site-id 1        Crawl & cache internal links (no GSC)
  inspect-url <url>             Run a single URL Inspection via GSC
  full-audit --site-id 1        Crawl + inspect all discovered URLs
  url-report <url> --format md  Export an inspection report for one URL
  check-links --site-id 1       Find internal URLs not yet indexed
```

Run `seo-audit-machine <command> --help` for full options.

---

## Project Structure

```
seo_audit_machine/
├── cli.py              # CLI entry‑point (argparse)
├── database.py         # SQLite models & helpers
├── sitemap_parser.py   # Sitemap logic
├── gsc_api.py          # Google Search Console wrapper
├── auditor.py          # Core audit orchestrator
├── link_checker.py     # (optional module)
├── utils.py            # Shared helpers
├── requirements.txt
└── README.md           # You are here
```

---

## Development

```bash
# Format, lint, and run tests
$ pre-commit run --all-files
$ pytest -q
```

* Recommended Python ≥ 3.10
* Uses **ruff** for linting & **black** for formatting
* Dev dependencies listed in `requirements-dev.txt`

---

## Roadmap

* [ ] Broken‑link checker
* [ ] Lighthouse performance integration
* [ ] On‑page keyword analysis
* [ ] Scheduled re‑audits (cron‑friendly)
* [ ] JSON output for CI pipelines
* [ ] Web dashboard (Flask or Streamlit)

See `docs/roadmap.md` for the full list.

---

## Contributing

Contributions are welcome! Please open an issue to discuss your idea before submitting a PR.

1. Fork the repository and create your branch from `main`.
2. Commit your changes with clear messages.
3. Ensure `pytest` passes and `pre‑commit` hooks succeed.
4. Open a pull request and fill out the template.

By contributing, you agree to license your work under the [Apache 2.0 License](LICENSE).

---

## License

This project is licensed under the **Apache 2.0 License**. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

* Google Search Console API team
* Open‑source community for libraries such as `google-api-python-client`, `aiohttp`, and `beautifulsoup4`
* *Special thanks* to everyone who reports bugs and submits improvements!

---

> © 2025 Fred Tyre — Built with curiosity and courage.
