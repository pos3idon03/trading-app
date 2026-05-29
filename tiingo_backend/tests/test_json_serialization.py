import json
from datetime import date, datetime, timezone
from uuid import uuid4

from utils.json_serialization import json_safe


def test_json_safe_converts_uuid_and_datetime():
    deployment_id = uuid4()
    order_id = uuid4()
    bar_time = datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc)

    payload = {
        "deployment_id": deployment_id,
        "evaluation": {
            "id": order_id,
            "bar_time": bar_time,
            "created_at": bar_time,
        },
        "items": [deployment_id],
    }

    safe = json_safe(payload)

    assert safe["deployment_id"] == str(deployment_id)
    assert safe["evaluation"]["id"] == str(order_id)
    assert safe["evaluation"]["bar_time"] == bar_time.isoformat()
    assert safe["items"] == [str(deployment_id)]
    json.dumps(safe)


def test_json_safe_converts_date():
    payload = {"as_of": date(2026, 5, 28)}
    safe = json_safe(payload)
    assert safe["as_of"] == "2026-05-28"
    json.dumps(safe)


def test_json_safe_leaves_scalars_unchanged():
    payload = {"count": 3, "ok": True, "label": "done", "missing": None}
    assert json_safe(payload) == payload
