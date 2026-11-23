from __future__ import annotations

from pathlib import Path

import tifffile
from pymmcore_plus import CMMCorePlus
import numpy as np
from PIL import Image

from pymmcore_gui._qt.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)


class SaveImageWidget(QWidget):
    def __init__(
        self,
        mmcore: CMMCorePlus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._mmc = mmcore

        self.save_button = QPushButton("Save Current Image")
        self.status_label = QLabel("")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        layout.addWidget(self.save_button)
        layout.addWidget(self.status_label)

        self.save_button.clicked.connect(self.save_current_image)

    def save_current_image(self) -> None:
        try:
            image = self._mmc.getImage()

            if image is None:
                QMessageBox.warning(
                    self,
                    "No image",
                    "There is no image available to save.",
                )
                return

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save image",
                "image.png",
                "PNG images (*.png)",
            )

            if not filename:
                return

            path = Path(filename)
            if path.suffix.lower() != ".png":
                path = path.with_suffix(".png")

            # Convert to 8-bit for broad PNG viewer compatibility
            image = np.asarray(image)

            if image.dtype != np.uint8:
                image_min = image.min()
                image_max = image.max()

                if image_max > image_min:
                    image = (
                            (image.astype(np.float32) - image_min)
                            / (image_max - image_min)
                            * 255
                    ).astype(np.uint8)
                else:
                    image = np.zeros(image.shape, dtype=np.uint8)

            Image.fromarray(image).save(path)

            self.status_label.setText(f"Saved: {path.name}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Image saving error",
                str(e),
            )