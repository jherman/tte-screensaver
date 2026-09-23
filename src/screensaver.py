"""Main screensaver pygame loop."""

import multiprocessing
import os
import queue
import sys
import random
import pygame
from dataclasses import dataclass
from multiprocessing.context import BaseContext
from multiprocessing.synchronize import Event
from typing import Dict, Optional, Tuple, List

from .config import Config, load_config
from .monitor_worker import WorkerSpec, run_worker
from .renderer import ANSIRenderer


@dataclass
class MonitorInfo:
    """Information about a single monitor."""
    x: int  # Position relative to virtual desktop
    y: int
    width: int
    height: int
    scale: float = 1.0  # Windows display scaling; 1.5 at 144 DPI. Always 1.0 unless the process is DPI-aware.


def enable_dpi_awareness() -> None:
    """Use physical pixels, so Windows stops bitmap-stretching the window on scaled monitors.

    Call before any window exists or any geometry is read. The setting is process-wide and permanent.
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
    except (ImportError, AttributeError):
        return  # Not Windows
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
    except AttributeError:
        user32.SetProcessDPIAware()  # Before Windows 10 1703


def get_virtual_desktop_size() -> Tuple[int, int, int, int]:
    """
    Get the virtual desktop bounds (covers all monitors).
    Returns (x, y, width, height) where x,y is the top-left corner.
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        return (x, y, width, height)
    except Exception:
        pass

    pygame.display.init()
    info = pygame.display.Info()
    return (0, 0, info.current_w, info.current_h)


def get_monitors() -> List[MonitorInfo]:
    """
    Get information about all connected monitors.
    Returns list of MonitorInfo with position and size.
    """
    monitors = []

    try:
        import ctypes
        from ctypes import wintypes

        # Define the callback type
        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )

        def monitor_enum_callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            rect = lprcMonitor.contents
            monitors.append(MonitorInfo(
                x=rect.left,
                y=rect.top,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top,
                scale=_monitor_scale(hMonitor),
            ))
            return True

        # Enumerate monitors
        ctypes.windll.user32.EnumDisplayMonitors(
            None, None,
            MONITORENUMPROC(monitor_enum_callback),
            0
        )

        if monitors:
            return monitors
    except Exception as e:
        print(f"Monitor enumeration failed: {e}", file=sys.stderr)

    # Fallback: single monitor
    vx, vy, vw, vh = get_virtual_desktop_size()
    return [MonitorInfo(x=vx, y=vy, width=vw, height=vh)]


def _monitor_scale(hmonitor) -> float:
    try:
        import ctypes
        from ctypes import wintypes
        dpi_x, dpi_y = wintypes.UINT(), wintypes.UINT()
        # MDT_EFFECTIVE_DPI; Windows 8.1+
        if ctypes.windll.shcore.GetDpiForMonitor(hmonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
            return dpi_x.value / 96
    except (AttributeError, OSError):
        pass
    return 1.0


class MonitorEffect:
    """Draws one monitor's effects, which a worker process generates and diffs."""

    def __init__(
        self,
        monitor: MonitorInfo,
        config: Config,
        renderer: ANSIRenderer,
        virtual_origin: Tuple[int, int],
        start_index: int,
        context: BaseContext,
        stop: Event,
    ):
        self.monitor = monitor
        self.config = config
        self.renderer = renderer

        # Calculate position relative to pygame window (which starts at virtual origin)
        self.offset_x = monitor.x - virtual_origin[0]
        self.offset_y = monitor.y - virtual_origin[1]

        # Calculate canvas size for this monitor
        self.canvas_width = monitor.width // renderer.char_width
        self.canvas_height = monitor.height // renderer.char_height

        self.effect_name: Optional[str] = None
        self._worker_lost = False
        # Bounded so the worker runs at most two frames ahead of the display.
        self.deltas = context.Queue(maxsize=2)
        spec = WorkerSpec(
            text=config.ascii_art,
            enabled_effects=config.enabled_effects,
            canvas_width=self.canvas_width,
            canvas_height=self.canvas_height,
            start_index=start_index,
        )
        self.process = context.Process(target=run_worker, args=(spec, self.deltas, stop), daemon=True)
        self.process.start()

    def update_and_render(self, surface: pygame.Surface) -> None:
        """Blit the worker's next delta, if one is ready. At most one per tick keeps effects at display speed."""
        if self._worker_lost:
            return
        try:
            self.effect_name, clears, draws = self.deltas.get_nowait()
        except queue.Empty:
            if not self.process.is_alive():
                self._blank(surface)
            return
        except Exception as e:
            print(f"Monitor worker delta unreadable: {e}", file=sys.stderr)
            self._blank(surface)
            return
        self.renderer.apply_delta(surface, clears, draws, self.offset_x, self.offset_y)

    def _blank(self, surface: pygame.Surface) -> None:
        """A dead worker blanks its monitor instead of taking down the screensaver."""
        self._worker_lost = True
        surface.fill(
            self.config.background_color,
            pygame.Rect(self.offset_x, self.offset_y, self.monitor.width, self.monitor.height),
        )

    def close(self, timeout: float = 1.0) -> None:
        self.process.join(timeout)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout)


class Screensaver:
    """Main screensaver application."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the screensaver."""
        self.config = config or load_config()
        self.running = False
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.monitor_effects: List[MonitorEffect] = []

        # Track mouse position for exit detection
        self.initial_mouse_pos: Optional[Tuple[int, int]] = None
        self.mouse_move_threshold = 10

    def _init_pygame(self, fullscreen: bool = True) -> Tuple[int, int]:
        """Initialize pygame and create the display."""
        if fullscreen:
            vx, vy, vw, vh = get_virtual_desktop_size()
            screen_size = (vw, vh)

            os.environ['SDL_VIDEO_WINDOW_POS'] = f"{vx},{vy}"

            pygame.init()
            pygame.mouse.set_visible(False)

            self.screen = pygame.display.set_mode(
                screen_size, pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF
            )

            # Make window topmost
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info()['window']
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 1 | 2)
            except Exception:
                pass
        else:
            pygame.init()
            pygame.mouse.set_visible(False)
            screen_size = (1280, 720)
            self.screen = pygame.display.set_mode(screen_size)

        pygame.display.set_caption("TTE Screensaver")
        self.clock = pygame.time.Clock()

        return screen_size

    def _handle_events(self) -> bool:
        """Handle pygame events. Returns False if should exit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                return False

            if event.type == pygame.MOUSEBUTTONDOWN:
                return False

            if event.type == pygame.MOUSEMOTION:
                current_pos = pygame.mouse.get_pos()
                if self.initial_mouse_pos is None:
                    self.initial_mouse_pos = current_pos
                else:
                    dx = abs(current_pos[0] - self.initial_mouse_pos[0])
                    dy = abs(current_pos[1] - self.initial_mouse_pos[1])
                    if dx > self.mouse_move_threshold or dy > self.mouse_move_threshold:
                        return False

        return True

    def run(self, fullscreen: bool = True) -> None:
        """Run the screensaver main loop."""
        # Spawn on every platform: workers must not inherit pygame or display state.
        context = multiprocessing.get_context("spawn")
        stop_workers = context.Event()
        if fullscreen:
            enable_dpi_awareness()
        try:
            screen_size = self._init_pygame(fullscreen)

            # Get virtual desktop origin for coordinate conversion
            vx, vy, _, _ = get_virtual_desktop_size()
            virtual_origin = (vx, vy)

            # Get all monitors and create an effect manager for each
            if fullscreen:
                monitors = get_monitors()
            else:
                # Single "monitor" for windowed mode
                monitors = [MonitorInfo(x=0, y=0, width=screen_size[0], height=screen_size[1])]

            print(f"Detected {len(monitors)} monitor(s)", file=sys.stderr)
            for i, m in enumerate(monitors):
                print(f"  Monitor {i+1}: {m.width}x{m.height} at ({m.x}, {m.y}) scale {m.scale:g}", file=sys.stderr)

            # Scale the font with each monitor's DPI so text keeps its physical size and the grid its cell count.
            renderers: Dict[int, ANSIRenderer] = {}

            def renderer_for(monitor: MonitorInfo) -> ANSIRenderer:
                font_size = round(self.config.font_size * monitor.scale)
                if font_size not in renderers:
                    renderers[font_size] = ANSIRenderer(font_size, self.config.background_color)
                return renderers[font_size]

            # Create independent effect for each monitor with different starting effects
            # Spread start indices apart so monitors don't show same effect
            num_effects = len(self.config.enabled_effects)
            self.monitor_effects = [
                MonitorEffect(
                    monitor, self.config, renderer_for(monitor), virtual_origin,
                    start_index=(i * num_effects // len(monitors)) + random.randint(0, 5),
                    context=context,
                    stop=stop_workers,
                )
                for i, monitor in enumerate(monitors)
            ]

            self.running = True

            # Clear screen once at startup (delta rendering handles subsequent frames)
            self.screen.fill(self.config.background_color)

            while self.running:
                if not self._handle_events():
                    self.running = False
                    break

                # Render each monitor's effect using delta rendering
                # (only updates changed cells, much faster than full redraw)
                for monitor_effect in self.monitor_effects:
                    monitor_effect.update_and_render(self.screen)

                pygame.display.flip()
                self.clock.tick(self.config.target_fps)

        except Exception as e:
            print(f"Screensaver error: {e}", file=sys.stderr)
            raise
        finally:
            stop_workers.set()
            # Close the window first so exiting feels instant, then reap the workers.
            pygame.quit()
            for monitor_effect in self.monitor_effects:
                monitor_effect.close()


def run_screensaver(fullscreen: bool = True, config: Optional[Config] = None) -> None:
    """Convenience function to run the screensaver."""
    screensaver = Screensaver(config=config)
    screensaver.run(fullscreen=fullscreen)
