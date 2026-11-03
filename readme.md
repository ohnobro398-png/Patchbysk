# Patchbysk — APK Analysis and Patching Toolkit

A Python command-line toolkit for APK patching workflows. The codebase identifies itself as "APK-X Enterprise Suite v11.0" (see `main.py`).

## What it does

- `dashboard` — show the tool dashboard
- `stats` — show usage statistics
- `patch <apk>` — run the patch workflow on an APK file

The tool stores its working data under an `APKX_Enterprise` directory (output, backups, logs, database, plugins, temp, reports) and uses a local SQLite database.

## Requirements

- Python 3.9+
- System tools (installed by `setup.sh`): JDK 17, `aapt`, `apksigner`, `apktool`, `git`, `wget`, `curl`
- Python packages in `requirements.txt` (rich, colorama, requests, pycryptodome, lxml, beautifulsoup4, pyyaml, tqdm, cryptography, jinja2)

## Install

```bash
bash setup.sh
```

## Usage

```bash
python main.py dashboard
python main.py patch /path/to/app.apk
python main.py stats
```

## Authorized use only

Use this tool **only on APKs you own or are explicitly authorized to test**. Do not use it to bypass protections, access other people's accounts or data, or break platform rules.

## Repository contents

| File | Purpose |
|---|---|
| `main.py` | Main CLI entry point |
| `lm.py` | Supporting module |
| `setup.sh` | One-command environment setup (Termux or Linux) |
| `requirements.txt` | Python dependencies |
| `.github/workflows/pylint.yml` | Existing lint workflow |

## Limitations (honest)

- No automated tests in this repository.
- No `LICENSE` file in this repository — the license is currently unspecified.
- The grand claims in the code's own comments (company names, "enterprise grade" wording) are the original author's, not verified here.

## Roadmap

- Add automated tests
- Add a `LICENSE` file
- Document each command's options in detail
