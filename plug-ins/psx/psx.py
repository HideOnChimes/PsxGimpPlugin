#!/usr/bin/env python3
# GIMP PSX Plugin - Resize > RGB Noise > Indexed > Gaussian Blur in sequence.

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gegl', '0.4')
gi.require_version('Gtk', '3.0')
from gi.repository import Gimp, GimpUi, Gegl, Gtk, GLib
import sys
import random


def _spin(value, lo, hi, step=1.0, digits=0):
    adj = Gtk.Adjustment(value=value, lower=lo, upper=hi,
                         step_increment=step, page_increment=step * 10)
    spin = Gtk.SpinButton()
    spin.set_adjustment(adj)
    spin.set_digits(digits)
    spin.set_numeric(True)
    return spin


def _combo(options, active=0):
    box = Gtk.ComboBoxText()
    for lbl in options:
        box.append_text(lbl)
    box.set_active(active)
    return box


def _check(label, active=False):
    btn = Gtk.CheckButton()
    btn.set_label(label)
    btn.set_active(active)
    return btn


def _step_dialog(title, rows):
    """Build and run a modal dialog with (label_text, widget) rows.
    When label_text is '' the widget spans both columns (used for checkboxes).
    Returns (response, dialog). Read widget values before calling dialog.destroy()."""
    dlg = Gtk.Dialog()
    dlg.set_title(title)
    dlg.set_modal(True)
    dlg.set_destroy_with_parent(True)
    dlg.set_border_width(12)
    dlg.add_button('_Cancel', Gtk.ResponseType.CANCEL)
    ok_btn = dlg.add_button('_OK', Gtk.ResponseType.OK)
    ok_btn.get_style_context().add_class('suggested-action')
    dlg.set_default_response(Gtk.ResponseType.OK)

    grid = Gtk.Grid()
    grid.set_row_spacing(8)
    grid.set_column_spacing(16)
    grid.set_border_width(8)
    for i, (lbl_text, widget) in enumerate(rows):
        if lbl_text:
            lbl = Gtk.Label(label=lbl_text)
            lbl.set_xalign(0)
            grid.attach(lbl, 0, i, 1, 1)
            grid.attach(widget, 1, i, 1, 1)
        else:
            grid.attach(widget, 0, i, 2, 1)

    dlg.get_content_area().add(grid)
    dlg.show_all()
    resp = dlg.run()
    return resp, dlg


def psx_run(procedure, run_mode, image, drawables, config, data):
    GimpUi.init('python-fu-psx')
    Gegl.init(None)

    Gimp.context_push()
    image.undo_group_start()

    try:
        orig_w = image.get_width()
        orig_h = image.get_height()

        # ── Step 1 — Resize ──────────────────────────────────────────────── #
        w_spin     = _spin(orig_w, 1, 32767)
        h_spin     = _spin(orig_h, 1, 32767)
        aspect_chk = _check('Keep aspect ratio', True)
        interp_box = _combo(['None (pixelated)', 'Linear', 'Cubic', 'NoHalo', 'LoHalo'])
        INTERP = [
            Gimp.InterpolationType.NONE,
            Gimp.InterpolationType.LINEAR,
            Gimp.InterpolationType.CUBIC,
            Gimp.InterpolationType.NOHALO,
            Gimp.InterpolationType.LOHALO,
        ]

        ratio      = [orig_w / orig_h if orig_h else 1.0]
        updating   = [False]

        def on_w_changed(spin):
            if updating[0] or not aspect_chk.get_active():
                return
            updating[0] = True
            h_spin.set_value(round(spin.get_value() / ratio[0]))
            updating[0] = False

        def on_h_changed(spin):
            if updating[0] or not aspect_chk.get_active():
                return
            updating[0] = True
            w_spin.set_value(round(spin.get_value() * ratio[0]))
            updating[0] = False

        w_spin.connect('value-changed', on_w_changed)
        h_spin.connect('value-changed', on_h_changed)

        resp, dlg = _step_dialog('PSX - Step 1: Resize', [
            ('Width (px)',    w_spin),
            ('Height (px)',   h_spin),
            ('',              aspect_chk),
            ('Interpolation', interp_box),
        ])
        new_w  = int(w_spin.get_value())
        new_h  = int(h_spin.get_value())
        interp = INTERP[interp_box.get_active()]
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        Gimp.context_set_interpolation(interp)
        image.scale(new_w, new_h)

        # ── Step 2 — RGB Noise ───────────────────────────────────────────── #
        r_spin     = _spin(0.20, 0.0, 1.0, 0.01, 2)
        g_spin     = _spin(0.20, 0.0, 1.0, 0.01, 2)
        b_spin     = _spin(0.20, 0.0, 1.0, 0.01, 2)
        a_spin     = _spin(0.00, 0.0, 1.0, 0.01, 2)
        seed_spin  = _spin(random.randint(0, 2**31 - 1), 0, 2**31 - 1)
        corr_chk   = _check('Correlated noise', False)
        indep_chk  = _check('Independent RGB',  True)
        linear_chk = _check('Linear RGB',       False)
        gauss_chk  = _check('Gaussian',         False)

        resp, dlg = _step_dialog('PSX - Step 2: RGB Noise', [
            ('Red',   r_spin),
            ('Green', g_spin),
            ('Blue',  b_spin),
            ('Alpha', a_spin),
            ('Seed',  seed_spin),
            ('',      corr_chk),
            ('',      indep_chk),
            ('',      linear_chk),
            ('',      gauss_chk),
        ])
        r_val    = r_spin.get_value()
        g_val    = g_spin.get_value()
        b_val    = b_spin.get_value()
        a_val    = a_spin.get_value()
        seed     = int(seed_spin.get_value())
        corr     = corr_chk.get_active()
        indep    = indep_chk.get_active()
        linear   = linear_chk.get_active()
        gaussian = gauss_chk.get_active()
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        targets = list(drawables) if drawables else []
        if not targets:
            ad = image.get_active_drawable()
            if ad:
                targets = [ad]

        for d in targets:
            try:
                f   = Gimp.DrawableFilter.new(d, 'gegl:noise-rgb', '')
                cfg = f.get_config()
                for prop, val in [
                    ('red',         r_val),
                    ('green',       g_val),
                    ('blue',        b_val),
                    ('alpha',       a_val),
                    ('seed',        seed),
                    ('correlated',  corr),
                    ('independent', indep),
                    ('linear',      linear),
                    ('gaussian',    gaussian),
                ]:
                    try:
                        cfg.set_property(prop, val)
                    except Exception:
                        pass
                d.merge_filter(f)
            except Exception as e:
                Gimp.message('PSX RGB Noise error: %s' % e)

        # ── Step 3 — Convert to Indexed ──────────────────────────────────── #
        palette_box = _combo([
            'Generate optimum palette',
            'Web-optimized palette',
            'Black and white (1-bit)',
        ])
        ncols_spin       = _spin(16, 2, 256)
        dither_box       = _combo([
            'None',
            'Floyd-Steinberg',
            'Floyd-Steinberg (reduced bleeding)',
            'Positioned',
        ], active=1)
        alpha_dither_chk  = _check('Dither transparency',    False)
        remove_unused_chk = _check('Remove unused colors',   True)

        PALETTE = [
            Gimp.ConvertPaletteType.GENERATE,
            Gimp.ConvertPaletteType.WEB,
            Gimp.ConvertPaletteType.MONO,
        ]
        DITHER = [
            Gimp.ConvertDitherType.NONE,
            Gimp.ConvertDitherType.FS,
            Gimp.ConvertDitherType.FS_LOWBLEED,
            Gimp.ConvertDitherType.FIXED,
        ]

        resp, dlg = _step_dialog('PSX - Step 3: Convert to Indexed', [
            ('Palette type',    palette_box),
            ('Max colors',      ncols_spin),
            ('Color dithering', dither_box),
            ('',                alpha_dither_chk),
            ('',                remove_unused_chk),
        ])
        palette_type  = PALETTE[palette_box.get_active()]
        n_cols        = int(ncols_spin.get_value())
        dither        = DITHER[dither_box.get_active()]
        alpha_dither  = alpha_dither_chk.get_active()
        remove_unused = remove_unused_chk.get_active()
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        if image.get_base_type() == Gimp.ImageBaseType.RGB:
            image.convert_indexed(
                dither, palette_type, n_cols, alpha_dither, remove_unused, '')

        # ── Step 4 — Gaussian Blur ───────────────────────────────────────── #
        x_spin     = _spin(2.0, 0.0, 1500.0, 0.5, 1)
        y_spin     = _spin(2.0, 0.0, 1500.0, 0.5, 1)
        link_chk   = _check('Link X / Y', True)
        filter_box = _combo(['Auto', 'FIR', 'IIR'])
        abyss_box  = _combo(['None', 'Clamp', 'Black', 'White'])
        clip_chk   = _check('Clip to input extent', True)

        xy_updating = [False]

        def on_x_changed(spin):
            if xy_updating[0] or not link_chk.get_active():
                return
            xy_updating[0] = True
            y_spin.set_value(spin.get_value())
            xy_updating[0] = False

        def on_y_changed(spin):
            if xy_updating[0] or not link_chk.get_active():
                return
            xy_updating[0] = True
            x_spin.set_value(spin.get_value())
            xy_updating[0] = False

        x_spin.connect('value-changed', on_x_changed)
        y_spin.connect('value-changed', on_y_changed)

        resp, dlg = _step_dialog('PSX - Step 4: Gaussian Blur', [
            ('Size X (px)',    x_spin),
            ('Size Y (px)',    y_spin),
            ('',               link_chk),
            ('Filter',         filter_box),
            ('Abyss policy',   abyss_box),
            ('',               clip_chk),
        ])
        blur_x      = x_spin.get_value()
        blur_y      = y_spin.get_value()
        filter_idx  = filter_box.get_active()   # 0=auto 1=fir 2=iir
        abyss_idx   = abyss_box.get_active()    # 0=none 1=clamp 2=black 3=white
        clip_extent = clip_chk.get_active()
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        # GEGL cannot blur indexed images — convert back to RGB first
        if image.get_base_type() == Gimp.ImageBaseType.INDEXED:
            image.convert_rgb()

        d = image.get_active_drawable()
        if d is not None:
            f   = Gimp.DrawableFilter.new(d, 'gegl:gaussian-blur', '')
            cfg = f.get_config()
            cfg.set_property('std-dev-x', blur_x)
            cfg.set_property('std-dev-y', blur_y)
            try:
                cfg.set_property('filter', filter_idx)
            except Exception:
                pass
            try:
                cfg.set_property('abyss-policy', abyss_idx)
            except Exception:
                pass
            try:
                cfg.set_property('clip-extent', clip_extent)
            except Exception:
                pass
            d.merge_filter(f)

        Gimp.displays_flush()

    finally:
        image.undo_group_end()
        Gimp.context_pop()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class PSX(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False, None, None

    def do_query_procedures(self):
        return ['python-fu-psx']

    def do_create_procedure(self, name):
        Gegl.init(None)
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, psx_run, None
        )
        procedure.set_image_types('RGB*')
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE |
            Gimp.ProcedureSensitivityMask.DRAWABLES
        )
        procedure.set_documentation(
            'PSX aesthetic workflow',
            'Resize, RGB noise, indexed palette and gaussian blur — in sequence.',
            name
        )
        procedure.set_menu_label('PSX...')
        procedure.add_menu_path('<Image>/Filters')
        procedure.set_attribution('gimp-psx-plugin', 'gimp-psx-plugin', '2026')
        return procedure


Gimp.main(PSX.__gtype__, sys.argv)
