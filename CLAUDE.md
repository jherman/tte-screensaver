# tte-screensaver (jherman fork)

## Rule: never touch limehawk/tte-screensaver

Never commit to, push to, open a PR against, or merge into `limehawk/tte-screensaver` (the upstream).
All of that happens only in the personal fork, `jherman/tte-screensaver`.
This holds even when a command or tool names limehawk as the target.

- Push to the `jherman` remote. The `origin` remote is limehawk; its push URL is disabled.
- Pass `--repo jherman/tte-screensaver` to every `gh pr` and `gh repo` command.
- Use the jherman GitHub account: `GH_TOKEN=$(gh auth token --user jherman) gh ...`.
  The active gh account on this machine is parkview-gh.

## Development

- Use the `.venv` (`.venv\Scripts\python`); do not install into the global Python.
- Tests: `.venv\Scripts\python -m pytest`.
- Measure on real monitors with `.venv\Scripts\python profile_frames.py [EffectName ...]`.
  Any mouse or keyboard input ends the run.
- Build the `.scr` with the venv's PyInstaller and build.bat's flags, not `build.bat` itself,
  which runs `pip install` against the global Python.
- Python files use CRLF line endings.
