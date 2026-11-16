from pymmcore_plus import CMMCorePlus
from pymmcore_gui._qt.QtWidgets import QMenu, QMainWindow

#from .CustomWidgets.<widget name> import add_menu_entry as <your function name>
from .CustomWidgets.average_pixel_value import add_menu_entry as average_pixel


class CustomMenu(QMenu):
    def __init__(
        self,
        mmc: CMMCorePlus,
        parent: QMainWindow,
    ):
        super().__init__("Custom Menu", parent)

        self._mmc = mmc
        self._window = parent

        # Get the shared log window from the main window
        log = parent.custom_log

        #<your function name>(self, mmc, log)
        average_pixel(self, mmc, log)
