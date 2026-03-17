# PRD: Port Mac Mini Agent to Ubuntu

## Context

El proyecto **Mac Mini Agent** es un toolkit de automatizacion de escritorio para agentes AI. Tiene 4 apps: **Steer** (GUI automation, Swift), **Drive** (terminal/tmux, Python), **Listen** (job server, Python), **Direct** (HTTP client, Python). Actualmente solo funciona en macOS. El objetivo es portarlo a Ubuntu Linux manteniendo la misma interfaz CLI y formato de salida JSON.

## Alcance

| App | Accion |
|-----|--------|
| **Drive** | Sin cambios — tmux funciona nativo en Linux |
| **Listen** | Cambio menor en `worker.py` (reemplazar `osascript`/Terminal.app por tmux directo) |
| **Direct** | Sin cambios |
| **Steer** | Reescritura completa: Swift → Python, macOS APIs → herramientas Linux |
| **Prompts** | Actualizar referencias de "macOS" a "Ubuntu/Linux" |

---

## 1. Reescribir Steer en Python

### Ubicacion

Crear `apps/steer-linux/` con la misma estructura que `apps/drive/`:

```
apps/steer-linux/
  main.py              # CLI entry (Click), mismos 14 subcomandos
  pyproject.toml       # deps: click, pillow, pytesseract, psutil
  commands/
    see.py             # screenshot + accessibility
    click.py           # click elements
    type_cmd.py        # type text
    hotkey.py          # keyboard shortcuts
    scroll.py          # scroll
    drag.py            # drag
    apps.py            # list/launch/activate apps
    screens.py         # list displays
    window.py          # window management
    ocr.py             # OCR
    focus.py           # focused element
    find.py            # search elements in snapshot
    clipboard.py       # clipboard read/write
    wait.py            # polling wait
  modules/
    input.py           # xdotool wrapper (reemplaza MouseControl.swift + Keyboard.swift)
    accessibility.py   # AT-SPI2 (reemplaza AccessibilityTree.swift)
    capture.py         # scrot/xrandr (reemplaza ScreenCapture.swift)
    ocr_engine.py      # pytesseract (reemplaza OCR.swift)
    element_store.py   # snapshot cache /tmp/steer/ (misma logica que ElementStore.swift)
    app_control.py     # wmctrl/xdotool (reemplaza AppControl.swift)
    window_control.py  # wmctrl (reemplaza WindowControl.swift)
    errors.py          # mismos tipos de error que Errors.swift
    output.py          # JSON/text output helper
```

### Dependencias del sistema (apt)

```bash
sudo apt install xdotool wmctrl scrot xclip tesseract-ocr python3-atspi imagemagick x11-utils
```

### Dependencias Python (`pyproject.toml`)

```toml
[project]
name = "steer"
version = "0.2.0"
requires-python = ">=3.11"
dependencies = ["click>=8.1", "pillow>=10.0", "pytesseract>=0.3", "psutil>=5.9"]

[project.scripts]
steer = "main:cli"
```

---

## 2. Mapeo de APIs: macOS → Linux

Cada modulo de `modules/` reemplaza una API de macOS con su equivalente Linux via `subprocess.run()`.

### `modules/capture.py` — Reemplaza `apps/steer/Sources/steer/ScreenCapture.swift`

| macOS | Linux |
|-------|-------|
| `CGWindowListCreateImage` | `scrot` (X11) / `grim` (Wayland) |
| `NSScreen` | `xrandr --query` |
| `CGWindowListCopyWindowInfo` | `wmctrl -lG` |

Funciones:
- `capture_screen(index: int | None) -> Path` — captura pantalla completa o por indice, guarda PNG en `/tmp/steer/`
- `capture_app(app_name: str) -> Path` — `xdotool search --name` para window ID, luego `import -window <id> /tmp/steer/<snap>.png` (ImageMagick)
- `list_screens() -> list[ScreenInfo]` — parsea `xrandr --query` → nombre, resolucion, offset, primary
- `screen_info(index: int) -> ScreenInfo | None`
- `window_bounds(app_name: str) -> list[WindowBounds]` — parsea `wmctrl -lG`

### `modules/accessibility.py` — Reemplaza `apps/steer/Sources/steer/AccessibilityTree.swift`

| macOS | Linux |
|-------|-------|
| `AXUIElement` | AT-SPI2 via `python3-atspi` o D-Bus |
| `AXUIElementCopyAttributeValue` | `Atspi.Accessible.get_*()` |
| `kAXFocusedUIElementAttribute` | `Atspi.get_desktop(0)` traversal |

Funciones:
- `walk(app_name: str, max_depth: int = 15) -> list[UIElement]` — recorre arbol AT-SPI2, asigna IDs con mismo esquema de prefijos
- `focused_element(app_name: str) -> UIElement | None` — elemento con foco via AT-SPI2
- `is_accessibility_granted() -> bool` — en Linux AT-SPI2 suele estar habilitado por defecto

Mapeo de roles (mismos prefijos que Swift original):

| AT-SPI2 role | Prefijo |
|--------------|---------|
| `push button` | B |
| `text` | T |
| `label` | S |
| `image` | I |
| `check box` | C |
| `radio button` | R |
| `combo box` | P |
| `slider` | SL |
| `link` | L |
| `menu item` | M |
| `page tab` | TB |
| otros | E |

**Nota**: AT-SPI2 es menos consistente que macOS Accessibility. El OCR con `--ocr` flag sera mas importante como fallback.

### `modules/input.py` — Reemplaza `apps/steer/Sources/steer/MouseControl.swift` + `Keyboard.swift`

| macOS | Linux |
|-------|-------|
| `CGEvent` | `xdotool` (X11) / `ydotool` (Wayland) |
| `CGWarpMouseCursorPosition` | `xdotool mousemove --sync` |
| Virtual key codes | `xdotool key` con nombres X11 |

Funciones:
- `click(x, y, button="left", count=1, modifiers=[])` — `xdotool mousemove --sync {x} {y} click {button_num}`
- `type_text(text)` — `xdotool type --delay 50 "{text}"`
- `hotkey(combo)` — parsea `"cmd+s"` → `xdotool key super+s`
- `scroll(direction, lines)` — `xdotool click {4|5|6|7}` repetido (4=up, 5=down, 6=left, 7=right)
- `drag(from_x, from_y, to_x, to_y, steps=20)` — mousedown + mousemove interpolado + mouseup
- `move_to(x, y)` — `xdotool mousemove --sync`
- `key_down(key)` / `key_up(key)` — para modifiers sticky

**Mapeo de modificadores**: `cmd` → `super`, `alt` → `alt`, `ctrl` → `ctrl`, `shift` → `shift`

### `modules/ocr_engine.py` — Reemplaza `apps/steer/Sources/steer/OCR.swift`

| macOS | Linux |
|-------|-------|
| `VNRecognizeTextRequest` | `pytesseract.image_to_data()` |
| `VNImageRequestHandler` | `Pillow` para cargar imagen |

Funciones:
- `recognize(image_path, confidence=0.5) -> list[OCRResult]` — pytesseract con output_type=dict → texto + bounding boxes + confianza
- `to_elements(results) -> list[UIElement]` — convierte a UIElements con IDs O1, O2, etc.

### `modules/element_store.py` — Reemplaza `apps/steer/Sources/steer/ElementStore.swift`

Misma logica exacta portada a Python. Almacena en `/tmp/steer/<snapid>.json` y `.png`.

Funciones: `save(id, elements, screenshot_path)`, `load(id)`, `latest()`, `resolve(query, snap_id)`

Esquema de IDs identico: 8-char UUID prefix, elementos con role-prefix (B1, T2, S3).

### `modules/app_control.py` — Reemplaza `apps/steer/Sources/steer/AppControl.swift`

| macOS | Linux |
|-------|-------|
| `NSWorkspace.shared.runningApplications` | `wmctrl -l` + `ps aux` |
| `NSApplication.activate` | `wmctrl -a` / `xdotool windowactivate` |
| `NSWorkspace.launchApplication` | `subprocess.Popen` / `.desktop` files |

Funciones:
- `list_apps() -> list[AppInfo]` — combina `wmctrl -l` con `ps`
- `find(name) -> AppInfo | None` — busqueda case-insensitive
- `activate(name)` — `wmctrl -a "{name}"`
- `launch(name)` — `subprocess.Popen([name])` o buscar en `/usr/share/applications/`
- `frontmost() -> AppInfo | None` — `xdotool getactivewindow`

### `modules/window_control.py` — Reemplaza `apps/steer/Sources/steer/WindowControl.swift`

| macOS | Linux |
|-------|-------|
| `AXUIElement` window attrs | `wmctrl` + `xdotool` |
| `AXUIElementSetAttributeValue` | `wmctrl -r -e` / `-b` |

Funciones:
- `list_windows(app) -> list[WindowInfo]` — `wmctrl -lGp` filtrado por PID
- `move(app, x, y)` — `wmctrl -r :ACTIVE: -e 0,{x},{y},-1,-1`
- `resize(app, w, h)` — `wmctrl -r :ACTIVE: -e 0,-1,-1,{w},{h}`
- `minimize(app)` — `xdotool windowminimize`
- `restore(app)` — `wmctrl -r -b remove,hidden`
- `fullscreen(app)` — `wmctrl -r -b toggle,fullscreen`
- `close(app)` — `wmctrl -c "{app}"`

### `modules/errors.py` — Reemplaza `apps/steer/Sources/steer/Errors.swift`

```python
class SteerError(Exception): pass
class CaptureFailure(SteerError): pass
class AppNotFound(SteerError): pass
class ElementNotFound(SteerError): pass
class NoSnapshot(SteerError): pass
class ScreenNotFound(SteerError): pass
class WindowNotFound(SteerError): pass
class ClipboardEmpty(SteerError): pass
class WaitTimeout(SteerError): pass
class OcrFailed(SteerError): pass
```

---

## 3. Comandos CLI — Interfaz identica al Swift

Cada comando debe tener **exactamente los mismos flags, opciones y argumentos** que el Swift original. Referencia: `apps/steer/Sources/steer/*.swift`.

### `see` — Ref: `apps/steer/Sources/steer/See.swift`

```
steer see [--app NAME] [--screen INDEX] [--ocr] [--role ROLE] [--json]
```

JSON output:
```json
{"snapshot":"ab12cd34","app":"Firefox","screenshot":"/tmp/steer/ab12cd34.png","count":42,"windows":[{"id":0,"title":"...","x":0,"y":0,"width":1920,"height":1080}],"elements":[{"id":"B1","role":"button","label":"Close","value":null,"x":100,"y":200,"width":30,"height":30,"isEnabled":true,"depth":1}]}
```

### `click` — Ref: `apps/steer/Sources/steer/Click.swift`

```
steer click [--on ID|LABEL] [-x X] [-y Y] [--snapshot ID] [--screen INDEX] [--double] [--right] [--middle] [--modifier COMBO] [--json]
```

JSON: `{"action":"click","x":100,"y":200,"label":"Close","ok":true}`

### `type` — Ref: `apps/steer/Sources/steer/Type.swift`

```
steer type TEXT [--into ID|LABEL] [--snapshot ID] [--screen INDEX] [--clear] [--json]
```

JSON: `{"action":"type","text":"hello","ok":true}`

### `hotkey` — Ref: `apps/steer/Sources/steer/Hotkey.swift`

```
steer hotkey COMBO [--json]
```

JSON: `{"action":"hotkey","combo":"cmd+s","ok":true}`

### `scroll` — Ref: `apps/steer/Sources/steer/Scroll.swift`

```
steer scroll DIRECTION [LINES=3] [--json]
```

JSON: `{"action":"scroll","direction":"down","lines":3,"ok":true}`

### `drag` — Ref: `apps/steer/Sources/steer/Drag.swift`

```
steer drag [--from ID|LABEL] [--from-x X] [--from-y Y] [--to ID|LABEL] [--to-x X] [--to-y Y] [--snapshot ID] [--screen INDEX] [--modifier COMBO] [--steps 20] [--json]
```

JSON: `{"action":"drag","fromX":100,"fromY":200,"toX":300,"toY":400,"ok":true}`

### `apps` — Ref: `apps/steer/Sources/steer/Apps.swift`

```
steer apps [ACTION=list] [NAME] [--json]
```

JSON list: `[{"name":"Firefox","pid":1234,"bundleId":"","isActive":true}]`
JSON action: `{"action":"launch","app":"Firefox","ok":true}`

**Nota**: `bundleId` no existe en Linux — devolver string vacio `""`.

### `screens` — Ref: `apps/steer/Sources/steer/Screens.swift`

```
steer screens [--json]
```

JSON: `[{"index":0,"name":"eDP-1","width":1920,"height":1080,"originX":0,"originY":0,"isMain":true,"scaleFactor":1.0}]`

### `window` — Ref: `apps/steer/Sources/steer/Window.swift`

```
steer window ACTION APP [-x X] [-y Y] [-w WIDTH] [-h HEIGHT] [--json]
```

Actions: `list`, `move`, `resize`, `minimize`, `restore`, `fullscreen`, `close`

JSON list: `[{"app":"Firefox","title":"Tab","x":0,"y":0,"width":1920,"height":1080,"isMinimized":false,"isFullscreen":false}]`
JSON action: `{"action":"move","app":"Firefox","ok":true}`

### `ocr` — Ref: `apps/steer/Sources/steer/OcrCommand.swift`

```
steer ocr [--image PATH] [--app NAME] [--screen INDEX] [--confidence 0.5] [--store] [--json]
```

JSON: `{"app":"Firefox","count":15,"snapshot":"ab12cd34","results":[{"text":"Hello","confidence":0.95,"x":100,"y":200,"width":50,"height":20}]}`

### `focus` — Ref: `apps/steer/Sources/steer/Focus.swift`

```
steer focus [--app NAME] [--json]
```

JSON: `{"app":"Firefox","focused":{"id":"F0","role":"text","label":"Search","value":"","x":100,"y":200,"width":300,"height":30,"isEnabled":true,"depth":0}}`

### `find` — Ref: `apps/steer/Sources/steer/Find.swift`

```
steer find QUERY [--snapshot ID] [--exact] [--json]
```

JSON: `{"snapshot":"ab12cd34","query":"Close","count":1,"matches":[{"id":"B1","role":"button","label":"Close","value":null,"x":100,"y":200,"width":30,"height":30,"isEnabled":true,"depth":1}]}`

### `clipboard` — Ref: `apps/steer/Sources/steer/Clipboard.swift`

```
steer clipboard ACTION [TEXT] [--type text|image] [--file PATH] [--json]
```

Actions: `read`, `write`

JSON read text: `{"action":"read","type":"text","content":"hello","ok":true}`
JSON read image: `{"action":"read","type":"image","file":"/tmp/steer/clipboard-uuid.png","ok":true}`
JSON write: `{"action":"write","type":"text","ok":true}`

**Linux**: usa `xclip -selection clipboard` para texto, `xclip -selection clipboard -t image/png` para imagenes.

### `wait` — Ref: `apps/steer/Sources/steer/Wait.swift`

```
steer wait [--for ID|LABEL] [--app NAME] [--timeout 10] [--interval 0.5] [--json]
```

JSON: `{"action":"wait","condition":"element","id":"B1","label":"Close","app":"Firefox","ok":true}`
JSON timeout: `{"action":"wait","condition":"app","app":"Firefox","ok":false,"error":"timeout"}`

---

## 4. Adaptar worker.py en Listen

**Archivo**: `apps/listen/worker.py` lineas 32-47

**Cambio unico**: reemplazar `_open_terminal()` que usa `osascript` (macOS Terminal.app) por tmux directo:

```python
def _open_terminal(session_name: str, cwd: str) -> None:
    """Create a tmux session directly (no GUI terminal needed on Linux)."""
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-c", cwd],
        capture_output=True, text=True, check=True,
    )
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if _session_exists(session_name):
            return
        time.sleep(0.2)
    raise RuntimeError(f"tmux session '{session_name}' did not appear within 5s")
```

El resto de worker.py (tmux send-keys, sentinel pattern, YAML) funciona sin cambios.

---

## 5. Actualizar archivos en `.claude/` — Referencias macOS → Linux

Todos los archivos dentro de `.claude/` que referencian macOS deben actualizarse. A continuacion cada archivo con los cambios exactos:

### 5.1 `.claude/commands/listen-drive-and-steer-user-prompt.md`

| Linea | Actual | Nuevo |
|-------|--------|-------|
| 2 | `description: Execute a task using steer (GUI) and drive (terminal) to control the entire macOS device` | `description: Execute a task using steer (GUI) and drive (terminal) to control the entire Ubuntu Linux device` |
| 10 | `You are an autonomous macOS agent with full control of this device via two CLI tools:` | `You are an autonomous Ubuntu Linux agent with full control of this device via two CLI tools:` |

### 5.2 `.claude/commands/install-agent-sandbox.md`

Este archivo es el instalador del sandbox en macOS. Crear version Linux o reescribir completo:

| Linea | Actual | Nuevo |
|-------|--------|-------|
| 3 | `description: Install, configure, and verify the steer agent sandbox on this macOS device` | `description: Install, configure, and verify the steer agent sandbox on this Ubuntu Linux device` |
| 8 | `Run directly on the agent sandbox device (e.g. Mac Mini)` | `Run directly on the agent sandbox device (e.g. Ubuntu server/desktop)` |
| 19 | `steer/          # Swift CLI — needs swift build -c release` | `steer-linux/    # Python CLI — needs uv pip install -e .` |
| 72 | `Do NOT attempt to modify macOS permissions via CLI` | `Ensure X11/Wayland display server is running and AT-SPI2 is enabled` |
| 84-86 | `Check macOS version: sw_vers` | `Check Ubuntu version: lsb_release -a` |
| 91 | `which brew swift tmux just uv yq claude node pi ipi` | `which tmux just uv yq claude node xdotool wmctrl scrot xclip tesseract` |
| 95 | `swift --version` | Eliminar — no se usa Swift |
| 104-106 | `Install Xcode Command Line Tools if Swift is missing: xcode-select --install` | `Install system dependencies: sudo apt install xdotool wmctrl scrot xclip tesseract-ocr python3-atspi imagemagick x11-utils` |
| 131-133 | `Build steer (Swift CLI): cd apps/steer && swift build -c release` | `Install steer (Python CLI): cd apps/steer-linux && uv pip install -e .` |
| 231 | `macOS: [version]` | `Ubuntu: [version]` |
| 240 | `Swift \| [installed/missing] \| [version]` | `xdotool \| [installed/missing] \| [version]` |
| 293 | `excluding macOS permissions which require manual setup` | `excluding display server permissions which may require manual setup` |

Reemplazos adicionales en todo el archivo:
- `brew install` → `sudo apt install`
- `Homebrew` → `apt`
- `pmset` (sleep settings) → `systemctl mask sleep.target` o `gsettings set org.gnome.settings-daemon.plugins.power`
- `System Settings > Privacy > Accessibility` → `AT-SPI2 is enabled by default on Ubuntu; verify with: busctl --user list | grep Accessibility`
- `System Settings > Privacy > Screen Recording` → Eliminar — no se requiere en Linux (X11 permite captura sin permisos especiales)

### 5.3 `.claude/commands/install-engineer-devbox.md`

| Linea | Actual | Nuevo |
|-------|--------|-------|
| 19 | `This device only needs the CLI client tools — it does NOT need steer, Swift, or tmux` | `This device only needs the CLI client tools — it does NOT need steer, xdotool, or tmux` |
| 24 | `ask the user for the Mac Mini's IP or hostname` | `ask the user for the sandbox device's IP or hostname` |
| 33 | `Check macOS version:` | `Check OS version:` |
| 35 | `sw_vers` | `lsb_release -a` |
| 127 | `macOS: [version]` | `Ubuntu: [version]` |

### 5.4 `.claude/commands/prime.md`

| Linea | Actual | Nuevo |
|-------|--------|-------|
| 7 | `a macOS automation framework with four apps` | `a Linux automation framework with four apps` |
| 34 | `stack (Swift + Python)` | `stack (Python)` |

### 5.5 `.claude/skills/steer/SKILL.md`

| Linea | Actual | Nuevo |
|-------|--------|-------|
| 3 | `description: macOS GUI automation CLI` | `description: Ubuntu Linux GUI automation CLI` |
| 6 | `# Steer — macOS GUI Automation` | `# Steer — Ubuntu Linux GUI Automation` |
| 35 | `You are controlling a real macOS desktop` | `You are controlling a real Ubuntu Linux desktop` |

### 5.6 `.claude/skills/drive/SKILL.md`

| Linea | Actual | Nuevo |
|-------|--------|-------|
| 24 | `a new Terminal.app window opens attached to the session` | `a new terminal window opens attached to the session` |

### 5.7 `.claude/agents/listen-drive-and-steer-system-prompt.md`

Buscar y reemplazar cualquier referencia a:
- `macOS` → `Ubuntu Linux`
- `Mac` → `Linux device`
- `Terminal.app` → `terminal`

### 5.8 `justfile` (root)

- Asegurar que `steer` apunte al nuevo CLI Python:
  - Opcion A: alias en justfile `steer := "uv run --directory apps/steer-linux python main.py"`
  - Opcion B: instalar con `cd apps/steer-linux && uv pip install -e .` para que `steer` este en PATH
- Actualizar comentarios que mencionen macOS, Swift o Mac Mini

---

## 6. Orden de implementacion

1. `modules/errors.py` — base para todo
2. `modules/output.py` — helper de formato JSON/text
3. `modules/element_store.py` — no depende de APIs del sistema
4. `modules/capture.py` — screenshot con scrot
5. `modules/input.py` — xdotool wrappers
6. `modules/app_control.py` — wmctrl + ps
7. `modules/window_control.py` — wmctrl
8. `modules/ocr_engine.py` — pytesseract
9. `modules/accessibility.py` — AT-SPI2 (el mas complejo)
10. Comandos en orden: `see` → `click` → `type` → `hotkey` → `scroll` → `drag` → `apps` → `screens` → `window` → `ocr` → `focus` → `find` → `clipboard` → `wait`
11. `main.py` — registrar todos los comandos
12. `worker.py` — cambio de `_open_terminal()`
13. Prompts — actualizar referencias macOS → Linux

---

## 7. Verificacion

```bash
# Prerequisitos
sudo apt install xdotool wmctrl scrot xclip tesseract-ocr python3-atspi imagemagick x11-utils
echo $DISPLAY  # debe mostrar :0 o similar
xdotool --version && wmctrl --help && scrot --version && tesseract --version

# Unit: cada modulo con mocks de subprocess
# CLI: ejecutar los 14 comandos y verificar JSON identico al Swift
# Integracion: just steer-cc "open firefox and search for hello world"
# Drive: verificar que sigue funcionando sin cambios
# Listen: enviar job via direct y verificar worker.py crea sesion tmux
```
