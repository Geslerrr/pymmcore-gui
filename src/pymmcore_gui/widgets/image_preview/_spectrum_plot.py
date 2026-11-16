from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pymmcore_gui._qt.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ._preview_base import ImagePreviewBase

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus

COLOR = 'xkcd:light grey'
mpl.rcParams['text.color'] = COLOR
mpl.rcParams['axes.labelcolor'] = COLOR
mpl.rcParams['xtick.color'] = COLOR
mpl.rcParams['ytick.color'] = COLOR

class SpectrumPlotPreview(ImagePreviewBase):
    """Live line plot preview for a one-row camera such as a spectrometer."""

    def __init__(
        self,
        mmcore: CMMCorePlus,
        parent: QWidget | None = None,
        *,
        use_with_mda: bool = False,
    ) -> None:
        super().__init__(parent, mmcore, use_with_mda=use_with_mda)
        default_bg_color = 'xkcd:dark grey'
        self.figure = Figure(facecolor=default_bg_color)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_facecolor(default_bg_color)
        self.axes.set_xlabel("Pixel")
        self.axes.set_ylabel("Intensity")
        self.axes.grid(True, alpha=0.25)
        (self._line,) = self.axes.plot([], [])
        self._wavelengths: np.ndarray | None = None
        self._refresh_wavelengths()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        controls = QHBoxLayout()
        controls.addStretch()
        self._save_button = QPushButton("Save spectrum…", self)
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._save_spectrum)
        controls.addWidget(self._save_button)
        layout.addLayout(controls)

    def append(self, data: np.ndarray) -> None:
        """Plot the intensity values from one CCD row."""
        row = np.asarray(data).squeeze()
        if row.ndim == 0:
            row = row.reshape(1)
        elif row.ndim > 1:
            row = row[0].reshape(-1)

        x = self._x_axis(row.size)
        self._line.set_data(x, row)
        self._save_button.setEnabled(True)
        calibrated = self._wavelengths is not None and self._wavelengths.size == row.size
        self.axes.set_xlabel("Wavelength (nm)" if calibrated else "Pixel")
        self.axes.relim()
        self.axes.autoscale_view()
        self.canvas.draw_idle()

    def _x_axis(self, size: int) -> np.ndarray:
        if self._wavelengths is not None and self._wavelengths.size == size:
            return self._wavelengths
        return np.arange(size)

    def _refresh_wavelengths(self) -> None:
        """Read the CCS100 wavelength calibration when it is exposed as a property."""
        core = self._mmc
        self._wavelengths = None
        if core is None:
            return
        try:
            camera = str(core.getCameraDevice())
            if "ccs100" not in camera.casefold():
                return

            calibration_path = Path(__file__).with_name("wvl_cal.csv")
            values = np.loadtxt(calibration_path, delimiter=",")
            values = np.atleast_1d(values)
            if values.size and np.all(np.isfinite(values)):
                self._wavelengths = values
        except Exception:
            # Calibration is optional; continue plotting against detector pixels.
            return

    def _save_spectrum(self) -> None:
        """Save the currently displayed spectrum as CSV data or a PNG plot."""
        filters = "CSV files (*.csv);;PNG images (*.png)"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save spectrum",
            "spectrum.csv",
            filters,
        )
        if not path:
            return

        extension = ".png" if "PNG" in selected_filter else ".csv"
        destination = Path(path)
        if destination.suffix.casefold() != extension:
            destination = destination.with_suffix(extension)

        if extension == ".png":
            self.figure.savefig(
                destination, format="png", facecolor=self.figure.get_facecolor()
            )
            return

        x, intensity = self._line.get_data()
        x_label = self.axes.get_xlabel()
        x_header = "wavelength_nm" if x_label == "Wavelength (nm)" else "pixel"
        np.savetxt(
            destination,
            np.column_stack((x, intensity)),
            delimiter=",",
            header=f"{x_header},intensity",
            comments="",
        )

    def _on_system_config_loaded(self) -> None:
        self._refresh_wavelengths()

    def _on_property_changed(self, dev: str, prop: str, value: str) -> None:
        if "ccs100" in dev.casefold():
            self._refresh_wavelengths()
