from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Client:
    client_id: int
    contact_name: str
    contact_email: str
    street: str
    city: str
    country: str
    postal_code: str


@dataclass
class LicenseType:
    type_id: int
    type_name: str
    description: str


@dataclass
class Feature:
    feature_id: int
    feature_name: str


@dataclass
class Payment:
    transaction_id: str
    payment_status: str
    payment_method: str
    amount: Decimal
    currency: str
    tax_rate: Decimal
    license_key: str


@dataclass
class Device:
    license_key: str
    hardware_id: str
    device_status: str
    activation_date: date


@dataclass
class SoftwareLicenseFeature:
    license_key: str
    feature_id: int
    feature: Feature | None = None


@dataclass
class SoftwareLicense:
    license_key: str
    license_id: int
    issue_date: date
    status: str
    duration: int
    limit_activation: int
    activation_count: int
    client_id: int
    type_id: int
    client: Client | None = None
    license_type: LicenseType | None = None
    payments: list[Payment] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)
    feature_links: list[SoftwareLicenseFeature] = field(default_factory=list)
