from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class Shipment:
    shipment_id: str
    part_number: str
    description: str
    required_units: int
    launch_date: date
    original_eta: date
    delayed_eta: date
    incumbent_unit_cost: float
    incumbent_partial_units: int
    incumbent_partial_eta: date


@dataclass(frozen=True)
class SupplierOffer:
    supplier_id: str
    part_number: str
    available_units: int
    eta: date
    unit_cost: float
    expedite_fee: float
    quality_status: str


@dataclass(frozen=True)
class PolicyDecision:
    alternate_supplier_allowed: bool
    split_shipment_allowed: bool
    max_incremental_cost: float
    max_expedite_fee: float
    minimum_units_by_launch: int
    requires_director_approval: bool
    rationale: str


@dataclass(frozen=True)
class RecoveryOption:
    name: str
    units_by_launch: int
    eta: date
    incremental_cost: float
    policy_compliant: bool
    director_approval_required: bool
    explanation: str


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def load_demo_data(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_shipment(text: str, data: dict[str, Any]) -> Shipment:
    match = re.search(r"\bSHP-\d{5}\b", text.upper())
    shipment_id = match.group(0) if match else data["default_shipment_id"]
    raw = data["shipments"].get(shipment_id)
    if raw is None:
        raise ValueError(f"Unknown shipment ID: {shipment_id}")
    return Shipment(
        shipment_id=shipment_id,
        part_number=raw["part_number"],
        description=raw["description"],
        required_units=int(raw["required_units"]),
        launch_date=_parse_date(raw["launch_date"]),
        original_eta=_parse_date(raw["original_eta"]),
        delayed_eta=_parse_date(raw["delayed_eta"]),
        incumbent_unit_cost=float(raw["incumbent_unit_cost"]),
        incumbent_partial_units=int(raw["incumbent_partial_units"]),
        incumbent_partial_eta=_parse_date(raw["incumbent_partial_eta"]),
    )


def parse_policy(payload: dict[str, Any]) -> PolicyDecision:
    return PolicyDecision(
        alternate_supplier_allowed=bool(payload["alternate_supplier_allowed"]),
        split_shipment_allowed=bool(payload["split_shipment_allowed"]),
        max_incremental_cost=float(payload["max_incremental_cost"]),
        max_expedite_fee=float(payload["max_expedite_fee"]),
        minimum_units_by_launch=int(payload["minimum_units_by_launch"]),
        requires_director_approval=bool(payload.get("requires_director_approval", False)),
        rationale=str(payload["rationale"]),
    )


def parse_offers(payload: dict[str, Any]) -> list[SupplierOffer]:
    return [
        SupplierOffer(
            supplier_id=str(item["supplier_id"]),
            part_number=str(item["part_number"]),
            available_units=int(item["available_units"]),
            eta=_parse_date(item["eta"]),
            unit_cost=float(item["unit_cost"]),
            expedite_fee=float(item["expedite_fee"]),
            quality_status=str(item["quality_status"]),
        )
        for item in payload["offers"]
    ]


def as_json(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    return json.dumps(value, default=str, ensure_ascii=True, sort_keys=True)
