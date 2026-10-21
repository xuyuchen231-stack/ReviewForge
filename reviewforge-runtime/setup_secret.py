"""One-time local setup: secret is entered on the user's own computer."""
from pathlib import Path
from getpass import getpass

base = Path(__file__).resolve().parent
secret = getpass('Token Harbor API key (hidden): ').strip()
if not secret or '\n' in secret or '\r' in secret:
    raise SystemExit('A nonempty single-line API key is required.')
template = (base / '.env.example').read_text(encoding='utf-8')
(base / '.env').write_text(template.replace('RF_API_KEY=replace_me', 'RF_API_KEY=' + secret), encoding='utf-8')
print('Saved local .env (excluded from Git).')
