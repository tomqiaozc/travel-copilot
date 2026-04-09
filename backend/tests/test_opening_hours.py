from app.maps.opening_hours import normalize_periods


def test_normalize_basic():
    raw = {"periods": [
        {"open": {"day": 1, "hour": 9, "minute": 0}, "close": {"day": 1, "hour": 17, "minute": 30}},
    ]}
    result = normalize_periods(raw)
    assert result == {"periods": [{"day": 1, "open": "09:00", "close": "17:30"}]}


def test_normalize_empty():
    assert normalize_periods({}) is None
    assert normalize_periods({"periods": []}) is None


def test_normalize_multiple_days():
    raw = {"periods": [
        {"open": {"day": 0, "hour": 10, "minute": 0}, "close": {"day": 0, "hour": 18, "minute": 0}},
        {"open": {"day": 1, "hour": 9, "minute": 0}, "close": {"day": 1, "hour": 17, "minute": 0}},
    ]}
    result = normalize_periods(raw)
    assert len(result["periods"]) == 2


def test_normalize_24h_place():
    # 24h places: single period, day=0, hour=0, no close -> expand to all 7 days
    raw = {"periods": [
        {"open": {"day": 0, "hour": 0, "minute": 0}},
    ]}
    result = normalize_periods(raw)
    assert len(result["periods"]) == 7
    for i, p in enumerate(result["periods"]):
        assert p["day"] == i
        assert p["open"] == "00:00"
        assert p["close"] == "23:59"


def test_normalize_single_day_with_close_not_24h():
    # Single period WITH close is NOT 24/7 — just a normal single-day entry
    raw = {"periods": [
        {"open": {"day": 3, "hour": 10, "minute": 0}, "close": {"day": 3, "hour": 22, "minute": 0}},
    ]}
    result = normalize_periods(raw)
    assert len(result["periods"]) == 1
    assert result["periods"][0] == {"day": 3, "open": "10:00", "close": "22:00"}
