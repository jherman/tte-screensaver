"""
TTE Screensaver - Main entry point.

Windows screensaver command-line arguments:
  /s - Run the screensaver in fullscreen mode
  /c - Show the configuration dialog
  /p <hwnd> - Preview: animate the small monitor in Screen Saver Settings (window handle hwnd)
  (no args) - Show configuration dialog
"""

import multiprocessing
import sys
from typing import List, Optional


def main() -> None:
    """Main entry point for the screensaver."""
    # In the frozen .scr, monitor worker processes re-launch this executable; this hands them off.
    multiprocessing.freeze_support()
    args = [arg.lower() for arg in sys.argv[1:]]

    if not args:
        # No arguments - show config dialog
        from .config_dialog import show_config_dialog
        show_config_dialog()

    elif "/s" in args or "-s" in args:
        # Run screensaver in fullscreen
        from .screensaver import run_screensaver
        run_screensaver(fullscreen=True)

    elif "/c" in args or "-c" in args:
        # Show configuration dialog
        from .config_dialog import show_config_dialog
        show_config_dialog()

    elif _preview_window(args) is not None:
        from .preview import run_preview
        run_preview(_preview_window(args))

    else:
        # Unknown argument - show config dialog
        from .config_dialog import show_config_dialog
        show_config_dialog()


def _preview_window(args: List[str]) -> Optional[int]:
    """The window handle from "/p <hwnd>" or "/p:<hwnd>", or None if this is not a preview request."""
    for index, arg in enumerate(args):
        value = None
        if arg in ("/p", "-p") and index + 1 < len(args):
            value = args[index + 1]
        elif arg.startswith(("/p:", "-p:")):
            value = arg[3:]
        if value is not None:
            try:
                return int(value)
            except ValueError:
                return None
    return None


if __name__ == "__main__":
    main()
