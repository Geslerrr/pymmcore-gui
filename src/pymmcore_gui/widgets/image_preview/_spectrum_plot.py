from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pymmcore_gui._qt.QtWidgets import QVBoxLayout, QWidget

from ._preview_base import ImagePreviewBase

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


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

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_xlabel("Pixel")
        self.axes.set_ylabel("Intensity")
        self.axes.grid(True, alpha=0.25)
        (self._line,) = self.axes.plot([], [])

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

        pixels = np.arange(row.size)
        self._line.set_data(pixels, row)
        self.axes.relim()
        self.axes.autoscale_view()
        self.canvas.draw_idle()
