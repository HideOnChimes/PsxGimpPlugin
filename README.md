# gimp-psx-plugin

A GIMP 3.x plugin that adds a **Filters → PSX...** menu item. Clicking it opens
GIMP's native editing dialogs **one after the other**, in the exact order needed
to apply a classic PlayStation 1 / PSX aesthetic:

1. **Scale Image** — reduce resolution
2. **RGB Noise** — add grain/dithering noise
3. **Convert to Indexed** — reduce color palette
4. **Gaussian Blur** — soften the result

Each dialog waits for you to apply (or cancel) before the next one opens.
No more forgetting a step or hunting through menus.

---

## Requirements

- **Windows** (the automation layer is PowerShell + Win32 — macOS/Linux not supported)
- **GIMP 3.0 or later** (tested on GIMP 3.2.4)

---

## Install

**Option A — double-click:**
```
install.bat
```

**Option B — one command in PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer will:
1. Find your GIMP 3.x config folder automatically.
2. Wait for GIMP to close if it's open (required, since GIMP saves shortcuts on exit).
3. Copy the plugin files.
4. Assign four keyboard shortcuts — picking free keys automatically if your
   preferred defaults (`Ctrl+Shift+F1..F4`) are already taken.
5. Write `psx_keys.txt` so the automation always uses the correct keys for your machine.

After installation, **restart GIMP** — the `Filters → PSX...` entry will appear.

---

## Usage

1. Open an image in GIMP.
2. Click **Filters → PSX...**
3. A terminal window shows the current step. Work through each dialog normally
   (adjust settings → OK or Cancel). The next dialog opens automatically.

> **Tip:** Cancelling a dialog counts as "closed" — the sequence moves on.
> The plugin cannot distinguish Apply from Cancel from outside GIMP.

---

## Keyboard shortcuts

The installer assigns `Ctrl+Shift+F1` through `Ctrl+Shift+F4` by default.
If any of those are already in use, it automatically picks the next free
combination from a pool of 36 options (`Ctrl+Shift+F1..F12`,
`Ctrl+Alt+F1..F12`, `Ctrl+Shift+Alt+F1..F12`).

The assigned keys are printed at the end of the install and can be checked
anytime via **Edit → Keyboard Shortcuts** in GIMP.

---

## Uninstall

```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

Removes the plugin folder and cleans up its shortcut entries from GIMP's config.
Run with GIMP closed.

---

## How it works

GIMP 3.x does not expose a scripting API to open its native filter dialogs
(Gaussian Blur, RGB Noise, etc. are GEGL filters with no PDB procedure for
launching their UI). This plugin works around that by:

1. Registering a `Filters → PSX...` menu item via the GIMP Python-Fu plugin API.
2. When clicked, launching a detached PowerShell script (`psx_sequence.ps1`).
3. The PowerShell script sends each dialog's keyboard shortcut to GIMP using
   `SendKeys`, then uses Win32 (`EnumWindows`) to detect when a new top-level
   window appears (the dialog) and when it closes, before sending the next key.

---

## Known limitations

- **Windows only** — the automation uses PowerShell and Win32 APIs.
- **Closing or switching focus during the sequence** may confuse the window
  detection; the script will time out after 30 seconds and warn you.
- **Cancel = advance** — the plugin cannot tell if you applied or cancelled a
  dialog. It moves on either way.
- If GIMP is very slow to open a dialog (e.g. large file), the 30-second timeout
  can be increased by editing `StepTimeout` at the top of `psx_sequence.ps1`.

---

## License

MIT — see [LICENSE](LICENSE).
