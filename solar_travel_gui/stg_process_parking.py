import os
import json
import time
from dateutil.parser import parse

import PyQt5
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.Qt import QtGui, QtCore
import sys

# import stg_function as stg_func
import solar_travel_gui.stg_function as stg_func

class ProcessParking(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setupGUI()
        
        arg_list = self.retrieve_arg()      
        # arg_list = ['F:\\kianwee_work\\spyder_workspace\\solar_travel_gui\\solar_travel_gui\\p4d_process_travel.py', 
        #             'F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\golfcart\\model3d\\solar_travel_data\\parking', 
        #             'F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\golfcart\\model3d\\solar_travel_data\\travel', 
        #             'F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\golfcart\\model3d\\solar_travel_data\\ground_solar']
        
        self.arg_list = arg_list
        
        self.parking_dir = arg_list[1]
        self.travel_dir = arg_list[2]
        self.solar_dir = arg_list[3]
        
        self.analyse_range = dict(name='Analysis', type='group', expanded = True, title = "Find Potential Parking Spots",
                                  children=[dict(name='Start Date', type = 'group', expanded = True, title = "Specify Start Date", 
                                                 children = [dict(name='Year:', type= 'list', values= [2018, 2019], value=2019),
                                                             dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                             dict(name='Day:', type= 'int', limits = (1,31), value = 2),
                                                             dict(name='Hour:', type= 'int', limits = (0,23), value = 10)]),
                                            
                                            dict(name='End Date', type = 'group', expanded = True, title = "Specify End Date",
                                                 children = [dict(name='Year:', type= 'list', values= [2018, 2019], value=2019),
                                                             dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                             dict(name='Day:', type= 'int', limits = (1,31), value = 2),
                                                             dict(name='Hour:', type= 'int', limits = (0,23), value = 18)]),
                                            
                                            dict(name='Data Range Loaded', type = 'str', readonly = True),
                                            dict(name='Load Data Range', type = 'action'),
                                            dict(name='Parking Radius', type = 'float', title = "Parking Radius (m)", value = 100),
                                            dict(name='Parking Time Threshold', type = 'float', title = "Parking Time Threshold (hr)", value = 0.5),
                                            dict(name = 'Analyse Data', type = 'action'),
                                            dict(name = 'Clear All Data in Parking Folder', type = 'action'),
                                            dict(name='Progress', type = 'str', value ="",  readonly = True, title = "Progress")]
                                  )
                                  
        self.params = Parameter.create(name='ParmX', type='group', children=[self.analyse_range])        
        self.tree.setParameters(self.params, showTop=False)      
        self.params.param('Analysis').param('Load Data Range').sigActivated.connect(self.load_analyse_data_range)
        self.params.param('Analysis').param('Analyse Data').sigActivated.connect(self.find_parking)
        self.params.param('Analysis').param('Clear All Data in Parking Folder').sigActivated.connect(self.clear_parking) 
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
        
    def load_analyse_data_range(self):
        #get the start date
        s_year = self.params.param('Analysis').param('Start Date').param("Year:").value()
        s_mth = self.params.param('Analysis').param('Start Date').param("Month:").value()
        s_day = self.params.param('Analysis').param('Start Date').param("Day:").value()
        s_hour = self.params.param('Analysis').param('Start Date').param("Hour:").value()
        s_min = 0
        s_sec = 0
        str_sp_date = str(s_year) + "-" + str(s_mth) + "-" + str(s_day) + "-" +\
                        str(s_hour) + ":" + str(s_min) + ":" + str(s_sec)
                                
        #get the end date
        e_year = self.params.param('Analysis').param('End Date').param("Year:").value()
        e_mth = self.params.param('Analysis').param('End Date').param("Month:").value()
        e_day = self.params.param('Analysis').param('End Date').param("Day:").value()
        e_hour = self.params.param('Analysis').param('End Date').param("Hour:").value()
        e_min = 0
        e_sec = 0
        str_e_date = str(e_year) + "-" + str(e_mth) + "-" + str(e_day) + "-" +\
                        str(e_hour) + ":" + str(e_min) + ":" + str(e_sec)
                                
        self.str_analysis_start_date = str_sp_date
        self.str_analysis_end_date = str_e_date
        
        self.params.param('Analysis').param('Data Range Loaded').setValue(str_sp_date + " to " + str_e_date)
        
    def find_parking(self):
        try:
            self.timer = pg.QtCore.QTimer()
            self.timer.timeout.connect(self.update_bar)
            self.timer.start(50)
            
            time1 = time.perf_counter()
            #===============================================================================================
            #UPDATE GUI
            #===============================================================================================
            QtGui.QApplication.processEvents()
            self.progress = 0
            self.params.param('Analysis').param('Progress').setValue("Retrieving solar and travel data ... ...")
            self.process_status = "Retrieving solar and travel data"
            #===============================================================================================
            #===============================================================================================
            #first get all the parameters from the gui
            start_date = parse(self.str_analysis_start_date)
            end_date = parse(self.str_analysis_end_date)
            start_hour = stg_func.date2index(start_date)
            end_hour = stg_func.date2index(end_date)
    
            parking_radius = self.params.param('Analysis').param('Parking Radius').value()
            parking_time = self.params.param('Analysis').param('Parking Time Threshold').value()
            
            solar_dir = self.solar_dir
            travel_dir = self.travel_dir
            parking_dir = self.parking_dir
            
            #then where are the parking spots according to the travel data
            travel_dict = stg_func.retrieve_travel_ext_analysis(travel_dir, start_hour, end_hour)
            stop_dict = stg_func.find_stops(travel_dict, stop_threshold = parking_time)
            
            hours_interest = range(start_hour, end_hour+1)
            week_list = stg_func.id_weeks(start_hour, end_hour)
            
            solar_res_dict = stg_func.retrieve_solar4analysis(hours_interest, week_list, solar_dir)
            solar_pts = stg_func.get_solar_pts(solar_dir)
            #===============================================================================================
            #UPDATE GUI
            #===============================================================================================
            QtGui.QApplication.processEvents()
            self.progress = 0
            self.params.param('Analysis').param('Progress').setValue("Starting stops analysis ... ...")
            self.process_status = "Starting stops analysis"
            #===============================================================================================
            #===============================================================================================
                
            total_stops = len(stop_dict.items())
            scnt = 0
            for hour, stops in stop_dict.items():
                #===============================================================================================
                #UPDATE GUI
                #===============================================================================================
                QtGui.QApplication.processEvents()
                self.progress = (scnt/total_stops) * 100
                self.params.param('Analysis').param('Progress').setValue("Processing Stops:" + str(scnt) + "/" + str(total_stops))
                self.process_status = "Processing Stops:" + str(scnt) + "/" + str(total_stops)
                #===============================================================================================
                #===============================================================================================
                week_index = stg_func.id_week(hour)
                #for each hour find the potential parking spot
                result_dict = stg_func.find_parking4_the_hour(stops, solar_pts, hour, parking_radius, solar_res_dict)
                #write the file for analysis
                parking_filepath = os.path.join(parking_dir, "analysis", "parking_wk" + str(week_index) + ".json")
                stg_func.append2json(parking_filepath, result_dict[hour], hour)
                
                #generate the meshes for the visualisation results 
                parking_viz_filepath = os.path.join(parking_dir,"viz",  "viz_parking_wk" + str(week_index) + ".json")
                mesh_dict = stg_func.gen_parking_mesh(result_dict, hour)
                stg_func.append2json(parking_viz_filepath, mesh_dict, hour)
                
                scnt+=1
            
            #write to source file
            source_path = os.path.join(parking_dir, "source.json")
            s_f = open(source_path, "w")
            json.dump({"dates":[self.str_analysis_start_date, self.str_analysis_end_date]}, s_f)
            s_f.close()
            
            time2 = time.perf_counter()
            total_time = (time2-time1)/60
            time_str = "SUCCESSFULLY COMPLETE PROCESSING, Total Processing Time: " + str(round(total_time,2)) + " mins"
            
            QtGui.QApplication.processEvents()
            self.progress = 100
            self.update_bar()
            self.params.param('Analysis').param('Progress').setValue(time_str)
            self.timer.stop()
            
        except:
            self.params.param('Analysis').param('Progress').setValue("ERROR ... Last known status:" + self.process_status)
        
    def clear_parking(self):
        parking_dir = self.parking_dir
        viz_dir = os.path.join(parking_dir, "viz")
        stg_func.clear_files(viz_dir)
        
        analysis_dir = os.path.join(parking_dir, "analysis")
        stg_func.clear_files(analysis_dir)
        
            
        #empty the source file
        source_path = os.path.join(parking_dir, "source.json")
        stg_func.clean_file(source_path)
        
        self.params.param('Analysis').param('Progress').setValue("ALL DATA SUCCESSFULLY CLEARED FROM FOLDER")
        
    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

#=====================================================================================================================================================================================================================
if __name__ == '__main__':
    pg.mkQApp()
    win = ProcessParking()
    win.setWindowTitle("Processing the Parking Data")
    win.show()
    win.resize(500,480)
    win.start()