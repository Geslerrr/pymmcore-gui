from pymmcore_plus import CMMCorePlus
from pymmcore_gui._qt.QtWidgets import QMenu
import numpy as np


def add_menu_entry(menu: QMenu, mmc: CMMCorePlus, log) -> None:
    action = menu.addAction("average pixel value")

    def run(checked=False):
        try:
            image = mmc.snap()

            result = {
                "mean": float(np.mean(image)),
                "minimum": int(np.min(image)),
                "maximum": int(np.max(image)),
            }

            log.add_result("average pixel value result", result)

        except Exception as e:
            log.add_error("average pixel value error", str(e))

    action.triggered.connect(run)