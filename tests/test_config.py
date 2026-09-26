from src.config import Config


def test_a_legacy_sync_on_config_loads_as_sync():
    assert Config.from_dict({"sync_monitors": True}).monitor_mode == "sync"


def test_a_legacy_sync_off_config_loads_as_independent():
    assert Config.from_dict({"sync_monitors": False}).monitor_mode == "independent"


def test_a_config_without_any_monitor_setting_loads_as_independent():
    assert Config.from_dict({"font_size": 30}).monitor_mode == "independent"


def test_monitor_mode_wins_over_the_legacy_key():
    assert Config.from_dict({"monitor_mode": "span", "sync_monitors": True}).monitor_mode == "span"


def test_an_unknown_monitor_mode_loads_as_independent():
    assert Config.from_dict({"monitor_mode": "diagonal"}).monitor_mode == "independent"


def test_monitor_mode_survives_a_save_and_load():
    assert Config.from_dict(Config(monitor_mode="span").to_dict()).monitor_mode == "span"


def test_a_legacy_config_keeps_its_other_settings():
    config = Config.from_dict({"font_size": 30, "target_fps": 60, "sync_monitors": True})
    assert (config.font_size, config.target_fps, config.monitor_mode) == (30, 60, "sync")
