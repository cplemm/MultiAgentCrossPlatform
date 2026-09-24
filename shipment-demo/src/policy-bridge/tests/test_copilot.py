import pytest

from copilot import extract_policy_json


def test_extracts_policy_from_code_fence():
    text = """```json
{
  "alternate_supplier_allowed": true,
  "split_shipment_allowed": true,
  "max_incremental_cost": 30000,
  "max_expedite_fee": 12000,
  "minimum_units_by_launch": 900,
  "requires_director_approval": false,
  "rationale": "Within emergency authority."
}
```"""
    policy = extract_policy_json(text)
    assert policy["minimum_units_by_launch"] == 900


def test_rejects_incomplete_policy():
    with pytest.raises(ValueError, match="missing"):
        extract_policy_json('{"alternate_supplier_allowed": true}')
