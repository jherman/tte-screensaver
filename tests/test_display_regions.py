from src.screensaver import MonitorInfo, display_regions

# This machine: a landscape monitor with a portrait monitor on each side.
MONITORS = [
    MonitorInfo(x=3840, y=-1660, width=2560, height=3840, scale=1.5),
    MonitorInfo(x=0, y=0, width=3840, height=2160, scale=1.5),
    MonitorInfo(x=-2560, y=-1674, width=2560, height=3840, scale=1.5),
]
VIRTUAL_DESKTOP = (-2560, -1674, 8960, 3854)


def test_span_covers_the_virtual_desktop_with_one_region():
    assert display_regions(MONITORS, "span", VIRTUAL_DESKTOP) == [
        MonitorInfo(x=-2560, y=-1674, width=8960, height=3854, scale=1.5)
    ]


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
        MonitorInfo(x=0, y=0, width=5760, height=2160, scale=1.5)
    ]
