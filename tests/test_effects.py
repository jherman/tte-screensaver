import time
from types import SimpleNamespace

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



def test_managers_with_the_same_seed_pick_the_same_effects(monkeypatch):
    names = ["ClockedA", "ClockedB", "ClockedC", "ClockedD"]
    for name in names:
        monkeypatch.setitem(effects.AVAILABLE_EFFECTS, name, ClockedEffect)

    def sequence(seed):
        manager = EffectManager("text", names, start_index=2, seed=seed)
        picked = [manager.get_current_effect_name()]
        for _ in range(20):
            manager.switch_to_next_effect()
            picked.append(manager.get_current_effect_name())
        return picked

    assert sequence(7) == sequence(7)
    assert len(set(sequence(7))) == 4
