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


def _step_dialog(title, rows):
    """Build and run a modal dialog with (label_text, widget) rows.
    Returns (Gtk.ResponseType, dialog). Read widget values before calling dialog.destroy()."""
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
        lbl = Gtk.Label(label=lbl_text)
        lbl.set_xalign(0)
        grid.attach(lbl, 0, i, 1, 1)
        grid.attach(widget, 1, i, 1, 1)

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
        # ── Step 1 — Resize ──────────────────────────────────────────────── #
        w_spin = _spin(image.get_width(),  1, 32767)
        h_spin = _spin(image.get_height(), 1, 32767)

        interp_box = Gtk.ComboBoxText()
        INTERP = [
            ('None (pixelated)', Gimp.InterpolationType.NONE),
            ('Linear',           Gimp.InterpolationType.LINEAR),
            ('Cubic',            Gimp.InterpolationType.CUBIC),
        ]
        for label, _ in INTERP:
            interp_box.append_text(label)
        interp_box.set_active(0)

        resp, dlg = _step_dialog('PSX - Step 1: Resize', [
            ('Width (px)',    w_spin),
            ('Height (px)',   h_spin),
            ('Interpolation', interp_box),
        ])
        new_w  = int(w_spin.get_value())
        new_h  = int(h_spin.get_value())
        interp = INTERP[interp_box.get_active()][1]
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        Gimp.context_set_interpolation(interp)
        image.scale(new_w, new_h)

        # ── Step 2 — RGB Noise ───────────────────────────────────────────── #
        amt_spin  = _spin(0.20, 0.0, 1.0, 0.01, 2)
        gauss_chk = Gtk.CheckButton()
        gauss_chk.set_label('Gaussian')

        resp, dlg = _step_dialog('PSX - Step 2: RGB Noise', [
            ('Amount (0 - 1)', amt_spin),
            ('Mode',           gauss_chk),
        ])
        amount   = amt_spin.get_value()
        gaussian = gauss_chk.get_active()
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        for d in drawables:
            f   = Gimp.DrawableFilter.new(d, 'gegl:noise-rgb', '')
            cfg = f.get_config()
            cfg.set_property('red',         amount)
            cfg.set_property('green',       amount)
            cfg.set_property('blue',        amount)
            cfg.set_property('independent', True)
            cfg.set_property('gaussian',    gaussian)
            cfg.set_property('seed',        random.randint(0, 2 ** 31 - 1))
            d.merge_filter(f)

        # ── Step 3 — Convert to Indexed ──────────────────────────────────── #
        ncols_spin = _spin(16, 2, 256)
        dither_box = Gtk.ComboBoxText()
        DITHER = [
            ('Floyd-Steinberg', Gimp.ConvertDitherType.FS),
            ('None',            Gimp.ConvertDitherType.NONE),
        ]
        for label, _ in DITHER:
            dither_box.append_text(label)
        dither_box.set_active(0)

        resp, dlg = _step_dialog('PSX - Step 3: Convert to Indexed', [
            ('Colors (2 - 256)', ncols_spin),
            ('Dither',           dither_box),
        ])
        n_cols = int(ncols_spin.get_value())
        dither = DITHER[dither_box.get_active()][1]
        dlg.destroy()

        if resp != Gtk.ResponseType.OK:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        if image.get_base_type() == Gimp.ImageBaseType.RGB:
            image.convert_indexed(
                dither, Gimp.ConvertPaletteType.GENERATE, n_cols, False, True, '')

        # ── Step 4 — Gaussian Blur ───────────────────────────────────────── #
        blur_spin = _spin(2.0, 0.0, 100.0, 0.5, 1)

        resp, dlg = _step_dialog('PSX - Step 4: Gaussian Blur', [
            ('Radius (px)', blur_spin),
        ])
        blur_r = blur_spin.get_value()
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
            cfg.set_property('std-dev-x', blur_r)
            cfg.set_property('std-dev-y', blur_r)
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
