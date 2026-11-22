#!/usr/bin/env python3
"""Prepare local development config without overwriting existing config or DB data.

Only Python's standard library is needed. Secrets stay in local mode-0600 files.
The --preserve-existing mode refuses to guess database or broker credentials.
"""
import argparse
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import quote

SECRET_FIELDS = ('SECRET_KEY', 'REFRESH_SECRET_KEY', 'INTERNAL_API_TOKEN',
                 'AUTH_SECRET', 'FIRST_SUPERUSER_PASSWORD', 'GRAFANA_PASSWORD',
                 'OPENSEARCH_ADMIN_PASSWORD', 'RABBITMQ_COOKIE')
FILE_FIELDS = {'POSTGRES_USER': 'postgres_user', 'POSTGRES_PASSWORD': 'postgres_password',
               'POSTGRES_DB': 'postgres_db', 'RABBITMQ_USER': 'rabbitmq_user',
               'RABBITMQ_PASS': 'rabbitmq_pass'}


def read_env(path, source_env):
    # The setup Compose service parses values, quotes and references for us.
    # Only names are read here. No shell sourcing, eval or hand-written parser.
    if not path.exists():
        return {}
    names = re.findall(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', path.read_text(encoding='utf-8'), re.MULTILINE)
    return {name: source_env.get(name, '') for name in names}


def env_value(value):
    if '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('Multiline values need manual local configuration; no secret is printed')
    # JSON quoting handles quotes/backslashes; $$ is Compose's literal dollar.
    return json.dumps(value.replace('$', '$$'), ensure_ascii=False)


def write_private(path, contents):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        out.write(contents)


def prepare(root, preserve_existing=False, source_env=None, fresh=False):
    root = Path(root).resolve()
    target = root / '.env.dev'
    if target.exists():
        raise ValueError('.env.dev already exists; it was not overwritten')
    source_env = os.environ if source_env is None else source_env
    template = read_env(root / '.env.dev.example', source_env)
    old = read_env(root / '.env', source_env)
    # Existing mounted files take precedence, matching BaseAppConfig.
    for key, filename in FILE_FIELDS.items():
        source = root / 'secrets' / filename
        if source.is_file():
            old[key] = source.read_text(encoding='utf-8').rstrip('\r\n')
    if preserve_existing:
        missing = [key for key in FILE_FIELDS if not old.get(key)]
        if missing:
            raise ValueError('Existing credentials not found locally for: ' + ', '.join(missing) + '. Fill them locally; they will not be guessed.')
    values = {**template, **old}
    if fresh:
        if preserve_existing:
            raise ValueError('Choose fresh or preservation mode, not both')
        # Fresh credentials must never be paired with an unknown existing DB or
        # broker volume. Store the private, stable volume names in .env.dev.
        identity = secrets.token_hex(12)
        values.update(POSTGRES_USER='airdeliver', POSTGRES_DB='airdeliver',
                      POSTGRES_PASSWORD='', RABBITMQ_USER='airdeliver', RABBITMQ_PASS='',
                      AIRDELIVER_DEV_POSTGRES_VOLUME='airdeliver_dev_postgres19_fresh_' + identity,
                      AIRDELIVER_DEV_RABBITMQ_VOLUME='airdeliver_dev_rabbitmq_fresh_' + identity)
    values['AUTH_SECRET'] = values.get('AUTH_SECRET') or values.get('NEXTAUTH_SECRET') or ''
    defaults = {'POSTGRES_USER': 'airdeliver', 'POSTGRES_DB': 'airdeliver', 'RABBITMQ_USER': 'airdeliver'}
    for key, default in defaults.items():
        values[key] = values.get(key) or default
    for key in (*SECRET_FIELDS, 'POSTGRES_PASSWORD', 'RABBITMQ_PASS'):
        if not values.get(key):
            values[key] = 'Dev!' + secrets.token_hex(24) + 'A9'
    host = values.get('HOST_IP') or '127.0.0.1'
    if host != 'localhost':
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            raise ValueError('HOST_IP must be localhost or a private IPv4 address for this local dev setup') from None
        if address.version != 4 or not (address.is_private or address.is_loopback):
            raise ValueError('HOST_IP must be localhost or a private IPv4 address for this local dev setup')
    values.update(APP_ENV='development', COMPOSE_PROJECT_NAME='airdeliver_dev',
                  AIRDELIVER_ENV_FILE='.env.dev', AIRDELIVER_DEV_SECRET_DIR='./secrets/dev',
                  HOST_IP=host, POSTGRES_SERVER='postgres', POSTGRES_PORT='5432',
                  RABBITMQ_HOST='mq', REDIS_HOST='redis', USE_REDIS='true', COOKIES_SECURE='false',
                  API_BASE_URL=f'http://{host}', NEXT_PUBLIC_API_URL=f'http://{host}/api/v1',
                  AUTH_URL=f'http://{host}:3000', NEXTAUTH_URL=f'http://{host}:3000',
                  API_URL='http://api:8000/api/v1', BACKEND_API_URL='http://api:8000')
    values['BACKEND_CORS_ORIGINS'] = json.dumps(list(dict.fromkeys([f'http://{host}:3000', 'http://localhost:3000', 'http://127.0.0.1:3000'])))
    user, password, db = (quote(values[key], safe='') for key in ('POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_DB'))
    values['DATABASE_URL_ASYNC'] = f'postgresql+asyncpg://{user}:{password}@postgres:5432/{db}'
    values['DATABASE_URL_SYNC'] = f'postgresql+psycopg://{user}:{password}@postgres:5432/{db}'
    values['DATABASE_URI'] = values['DATABASE_URL_ASYNC']
    values['FIRST_SUPERUSER'] = values.get('FIRST_SUPERUSER') or 'dev-admin@example.com'
    values['GRAFANA_USER'] = values.get('GRAFANA_USER') or 'dev-admin'
    values['TRAEFIK_DASHBOARD_USER'] = values.get('TRAEFIK_DASHBOARD_USER') or 'dev-admin'
    if not values.get('TRAEFIK_DASHBOARD_PASS_HASH'):
        local_password = secrets.token_hex(32)
        values['TRAEFIK_DEV_PASSWORD'] = local_password
        values['TRAEFIK_DASHBOARD_PASS_HASH'] = '{SHA}' + base64.b64encode(hashlib.sha1(local_password.encode()).digest()).decode()
    # Optional payments stay unconfigured unless a complete Stripe TEST setup exists.
    if not (values.get('STRIPE_SECRET_KEY', '').startswith('sk_test_') and values.get('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY', '').startswith('pk_test_')):
        values['STRIPE_SECRET_KEY'] = ''
        values['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY'] = ''
        values['STRIPE_WEBHOOK_SECRET'] = ''
    values['STRIPE_PUBLISHABLE_KEY'] = values['NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY']
    values['PAYPAL_API_BASE_URL'] = 'https://api-m.sandbox.paypal.com'
    values['REDIS_PASSWORD'] = ''
    values['OPENSEARCH_USE_SSL'] = 'false'
    values['OPENSEARCH_VERIFY_CERTS'] = 'false'
    # Validate serialization before writing anything.
    body = '# LOCAL DEVELOPMENT ONLY. Generated locally. Never commit this file.\n'
    body += '\n'.join(f'{key}={env_value(str(value))}' for key,value in sorted(values.items())) + '\n'
    directory = root / 'secrets' / 'dev'
    for key, filename in FILE_FIELDS.items():
        destination = directory / filename
        if destination.exists() and destination.read_text(encoding='utf-8').rstrip('\r\n') != values[key]:
            raise ValueError('An existing dev secret differs; no credential was overwritten')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for key, filename in FILE_FIELDS.items():
        destination = directory / filename
        if not destination.exists():
            write_private(destination, values[key] + '\n')
    write_private(target, body)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--preserve-existing', action='store_true', help='Require existing local DB and RabbitMQ credentials; never guess them')
    mode.add_argument('--fresh', action='store_true', help='Generate local dev credentials and isolate new PG19 and RabbitMQ volumes; leave originals untouched')
    args = parser.parse_args()
    if os.environ.get('AIRDELIVER_DEV_CONFIG_INPUT') != 'compose':
        parser.exit(1, 'Run this helper through docker-compose.dev-setup.yml so Compose parses existing env values safely.\n')
    try:
        target = prepare(Path(__file__).resolve().parents[1], args.preserve_existing, fresh=args.fresh)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(f'Prepared {target.name} and private development secret files. No secret values were printed.')
    print('Existing .env, original secret files and Docker data volumes were not changed.')
    print('Historical timestamp timezone was not guessed. Back up and inspect before migration.')


if __name__ == '__main__':
    main()
