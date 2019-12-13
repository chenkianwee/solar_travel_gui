import os
import json
import time
from dateutil.parser import parse

import PyQt5
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.Qt import QtGui, QtCore
import sys

import stg_loc_hourly as stg_loc
import stg_function as stg_func

class ProcessTravel(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setupGUI()
        
        arg_list = self.retrieve_arg()      
        # arg_list = ['F:\\kianwee_work\\spyder_workspace\\solar_travel_gui\\solar_travel_gui\\p4d_process_travel.py', 
        #             'F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\campus_as_a_lab\\data\\solar_travel_data\\context3d\\terrain.brep', 
        #             'F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\campus_as_a_lab\\data\\solar_travel_data\\travel']

        self.arg_list = arg_list
        
        self.terrain_filepath = arg_list[1]
        self.travel_dir = arg_list[2]
        
        
        self.result_view = dict(name='Progress', type = 'str', value ="",  readonly = True, title = "Progress")
                                        
        self.params = Parameter.create(name='ParmX', type='group', children=[dict(name='Travel File Loaded', type='str', value="", readonly=True),
                                                                             dict(name='Choose Travel File', type='action'),
                                                                             dict(name='Process Travel Data', type='action'),
                                                                             dict(name='Clear All Travel Data in the travel Folder', type='action'),
                                                                             self.result_view])
                                                                             
                                                                             
        self.tree.setParameters(self.params, showTop=False)      
        self.params.param('Choose Travel File').sigActivated.connect(self.choose_travel_file)
        self.params.param('Process Travel Data').sigActivated.connect(self.process_travel_data)
        self.params.param("Clear All Travel Data in the travel Folder").sigActivated.connect(self.clear_travel)
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
    
    def choose_travel_file(self):
        fn = pg.QtGui.QFileDialog.getOpenFileName(self, "Choose Travel File", "")
        self.params.param('Travel File Loaded').setValue(str(fn[0]))
        self.location_path = str(fn[0])
        if fn == '':
            return
        
    def clear_travel(self):
        travel_dir = self.travel_dir
        viz_dir = os.path.join(travel_dir, "viz")
        stg_func.clear_files(viz_dir)
        
        analysis_dir = os.path.join(travel_dir, "analysis")
        stg_func.clear_files(analysis_dir)
        
        #empty the source file
        source_path = os.path.join(travel_dir, "source.json")
        stg_func.clean_file(source_path)
        
    def process_travel_data(self):
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_bar)
        self.timer.start(50)
        
        try:                    
            time1 = time.perf_counter()
            #===============================================================================================
            #UPDATE GUI
            #===============================================================================================
            QtGui.QApplication.processEvents()
            self.progress = 0
            self.params.param('Progress').setValue("Reading the files  ... ...")
            self.process_status = "Reading location file"
            #===============================================================================================
            #===============================================================================================
            hourly_list, loc_pyptlist, date_str_list = stg_loc.read_process_loc_json(self.location_path)
            self.process_status = "Reading terrain file"
            
            id_terrain_list = stg_loc.id_terrains_with_loc_pts(self.terrain_filepath, loc_pyptlist)
            self.process_status = "Finished reading location and terrain files"
            self.params.param('Progress').setValue("Read and Id the Terrains  ... ...")
            
            path_att_2dlist = []
            path_wire_list = []    
            gdict_list = []
            ndates = len(date_str_list)
            
            progress_cnt = 0
            hcnt = 0
            for locd in hourly_list:    
                locs_list = locd["locations"]
                if locs_list:
                    QtGui.QApplication.processEvents()
                    self.progress = (progress_cnt/ndates)*100
                    self.params.param('Progress').setValue("Processing locations: " + str(hcnt) + "/8760")
                    self.process_status = "Processing locations: " + str(hcnt) + "/8760"
                    # if 5832<= hcnt <= 5838:
                    stg_loc.process_hourly_loc(hcnt, locd, id_terrain_list, gdict_list, path_wire_list, path_att_2dlist, self.travel_dir)
                    progress_cnt+=1
                hcnt+=1
            
            #write the meta data of the data into a json file
            #read the file and check if it is an append or a new file
            
            source_path = os.path.join(self.travel_dir, "source.json")
            if os.stat(source_path).st_size != 0:
                self.process_status = "Updating json source file"
                f = open(source_path, "r")
                json_data = json.load(f)
                source = json_data["source"]
                source.append(self.location_path)
                
                date_str_list2 = json_data["dates"]
                start_date1 = parse(date_str_list[0])
                start_date2 = parse(date_str_list2[0])
                end_date1 = parse(date_str_list[-1])
                end_date2 = parse(date_str_list2[1])
                
                s_date_list = [start_date1, start_date2]
                e_date_list = [end_date1, end_date2]
                start_date = min(s_date_list)
                start_date_str = start_date.strftime("%Y-%m-%d %H:0:0")
                end_date = max(e_date_list)
                end_date_str = end_date.strftime("%Y-%m-%d %H:0:0")
                
                meta = {"source": source, "dates":[start_date_str, end_date_str]}
                f.close()
            else:
                self.process_status = "Writing json source file"
                meta = {"source": [self.location_path], "dates":[date_str_list[0], date_str_list[-1]]}
            
            self.process_status = "Writing to json source file"
            f = open(source_path, 'w')
            json.dump(meta, f)
            f.close()
            
            time2 = time.perf_counter()
            total_time = (time2-time1)/60
            time_str = "SUCCESSFULLY COMPLETE PROCESSING, Total Processing Time: " + str(round(total_time,2)) + " mins"
            
            QtGui.QApplication.processEvents()
            self.progress = 100
            self.update_bar()
            self.params.param('Progress').setValue(time_str)
            self.timer.stop()
            
        except:
            self.params.param('Progress').setValue("ERROR ... Last known status:" + self.process_status)
        
    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

#=====================================================================================================================================================================================================================
if __name__ == '__main__':
    pg.mkQApp()
    win = ProcessTravel()
    win.setWindowTitle("Processing the Travelling Data")
    win.show()
    win.resize(500,200)
    win.start()