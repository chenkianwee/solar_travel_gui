import time
from dateutil.parser import parse

import PyQt5
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.Qt import QtGui, QtCore
import sys

from pyproj import Proj

# import stg_function as stg_func
import solar_travel_gui.stg_function as stg_func


class ExportData(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setupGUI()
        
        arg_list = self.retrieve_arg()      
        # arg_list = ['F:\\kianwee_work\\spyder_workspace\\solar_travel_gui\\solar_travel_gui\\stg_export_data.py', 
        #             'F:/kianwee_work/princeton/2020_01_to_2020_06/golfcart/model3d/solar_travel_data\\parking', 
        #             'F:/kianwee_work/princeton/2020_01_to_2020_06/golfcart/model3d/solar_travel_data\\travel']
        
        self.arg_list = arg_list
        
        self.parking_dir = arg_list[1]
        self.travel_dir = arg_list[2]
        
        self.export_range = dict(name='Export', type='group', expanded = True, title = "Export Data to CSV",
                                  children=[dict(name='Start Date', type = 'group', expanded = True, title = "Specify Start Date", 
                                                 children = [dict(name='Year:', type= 'list', values= [2019, 2020], value=2019),
                                                             dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                             dict(name='Day:', type= 'int', limits = (1,31), value = 2),
                                                             dict(name='Hour:', type= 'int', limits = (0,23), value = 10)]),
                                            
                                            dict(name='End Date', type = 'group', expanded = True, title = "Specify End Date",
                                                 children = [dict(name='Year:', type= 'list', values= [2019, 2020], value=2020),
                                                             dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                             dict(name='Day:', type= 'int', limits = (1,31), value = 2),
                                                             dict(name='Hour:', type= 'int', limits = (0,23), value = 18)]),
                                            
                                            dict(name='Data Range Loaded', type = 'str', readonly = True),
                                            dict(name='Load Data Range', type = 'action'),
                                            dict(name='Result File Chosen', type = 'str', readonly = True),
                                            dict(name = 'Choose Result Path', type = 'action'),
                                            dict(name = 'Export', type = 'action'),
                                            dict(name='Progress', type = 'str', value ="",  readonly = True, title = "Progress")]
                                  )
                                  
        self.params = Parameter.create(name='ParmX', type='group', children=[self.export_range])        
        self.tree.setParameters(self.params, showTop=False)
        
        self.params.param('Export').param('Load Data Range').sigActivated.connect(self.load_export_data_range)
        self.params.param('Export').param('Choose Result Path').sigActivated.connect(self.choose_filepath)
        self.params.param('Export').param('Export').sigActivated.connect(self.export_data)
        self.progress = 0
        
    def setupGUI(self):
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.splitter)
        
        self.tree = ParameterTree(showHeader=False)
        self.progress_bar = QtGui.QProgressBar(self)
        self.progress_bar.setGeometry(200, 80, 250, 20)
        self.splitter.addWidget(self.tree)
        self.layout.addWidget(self.progress_bar)
        
    def update_bar(self):
        progress_value = self.progress
        self.progress_bar.setValue(progress_value)
        
    def retrieve_arg(self):
        arg_list = sys.argv
        return arg_list
            
    def load_export_data_range(self):
        #get the start date
        s_year = self.params.param('Export').param('Start Date').param("Year:").value()
        s_mth = self.params.param('Export').param('Start Date').param("Month:").value()
        s_day = self.params.param('Export').param('Start Date').param("Day:").value()
        s_hour = self.params.param('Export').param('Start Date').param("Hour:").value()
        s_min = 0
        s_sec = 0
        str_sp_date = str(s_year) + "-" + str(s_mth) + "-" + str(s_day) + "-" +\
                        str(s_hour) + ":" + str(s_min) + ":" + str(s_sec)
        
        #get the end date
        e_year = self.params.param('Export').param('End Date').param("Year:").value()
        e_mth = self.params.param('Export').param('End Date').param("Month:").value()
        e_day = self.params.param('Export').param('End Date').param("Day:").value()
        e_hour = self.params.param('Export').param('End Date').param("Hour:").value()
        e_min = 0
        e_sec = 0
        str_e_date = str(e_year) + "-" + str(e_mth) + "-" + str(e_day) + "-" +\
                        str(e_hour) + ":" + str(e_min) + ":" + str(e_sec)
        
        self.str_export_start_date = str_sp_date
        self.str_export_end_date = str_e_date
        
        self.params.param('Export').param('Data Range Loaded').setValue(str_sp_date + " to " + str_e_date)
        
    def choose_filepath(self):
        fn = pg.QtGui.QFileDialog.getSaveFileName(self, "Choose File Path", "exported_data.csv", 'CSV (*.csv)')
        self.params.param('Export').param('Result File Chosen').setValue(str(fn[0]))
        self.result_filepath = str(fn[0])
        if fn == '':
            return
        
    def export_data(self):
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_bar)
        self.timer.start(50)
        try:
            time1 = time.perf_counter()
            self.process_status = "Exporting ... "
            self.params.param('Export').param('Progress').setValue(self.process_status)
            start_date =  parse(self.str_export_start_date)
            start_hour = stg_func.date2index(start_date)
            start_year = start_date.year
            
            end_date = parse(self.str_export_end_date)
            end_hour = stg_func.date2index(end_date)
            end_year = end_date.year
            
            res_filepath = self.result_filepath
            
            self.process_status = "Reading data ... "
            self.params.param('Export').param('Progress').setValue(self.process_status)
            
            path_dict = stg_func.retrieve_travel_path_analysis(self.travel_dir, start_hour, start_year, end_hour, end_year)
            parking_dict = stg_func.retrieve_parking_analysis(self.parking_dir, start_hour, start_year, end_hour, end_year)
            
            self.process_status = "Read all Dicitonaries ... "
            self.params.param('Export').param('Progress').setValue(self.process_status)
            
            if start_year == end_year:
                year_list = [start_year]
            else:
                year_list = range(start_year, end_year+1)
            
            projection = Proj(proj='utm',zone=18,ellps='GRS80', preserve_units=False)
            nyear = len(year_list)
            
            strx = "Date,DistanceTravelled(m),ParkingTime(hr),SolarMax(wh/m2),SolarMaxPos,SolarMaxZ(m),SolarMin(wh/m2),SolarMinPos,SolarMinZ(m),SolarMedian(wh/m2),SolarMedPos,SolarMedZ(m)\n"
            
            ycnt = 0
            for year in year_list:
                week_list, hour_interest = stg_func.gen_week_hour_interest_from_year_cnt(ycnt, nyear, start_hour, end_hour)
                total_hours = len(hour_interest)
                hcnt = 0
                for hour in hour_interest:
                    QtGui.QApplication.processEvents()
                    self.progress = (hcnt/total_hours) * 100
                    self.process_status = "Processing Stops:" + str(hcnt) + "/" + str(total_hours) + " year " + str(year) + "/" + str(list(year_list)[-1])
                    self.params.param('Export').param('Progress').setValue(self.process_status)
                    
                    res_str = stg_func.export_data(hour, year, path_dict, parking_dict, projection)
                    strx += res_str
                
                    hcnt+=1
                ycnt+=1
            
            f = open(res_filepath, "w")
            f.write(strx)
            f.close()
        
            time2 = time.perf_counter()
            total_time = (time2-time1)/60
            time_str = "SUCCESSFULLY COMPLETE PROCESSING, Total Processing Time: " + str(round(total_time,2)) + " mins"
            
            QtGui.QApplication.processEvents()
            self.progress = 100
            self.update_bar()
            self.params.param('Export').param('Progress').setValue(time_str)
            self.timer.stop()
            
        except:
            self.params.param('Export').param('Progress').setValue("ERROR ... Last known status:" + self.process_status)
        
    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

#=====================================================================================================================================================================================================================
if __name__ == '__main__':
    pg.mkQApp()
    win = ExportData()
    win.setWindowTitle("Export the Data")
    win.show()
    win.resize(800,800)
    win.start()