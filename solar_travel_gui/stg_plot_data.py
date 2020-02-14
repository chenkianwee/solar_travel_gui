from dateutil.parser import parse
from datetime import datetime
from dateutil.tz import gettz

import PyQt5
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.Qt import QtGui, QtCore
import sys

from pyproj import Proj

# import stg_function as stg_func
import solar_travel_gui.stg_function as stg_func


def hourindex2dt(timestamp):
    return(datetime.fromtimestamp(timestamp))

class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        # PySide's QTime() initialiser fails miserably and dismisses args/kwargs
        #return [QTime().addMSecs(value).toString('mm:ss') for value in values]
        return [hourindex2dt(value).strftime("%y-%m-%d %H00") for value in values]
    
class PlotData(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setupGUI()
        
        arg_list = self.retrieve_arg()      

        # arg_list = [ 'F:\\kianwee_work\\spyder_workspace\\solar_travel_gui\\solar_travel_gui\\stg_plot_data.py', 
        #             'F:/kianwee_work/princeton/2020_01_to_2020_06/golfcart/model3d/solar_travel_data\\parking', 
        #             'F:/kianwee_work/princeton/2020_01_to_2020_06/golfcart/model3d/solar_travel_data\\travel']
                    

        self.arg_list = arg_list
        
        self.parking_dir = arg_list[1]
        self.travel_dir = arg_list[2]
        dlist_values = ["Parking Time(hr)", "Dist Travelled(m)", "Max Irrad(W/m2)", "Med Irrad(W/m2)", "Min Irrad(W/m2)"]
        self.val_list = dlist_values
        self.plot_range = dict(name='Plot', type='group', expanded = True, title = "Plot Data",
                                  children=[dict(name='Start Date', type = 'group', expanded = True, title = "Specify Start Date", 
                                                 children = [dict(name='Year:', type= 'list', values= [2019, 2020], value=2020),
                                                             dict(name='Month:', type= 'int', limits = (1,12), value = 2),
                                                             dict(name='Day:', type= 'int', limits = (1,31), value = 5),
                                                             dict(name='Hour:', type= 'int', limits = (0,23), value = 10)]),
                                            
                                            dict(name='End Date', type = 'group', expanded = True, title = "Specify End Date",
                                                 children = [dict(name='Year:', type= 'list', values= [2019, 2020], value=2020),
                                                             dict(name='Month:', type= 'int', limits = (1,12), value = 2),
                                                             dict(name='Day:', type= 'int', limits = (1,31), value = 5),
                                                             dict(name='Hour:', type= 'int', limits = (0,23), value = 18)]),
                                            
                                            dict(name='Data Range Loaded', type = 'str', readonly = True),
                                            dict(name='Load Data Range', type = 'action'),
                                            dict(name='Y-axis1:', type= 'list', values= dlist_values, value="Parking Time(hr)"),
                                            dict(name='Y-axis2:', type= 'list', values= dlist_values, value="Dist Travelled(m)"),
                                            dict(name = 'Plot', type = 'action'),
                                            ]
                                  )
                                  
        self.params = Parameter.create(name='ParmX', type='group', children=[self.plot_range])        
        self.tree.setParameters(self.params, showTop=False)
        
        self.params.param('Plot').param('Load Data Range').sigActivated.connect(self.load_data_range)
        self.params.param('Plot').param('Plot').sigActivated.connect(self.plot_data)
        self.progress = 0
        
    def setupGUI(self):
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.splitter)
        
        self.tree = ParameterTree(showHeader=False)
        self.splitter.addWidget(self.tree)
        
        self.pw = pg.PlotWidget(axisItems = {'bottom':TimeAxisItem(orientation='bottom')})
        self.splitter.addWidget(self.pw)
        
        global p1, p2
        p1 = self.pw.plotItem
        ## create a new ViewBox, link the right axis to its coordinate system
        p2 = pg.ViewBox()
        p1.showAxis('right')
        p1.scene().addItem(p2)
        p1.getAxis('right').linkToView(p2)
        p2.setXLink(p1)
        
        ## Handle view resizing 
        def updateViews():
            ## view has resized; update auxiliary views to match
            p2.setGeometry(p1.vb.sceneBoundingRect())
            ## need to re-update linked axes since this was called
            ## incorrectly while views had different shapes.
            ## (probably this should be handled in ViewBox.resizeEvent)
            p2.linkedViewChanged(p1.vb, p2.XAxis)
        
        updateViews()
        p1.vb.sigResized.connect(updateViews)
        
        self.plot = p1
        self.curve1 = p1.plot()
        self.curve2 = pg.PlotCurveItem(pen='r')
        p2.addItem(self.curve2)
        self.plotitem = p1
        
    def retrieve_arg(self):
        arg_list = sys.argv
        return arg_list
    
    def load_data_range(self):
        #get the start date
        s_year = self.params.param('Plot').param('Start Date').param("Year:").value()
        s_mth = self.params.param('Plot').param('Start Date').param("Month:").value()
        s_day = self.params.param('Plot').param('Start Date').param("Day:").value()
        s_hour = self.params.param('Plot').param('Start Date').param("Hour:").value()
        s_min = 0
        s_sec = 0
        str_sp_date = str(s_year) + "-" + str(s_mth) + "-" + str(s_day) + "-" +\
                        str(s_hour) + ":" + str(s_min) + ":" + str(s_sec)
        
        #get the end date
        e_year = self.params.param('Plot').param('End Date').param("Year:").value()
        e_mth = self.params.param('Plot').param('End Date').param("Month:").value()
        e_day = self.params.param('Plot').param('End Date').param("Day:").value()
        e_hour = self.params.param('Plot').param('End Date').param("Hour:").value()
        e_min = 0
        e_sec = 0
        str_e_date = str(e_year) + "-" + str(e_mth) + "-" + str(e_day) + "-" +\
                        str(e_hour) + ":" + str(e_min) + ":" + str(e_sec)
        
        self.str_plot_start_date = str_sp_date
        self.str_plot_end_date = str_e_date
        
        self.params.param('Plot').param('Data Range Loaded').setValue(str_sp_date + " to " + str_e_date)
        
    def plot_data(self):
        start_date =  parse(self.str_plot_start_date)
        start_hour = stg_func.date2index(start_date)
        start_year = start_date.year
        
        end_date = parse(self.str_plot_end_date)
        end_hour = stg_func.date2index(end_date)
        end_year = end_date.year
        
        path_dict = stg_func.retrieve_travel_path_analysis(self.travel_dir, start_hour, start_year, end_hour, end_year)
        parking_dict = stg_func.retrieve_parking_analysis(self.parking_dir, start_hour, start_year, end_hour, end_year)
        
        y1 = self.params.param('Plot').param('Y-axis1:').value()
        y2 = self.params.param('Plot').param('Y-axis2:').value()
        
        val_list = self.val_list
        key_list = ["total_park_time", "total_dist", "solar_max", "solar_med", "solar_min"]
        key_index1 = val_list.index(y1)
        key_index2 = val_list.index(y2)
        key1 = key_list[key_index1]
        key2 = key_list[key_index2]
        
        y1_list = []
        y2_list = []
        hlist = []
        
        if start_year == end_year:
            year_list = [start_year]
        else:
            year_list = range(start_year, end_year+1)
        
        projection = Proj(proj='utm',zone=18,ellps='GRS80', preserve_units=False)
        timezone = gettz()
        nyear = len(year_list)
        ycnt = 0
        for year in year_list:
            week_list, hour_interest = stg_func.gen_week_hour_interest_from_year_cnt(ycnt, nyear, start_hour, end_hour)
            for hour in hour_interest:
                res_dict = stg_func.retrieve_plot_data(hour, year, path_dict, parking_dict, projection)
                y1_list.append(res_dict[key1])
                y2_list.append(res_dict[key2])
                date_str = res_dict["date_str"]
                date = parse(date_str)
                date = date.replace(tzinfo=timezone)
                timestamp = datetime.timestamp(date)
                hlist.append(timestamp)
            ycnt+=1
                
        self.plot.setLabel("left", y1)
        self.plot.getAxis('right').setLabel(y2, color='RED')
        
        print(len(hlist), len(y1_list))
        self.curve1.setData(x = hlist, y = y1_list)
        self.curve2.setData(x = hlist, y = y2_list)
        
    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

#=====================================================================================================================================================================================================================
if __name__ == '__main__':
    pg.mkQApp()
    win = PlotData()
    win.setWindowTitle("Export the Data")
    win.show()
    win.resize(1000,500)
    win.start()