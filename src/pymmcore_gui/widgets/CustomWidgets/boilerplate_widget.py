from pymmcore_plus import CMMCorePlus
from pymmcore_gui._qt.QtWidgets import QMenu


def add_menu_entry(menu: QMenu, mmc: CMMCorePlus, log) -> None:
    action = menu.addAction("NAME HERE")

    def run(checked=False):
        try:

            #code here

            result = {
            #results here
            }

            log.add_result("RESULT NAME", result)

        except Exception as e:
            log.add_error("RESULT NAME", str(e))

    action.triggered.connect(run)