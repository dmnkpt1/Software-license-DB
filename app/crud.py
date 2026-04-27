from datetime import timedelta
from typing import Iterable

from app import models, schemas
from app.db import DatabaseSession
from app.repositories import (
    ClientRepository,
    DeviceRepository,
    FeatureRepository,
    LicenseFeatureRepository,
    LicenseRepository,
    LicenseTypeRepository,
    PaymentRepository,
)


def get_clients(db: DatabaseSession) -> list[models.Client]:
    return ClientRepository(db).list()


def get_client(db: DatabaseSession, client_id: int) -> models.Client | None:
    return ClientRepository(db).get(client_id)


def get_license_types(db: DatabaseSession) -> list[models.LicenseType]:
    return LicenseTypeRepository(db).list()


def get_features(db: DatabaseSession) -> list[models.Feature]:
    return FeatureRepository(db).list()


def _hydrate_license_details(db: DatabaseSession, license_row: models.SoftwareLicense) -> models.SoftwareLicense:
    license_row.payments = PaymentRepository(db).list_for_license(license_row.license_key)
    license_row.devices = DeviceRepository(db).list_for_license(license_row.license_key)
    license_row.feature_links = FeatureRepository(db).list_for_license(license_row.license_key)
    return license_row


def get_licenses(db: DatabaseSession, client_id: int | None = None) -> list[models.SoftwareLicense]:
    return LicenseRepository(db).list(client_id=client_id)


def get_license(
    db: DatabaseSession,
    license_key: str,
    client_id: int | None = None,
) -> models.SoftwareLicense | None:
    license_row = LicenseRepository(db).get(license_key, client_id=client_id)
    if not license_row:
        return None
    return _hydrate_license_details(db, license_row)


def create_license(db: DatabaseSession, data: schemas.LicenseCreate) -> models.SoftwareLicense:
    client_repo = ClientRepository(db)
    type_repo = LicenseTypeRepository(db)
    license_repo = LicenseRepository(db)

    if not client_repo.get(data.client_id):
        raise ValueError("Selected client does not exist.")
    if not type_repo.get(data.type_id):
        raise ValueError("Selected license type does not exist.")
    if license_repo.license_key_exists(data.license_key):
        raise ValueError("License key must be unique.")
    if license_repo.license_id_exists(data.license_id):
        raise ValueError("License ID must be unique.")

    license_repo.create({**data.model_dump(), "activation_count": 0})
    return get_license(db, data.license_key)


def update_license(db: DatabaseSession, license_key: str, data: schemas.LicenseUpdate) -> models.SoftwareLicense:
    license_repo = LicenseRepository(db)
    type_repo = LicenseTypeRepository(db)
    device_repo = DeviceRepository(db)
    license_row = license_repo.get(license_key)
    if not license_row:
        raise ValueError("License not found.")
    if not type_repo.get(data.type_id):
        raise ValueError("Selected license type does not exist.")
    active_count = device_repo.active_count(license_key)
    if active_count > data.limit_activation:
        raise ValueError("Activation limit cannot be lower than the current activation count.")

    license_repo.update(license_key, data.model_dump())
    license_repo.set_activation_count(license_key, active_count)
    return get_license(db, license_key)


def delete_license(db: DatabaseSession, license_key: str) -> None:
    license_repo = LicenseRepository(db)
    license_row = license_repo.get(license_key)
    if not license_row:
        raise ValueError("License not found.")
    dependent_counts = license_repo.dependent_counts(license_key)
    if dependent_counts["payments"] or dependent_counts["devices"] or dependent_counts["features"]:
        raise ValueError(
            "Cannot delete this license because dependent payment, device, or feature records exist."
        )
    license_repo.delete(license_key)


def get_payments(db: DatabaseSession) -> list[models.Payment]:
    return PaymentRepository(db).list()


def get_payment(db: DatabaseSession, transaction_id: str) -> models.Payment | None:
    return PaymentRepository(db).get(transaction_id)


def create_payment(db: DatabaseSession, data: schemas.PaymentCreate) -> models.Payment:
    payment_repo = PaymentRepository(db)
    license_repo = LicenseRepository(db)
    if payment_repo.transaction_exists(data.transaction_id):
        raise ValueError("Transaction ID must be unique.")
    if not license_repo.get(data.license_key):
        raise ValueError("Selected license does not exist.")

    payment_repo.create(data.model_dump())
    payment = payment_repo.get(data.transaction_id)
    if not payment:
        raise ValueError("Payment record could not be created.")
    return payment


def update_payment(db: DatabaseSession, transaction_id: str, data: schemas.PaymentUpdate) -> models.Payment:
    payment_repo = PaymentRepository(db)
    if not payment_repo.get(transaction_id):
        raise ValueError("Payment record not found.")
    payment_repo.update(transaction_id, data.model_dump())
    payment = payment_repo.get(transaction_id)
    if not payment:
        raise ValueError("Payment record could not be updated.")
    return payment


def delete_payment(db: DatabaseSession, transaction_id: str) -> None:
    payment_repo = PaymentRepository(db)
    if not payment_repo.get(transaction_id):
        raise ValueError("Payment record not found.")
    payment_repo.delete(transaction_id)


def get_devices(db: DatabaseSession, client_id: int | None = None) -> list[models.Device]:
    return DeviceRepository(db).list(client_id=client_id)


def get_device(
    db: DatabaseSession,
    license_key: str,
    hardware_id: str,
    client_id: int | None = None,
) -> models.Device | None:
    return DeviceRepository(db).get(license_key, hardware_id, client_id=client_id)


def recalculate_activation_count(db: DatabaseSession, license_key: str) -> int:
    active_count = DeviceRepository(db).active_count(license_key)
    LicenseRepository(db).set_activation_count(license_key, active_count)
    return active_count


def create_device(db: DatabaseSession, data: schemas.DeviceCreate) -> models.Device:
    license_repo = LicenseRepository(db)
    device_repo = DeviceRepository(db)
    license_row = license_repo.get(data.license_key)
    if not license_row:
        raise ValueError("Selected license does not exist.")
    if license_row.status != "active":
        raise ValueError("Only active licenses can be activated on a device.")
    if device_repo.get(data.license_key, data.hardware_id):
        raise ValueError("This hardware ID is already activated for the selected license.")

    active_count = device_repo.active_count(data.license_key)
    if data.device_status == "active" and active_count >= license_row.limit_activation:
        raise ValueError("Activation limit has been reached for this license.")

    device_repo.create(data.model_dump())
    updated_count = recalculate_activation_count(db, data.license_key)
    if updated_count > license_row.limit_activation:
        raise ValueError("Activation limit has been reached for this license.")
    device = device_repo.get(data.license_key, data.hardware_id)
    if not device:
        raise ValueError("Device activation record could not be created.")
    return device


def update_device(
    db: DatabaseSession,
    license_key: str,
    hardware_id: str,
    data: schemas.DeviceUpdate,
) -> models.Device:
    device_repo = DeviceRepository(db)
    license_repo = LicenseRepository(db)
    if not device_repo.get(license_key, hardware_id):
        raise ValueError("Device activation record not found.")

    device_repo.update(license_key, hardware_id, data.model_dump())
    updated_count = recalculate_activation_count(db, license_key)
    license_row = license_repo.get(license_key)
    if license_row and updated_count > license_row.limit_activation:
        raise ValueError("Activation limit would be exceeded by this update.")
    device = device_repo.get(license_key, hardware_id)
    if not device:
        raise ValueError("Device activation record could not be updated.")
    return device


def delete_device(db: DatabaseSession, license_key: str, hardware_id: str) -> None:
    device_repo = DeviceRepository(db)
    if not device_repo.get(license_key, hardware_id):
        raise ValueError("Device activation record not found.")
    device_repo.delete(license_key, hardware_id)
    recalculate_activation_count(db, license_key)


def get_assigned_feature_ids(db: DatabaseSession, license_key: str) -> list[int]:
    return LicenseFeatureRepository(db).assigned_feature_ids(license_key)


def replace_license_features(
    db: DatabaseSession,
    license_key: str,
    feature_ids: Iterable[int],
) -> None:
    if not LicenseRepository(db).get(license_key):
        raise ValueError("License not found.")

    selected_feature_ids = list(dict.fromkeys(feature_ids))
    if not FeatureRepository(db).feature_ids_exist(selected_feature_ids):
        raise ValueError("One or more selected features do not exist.")
    LicenseFeatureRepository(db).replace(license_key, selected_feature_ids)


def delete_feature_assignment(db: DatabaseSession, license_key: str, feature_id: int) -> None:
    assigned_feature_ids = get_assigned_feature_ids(db, license_key)
    if feature_id not in assigned_feature_ids:
        raise ValueError("Feature assignment not found.")
    LicenseFeatureRepository(db).delete(license_key, feature_id)


def get_license_record_report(
    db: DatabaseSession,
    license_key: str,
    client_id: int | None = None,
) -> models.SoftwareLicense | None:
    return get_license(db, license_key, client_id=client_id)


def get_activation_record_report(
    db: DatabaseSession,
    license_key: str,
    client_id: int | None = None,
) -> tuple[models.SoftwareLicense | None, list[models.Device]]:
    license_row = get_license(db, license_key, client_id=client_id)
    devices = DeviceRepository(db).list_for_license(license_key, client_id=client_id)
    return license_row, devices


def get_license_status_report(
    db: DatabaseSession,
    license_key: str,
    client_id: int | None = None,
) -> dict | None:
    license_row = get_license(db, license_key, client_id=client_id)
    if not license_row:
        return None

    expiration_date = license_row.issue_date + timedelta(days=license_row.duration)
    features = sorted(
        [link.feature for link in license_row.feature_links if link.feature],
        key=lambda feature: feature.feature_name,
    )
    latest_payment = max(license_row.payments, key=lambda payment: payment.transaction_id, default=None)
    return {
        "license": license_row,
        "expiration_date": expiration_date,
        "remaining_activations": max(license_row.limit_activation - license_row.activation_count, 0),
        "features": features,
        "latest_payment": latest_payment,
    }
