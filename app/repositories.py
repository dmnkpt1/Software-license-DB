from __future__ import annotations

from typing import Iterable

from app import models
from app.db import DatabaseSession


class ClientRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def list(self) -> list[models.Client]:
        rows = self.db.fetchall(
            """
            SELECT client_id, contact_name, contact_email, street, city, country, postal_code
            FROM client
            ORDER BY contact_name
            """
        )
        return [models.Client(**row) for row in rows]

    def get(self, client_id: int) -> models.Client | None:
        row = self.db.fetchone(
            """
            SELECT client_id, contact_name, contact_email, street, city, country, postal_code
            FROM client
            WHERE client_id = %s
            """,
            (client_id,),
        )
        return models.Client(**row) if row else None


class LicenseTypeRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def list(self) -> list[models.LicenseType]:
        rows = self.db.fetchall(
            """
            SELECT type_id, type_name, description
            FROM license_type
            ORDER BY type_name
            """
        )
        return [models.LicenseType(**row) for row in rows]

    def get(self, type_id: int) -> models.LicenseType | None:
        row = self.db.fetchone(
            """
            SELECT type_id, type_name, description
            FROM license_type
            WHERE type_id = %s
            """,
            (type_id,),
        )
        return models.LicenseType(**row) if row else None


class FeatureRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def list(self) -> list[models.Feature]:
        rows = self.db.fetchall(
            """
            SELECT feature_id, feature_name
            FROM feature
            ORDER BY feature_name
            """
        )
        return [models.Feature(**row) for row in rows]

    def list_for_license(self, license_key: str) -> list[models.SoftwareLicenseFeature]:
        rows = self.db.fetchall(
            """
            SELECT slf.license_key, slf.feature_id, f.feature_name
            FROM software_license_feature slf
            JOIN feature f ON f.feature_id = slf.feature_id
            WHERE slf.license_key = %s
            ORDER BY f.feature_name
            """,
            (license_key,),
        )
        return [
            models.SoftwareLicenseFeature(
                license_key=row["license_key"],
                feature_id=row["feature_id"],
                feature=models.Feature(feature_id=row["feature_id"], feature_name=row["feature_name"]),
            )
            for row in rows
        ]

    def feature_ids_exist(self, feature_ids: Iterable[int]) -> bool:
        values = list(dict.fromkeys(feature_ids))
        if not values:
            return True
        placeholders = ", ".join(["%s"] * len(values))
        row = self.db.fetchone(
            f"SELECT COUNT(*) AS item_count FROM feature WHERE feature_id IN ({placeholders})",
            tuple(values),
        )
        return bool(row and row["item_count"] == len(values))


class LicenseRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def list(self, client_id: int | None = None) -> list[models.SoftwareLicense]:
        filters = ""
        params: list[object] = []
        if client_id is not None:
            filters = "WHERE sl.client_id = %s"
            params.append(client_id)
        rows = self.db.fetchall(
            f"""
            SELECT
                sl.license_key,
                sl.license_id,
                sl.issue_date,
                sl.status,
                sl.duration,
                sl.limit_activation,
                COALESCE(active_counts.active_count, 0) AS activation_count,
                sl.client_id,
                sl.type_id,
                c.contact_name,
                c.contact_email,
                c.street,
                c.city,
                c.country,
                c.postal_code,
                lt.type_name,
                lt.description
            FROM software_license sl
            JOIN client c ON c.client_id = sl.client_id
            JOIN license_type lt ON lt.type_id = sl.type_id
            LEFT JOIN (
                SELECT license_key, COUNT(*) AS active_count
                FROM device
                WHERE device_status = 'active'
                GROUP BY license_key
            ) active_counts ON active_counts.license_key = sl.license_key
            {filters}
            ORDER BY sl.issue_date DESC, sl.license_id DESC
            """,
            tuple(params),
        )
        return [self._build_license(row) for row in rows]

    def get(self, license_key: str, client_id: int | None = None) -> models.SoftwareLicense | None:
        filters = "WHERE sl.license_key = %s"
        params: list[object] = [license_key]
        if client_id is not None:
            filters += " AND sl.client_id = %s"
            params.append(client_id)
        row = self.db.fetchone(
            f"""
            SELECT
                sl.license_key,
                sl.license_id,
                sl.issue_date,
                sl.status,
                sl.duration,
                sl.limit_activation,
                COALESCE(active_counts.active_count, 0) AS activation_count,
                sl.client_id,
                sl.type_id,
                c.contact_name,
                c.contact_email,
                c.street,
                c.city,
                c.country,
                c.postal_code,
                lt.type_name,
                lt.description
            FROM software_license sl
            JOIN client c ON c.client_id = sl.client_id
            JOIN license_type lt ON lt.type_id = sl.type_id
            LEFT JOIN (
                SELECT license_key, COUNT(*) AS active_count
                FROM device
                WHERE device_status = 'active'
                GROUP BY license_key
            ) active_counts ON active_counts.license_key = sl.license_key
            {filters}
            """,
            tuple(params),
        )
        return self._build_license(row) if row else None

    def license_key_exists(self, license_key: str) -> bool:
        return bool(
            self.db.fetchone(
                "SELECT 1 AS item_exists FROM software_license WHERE license_key = %s",
                (license_key,),
            )
        )

    def license_id_exists(self, license_id: int) -> bool:
        return bool(
            self.db.fetchone(
                "SELECT 1 AS item_exists FROM software_license WHERE license_id = %s",
                (license_id,),
            )
        )

    def create(self, data: dict) -> None:
        self.db.execute(
            """
            INSERT INTO software_license
                (license_key, license_id, issue_date, status, duration, limit_activation, activation_count, client_id, type_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["license_key"],
                data["license_id"],
                data["issue_date"],
                data["status"],
                data["duration"],
                data["limit_activation"],
                data["activation_count"],
                data["client_id"],
                data["type_id"],
            ),
        )

    def update(self, license_key: str, data: dict) -> None:
        self.db.execute(
            """
            UPDATE software_license
            SET status = %s, duration = %s, limit_activation = %s, type_id = %s
            WHERE license_key = %s
            """,
            (
                data["status"],
                data["duration"],
                data["limit_activation"],
                data["type_id"],
                license_key,
            ),
        )

    def delete(self, license_key: str) -> None:
        self.db.execute("DELETE FROM software_license WHERE license_key = %s", (license_key,))

    def dependent_counts(self, license_key: str) -> dict[str, int]:
        return {
            "payments": self._count("payment", "license_key", license_key),
            "devices": self._count("device", "license_key", license_key),
            "features": self._count("software_license_feature", "license_key", license_key),
        }

    def set_activation_count(self, license_key: str, activation_count: int) -> None:
        self.db.execute(
            """
            UPDATE software_license
            SET activation_count = %s
            WHERE license_key = %s
            """,
            (activation_count, license_key),
        )

    def _count(self, table_name: str, column_name: str, value: object) -> int:
        row = self.db.fetchone(
            f"SELECT COUNT(*) AS item_count FROM {table_name} WHERE {column_name} = %s",
            (value,),
        )
        return int(row["item_count"]) if row else 0

    def _build_license(self, row: dict) -> models.SoftwareLicense:
        client = models.Client(
            client_id=row["client_id"],
            contact_name=row["contact_name"],
            contact_email=row["contact_email"],
            street=row["street"],
            city=row["city"],
            country=row["country"],
            postal_code=row["postal_code"],
        )
        license_type = models.LicenseType(
            type_id=row["type_id"],
            type_name=row["type_name"],
            description=row["description"],
        )
        return models.SoftwareLicense(
            license_key=row["license_key"],
            license_id=row["license_id"],
            issue_date=row["issue_date"],
            status=row["status"],
            duration=row["duration"],
            limit_activation=row["limit_activation"],
            activation_count=row["activation_count"],
            client_id=row["client_id"],
            type_id=row["type_id"],
            client=client,
            license_type=license_type,
        )


class PaymentRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def list(self) -> list[models.Payment]:
        rows = self.db.fetchall(
            """
            SELECT transaction_id, payment_status, payment_method, amount, currency, tax_rate, license_key
            FROM payment
            ORDER BY transaction_id DESC
            """
        )
        return [models.Payment(**row) for row in rows]

    def get(self, transaction_id: str) -> models.Payment | None:
        row = self.db.fetchone(
            """
            SELECT transaction_id, payment_status, payment_method, amount, currency, tax_rate, license_key
            FROM payment
            WHERE transaction_id = %s
            """,
            (transaction_id,),
        )
        return models.Payment(**row) if row else None

    def transaction_exists(self, transaction_id: str) -> bool:
        return bool(
            self.db.fetchone(
                "SELECT 1 AS item_exists FROM payment WHERE transaction_id = %s",
                (transaction_id,),
            )
        )

    def create(self, data: dict) -> None:
        self.db.execute(
            """
            INSERT INTO payment
                (transaction_id, payment_status, payment_method, amount, currency, tax_rate, license_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["transaction_id"],
                data["payment_status"],
                data["payment_method"],
                data["amount"],
                data["currency"],
                data["tax_rate"],
                data["license_key"],
            ),
        )

    def update(self, transaction_id: str, data: dict) -> None:
        self.db.execute(
            """
            UPDATE payment
            SET payment_status = %s, payment_method = %s, amount = %s, currency = %s, tax_rate = %s
            WHERE transaction_id = %s
            """,
            (
                data["payment_status"],
                data["payment_method"],
                data["amount"],
                data["currency"],
                data["tax_rate"],
                transaction_id,
            ),
        )

    def delete(self, transaction_id: str) -> None:
        self.db.execute("DELETE FROM payment WHERE transaction_id = %s", (transaction_id,))

    def list_for_license(self, license_key: str) -> list[models.Payment]:
        rows = self.db.fetchall(
            """
            SELECT transaction_id, payment_status, payment_method, amount, currency, tax_rate, license_key
            FROM payment
            WHERE license_key = %s
            ORDER BY transaction_id DESC
            """,
            (license_key,),
        )
        return [models.Payment(**row) for row in rows]


class DeviceRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def list(self, client_id: int | None = None) -> list[models.Device]:
        query = "SELECT d.license_key, d.hardware_id, d.device_status, d.activation_date FROM device d"
        params: list[object] = []
        if client_id is not None:
            query += " JOIN software_license sl ON sl.license_key = d.license_key WHERE sl.client_id = %s"
            params.append(client_id)
        query += " ORDER BY d.activation_date DESC"
        rows = self.db.fetchall(query, tuple(params))
        return [models.Device(**row) for row in rows]

    def get(self, license_key: str, hardware_id: str, client_id: int | None = None) -> models.Device | None:
        query = "SELECT d.license_key, d.hardware_id, d.device_status, d.activation_date FROM device d"
        params: list[object] = []
        if client_id is not None:
            query += " JOIN software_license sl ON sl.license_key = d.license_key"
        query += " WHERE d.license_key = %s AND d.hardware_id = %s"
        params.extend([license_key, hardware_id])
        if client_id is not None:
            query += " AND sl.client_id = %s"
            params.append(client_id)
        row = self.db.fetchone(query, tuple(params))
        return models.Device(**row) if row else None

    def create(self, data: dict) -> None:
        self.db.execute(
            """
            INSERT INTO device (license_key, hardware_id, device_status, activation_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                data["license_key"],
                data["hardware_id"],
                data["device_status"],
                data["activation_date"],
            ),
        )

    def update(self, license_key: str, hardware_id: str, data: dict) -> None:
        self.db.execute(
            """
            UPDATE device
            SET device_status = %s, activation_date = %s
            WHERE license_key = %s AND hardware_id = %s
            """,
            (
                data["device_status"],
                data["activation_date"],
                license_key,
                hardware_id,
            ),
        )

    def delete(self, license_key: str, hardware_id: str) -> None:
        self.db.execute(
            "DELETE FROM device WHERE license_key = %s AND hardware_id = %s",
            (license_key, hardware_id),
        )

    def active_count(self, license_key: str) -> int:
        row = self.db.fetchone(
            """
            SELECT COUNT(*) AS item_count
            FROM device
            WHERE license_key = %s AND device_status = 'active'
            """,
            (license_key,),
        )
        return int(row["item_count"]) if row else 0

    def list_for_license(self, license_key: str, client_id: int | None = None) -> list[models.Device]:
        query = "SELECT d.license_key, d.hardware_id, d.device_status, d.activation_date FROM device d"
        params: list[object] = []
        if client_id is not None:
            query += " JOIN software_license sl ON sl.license_key = d.license_key"
        query += " WHERE d.license_key = %s"
        params.append(license_key)
        if client_id is not None:
            query += " AND sl.client_id = %s"
            params.append(client_id)
        query += " ORDER BY d.activation_date DESC, d.hardware_id"
        rows = self.db.fetchall(query, tuple(params))
        return [models.Device(**row) for row in rows]


class LicenseFeatureRepository:
    def __init__(self, db: DatabaseSession):
        self.db = db

    def assigned_feature_ids(self, license_key: str) -> list[int]:
        rows = self.db.fetchall(
            """
            SELECT feature_id
            FROM software_license_feature
            WHERE license_key = %s
            ORDER BY feature_id
            """,
            (license_key,),
        )
        return [row["feature_id"] for row in rows]

    def replace(self, license_key: str, feature_ids: Iterable[int]) -> None:
        self.db.execute("DELETE FROM software_license_feature WHERE license_key = %s", (license_key,))
        for feature_id in feature_ids:
            self.db.execute(
                """
                INSERT INTO software_license_feature (license_key, feature_id)
                VALUES (%s, %s)
                """,
                (license_key, feature_id),
            )

    def delete(self, license_key: str, feature_id: int) -> None:
        self.db.execute(
            """
            DELETE FROM software_license_feature
            WHERE license_key = %s AND feature_id = %s
            """,
            (license_key, feature_id),
        )
