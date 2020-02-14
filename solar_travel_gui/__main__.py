import sys

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# from stg_dashboard import Dashboard
from solar_travel_gui.stg_dashboard import Dashboard

def main(args=None):
    if args is None:
        args = sys.argv[1:]
        
    pg.mkQApp()
    win = Dashboard()
    win.setWindowTitle("Solar + Travel Visualiser (Alpha)")
    win.show()
    win.showMaximized()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
        

if __name__ == '__main__':
    main()