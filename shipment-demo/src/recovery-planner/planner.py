from __future__ import annotations

from datetime import date
from itertools import combinations
from typing import Any


def _date(value: str) -> date:
    return date.fromisoformat(value)


def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    shipment = payload["shipment"]
    policy = payload["policy"]
    offers = payload["supplier"]["offers"]

    launch_date = _date(shipment["launch_date"])
    incumbent_cost = float(shipment["incumbent_unit_cost"])
    partial_units = int(shipment["incumbent_partial_units"])
    partial_eta = _date(shipment["incumbent_partial_eta"])
    options: list[dict[str, Any]] = [
        {
            "name": "Use incumbent deliveries only",
            "units_by_launch": partial_units,
            "eta": shipment["delayed_eta"],
            "incremental_cost": 0.0,
            "policy_compliant": False,
            "director_approval_required": False,
            "explanation": (
                f"{partial_units} units arrive by {partial_eta}; remaining "
                f"units arrive on {shipment['delayed_eta']}."
            ),
        }
    ]

    eligible = [
        offer
        for offer in offers
        if offer["part_number"] == shipment["part_number"]
        and offer["quality_status"].lower() == "approved"
        and _date(offer["eta"]) <= launch_date
    ]
    for count in range(1, len(eligible) + 1):
        for selected in combinations(eligible, count):
            units = partial_units + sum(
                int(offer["available_units"]) for offer in selected
            )
            incremental_cost = sum(
                (
                    float(offer["unit_cost"]) - incumbent_cost
                ) * int(offer["available_units"])
                + float(offer["expedite_fee"])
                for offer in selected
            )
            max_expedite = max(
                float(offer["expedite_fee"]) for offer in selected
            )
            compliant = (
                bool(policy["alternate_supplier_allowed"])
                and bool(policy["split_shipment_allowed"])
                and units >= int(policy["minimum_units_by_launch"])
                and incremental_cost <= float(policy["max_incremental_cost"])
                and max_expedite <= float(policy["max_expedite_fee"])
            )
            suppliers = " + ".join(
                str(offer["supplier_id"]) for offer in selected
            )
            eta = max(
                [partial_eta] + [_date(offer["eta"]) for offer in selected]
            )
            options.append(
                {
                    "name": f"Split incumbent + {suppliers}",
                    "units_by_launch": units,
                    "eta": eta.isoformat(),
                    "incremental_cost": round(incremental_cost, 2),
                    "policy_compliant": compliant,
                    "director_approval_required": (
                        incremental_cost
                        > float(policy["max_incremental_cost"])
                    ),
                    "explanation": (
                        f"{partial_units} incumbent units plus "
                        f"{sum(int(o['available_units']) for o in selected)} "
                        f"alternate units arrive by {eta}."
                    ),
                }
            )

    options.sort(
        key=lambda item: (
            not item["policy_compliant"],
            -item["units_by_launch"],
            item["incremental_cost"],
            item["eta"],
        )
    )
    compliant = [item for item in options if item["policy_compliant"]]
    recommendation = min(
        compliant or options,
        key=lambda item: (
            item["incremental_cost"],
            -item["units_by_launch"],
            item["eta"],
        ),
    )
    return {
        "shipment": shipment,
        "policy": policy,
        "options": options,
        "recommended_option": recommendation,
        "planner": "shipment-recovery-planner Hosted Agent",
    }
