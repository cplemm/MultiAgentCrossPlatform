from planner import build_plan


def test_recommends_alpine_energy():
    payload = {
        "shipment": {
            "shipment_id": "SHP-10042",
            "part_number": "BAT-48V-750",
            "required_units": 1200,
            "launch_date": "2026-10-07",
            "delayed_eta": "2026-10-16",
            "incumbent_unit_cost": 175.0,
            "incumbent_partial_units": 400,
            "incumbent_partial_eta": "2026-10-05",
        },
        "policy": {
            "alternate_supplier_allowed": True,
            "split_shipment_allowed": True,
            "max_incremental_cost": 30000,
            "max_expedite_fee": 12000,
            "minimum_units_by_launch": 900,
        },
        "supplier": {
            "offers": [
                {
                    "supplier_id": "Northwind Cells",
                    "part_number": "BAT-48V-750",
                    "available_units": 700,
                    "eta": "2026-10-04",
                    "unit_cost": 188.0,
                    "expedite_fee": 7500.0,
                    "quality_status": "Approved",
                },
                {
                    "supplier_id": "Alpine Energy",
                    "part_number": "BAT-48V-750",
                    "available_units": 600,
                    "eta": "2026-10-06",
                    "unit_cost": 181.0,
                    "expedite_fee": 4200.0,
                    "quality_status": "Approved",
                },
            ]
        },
    }
    result = build_plan(payload)
    recommendation = result["recommended_option"]
    assert recommendation["name"] == "Split incumbent + Alpine Energy"
    assert recommendation["incremental_cost"] == 7800
    assert recommendation["units_by_launch"] == 1000
    assert result["planner"].endswith("Hosted Agent")
