from src.config import Config


def test_configs_saved_before_sync_monitors_existed_load_with_it_off():
    assert Config.from_dict({"font_size": 30}).sync_monitors is False


def test_sync_monitors_survives_a_save_and_load():
    assert Config.from_dict(Config(sync_monitors=True).to_dict()).sync_monitors is True
