"""Add a TokenHarbor key using local masked input, preserving quota history."""
import argparse
import getpass
import os
from pathlib import Path
import tempfile


def save_account(path, key, keys, suffix):
    if len(key) < 16 or not key.endswith(suffix) or any(c.isspace() or c in ',\"\'' for c in key):
        raise ValueError('Key format or suffix mismatch; configuration unchanged')
    order = list(dict.fromkeys([*keys, key]))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else []
    updated = [line for line in lines if not ('=' in line and line.split('=', 1)[0].strip() == 'RF_API_KEYS')]
    updated.append('RF_API_KEYS=' + ','.join(order))
    fd, name = tempfile.mkstemp(prefix='.rf-account-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write('\n'.join(updated) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if Path(name).exists():
            Path(name).unlink()
    return order


def main():
    from reviewforge import load_env, CompatibleAPI
    from account_cycles import is_tokenharbor_free
    from prioritize_account import restart_runner
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suffix', required=True)
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    runtime = Path(__file__).resolve().parent
    load_env(runtime / '.env')
    api = CompatibleAPI()
    if not all(is_tokenharbor_free(api.base, m) for m in (api.model, api.reviewer_model, api.fallback_model)):
        raise ValueError('TokenHarbor free routing required; nothing changed')
    key = getpass.getpass('Paste full TokenHarbor key here (hidden), then Enter: ').strip()
    paths = [runtime / '.env', Path.home() / '.reviewforge/credentials.env']
    target = next((p for p in paths if p.exists() and any(
        '=' in line and line.split('=', 1)[0].strip() == 'RF_API_KEYS'
        for line in p.read_text(encoding='utf-8-sig').splitlines())), paths[0])
    order = save_account(target, key, api.keys, args.suffix)
    os.environ['RF_API_KEYS'] = ','.join(order)
    print('Saved account ending ' + args.suffix + '; account count: ' + str(len(order)))
    print('Existing order and weekly quota history retained; no refresh date invented.')
    if args.restart:
        print('Resumed from caches; process ID ' + str(restart_runner(runtime)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, EOFError, KeyboardInterrupt) as error:
        print('Account operation stopped (' + type(error).__name__ + ').')
        raise SystemExit(1)
