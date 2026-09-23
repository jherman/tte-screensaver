import time
from types import SimpleNamespace

import terminaltexteffects.effects.effect_matrix as effect_matrix

import pytest

from src import effects
from src.effects import EffectManager


class ClockedEffect:
    """Like TTE's Matrix, its iterator starts a wall-clock timer when created. Each frame reports its age."""

    def __init__(self, text):
        self.terminal_config = SimpleNamespace()

    def __iter__(self):
        created = time.monotonic()
        return (f"{time.monotonic() - created:.3f}" for _ in range(1000))


@pytest.fixture
def clocked_effects(monkeypatch):
    monkeypatch.setitem(effects.AVAILABLE_EFFECTS, "ClockedA", ClockedEffect)
    monkeypatch.setitem(effects.AVAILABLE_EFFECTS, "ClockedB", ClockedEffect)


def test_an_effect_starts_its_clock_when_it_starts_playing(clocked_effects):
    manager = EffectManager("text", ["ClockedA", "ClockedB"], start_index=0)
    time.sleep(0.5)

    manager.switch_to_next_effect()

    assert manager.get_current_effect_name() == "ClockedB"
    assert float(manager.get_next_frame()) < 0.25


def test_switching_never_repeats_the_current_effect(clocked_effects):
    manager = EffectManager("text", ["ClockedA", "ClockedB"], start_index=0)
    names = []
    for _ in range(6):
        manager.switch_to_next_effect()
        names.append(manager.get_current_effect_name())
    assert names == ["ClockedB", "ClockedA"] * 3


def test_matrix_keeps_raining_instead_of_filling_the_screen(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(effect_matrix.time, "time", lambda: now[0])
    manager = EffectManager("hello", ["Matrix"], 40, 20, start_index=0)
    manager.get_next_frame()

    now[0] += 3600
    for _ in range(50):
        manager.get_next_frame()

    assert manager._current_iterator.phase == "rain"


def test_an_effect_with_a_time_limit_ends_when_it_runs_out(clocked_effects, monkeypatch):
    monkeypatch.setitem(effects.EFFECT_TIME_LIMITS, "ClockedA", 0.2)
    manager = EffectManager("text", ["ClockedA", "ClockedB"], start_index=0)
    assert manager.get_next_frame() is not None

    time.sleep(0.3)

    assert manager.get_next_frame() is None
    manager.switch_to_next_effect()
    assert manager.get_next_frame() is not None
