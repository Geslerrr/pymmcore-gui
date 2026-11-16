from pymmcore_gui import create_mmgui
from pymmcore_plus import CMMCorePlus
#from pymmcore_gui._qt.QtWidgets import QApplication
mmcore1=CMMCorePlus.instance()

print("Loading configuration")
try:
    create_mmgui(mm_config=r"D:\Aplikacje\MicroPLController\tests\cg_09-2026_V9_spectro.cfg")
except Exception as e:
    print(e)
    print("Failed to load configuration, loading demo configuration")
    create_mmgui()

print("Devices:")
for label in mmcore1.getLoadedDevices():
    print(repr(label), mmcore1.getDeviceType(label))

#QApplication.instance().exec()

#self note -
#currently, any function can be added to the menu thing
#for formatting, ask the gpt
#for actual code: next thing is to get a sequence of images in steps...
#...vary a parameter (ideally which param to vary should be an input, but test with something first), and click images for each step of that param
#eg. vary bandpass filter from A to B with N subdiv., and take a pic for each one (save the results somewhere?)