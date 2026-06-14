#!/usr/bin/env python3
# GIMP PSX Plugin — opens Scale, RGB Noise, Indexed, Gaussian Blur in sequence.

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib
import os
import sys
import subprocess

POWERSHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
DETACHED   = 0x00000008  # DETACHED_PROCESS


def psx_run(procedure, run_mode, image, drawables, config, data):
    ps1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'psx_sequence.ps1')

    if not os.path.exists(ps1):
        return procedure.new_return_values(
            Gimp.PDBStatusType.EXECUTION_ERROR,
            GLib.Error('psx', 0, f'Script not found: {ps1}')
        )

    subprocess.Popen(
        [POWERSHELL, '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Normal', '-File', ps1],
        creationflags=DETACHED,
        close_fds=True,
    )

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class PSX(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False, None, None

    def do_query_procedures(self):
        return ['python-fu-psx']

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, psx_run, None
        )
        procedure.set_image_types('*')
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE |
            Gimp.ProcedureSensitivityMask.DRAWABLES |
            Gimp.ProcedureSensitivityMask.NO_DRAWABLES
        )
        procedure.set_documentation(
            'PSX workflow',
            'Opens Scale Image, RGB Noise, Indexed mode and Gaussian Blur in sequence.',
            name
        )
        procedure.set_menu_label('PSX...')
        procedure.add_menu_path('<Image>/Filters')
        procedure.set_attribution('gimp-psx-plugin', 'gimp-psx-plugin', '2026')
        return procedure


Gimp.main(PSX.__gtype__, sys.argv)
