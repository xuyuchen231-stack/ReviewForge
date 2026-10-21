# ReviewForge — Windows local autonomous academic review editor

## Quick start (Windows)

1. Install Python 3.10+ and Git. Extract this ZIP.
2. Double-click `setup_secret.bat`. Paste a **new** Token Harbor key into the hidden prompt on your own computer. The key is stored only in the local `.env`, never inside this ZIP.
3. Check `.env` for `RF_BASE_URL=https://tokenharbor.ai/v1`. If your provider gives a different official API endpoint, replace this URL.
4. Put your manuscript into `workspace/manuscript.md`. Add evidence records to `workspace/sources.json` (see below).
5. In PowerShell in the extracted folder:

```powershell
py -m unittest discover -s tests -v
py run.py --dry-run --minutes 1
py run.py --hours 9
```

For interrupted runs: `py run.py --resume`. Alternatively double-click `start_9h.bat` or `resume_9h.bat`. Disable sleep mode during overnight operation.

## Models

- Writer: `mimo-v2.6-flash:free`
- Independent reviewer: `deepseek-v4.1-flash:free`
- Fallback: `deepseek-v4.1-flash:free`

Change `RF_WRITER_MODEL`, `RF_REVIEWER_MODEL`, `RF_FALLBACK_MODEL` in `.env`. The provider must actually offer these exact IDs. Model failures fall back, but a failed model call is not evidence that a model has been validated.

## Source format

```json
[
  {
    "id": "S1",
    "title": "Actual paper title",
    "doi": "10.xxxx/actual-doi",
    "excerpts": [
      {"locator": "p. 4, section 3", "text": "Exact text transcribed from the source document"}
    ]
  }
]
```

Use only excerpts you have permission to process. Metadata and excerpts must be supplied by the user; this release does not automatically download or validate primary full texts. The evidence gate checks exact quotation provenance, not semantic entailment. The model reviewer assesses semantics, but its judgment is not independent proof.

## Outputs and recovery

- `workspace/manuscript.md` remains unchanged.
- `workspace/revisions/revision_XXXX.md` stores accepted complete manuscripts.
- `workspace/reports/iteration_XXXX.json` stores reviewer feedback and evidence ledgers.
- `workspace/state.json` records deadline, progress, and best version.
- A Git repository is initialized in `workspace` when Git is installed; accepted revisions and reports are committed.
- `--resume` continues the original deadline rather than restarting nine hours.

## Security

Never put `.env` or API keys into Git, ZIP distributions, source code, or prompts. Rotate previously shared keys. This project does not send the API key to any destination other than the configured HTTPS API endpoint. Manuscript text and supplied excerpts are sent to that provider when real runs start.

## Limitations

- The current manuscript format is Markdown, not full Overleaf LaTeX project editing.
- The run can end early after three unsuccessful iterations or the configured maximum API calls.
- Free model rate limits, actual model availability, token limits, and provider retention policies depend on Token Harbor.
- Source excerpts are user-provided; no automatic DOI/full-text verification is included.
- API integration was tested using mocks, not a live Token Harbor credential.
- Model output is checked for provenance and reviewed, but correctness of all scientific statements is not guaranteed.

### Verify secret setup and real API access
Double-click `check_connection.bat` after `setup_secret.bat`. It reports whether `.env` exists, whether a key is configured (never prints the key), and makes a small live call to both writer and reviewer roles. `SUCCESS` means both calls returned; `FAIL` explains the category of failure. This uses real API quota and requires Internet access. You can also run `py check_connection.py` in PowerShell.
