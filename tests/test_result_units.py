import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from scipy.io import loadmat, savemat

from imr_gui.app import QFileDialog, MainWindow, QMessageBox


class ResultUnitTests(unittest.TestCase):
    @staticmethod
    def _loader() -> MainWindow:
        loader = MainWindow.__new__(MainWindow)
        loader._import_wizard_keywords = MainWindow._normalise_import_wizard_keywords({})
        loader._import_wizard_units = MainWindow._normalise_import_wizard_units({
            "t_exp": "s",
            "R_exp": "pixel",
            "Req": "um",
        })
        loader._import_wizard_um_per_pixel = 99.0
        loader._import_wizard_fps = 1_000_000.0
        loader._import_wizard_remove_below = False
        loader._import_wizard_remove_spikes = False
        loader._import_wizard_spike_threshold = 2.0
        return loader

    def test_export_unit_metadata_round_trips_through_mat(self):
        export = {}
        MainWindow._add_unit_system_to_export(export)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "result.mat"
            savemat(path, export)
            loaded = loadmat(path, squeeze_me=True, struct_as_record=False)

        self.assertEqual(int(loaded["unit_metadata_version"]), 1)
        self.assertEqual(str(loaded["unit_system"]), "SI")
        self.assertEqual(str(loaded["time_unit"]), "s")
        self.assertEqual(str(loaded["radius_unit"]), "m")

    def test_file_units_override_saved_import_defaults(self):
        loader = self._loader()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "micro_units.mat"
            savemat(path, {
                "t_exp": np.array([0.0, 1.0, 2.0]),
                "R_exp": np.array([1.0, 3.0, 2.0]),
                "Req": 2.0,
                "time_unit": "us",
                "radius_unit": "um",
            })
            exp = MainWindow._load_experiment_with_import_defaults(loader, str(path))

        np.testing.assert_allclose(np.diff(exp.t), [1e-6, 1e-6])
        self.assertAlmostEqual(float(np.ptp(exp.t)), 2e-6)
        np.testing.assert_allclose(exp.R, [1e-6, 3e-6, 2e-6])
        self.assertAlmostEqual(exp.R_eq, 2e-6)
        self.assertEqual(exp.import_metadata["unit_source"], "file")
        self.assertEqual(exp.import_metadata["t_unit"], "us")
        self.assertEqual(exp.import_metadata["R_unit"], "um")

    def test_req_and_rmax_pixel_units_use_saved_calibration(self):
        loader = self._loader()
        loader._import_wizard_um_per_pixel = 3.2

        req_preview = MainWindow._import_scalar_display_value("Req", 2.5, "pixel")
        rmax_preview = MainWindow._import_scalar_display_value("Rmax", 10.0, "pixel")
        req = MainWindow._import_unit_to_si(loader, "Req", req_preview, "pixel")
        rmax = MainWindow._import_unit_to_si(loader, "Rmax", rmax_preview, "pixel")

        self.assertEqual(req_preview, 2.5)
        self.assertEqual(rmax_preview, 10.0)
        self.assertAlmostEqual(float(np.asarray(req)), 8.0e-6)
        self.assertAlmostEqual(float(np.asarray(rmax)), 32.0e-6)

        saved_units = MainWindow._normalise_import_wizard_units({
            "Req": "pixel",
            "Rmax": "pixel",
        })
        self.assertEqual(saved_units["Req"], "pixel")
        self.assertEqual(saved_units["Rmax"], "pixel")

    def test_import_wizard_applies_explicit_rmax_to_experiment_controls(self):
        loader = self._loader()
        loader.state = SimpleNamespace(mode="simulation")
        loader._curve_collection_enabled = lambda: False
        loader._set_req_controls_from_exp = lambda *_args, **_kwargs: None
        loader._update_window_title = lambda: None
        loader._redraw_all = lambda: None
        loader.statusBar = lambda: SimpleNamespace(showMessage=lambda _text: None)
        loader.chk_Rmax_auto = SimpleNamespace(setChecked=lambda value: setattr(loader, "rmax_auto", value))
        loader.spin_Rmax_um = SimpleNamespace(setValue=lambda value: setattr(loader, "rmax_um", value))
        loader.spin_P_inf = SimpleNamespace(value=lambda: 101325.0, setValue=lambda _value: None)
        loader.spin_rho = SimpleNamespace(value=lambda: 1000.0, setValue=lambda _value: None)
        loader.spin_c_long = SimpleNamespace(setValue=lambda _value: None)
        loader.spin_gamma = SimpleNamespace(setValue=lambda _value: None)
        loader.spin_t_fit_start = SimpleNamespace(setValue=lambda _value: None)
        loader.spin_t_fit_end = SimpleNamespace(setValue=lambda _value: None)
        loader.chk_fit_window_cycles = SimpleNamespace(isChecked=lambda: False)

        MainWindow._apply_import_wizard_experiment(
            loader,
            path="pixel_scalar.mat",
            t=np.array([0.0, 1e-6, 2e-6]),
            R=np.array([5e-6, 32e-6, 8e-6]),
            legend="pixel scalar",
            Req=8e-6,
            Rmax=32e-6,
            P_inf=None,
            rho=None,
            c_long=None,
            gamma=None,
        )

        self.assertFalse(loader.rmax_auto)
        self.assertAlmostEqual(loader.rmax_um, 32.0)

    def test_exported_si_result_is_not_reconverted_by_pixel_defaults(self):
        loader = self._loader()
        result = {
            "t_exp": np.array([0.0, 1e-6, 2e-6]),
            "R_exp": np.array([1e-6, 3e-6, 2e-6]),
            "Req": 2e-6,
        }
        MainWindow._add_unit_system_to_export(result)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "exported_result.mat"
            savemat(path, result)
            exp = MainWindow._load_experiment_with_import_defaults(loader, str(path))

        np.testing.assert_allclose(exp.R, [1e-6, 3e-6, 2e-6])
        self.assertAlmostEqual(exp.R_eq, 2e-6)
        self.assertEqual(exp.import_metadata["unit_source"], "file")

    def test_legacy_struct_import_units_do_not_reconvert_result_arrays(self):
        loader = self._loader()
        mat = {
            "struct_import": {
                "t_unit": "us",
                "R_unit": "pixel",
            }
        }

        self.assertEqual(MainWindow._declared_mat_units(loader, mat), {})

    def test_learned_radius_without_time_uses_saved_fps_and_calibration(self):
        loader = self._loader()
        loader._import_wizard_keywords["R_exp"] = [
            "tracked_radius",
            *loader._import_wizard_keywords["R_exp"],
        ]
        loader._import_wizard_um_per_pixel = 3.2
        loader._import_wizard_fps = 1_000_000.0

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "radius_only.mat"
            savemat(path, {"tracked_radius": np.array([1.0, 3.0, 2.0, 1.5])})
            exp = MainWindow._load_experiment_with_import_defaults(loader, str(path))

        np.testing.assert_allclose(np.diff(exp.t), [1e-6, 1e-6, 1e-6])
        np.testing.assert_allclose(exp.R, np.array([1.0, 3.0, 2.0, 1.5]) * 3.2e-6)
        self.assertEqual(exp.t_key, "fps:1e+06")
        self.assertEqual(exp.R_key, "tracked_radius")
        self.assertTrue(exp.import_metadata["used_fps"])

    def test_curve_panel_batch_import_uses_learned_radius_and_saved_fps(self):
        loader = self._loader()
        loader._import_wizard_keywords["R_exp"] = [
            "bubble_size_px",
            *loader._import_wizard_keywords["R_exp"],
        ]
        loader._import_wizard_um_per_pixel = 3.2
        imported = []
        messages = []
        loader._file_dialog_start = lambda: ""
        loader._remember_file_dialog_path = lambda _path: None
        loader._curve_view_dock = SimpleNamespace(
            isVisible=lambda: True,
            setFloating=lambda _value: None,
            show=lambda: None,
        )
        loader.chk_multi_curve = SimpleNamespace(
            isChecked=lambda: True,
            setChecked=lambda _value: None,
        )
        loader._add_curve_to_view = lambda **kwargs: imported.append(kwargs)
        loader._redraw_all = lambda: None
        loader.statusBar = lambda: SimpleNamespace(showMessage=messages.append)
        loader.lbl_output = SimpleNamespace(appendPlainText=lambda _text: None)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "radius_only.mat"
            savemat(path, {"bubble_size_px": np.array([1.0, 3.0, 2.0, 1.5])})
            with (
                patch.object(QFileDialog, "getOpenFileNames", return_value=([str(path)], "")),
                patch.object(
                    QMessageBox,
                    "warning",
                    return_value=QMessageBox.StandardButton.Yes,
                ) as warning,
            ):
                MainWindow._on_batch_import_curves(loader)

        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0]["curve_type"], "experiment")
        np.testing.assert_allclose(np.diff(imported[0]["t"]), [1e-6, 1e-6, 1e-6])
        np.testing.assert_allclose(
            imported[0]["R"], np.array([1.0, 3.0, 2.0, 1.5]) * 3.2e-6
        )
        self.assertEqual(warning.call_count, 1)
        self.assertEqual(messages, ["Imported 1 curve(s)."])


if __name__ == "__main__":
    unittest.main()
