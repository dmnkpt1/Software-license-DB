from datetime import date
from decimal import Decimal
from typing import Iterable

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator


LICENSE_STATUSES = {"active", "inactive", "expired", "suspended"}
PAYMENT_STATUSES = {"completed", "pending", "failed"}
DEVICE_STATUSES = {"active", "inactive", "revoked"}


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: int
    contact_name: str
    contact_email: EmailStr


class LicenseTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type_id: int
    type_name: str


class FeatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_id: int
    feature_name: str


class LicenseBase(BaseModel):
    license_id: int
    license_key: str
    issue_date: date
    status: str
    duration: int
    limit_activation: int
    client_id: int
    type_id: int

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in LICENSE_STATUSES:
            raise ValueError("Status must be active, inactive, expired, or suspended.")
        return value

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Duration must be positive.")
        return value

    @field_validator("limit_activation")
    @classmethod
    def validate_limit_activation(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Activation limit must be non-negative.")
        return value


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(BaseModel):
    status: str
    duration: int
    limit_activation: int
    type_id: int

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in LICENSE_STATUSES:
            raise ValueError("Status must be active, inactive, expired, or suspended.")
        return value

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Duration must be positive.")
        return value

    @field_validator("limit_activation")
    @classmethod
    def validate_limit_activation(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Activation limit must be non-negative.")
        return value


class PaymentBase(BaseModel):
    transaction_id: str
    payment_status: str
    payment_method: str
    amount: Decimal
    currency: str
    tax_rate: Decimal
    license_key: str

    @field_validator("payment_status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in PAYMENT_STATUSES:
            raise ValueError("Payment status must be completed, pending, or failed.")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be positive.")
        return value

    @field_validator("tax_rate")
    @classmethod
    def validate_tax_rate(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Tax rate must be non-negative.")
        return value


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    payment_status: str
    payment_method: str
    amount: Decimal
    currency: str
    tax_rate: Decimal

    @field_validator("payment_status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in PAYMENT_STATUSES:
            raise ValueError("Payment status must be completed, pending, or failed.")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be positive.")
        return value

    @field_validator("tax_rate")
    @classmethod
    def validate_tax_rate(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Tax rate must be non-negative.")
        return value


class DeviceBase(BaseModel):
    license_key: str
    hardware_id: str
    device_status: str
    activation_date: date

    @field_validator("device_status")
    @classmethod
    def validate_device_status(cls, value: str) -> str:
        if value not in DEVICE_STATUSES:
            raise ValueError("Device status must be active, inactive, or revoked.")
        return value


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    device_status: str
    activation_date: date

    @field_validator("device_status")
    @classmethod
    def validate_device_status(cls, value: str) -> str:
        if value not in DEVICE_STATUSES:
            raise ValueError("Device status must be active, inactive, or revoked.")
        return value


class FeatureAssignmentUpdate(BaseModel):
    license_key: str
    feature_ids: list[int]

    @field_validator("feature_ids")
    @classmethod
    def unique_feature_ids(cls, value: Iterable[int]) -> list[int]:
        unique_values = list(dict.fromkeys(value))
        return unique_values

    @model_validator(mode="after")
    def validate_non_negative(self) -> "FeatureAssignmentUpdate":
        if any(feature_id <= 0 for feature_id in self.feature_ids):
            raise ValueError("Feature IDs must be positive integers.")
        return self
