from src.native_effects.base import layout_text
from src.screensaver import MonitorInfo, display_regions

# This machine: a landscape monitor with a portrait monitor on each side.
MONITORS = [
    MonitorInfo(x=3840, y=-1660, width=2560, height=3840, scale=1.5),
    MonitorInfo(x=0, y=0, width=3840, height=2160, scale=1.5),
    MonitorInfo(x=-2560, y=-1674, width=2560, height=3840, scale=1.5),
]
VIRTUAL_DESKTOP = (-2560, -1674, 8960, 3854)


def test_span_centers_one_region_on_the_primary_monitor():
    assert display_regions(MONITORS, "span", VIRTUAL_DESKTOP) == [
        MonitorInfo(x=-2560, y=-1674, width=8960, height=5508, scale=1.5)
    ]


def test_span_extends_past_the_desktop_when_the_primary_is_off_center():
    monitors = [
        MonitorInfo(x=0, y=0, width=1920, height=1080),
        MonitorInfo(x=1920, y=0, width=1920, height=1080),
    ]
    assert display_regions(monitors, "span", (0, 0, 3840, 1080)) == [
        MonitorInfo(x=-1920, y=0, width=5760, height=1080, scale=1.0)
    ]


def test_span_anchors_on_the_first_monitor_when_none_is_at_the_origin():
    monitors = [
        MonitorInfo(x=100, y=50, width=1920, height=1080),
        MonitorInfo(x=2020, y=50, width=1920, height=1080),
    ]
    assert display_regions(monitors, "span", (100, 50, 3840, 1080)) == [
        MonitorInfo(x=-1820, y=50, width=5760, height=1080, scale=1.0)
    ]


def test_span_text_lands_in_the_middle_of_the_primary_monitor():
    cell_w, cell_h = 25, 50
    (region,) = display_regions(MONITORS, "span", VIRTUAL_DESKTOP)
    cells = layout_text("TTE\nsaver\nTTE", region.width // cell_w, region.height // cell_h)
    rows = [row for row, _ in cells]
    cols = [col for _, col in cells]
    center_x = region.x + (min(cols) + max(cols) + 1) / 2 * cell_w
    center_y = region.y + (min(rows) + max(rows) + 1) / 2 * cell_h
    assert abs(center_x - 1920) <= cell_w
    assert abs(center_y - 1080) <= cell_h


def test_independent_keeps_one_region_per_monitor():
    assert display_regions(MONITORS, "independent", VIRTUAL_DESKTOP) == MONITORS


def test_sync_keeps_one_region_per_monitor():
    assert display_regions(MONITORS, "sync", VIRTUAL_DESKTOP) == MONITORS


def test_span_uses_the_largest_monitor_scale():
    monitors = [
        MonitorInfo(x=0, y=0, width=1920, height=1080, scale=1.0),
        MonitorInfo(x=1920, y=0, width=3840, height=2160, scale=1.5),
    ]
    assert display_regions(monitors, "span", (0, 0, 5760, 2160)) == [
        MonitorInfo(x=-3840, y=-1080, width=9600, height=3240, scale=1.5)
    ]
