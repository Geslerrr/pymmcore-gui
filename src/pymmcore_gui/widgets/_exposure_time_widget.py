from __future__ import annotations

from pymmcore_plus import CMMCorePlus

from pymmcore_gui._qt.QtCore import QSignalBlocker, Signal
from pymmcore_gui._qt.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class _ExposureSpinBox(QDoubleSpinBox):
    """Spin box that retains precise exposure values without padded zeros."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDecimals(12)

    def textFromValue(self, value: float) -> str:
        """Format values using the active locale and omit trailing zeros."""
        text = self.locale().toString(value, "f", 12)
        decimal_point = self.locale().decimalPoint()
        if decimal_point in text:
            text = text.rstrip("0").rstrip(decimal_point)
        return text


class ExposureTimeWidget(QWidget):
    """Compact control for setting the camera exposure time in milliseconds."""

    valueChanged = Signal(float)

    def __init__(
        self,
        mmcore: CMMCorePlus,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._mmc = mmcore
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.label = QLabel("Exposure time", self)
        self.spin_box = _ExposureSpinBox(self)
        self.spin_box.setRange(0.001, 1_000_000.0)
        self.spin_box.setSingleStep(1.0)
        # Applying each keystroke can trigger an exposureChanged event and
        # overwrite an unfinished value while the user is typing it.
        self.spin_box.setKeyboardTracking(False)
        self.spin_box.setSuffix(" ms")
        self.spin_box.setMinimumWidth(100)
        self.spin_box.setValue(self._mmc.getExposure())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        layout.addWidget(self.label)
        layout.addWidget(self.spin_box)

        self.spin_box.valueChanged.connect(self._on_value_changed)
        self._mmc.events.exposureChanged.connect(self._on_exposure_changed)
        self._mmc.events.propertyChanged.connect(self._on_property_changed)
        self._mmc.events.configSet.connect(self._on_config_set)
        self._mmc.events.configGroupChanged.connect(self._sync_from_core)
        self._mmc.events.systemConfigurationLoaded.connect(self._sync_from_core)

    def get_value(self) -> float:
        """Return the exposure time in milliseconds."""
        return self.spin_box.value()

    def set_value(self, value: float) -> None:
        """Set the exposure time in milliseconds."""
        self.spin_box.setValue(value)

    def _on_value_changed(self, value: float) -> None:
        self.valueChanged.emit(value)
        self._mmc.setExposure(value)

    def _on_exposure_changed(self, _device: str, value: float) -> None:
        """Use the precise value from the core exposure event."""
        with QSignalBlocker(self.spin_box):
            self.set_value(value)

    def _on_property_changed(self, device: str, prop: str, _value: str) -> None:
        """Refresh for exposure edits and changes to the active camera."""
        if prop.casefold() == "exposure":
            try:
                value = float(_value)
            except ValueError:
                return
            with QSignalBlocker(self.spin_box):
                self.set_value(value)
        elif device.casefold() == "core" and prop.casefold() in {
            "camera",
            "cameradevice",
        }:
            self._sync_from_core()

    def _on_config_set(self, _group: str, _config: str) -> None:
        """Refresh after a config preset may have changed camera exposure."""
        self._sync_from_core()

    def _sync_from_core(self) -> None:
        """Refresh the displayed exposure from the current camera."""
        camera = self._mmc.getCameraDevice()
        try:
            value = (
                float(self._mmc.getProperty(camera, "Exposure"))
                if camera
                else self._mmc.getExposure()
            )
        except Exception:
            value = self._mmc.getExposure()
        with QSignalBlocker(self.spin_box):
            self.set_value(value)
