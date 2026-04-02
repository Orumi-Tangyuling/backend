import os
from datetime import datetime
from unittest.mock import patch

import pytest

from fetch import fetchers


class FakeLocation:
    def __init__(self, code: str, distance_km: float):
        self.code = code
        self.distance_km = distance_km

    def distance_to(self, latitude: float, longitude: float) -> float:
        return self.distance_km


@pytest.fixture
def target_date():
    return datetime(2026, 4, 3, 0, 0, 0)


def _valid_item(obsrvn_dt: str, crdir: float, crsp: float) -> dict:
    return {
        "obsrvnDt": obsrvn_dt,
        "crdir": crdir,
        "crsp": crsp,
    }


@patch.dict(os.environ, {"CURRENT_API_KEY": "test-key"}, clear=False)
def test_fetch_current_uses_nearest_station_first(target_date):
    fake_locations = [
        FakeLocation("KG_0021", 5.0),
        FakeLocation("KG_0028", 10.0),
    ]

    with patch.object(fetchers.location, "OBSERVATORY_LOCATIONS", fake_locations):
        with patch("fetch.fetchers._fetch_tw_recent_items") as mock_fetch:
            mock_fetch.side_effect = lambda **kwargs: [
                _valid_item("2026-04-03 00:00", 120.0, 33.5)
            ] if kwargs["obs_code"] == "KG_0021" else []

            current_dir, current_speed = fetchers.fetch_current(target_date, 33.4, 126.5)

            assert current_dir == pytest.approx(120.0)
            assert current_speed == pytest.approx(33.5)
            first_call = mock_fetch.call_args_list[0].kwargs
            assert first_call["obs_code"] == "KG_0021"


@patch.dict(os.environ, {"CURRENT_API_KEY": "test-key"}, clear=False)
def test_fetch_current_fallback_from_kg_0021_to_kg_0028(target_date):
    fake_locations = [
        FakeLocation("KG_0021", 5.0),
        FakeLocation("KG_0028", 10.0),
    ]

    def fake_fetch(**kwargs):
        if kwargs["obs_code"] == "KG_0021":
            return [_valid_item("2026-04-03 00:00", None, None)]
        return [_valid_item("2026-04-03 00:00", 255.16, 27.5)]

    with patch.object(fetchers.location, "OBSERVATORY_LOCATIONS", fake_locations):
        with patch("fetch.fetchers._fetch_tw_recent_items", side_effect=fake_fetch):
            current_dir, current_speed = fetchers.fetch_current(target_date, 33.4, 126.5)

            assert current_dir == pytest.approx(255.16)
            assert current_speed == pytest.approx(27.5)


@patch.dict(os.environ, {"CURRENT_API_KEY": "test-key"}, clear=False)
def test_fetch_current_raises_when_all_stations_missing_values(target_date):
    fake_locations = [
        FakeLocation("KG_0021", 5.0),
        FakeLocation("KG_0028", 10.0),
    ]

    with patch.object(fetchers.location, "OBSERVATORY_LOCATIONS", fake_locations):
        with patch("fetch.fetchers._fetch_tw_recent_items", return_value=[_valid_item("2026-04-03 00:00", None, None)]):
            with pytest.raises(Exception) as exc_info:
                fetchers.fetch_current(target_date, 33.4, 126.5)

            assert "유효한 데이터가 없습니다" in str(exc_info.value)
            assert "KG_0021" in str(exc_info.value)
            assert "KG_0028" in str(exc_info.value)


@patch.dict(os.environ, {"CURRENT_API_KEY": "test-key"}, clear=False)
def test_fetch_current_selects_time_nearest_item():
    target = datetime(2026, 4, 3, 10, 20, 0)
    fake_locations = [FakeLocation("KG_0028", 1.0)]

    items = [
        _valid_item("2026-04-03 09:30", 10.0, 1.0),
        _valid_item("2026-04-03 10:30", 20.0, 2.0),
        _valid_item("2026-04-03 10:00", 30.0, 3.0),
    ]

    with patch.object(fetchers.location, "OBSERVATORY_LOCATIONS", fake_locations):
        with patch("fetch.fetchers._fetch_tw_recent_items", return_value=items):
            current_dir, current_speed = fetchers.fetch_current(target, 33.4, 126.5)

            assert current_dir == pytest.approx(20.0)
            assert current_speed == pytest.approx(2.0)


@patch.dict(os.environ, {"WIND_API_KEY": "wind-key"}, clear=False)
def test_fetch_current_uses_wind_key_as_fallback(target_date):
    fake_locations = [FakeLocation("KG_0028", 1.0)]

    with patch.object(fetchers.location, "OBSERVATORY_LOCATIONS", fake_locations):
        with patch("fetch.fetchers._fetch_tw_recent_items") as mock_fetch:
            mock_fetch.return_value = [_valid_item("2026-04-03 00:00", 90.0, 10.0)]
            with patch.dict(os.environ, {"CURRENT_API_KEY": ""}, clear=False):
                fetchers.fetch_current(target_date, 33.4, 126.5)

            call_kwargs = mock_fetch.call_args.kwargs
            assert call_kwargs["api_key"] == "wind-key"
