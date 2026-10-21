"""Configure a reusable per-user ReviewForge API key.

Credentials are stored outside the repository so they survive git pull,
fresh clones, and project upgrades. The key is never printed.
"""
from pathlib import Path
from getpass import getpass
import os

ROOT = Path(__file__).resolve().parent
TARGET = Path.home() / '.reviewforge' / 'credentials.env'
LEGACY = ROOT / '.env'
TEMPLATE = ROOT / '.env.example'


def valid_key(value):
    return bool(value and value.strip() and value.strip() != 'replace_me' and
                '\n' not in value and '\r' not in value)


def read_key(path):
    if not path.is_file():
        return ''
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.strip().startswith('RF_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''


def main():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    current = read_key(TARGET)
    if valid_key(current):
        print('Persistent API configuration: FOUND')
        answer = input('Keep existing key? [Y/n]: ').strip().lower()
        if answer not in ('n', 'no'):
            print('Existing configuration kept. No new key required.')
            return

    legacy = read_key(LEGACY)
    if valid_key(legacy) and not valid_key(current):
        answer = input('Existing local .env detected. Import it for all future projects? [Y/n]: ').strip().lower()
        if answer not in ('n', 'no'):
            TARGET.write_text(LEGACY.read_text(encoding='utf-8-sig'), encoding='utf-8')
            print('Imported existing configuration to:', TARGET)
            print('Your key was not printed.')
            return

    print('For multiple authorized keys, enter each separately. Leave blank to finish.')
    secrets = []
    while True:
        secret = getpass('Token Harbor API key ' + str(len(secrets) + 1) + ' (hidden; blank to finish): ').strip()
        if not secret:
            break
        if not valid_key(secret) or ',' in secret:
            raise SystemExit('Invalid API key; commas and newlines are not supported.')
        if secret not in secrets:
            secrets.append(secret)
    if not secrets:
        raise SystemExit('At least one API key is required.')
    secret = secrets[0]
    if not valid_key(secret):
        raise SystemExit('A nonempty single-line API key is required.')

    if TEMPLATE.is_file():
        template = TEMPLATE.read_text(encoding='utf-8-sig')
    else:
        template = 'RF_API_KEY=replace_me\n'
    lines = template.splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith('RF_API_KEY='):
            lines[i] = 'RF_API_KEY=' + secret
            found = True
    if not found:
        lines.append('RF_API_KEY=' + secret)
    if len(secrets) > 1:
        lines.append('RF_API_KEYS=' + ','.join(secrets))
        print('Multiple API keys configured:', len(secrets))
    TARGET.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if os.name == 'posix':
        TARGET.chmod(0o600)
    print('Saved persistent API configuration:', TARGET)
    print('The key will be reused across ReviewForge clones and upgrades.')


if __name__ == '__main__':
    main()
