from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pymmcore_gui._qt.QtWidgets import QVBoxLayout, QWidget
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

    def append(self, data: np.ndarray) -> None:
        """Plot the intensity values from one CCD row."""
        row = np.asarray(data).squeeze()
        if row.ndim == 0:
            row = row.reshape(1)
        elif row.ndim > 1:
            row = row[0].reshape(-1)

        x = self._x_axis(row.size)
        self._line.set_data(x, row)
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
            property_names = core.getDevicePropertyNames(camera)
            property_name = next(
                (
                    name
                    for name in property_names
                    if str(name).casefold() in {"wavelengths", "wavelenghts"}
                ),
                None,
            )
            if property_name is None:
                return
            raw = str(core.getProperty(camera, property_name))
            values = np.fromstring(raw.replace(";", ","), sep=",")
            if values.size and np.all(np.isfinite(values)):
                self._wavelengths = values
        except Exception:
            # Calibration is optional; continue plotting against detector pixels.
            return

    def _on_system_config_loaded(self) -> None:
        self._refresh_wavelengths()

    def _on_property_changed(self, dev: str, prop: str, value: str) -> None:
        if "ccs100" in dev.casefold() and prop.casefold() in {
            "wavelengths",
            "wavelenghts",
        }:
            self._refresh_wavelengths()
