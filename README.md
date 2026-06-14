# gimp-psx-plugin

A GIMP 3.x plugin that adds a **Filters > PSX...** menu item. Clicking it opens
four dialogs **one after the other**, in the exact order needed to apply a classic
PlayStation 1 / PSX aesthetic:

1. **Resize** — reduce resolution (default interpolation: None, for that hard-pixel look)
2. **RGB Noise** — add grain
3. **Convert to Indexed** — reduce color palette (Floyd-Steinberg dithering by default)
4. **Gaussian Blur** — soften the result

Each dialog waits for you to confirm (OK) or skip (Cancel) before the next one
opens. Cancelling any step stops the sequence; the steps already applied are kept.
One Ctrl+Z undoes the entire PSX workflow at once.

> **Note:** The blur step converts the image back to RGB automatically, since GEGL
> cannot blur an indexed image. The final result is an RGB image with a low-fi palette look.

---

## Requirements

- **GIMP 3.0 or later** (tested on GIMP 3.2.4)
- Works on **Windows, macOS, and Linux** — pure Python, no external dependencies

---

## Install

**Windows — double-click:**
```
install.bat
```

**Windows — PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**macOS / Linux — copy manually:**
```bash
mkdir -p ~/.config/GIMP/3.0/plug-ins/psx
cp plug-ins/psx/psx.py ~/.config/GIMP/3.0/plug-ins/psx/
chmod +x ~/.config/GIMP/3.0/plug-ins/psx/psx.py
```

After installation, **restart GIMP** — the `Filters > PSX...` entry will appear
(only active when an RGB image is open).

---

## Usage

1. Open an RGB image in GIMP.
2. Click **Filters > PSX...**
3. Work through each dialog: adjust settings and click **OK** to apply, or
   **Cancel** to skip that step and stop the sequence.

---

## Uninstall

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

**macOS / Linux:**
```bash
rm -rf ~/.config/GIMP/3.0/plug-ins/psx
```

---

## How it works

The plugin is a single Python file registered with the GIMP Plugin API
(`Gimp.ImageProcedure`). When invoked it opens its own GTK3 dialogs and applies
each effect directly via the GIMP/GEGL API:

- **Resize** — `image.scale(w, h)` with `Gimp.context_set_interpolation()`
- **RGB Noise** — `Gimp.DrawableFilter.new(d, "gegl:noise-rgb", "")` + `merge_filter`
- **Indexed** — `image.convert_indexed(dither, palette, n_cols, ...)`
- **Gaussian Blur** — `Gimp.DrawableFilter.new(d, "gegl:gaussian-blur", "")` + `merge_filter`

All steps are wrapped in `image.undo_group_start/end()` so Ctrl+Z undoes everything.

---

## License

MIT — see [LICENSE](LICENSE).
