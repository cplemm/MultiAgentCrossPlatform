from agent_framework import Message

from shipment_workflow import (
    _build_remote_planner_payload,
    _extract_policy,
    _response_output_text,
)


def test_builds_remote_planner_payload_from_fan_in_messages():
    messages = [
        Message(
            "assistant",
            [
                '{"shipment":{"shipment_id":"SHP-10042",'
                '"part_number":"BAT-48V-750"}}'
            ],
        ),
        Message(
            "assistant",
            [
                '{"specialists":{'
                '"purchasing_policy_specialist":{"policy":{'
                '"alternate_supplier_allowed":true,'
                '"split_shipment_allowed":true,'
                '"minimum_units_by_launch":900,'
                '"max_incremental_cost":30000,'
                '"max_expedite_fee":10000}},'
                '"supplier_specialist":{"supplier":{"offers":[]}}}}'
            ],
        ),
    ]
    payload = _build_remote_planner_payload(messages)
    assert payload["shipment"]["shipment_id"] == "SHP-10042"
    assert payload["policy"]["alternate_supplier_allowed"] is True
    assert payload["supplier"]["offers"] == []


def test_extracts_text_from_hosted_agent_response():
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"recommended":"Alpine"}'}
                ],
            }
        ]
    }
    assert _response_output_text(payload) == '{"recommended":"Alpine"}'


def test_extracts_direct_policy_result_from_specialist():
    policy = {
        "alternate_supplier_allowed": True,
        "split_shipment_allowed": True,
        "minimum_units_by_launch": 900,
        "max_incremental_cost": 30000,
        "max_expedite_fee": 10000,
    }
    assert _extract_policy(policy) == policy
