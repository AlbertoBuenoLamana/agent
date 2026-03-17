---
model: opus
description: Install, configure, and verify the steer agent sandbox on this Ubuntu Linux device
---

# Purpose

Run directly on the agent sandbox device (e.g. Ubuntu server/desktop) to install all dependencies, clone the repo, install steer, set up Python environments, and run a full verification suite that proves the sandbox is operational. This is the local bootstrap — run it on the machine that will execute agent jobs.

## Variables

LISTEN_PORT: 7600

## Codebase Structure

```
steer/
├── apps/
│   ├── steer-linux/    # Python CLI — needs uv pip install -e .
│   ├── drive/          # Python CLI — needs uv
│   ├── listen/         # Python — needs uv (FastAPI server)
│   └── direct/         # Python — needs uv (CLI client)
├── .claude/
│   ├── commands/       # Slash commands
│   ├── skills/         # Agent skills (steer, drive)
│   └── agents/         # System prompts
└── justfile            # Task runner recipes
```

## Prerequisites

Before running this installer, ensure the following:

| Requirement | Why | How to verify |
|-------------|-----|---------------|
| **X11 or Wayland display** | Steer needs a display server for GUI automation | `echo $DISPLAY` should show `:0` or similar |
| **AT-SPI2 enabled** | Steer reads accessibility trees for UI elements | `busctl --user list \| grep Accessibility` |
| **SSH access** (optional) | Lets the engineer manage the sandbox remotely | `sudo systemctl enable ssh` |

### Prevent Sleep (Keep-Alive)

The agent sandbox must never sleep — it needs to be always-on to pick up jobs at any time.

```bash
# Disable suspend/sleep via systemd
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

# If using GNOME, also disable screen blank and auto-suspend
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.desktop.session idle-delay 0
```

Verify with: `systemctl status sleep.target` — should show "masked".

## Instructions

- All commands run locally via Bash — this is running ON the agent device
- Run each command individually so you can check the output before proceeding
- If a dependency is already installed, skip it and note the version
- If a step fails, stop and report the failure — do not continue blindly
- Ensure X11/Wayland display server is running and AT-SPI2 is enabled
- Use `apt` for system package installations
- Use `uv` for all Python dependency management — do NOT use pip
- Verify each tool works after installation by running its `--version` or `--help`
- The verification phase must test real functionality, not just that binaries exist
- Every verification check must produce a clear PASS or FAIL result

## Workflow

### Phase 1: Install

1. Check Ubuntu version:
   ```
   lsb_release -a
   ```

2. Check what's already installed — run `which` for each tool and capture versions:
   ```
   which tmux just uv yq claude node xdotool wmctrl scrot xclip tesseract
   ```
   Then for each found tool, run its version command:
   - `tmux -V`
   - `just --version`
   - `uv --version`
   - `yq --version`
   - `claude --version`
   - `node --version`
   - `xdotool --version`
   - `wmctrl --help 2>&1 | head -1`
   - `scrot --version`
   - `tesseract --version`

3. Install system dependencies:
   ```
   sudo apt update && sudo apt install -y xdotool wmctrl scrot xclip tesseract-ocr python3-atspi imagemagick x11-utils tmux curl git
   ```

4. Install uv if missing:
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

5. Install just if missing:
   ```
   curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
   ```

6. Install Node.js if missing:
   ```
   sudo apt install -y nodejs npm
   ```

7. Install Claude Code if missing:
   ```
   npm install -g @anthropic-ai/claude-code
   ```

8. Install steer (Python CLI):
   ```
   cd apps/steer-linux && uv pip install -e .
   ```

9. Verify Python apps — uv will auto-install deps on first run:
    ```
    cd apps/drive && uv run python main.py --version
    cd apps/listen && uv run python main.py --help 2>&1 | head -1
    cd apps/direct && uv run python main.py --help 2>&1 | head -1
    ```

### Phase 2: Verify

Run each check and record PASS/FAIL. Do not stop on failure — run all checks and report results at the end.

10. **Steer CLI** — confirm it runs and prints version:
    ```
    cd apps/steer-linux && uv run python main.py --version
    ```

11. **Steer screenshots** — take a screenshot of the desktop (tests scrot + X11):
    ```
    cd apps/steer-linux && uv run python main.py see --json
    ```
    PASS if JSON output contains a `screenshot` path to a valid PNG. FAIL if error.

12. **Steer OCR** — run OCR on whatever is on screen (tests Tesseract):
    ```
    cd apps/steer-linux && uv run python main.py ocr --json
    ```
    PASS if JSON output contains `results` array. FAIL if error.

13. **Steer apps** — list running applications (tests wmctrl/xdotool):
    ```
    cd apps/steer-linux && uv run python main.py apps --json
    ```
    PASS if JSON output is an array with at least one app. FAIL if empty or error.

14. **Drive session** — create and destroy a tmux session (tests tmux):
    ```
    cd apps/drive && uv run python main.py session create --name verify-test --json
    cd apps/drive && uv run python main.py session list --json
    cd apps/drive && uv run python main.py session kill verify-test --json
    ```
    PASS if session creates, appears in list, and kills cleanly. FAIL if any step errors.

15. **Drive run** — execute a command in a tmux session (tests sentinel protocol):
    ```
    cd apps/drive && uv run python main.py session create --name verify-run --json
    cd apps/drive && uv run python main.py run verify-run "echo hello-from-drive" --json
    cd apps/drive && uv run python main.py session kill verify-run --json
    ```
    PASS if run output contains "hello-from-drive" and exit code 0. FAIL otherwise.

16. **Listen server** — start listen, verify it responds, then stop it:
    ```
    cd apps/listen && uv run python main.py &
    LISTEN_PID=$!
    sleep 2
    curl -s http://localhost:7600/jobs
    kill $LISTEN_PID 2>/dev/null
    ```
    PASS if curl returns a YAML response. FAIL if connection refused or error.

17. **Direct client** — verify the CLI parses correctly:
    ```
    cd apps/direct && uv run python main.py --help
    ```
    PASS if help text shows start/get/list/stop commands. FAIL if error.

18. **Justfile** — verify all recipes are visible:
    ```
    just --list
    ```
    PASS if output includes listen, send, job, jobs, stop. FAIL if any are missing.

19. **Claude Code** — verify it can start (non-interactive):
    ```
    claude --version
    ```
    PASS if version string returned. FAIL if command not found.

20. Remind the user about display server requirements if any steer checks failed:

    | Requirement | How to verify/fix |
    |-------------|-------------------|
    | X11 display | `echo $DISPLAY` should show `:0` — if headless, use `Xvfb :99 -screen 0 1280x720x24 &` and `export DISPLAY=:99` |
    | AT-SPI2 | `busctl --user list \| grep Accessibility` — install `at-spi2-core` if missing |
    | xdotool | `xdotool --version` — `sudo apt install xdotool` |
    | wmctrl | `wmctrl --help` — `sudo apt install wmctrl` |
    | scrot | `scrot --version` — `sudo apt install scrot` |
    | tesseract | `tesseract --version` — `sudo apt install tesseract-ocr` |

21. Now follow the `Report` section to report the completed work

## Report

Present results in this format:

## Agent Sandbox: [hostname]

**Ubuntu**: [version]
**Repo**: [path]

### Dependencies

| Tool | Status | Version |
|------|--------|---------|
| xdotool | [installed/missing] | [version] |
| wmctrl | [installed/missing] | [version] |
| scrot | [installed/missing] | [version] |
| xclip | [installed/missing] | [version] |
| tesseract | [installed/missing] | [version] |
| tmux | [installed/missing] | [version] |
| just | [installed/missing] | [version] |
| uv | [installed/missing] | [version] |
| yq | [installed/missing] | [version] |
| Node.js | [installed/missing] | [version] |
| Claude Code | [installed/missing] | [version] |

### Apps

| App | Build | Notes |
|-----|-------|-------|
| steer | [ready/failed] | [version or error] |
| drive | [ready/failed] | [version or error] |
| listen | [ready/failed] | [notes] |
| direct | [ready/failed] | [notes] |

### Verification

| Check | Result | Details |
|-------|--------|---------|
| steer --version | [PASS/FAIL] | [version or error] |
| steer see (screenshot) | [PASS/FAIL] | [screenshot path or error] |
| steer ocr | [PASS/FAIL] | [element count or error] |
| steer apps | [PASS/FAIL] | [app count or error] |
| drive session create/kill | [PASS/FAIL] | [details] |
| drive run (sentinel) | [PASS/FAIL] | [output or error] |
| listen server | [PASS/FAIL] | [response or error] |
| direct --help | [PASS/FAIL] | [commands found or error] |
| just --list | [PASS/FAIL] | [recipe count or error] |
| claude --version | [PASS/FAIL] | [version or error] |

### Display Server

If any steer checks failed, list what needs attention:

| Requirement | How to fix |
|-------------|------------|
| X11 display | If headless: `sudo apt install xvfb && Xvfb :99 -screen 0 1280x720x24 &` then `export DISPLAY=:99` |
| AT-SPI2 | `sudo apt install at-spi2-core` and verify with `busctl --user list \| grep Accessibility` |

### Result

**[X/10 checks passed]** — [READY / NOT READY — needs attention]

If all 10 pass: "Sandbox is fully operational. Start the server with `just listen`."
If any fail: List what needs to be fixed before the sandbox is ready.

### Fix It?

If any dependencies are missing or any checks failed (excluding display server permissions which may require manual setup), ask the user:

> "Would you like me to install the missing pieces and re-run the failed checks?"

If they say yes, go back and install/fix only what failed, then re-run only the failed verification checks and present an updated report.
