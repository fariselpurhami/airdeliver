"""Production configuration must resolve mounted secrets and all required fields."""
from pathlib import Path

import pytest
import yaml
from app.core.config import CoreSettings


def test_mounted_file_credentials_override_plain_environment(monkeypatch, tmp_path):
    secret = tmp_path / "password"
    secret.write_text("p@ss:word\n")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret))
    monkeypatch.setenv("POSTGRES_PASSWORD", "stale-plain-value")
    settings = CoreSettings(_env_file=None)
    assert settings.POSTGRES_PASSWORD.get_secret_value() == "p@ss:word"
    assert "p%40ss%3Aword" in settings.DATABASE_URI


def test_missing_mounted_secret_does_not_fall_back_silently(monkeypatch, tmp_path):
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(tmp_path / "missing"))
    with pytest.raises(OSError):
        CoreSettings(_env_file=None)


def test_empty_mounted_secret_is_rejected(monkeypatch, tmp_path):
    secret = tmp_path / "empty"
    secret.write_text("\n")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret))
    with pytest.raises(ValueError):
        CoreSettings(_env_file=None)


def test_production_api_and_migrator_wire_every_required_core_setting():
    root = Path(__file__).resolve().parents[3]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text())
    for service_name in ("api", "api-migrator"):
        environment = compose["services"][service_name]["environment"]
        if isinstance(environment, list):
            environment = dict(value.split("=", 1) for value in environment)
        missing = []
        for name, field in CoreSettings.model_fields.items():
            alias = field.alias or name
            if field.is_required() and alias not in environment and f"{alias}_FILE" not in environment:
                missing.append(alias)
        assert not missing, f"{service_name} is missing {missing}"


def test_url_credential_spaces_are_percent_encoded_not_plus(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test password")
    assert "test%20password" in CoreSettings(_env_file=None).DATABASE_URI


def test_payment_reference_migration_backfills_existing_records(monkeypatch):
    import importlib.util
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path = Path(__file__).resolve().parents[1] / "alembic/versions/a42bc980f321_add_payment_transaction_id.py"
    spec = importlib.util.spec_from_file_location("payment_reference_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE orders (id INTEGER PRIMARY KEY, stripe_payment_id VARCHAR)")
        connection.exec_driver_sql("INSERT INTO orders VALUES (1, 'pi_existing'), (2, NULL)")
        monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(connection)))
        module.upgrade()
        rows = connection.exec_driver_sql("SELECT payment_transaction_id FROM orders ORDER BY id").scalars().all()
        assert rows == ["pi_existing", None]
    engine.dispose()


def test_shipping_currency_migration_retains_historical_usd_without_inventing_address(monkeypatch):
    import importlib.util
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/c63ed102b543_order_shipping_currency.py'
    spec = importlib.util.spec_from_file_location('shipping_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE orders (id INTEGER PRIMARY KEY)')
        connection.exec_driver_sql('INSERT INTO orders VALUES (1)')
        monkeypatch.setattr(module, 'op', Operations(MigrationContext.configure(connection)))
        module.upgrade()
        assert connection.exec_driver_sql('SELECT currency, shipping_address_data FROM orders').first() == ('USD', None)
    engine.dispose()
