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
- Build the `.scr` with `.\build.bat`. It installs into `.venv` only and fails loudly.
  Call it with a path (`.\build.bat`): this machine sets `NoDefaultCurrentDirectoryInExePath`,
  so cmd does not find scripts in the current folder by bare name.
- Python files use CRLF line endings.
