from __future__ import annotations

from benchmarking.profiles import get_profile, list_profiles


def test_profiles_include_smoke_daily_full() -> None:
    assert set(list_profiles()) == {"smoke", "daily", "full"}


def test_profile_smoke_and_daily_are_offline_friendly() -> None:
    smoke = get_profile("smoke")
    daily = get_profile("daily")
    assert smoke.requires_external_corpora is False
    assert daily.requires_external_corpora is False


def test_profiles_expose_required_fields() -> None:
    for name in ("smoke", "daily", "full"):
        profile = get_profile(name)
        assert profile.scenarios
        assert profile.enabled_layers
        assert profile.rerun_count >= 1
        assert isinstance(profile.upload_results_by_default, bool)
