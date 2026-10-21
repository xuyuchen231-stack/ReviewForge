"""Safely check local configuration and live model access without revealing the API key."""
from pathlib import Path
import os
import sys
from reviewforge import load_env, CompatibleAPI

ROOT = Path(__file__).resolve().parent
load_env(ROOT / '.env')
key = os.environ.get('RF_API_KEY', '')
base = os.environ.get('RF_BASE_URL', '')
print('ReviewForge configuration check')
print('Local .env:', 'FOUND' if (ROOT / '.env').is_file() else 'MISSING')
print('Persistent user config:', 'FOUND' if (Path.home() / '.reviewforge' / 'credentials.env').is_file() else 'MISSING')
print('API key:', 'CONFIGURED (hidden)' if key and key != 'replace_me' else 'MISSING')
print('API URL:', base or 'MISSING')
print('Writer:', os.environ.get('RF_WRITER_MODEL', os.environ.get('RF_MODEL', 'MISSING')))
print('Reviewer:', os.environ.get('RF_REVIEWER_MODEL', 'MISSING'))
if not key or key == 'replace_me':
    print('FAIL: Run setup_secret.bat once, or import your existing .env.')
    sys.exit(1)
try:
    api = CompatibleAPI()
    for role in ('writer', 'reviewer'):
        print('Testing', role, '...', flush=True)
        response = api.chat('Respond with the word OK only.', 'Reply OK.', role=role)
        print(role.upper() + ': PASS (response received; model access works)')
    print('SUCCESS: Both model roles responded. Your API is configured.')
except Exception as exc:
    print('FAIL:', type(exc).__name__, str(exc))
    print('Check endpoint, model access, free-tier limits, and key permissions.')
    sys.exit(2)
