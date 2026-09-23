import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="DPI awareness is a Windows API")

REPO = Path(__file__).parent.parent


def monitors_in_fresh_process(dpi_aware: bool):
    """DPI awareness is process-wide and permanent, so each variant needs its own process."""
    script = (
        "import json\n"
        "from src.screensaver import enable_dpi_awareness, get_monitors\n"
        + ("enable_dpi_awareness()\n" if dpi_aware else "")
        + "print(json.dumps([m.__dict__ for m in get_monitors()]))\n"
    )
    output = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return json.loads(output.strip().splitlines()[-1])


def test_dpi_aware_monitors_report_physical_pixels_and_their_scale():
    logical = monitors_in_fresh_process(dpi_aware=False)
    physical = monitors_in_fresh_process(dpi_aware=True)

    assert len(physical) == len(logical)
    for before, after in zip(logical, physical):
        assert before["scale"] == 1.0
        assert after["scale"] >= 1.0
        assert abs(after["width"] - before["width"] * after["scale"]) <= 1
        assert abs(after["height"] - before["height"] * after["scale"]) <= 1
