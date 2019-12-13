import os
import json
import subprocess
from dateutil.parser import parse
from datetime import timedelta

import PyQt5
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree

import stg_function as stg_func

class Dashboard(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setupGUI()
        self.layers = dict(name = 'Layers', type='group', expanded = True, title = "Step 1: Specify the 3D Model Directory & Choose Which Layers to View", 
                           children =   [dict(name='Data Directory Chosen', type = 'str', value = "", readonly = True),
                                         dict(name='Choose Data Directory', type = 'action'),
                                         dict(name='Load 3D Model', type = 'action'),
                                         ]
                            )
        
        self.params = Parameter.create(name='ParmX', type='group', children=[self.layers])
        self.tree.setParameters(self.params, showTop=False)
        
        self.params.param('Layers').param("Choose Data Directory").sigActivated.connect(self.set_data_dir)
        self.params.param('Layers').param("Load 3D Model").sigActivated.connect(self.load_3dmodel)
        
    def setupGUI(self):
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        
        self.tree = ParameterTree(showHeader=False)
        self.splitter.addWidget(self.tree)

        self.splitter2 = QtGui.QSplitter()
        self.splitter2.setOrientation(QtCore.Qt.Horizontal)
        
        self.tree2 = ParameterTree(showHeader=True)
        self.splitter2.addWidget(self.splitter)
        self.splitter2.addWidget(self.tree2)
        self.splitter2.setStretchFactor(0, 3)
        
        self.layout.addWidget(self.splitter2)
        
        self.view3d = gl.GLViewWidget()
        self.splitter.addWidget(self.view3d)
        
    def set_data_dir(self):
        fn = pg.QtGui.QFileDialog.getExistingDirectory(self, "Choose Data Directory", "")
        self.params.param('Layers').param('Data Directory Chosen').setValue(fn)
        self.data_dir = fn
        if fn == '':
            return
        
    def load_3dmodel(self):        
        #========================================================================
        #Set all the directory for the data and 3d models
        #========================================================================
        data_dir = self.data_dir
        self.solar_dir = os.path.join(data_dir, "ground_solar")
        self.travel_dir = os.path.join(data_dir, "travel")
        self.parking_dir = os.path.join(data_dir, "parking")
        self.mesh_dir = os.path.join(data_dir, "context3d")
        
        #check if they are existing data from previous session
        self.check_travel_dir()
        
        file_loaded_status = ""
        date_str_list = []
        if self.is_travel_data:
            #if there are data do not expand the parameter group
            expand = False
            travel_source_path = os.path.join(self.travel_dir, "source.json")
            f = open(travel_source_path, "r")
            json_data = json.load(f)
            paths = json_data["source"]
            pcnt = 0
            for p in paths:
                if pcnt == len(paths)-1:
                    file_loaded_status+=p
                else:
                    file_loaded_status+=p + "\n"
                pcnt+=1
            date_str_list = json_data["dates"]
            f.close()
        else:
            #else expand the group 
            expand = True
            file_loaded_status = "NO TRAVEL DATA PLEASE LOAD TRAVEL DATA!!"
        #========================================================================
        #load the complete GUI
        #========================================================================
        layers_parm = [dict(name='Static Layer', type = 'group',
                            children = [dict(name = 'Terrain', type = 'bool', value=True),
                                        dict(name = 'Buildings', type = 'bool', value=True),
                                        dict(name = 'Trees', type = 'bool', value=True),
                                        dict(name = 'Roads', type = 'bool', value=True)]
                            ),  
                        dict(name='Falsecolour Layer', type = 'group',
                             children = [dict(name = 'Hourly Grd Solar Irradiation', type = 'bool', value=True),
                                         dict(name = 'Solar Date Range', type = 'str', value="2019-01-01-0:0:0 to 2019-12-31-23:0:0", readonly = True)]
                             ),
                        dict(name='Extrusion Layer', type = 'group',
                             children = [dict(name = 'Load Travel Data', type = 'group', expanded = expand,
                                              children = [dict(name='Travel File Loaded', type='str', value= file_loaded_status, readonly=True),
                                                          dict(name='Load Travel Data', type='action')
                                                      ]
                                              ),
                                        dict(name = 'Hourly Cart Travel Behaviour', type = 'bool', value=True),
                                        dict(name = 'Travel Date Range', type = 'str', value="", readonly = True)]                                                       
                             ),
                        dict(name='Change Layers Visibility', type = 'action')]
        
        self.params.param("Layers").removeChild(self.params.param("Layers").param("Choose Data Directory"))
        self.params.param("Layers").removeChild(self.params.param("Layers").param("Load 3D Model"))
        self.params.param("Layers").addChildren(layers_parm)
        
        if not expand:
            self.params.param('Layers').param("Extrusion Layer").param("Travel Date Range").setValue(date_str_list[0] + " to " + date_str_list[1])
        
        self.load_result = dict(name='Load Result', type='group', expanded = True, title = "Step 2: Specify a Date & Time and Manually Explore the Dynamic Data",
                                children=[dict(name='Date of Interest', type = 'group', title = "Specify Date of Interest", 
                                                   children = [dict(name='Year:', type= 'list', values= [2019], value=2019),
                                                               dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                               dict(name='Day:', type= 'int', limits = (1,31), value = 2),
                                                               dict(name='Hour:', type= 'int', limits = (0,23), value = 10)]),
                                              dict(name='Data Loaded', type='str', readonly=True),
                                              dict(name='Load Data', type='action'),
                                              dict(name='Forward', type='action'),
                                              dict(name='Backward', type='action')]
                                    
                                )
    
        self.date_range = dict(name='Date Range', type='group', expanded = True, title = "Step 3: Specify a Date Range and Automatically Explore the Dynamic Data",
                              children=[dict(name='Start Date', type = 'group', expanded = False, title = "Specify Start Date", 
                                             children = [dict(name='Year:', type= 'list', values= [2018, 2019], value=2019),
                                                         dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                         dict(name='Day:', type= 'int', limits = (1,31), value = 2),
                                                         dict(name='Hour:', type= 'int', limits = (0,23), value = 10)]),
                                        
                                        dict(name='End Date', type = 'group', expanded = False, title = "Specify End Date",
                                             children = [dict(name='Year:', type= 'list', values= [2018, 2019], value=2019),
                                                         dict(name='Month:', type= 'int', limits = (1,12), value = 9),
                                                         dict(name='Day:', type= 'int', limits = (1,31), value = 30),
                                                         dict(name='Hour:', type= 'int', limits = (0,23), value = 18)]),
                                        
                                        dict(name='Data Range Loaded', type = 'str', readonly = True),
                                        dict(name='Load Data Range', type = 'action'),
                                        dict(name = 'Play Data', type = 'action')]
                                )
                                        
        self.analyse_range = dict(name='Analysis', type='group', expanded = True, title = "Step 4: Find Potential Parking Spots",
                                  children=[dict(name = 'Find Potential Parking', type = 'action')]
                                )   
                                 
        self.export_range = dict(name='Export', type='group', expanded = True, title = "Step 5: Export the Data",
                                  children=[dict(name = 'Export Data', type = 'action')]
                                )
        
        self.params.addChildren([self.load_result,
                                 self.date_range,
                                 self.analyse_range,
                                 self.export_range])
                                 
        self.tree.setParameters(self.params, showTop=False)
        
        #generate falsecolour bar
        self.min_val = 133.0
        self.max_val = 914.0
        
        self.falsecolour = stg_func.gen_falsecolour_bar(self.min_val, self.max_val)
        self.min_max = dict(name='Min Max', type='group', expanded = True, title = "Specify the Min Max Value",
                            children=[dict(name='Min Value', type = 'float', title = "Min Value", value = self.min_val),
                                      dict(name='Max Value', type = 'float', title = "Max Value", value = self.max_val),
                                      dict(name = 'Change Min Max', type = 'action', title = 'Change Min Max')]
                            )
        
        self.params2 = Parameter.create(name = "Parmx2", type = "group", children = [self.falsecolour,
                                                                                     self.min_max])
        self.tree2.setParameters(self.params2, showTop=False)
        
        self.params.param('Layers').param("Extrusion Layer").param("Load Travel Data").param("Load Travel Data").sigActivated.connect(self.load_travel)
        self.params.param('Layers').param("Change Layers Visibility").sigActivated.connect(self.change_visibility)
        
        self.params.param('Load Result').param("Load Data").sigActivated.connect(self.load_data)
        self.params.param('Load Result').param("Forward").sigActivated.connect(self.forward)
        self.params.param('Load Result').param("Backward").sigActivated.connect(self.backward)
        
        self.params.param('Date Range').param("Load Data Range").sigActivated.connect(self.load_data_range)
        self.params.param('Date Range').param("Play Data").sigActivated.connect(self.play_data)
        
        self.params.param('Analysis').param("Find Potential Parking").sigActivated.connect(self.find_parking)
        
        self.params.param('Export').param("Export Data").sigActivated.connect(self.export_data)
        
        self.params2.param('Min Max').param("Change Min Max").sigActivated.connect(self.change_min_max)
        
        #check if there are parking data 
        self.is_parking_layer = False
        self.check_parking_dir()
        if self.is_parking_data == True:
            parking_layer = dict(name = 'Hourly Parking Spots', type = 'bool', value=True)
            self.params.param('Layers').param("Falsecolour Layer").addChild(parking_layer)
            
            source_path = os.path.join(self.parking_dir, "source.json")
            p_source = open(source_path, "r")
            json_data = json.load(p_source)
            date_str_list = json_data["dates"]
            date_range_val = date_str_list[0] + " to " + date_str_list[1] 
            parking_date_range = dict(name = 'Parking Date Range', type = 'str', value=date_range_val, readonly = True)
            self.params.param('Layers').param("Falsecolour Layer").addChild(parking_date_range)
            self.is_parking_layer = True
            
        #========================================================================
        #load the 3d terrain model
        #========================================================================
        terrain_mesh_json = os.path.join(self.mesh_dir, "terrains.json")
        terrains_mesh_list = stg_func.read_meshes_json(terrain_mesh_json, shader = "shaded",  gloptions = "additive")
        
        for t in terrains_mesh_list:
            t.setColor([1.0,1.0,1.0,1.0])
            
        self.terrain_meshes = terrains_mesh_list
        #========================================================================
        #laod the 3d buildings
        #========================================================================
        facade_mesh_json = os.path.join(self.mesh_dir, "facade.json")
        roof_mesh_json =  os.path.join(self.mesh_dir, "roof.json")
        roof_edge_json = os.path.join(self.mesh_dir, "roof_edge.json")
        
        roof_mesh_list = stg_func.read_meshes_json(roof_mesh_json, shader = "balloon", gloptions = "additive", draw_edges = False)
        roof_mesh_list[0].setColor([0.5,0.5,0.5,1])
        facade_mesh_list = stg_func.read_meshes_json(facade_mesh_json, shader = "balloon", gloptions = "additive", draw_edges = False)
        line_list = stg_func.read_edges_json(roof_edge_json, line_colour = (0,0,0,1), width = 1, antialias=True, mode="lines")
        
        self.roof_meshes = roof_mesh_list
        self.facade_meshes = facade_mesh_list
        self.bldg_lines = line_list
        #========================================================================
        #load the trees 
        #========================================================================
        tree_mesh_json = os.path.join(self.mesh_dir, "trees.json")
        tree_meshes = stg_func.read_meshes_json(tree_mesh_json, shader = "shaded", gloptions = "additive")
        tree_meshes[0].setColor([0,0.5,0,1])
        
        self.tree_meshes = tree_meshes
        #========================================================================
        #load roads 
        #========================================================================
        road_mesh_json = os.path.join(self.mesh_dir, "roads.json")
        road_meshes = stg_func.read_meshes_json(road_mesh_json)
        for mesh in road_meshes:
            mesh.setColor([0.5,0.5,0.5,1])
        
        self.road_meshes = road_meshes
        #========================================================================
        #load falsecolour results 
        #========================================================================
        #get all the geometries 
        json_mesh_filepath = os.path.join(self.mesh_dir, "solar_grd.json")  
        
        falsecolour_mesh_list = stg_func.read_meshes_json(json_mesh_filepath, shader = "balloon", gloptions = "translucent")
        self.colour_meshes = falsecolour_mesh_list
        #========================================================================
        #load extrusion results 
        #========================================================================
        self.path_lines = [None]
        self.extrude_meshes = [None]
        self.extrude_lines = [None]
        
        self.parking_meshes = [None]
        #========================================================================
        #determine the back and front of each geometry 
        #========================================================================
        stg_func.viz_graphic_items(terrains_mesh_list, self.view3d)
        
        stg_func.viz_graphic_items(road_meshes , self.view3d)
        
        stg_func.viz_graphic_items(tree_meshes, self.view3d)
        
        stg_func.viz_graphic_items(facade_mesh_list, self.view3d)
        stg_func.viz_graphic_items(line_list, self.view3d)
        stg_func.viz_graphic_items(roof_mesh_list, self.view3d)
        #========================================================================
        #configure the camera to orbit around the terrain
        #========================================================================
        midpt = [529580.7566756287, 4465755.661849028, 42.16880273814235]
        self.midpt_str = str(midpt[0]) + "," + str(midpt[1]) + "," + str(midpt[2])
        self.view3d.opts['center'] = PyQt5.QtGui.QVector3D(midpt[0], midpt[1], midpt[2])
        self.view3d.opts['distance'] = 5000
         
    def export_data(self):
        parking_dir = self.parking_dir
        travel_dir = self.travel_dir
        export_file = os.path.join(os.getcwd(), "stg_export_data.py")
        
        call_list = ["python", export_file, parking_dir, travel_dir]
        #=================================================================
        #execute the processing parking GUI
        #=================================================================
        subprocess.call(call_list)
        #=================================================================
        #add a new analysis layer to the layer tab
        #=================================================================
        
    def find_parking(self):
        parking_dir = self.parking_dir
        travel_dir = self.travel_dir
        solar_dir = self.solar_dir
        process_file = os.path.join(os.getcwd(), "stg_process_parking.py")
        
        call_list = ["python", process_file, parking_dir, travel_dir, solar_dir]
        #=================================================================
        #execute the processing parking GUI
        #=================================================================
        subprocess.call(call_list)
        #=================================================================
        #add a new analysis layer to the layer tab
        #=================================================================
        parking_source_path = os.path.join(self.parking_dir, "source.json")
        if os.stat(parking_source_path).st_size != 0:
            #if there are existing data in the folder
            f = open(parking_source_path, "r")
            json_data = json.load(f)
            date_str_list = json_data["dates"]
            
            if not self.is_parking_layer:
                #if there are existing data in the folder and there is no layer add the layer into the gui
                parking_layer = dict(name = 'Hourly Parking Spots', type = 'bool', value=True)
                self.params.param('Layers').param("Falsecolour Layer").addChild(parking_layer)
                
                parking_date_range = dict(name = 'Parking Date Range', type = 'str', value=date_str_list[0] + " to " + date_str_list[1], readonly = True)
                self.params.param('Layers').param("Falsecolour Layer").addChild(parking_date_range)
                
                #turn off the solar irradiation data layer
                self.params.param('Layers').param("Falsecolour Layer").param('Hourly Grd Solar Irradiation').setValue(False)
                self.change_visibility()
                self.is_parking_layer = True
                
                #load the freshly analysed data
                start_date = parse(date_str_list[0])
                self.params.param('Load Result').param('Date of Interest').param("Year:").setValue(int(start_date.strftime("%Y")))
                self.params.param('Load Result').param('Date of Interest').param("Month:").setValue(int(start_date.strftime("%m")))
                self.params.param('Load Result').param('Date of Interest').param("Day:").setValue(int(start_date.strftime("%d")))
                self.params.param('Load Result').param('Date of Interest').param("Hour:").setValue(int(start_date.strftime("%H")))
                self.load_data()
                
            else:
                #if there are existing data in the folder and there is layer update the information
                self.params.param('Layers').param("Falsecolour Layer").param("Parking Date Range").setValue(date_str_list[0] + " to " + date_str_list[1])
                
        else:
            #if there are no data and no existing layer do nothing 
            if self.is_parking_layer:
                #if there are no data and existing layer, remove the layer 
                parking_parm = self.params.param('Layers').param("Falsecolour Layer").param("Hourly Parking Spots")
                parking_date = self.params.param('Layers').param("Falsecolour Layer").param("Parking Date Range")
                self.params.param('Layers').param('Falsecolour Layer').removeChild(parking_parm)
                self.params.param('Layers').param('Falsecolour Layer').removeChild(parking_date)
                self.is_parking_layer = False
            
    def load_travel(self):
        terrain_path = os.path.join(self.mesh_dir, "terrain.brep")
        travel_dir = self.travel_dir
        process_file = os.path.join(os.getcwd(), "stg_process_travel.py")
        
        call_list = ["python", process_file, terrain_path, travel_dir]
        #=================================================================
        #execute the processing travel GUI
        #=================================================================
        #if you need to kill the window after use this segment
        # p = subprocess.Popen(call_list)
        # p.kill()
        
        #else use this segment
        subprocess.call(call_list)
        #=================================================================
        #execute the processing travel GUI
        #=================================================================
        travel_source_path = os.path.join(self.travel_dir, "source.json")
        if os.stat(travel_source_path).st_size != 0:
            f = open(travel_source_path, "r")
            json_data = json.load(f)
            f.close()
            source_list = json_data["source"]
            s_str = ""
            
            pcnt = 0
            for p in source_list:
                if pcnt == len(source_list)-1:
                    s_str+=p
                else:
                    s_str+=p + "\n"
                pcnt+=1
                
            self.params.param('Layers').param("Extrusion Layer").param("Load Travel Data").param("Travel File Loaded").setValue(s_str)
            date_str_list = json_data["dates"]
            self.params.param('Layers').param("Extrusion Layer").param("Travel Date Range").setValue(date_str_list[0] + " to " + date_str_list[1])
        else:
            self.params.param('Layers').param("Extrusion Layer").param("Load Travel Data").param("Travel File Loaded").setValue("NO TRAVEL DATA PLEASE LOAD TRAVEL DATA!!")
            self.params.param('Layers').param("Extrusion Layer").param("Travel Date Range").setValue("")
            
    def check_parking_dir(self):
        parking_dir = self.parking_dir 
        parking_source_path = os.path.join(parking_dir, "source.json")
        if os.stat(parking_source_path).st_size != 0:
            self.is_parking_data = True
        else:
            self.is_parking_data = False
        
    def check_travel_dir(self):
        travel_dir = self.travel_dir 
        travel_source_path = os.path.join(travel_dir, "source.json")
        if os.stat(travel_source_path).st_size != 0:
            self.is_travel_data = True
        else:
            self.is_travel_data = False
            
    def change_visibility(self):
        #get all the settings for static layers
        terrain_bool = self.params.param('Layers').param('Static Layer').param("Terrain").value()
        building_bool = self.params.param('Layers').param('Static Layer').param("Buildings").value()
        tree_bool = self.params.param('Layers').param('Static Layer').param("Trees").value()
        road_bool = self.params.param('Layers').param('Static Layer').param("Roads").value()
        
        #get all the settings for dynamic layers
        hrly_solar_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Grd Solar Irradiation").value()
        hrly_cart_bool = self.params.param('Layers').param('Extrusion Layer').param("Hourly Cart Travel Behaviour").value()
        
        #get all the meshes
        terrains = self.terrain_meshes
        
        trees = self.tree_meshes
        roads = self.road_meshes
        
        roofs = self.roof_meshes 
        facades = self.facade_meshes
        bldg_outlines = self.bldg_lines
        
        falsecolours = self.colour_meshes
        
        path_lines = self.path_lines
        extrude_meshes = self.extrude_meshes
        ext_lines = self.extrude_lines
        
        #set the visibility
        stg_func.set_graphic_items_visibility(terrains, terrain_bool)
        
        stg_func.set_graphic_items_visibility(roofs, building_bool)
        stg_func.set_graphic_items_visibility(facades, building_bool)
        stg_func.set_graphic_items_visibility(bldg_outlines, building_bool)
        
        stg_func.set_graphic_items_visibility(trees, tree_bool)
        stg_func.set_graphic_items_visibility(roads, road_bool)
        
        stg_func.set_graphic_items_visibility(falsecolours, hrly_solar_bool)
        
        stg_func.set_graphic_items_visibility(path_lines, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(extrude_meshes, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(ext_lines, hrly_cart_bool)
        
        #add a new analysis layer to the layer tab
        children = self.params.param('Layers').param("Falsecolour Layer").children()
        name_list = []
        for child in children:
            child_name = child.name()
            name_list.append(child_name)
 
        if 'Hourly Parking Spots' in name_list:
            parking_meshes = self.parking_meshes
            hrly_parking_bool = self.params.param('Layers').param('Falsecolour Layer').param('Hourly Parking Spots').value()
            stg_func.set_graphic_items_visibility(parking_meshes, hrly_parking_bool)
            
    def load_data(self):
        #get the specified date
        s_year = self.params.param('Load Result').param('Date of Interest').param("Year:").value()
        s_mth = self.params.param('Load Result').param('Date of Interest').param("Month:").value()
        s_day = self.params.param('Load Result').param('Date of Interest').param("Day:").value()
        s_hour = self.params.param('Load Result').param('Date of Interest').param("Hour:").value()
        s_min = 0
        s_sec = 0
        str_sp_date = str(s_year) + "-" + str(s_mth) + "-" + str(s_day) + "-" +\
                        str(s_hour) + ":" + str(s_min) + ":" + str(s_sec)
                                
        date = parse(str_sp_date)
        self.current_date = date
        str_date = date.strftime("%Y-%m-%d %H:%M:%S")
        self.params.param('Load Result').param('Data Loaded').setValue(str_date)
        hour_index = stg_func.date2index(date)
        self.current_index = hour_index
        #=============================================
        #retrieve the solar data from the date index
        #=============================================
        solar_dir = self.solar_dir
        solar_mesh = self.colour_meshes
        stg_func.retrieve_solar_data(solar_mesh[0], hour_index, solar_dir, self.min_val, self.max_val)
        stg_func.viz_graphic_items(solar_mesh, self.view3d)
        #=============================================
        #retrieve the travel data
        #=============================================
        path_lines = self.path_lines 
        extrude_meshes = self.extrude_meshes
        extrude_lines = self.extrude_lines 
        
        travel_dir = self.travel_dir
        mesh_vis, bdry_vis, path_vis = stg_func.retrieve_travel_data(hour_index, travel_dir, extrude_meshes, extrude_lines, path_lines, self.view3d)
        
        if mesh_vis !=None:
            stg_func.viz_graphic_items([mesh_vis], self.view3d)
            stg_func.viz_graphic_items([bdry_vis], self.view3d)
            
        if path_vis !=None:
            stg_func.viz_graphic_items([path_vis], self.view3d)
            
        self.path_lines = [path_vis]
        self.extrude_meshes = [mesh_vis]
        self.extrude_lines = [bdry_vis]
        
        hrly_cart_bool = self.params.param('Layers').param('Extrusion Layer').param("Hourly Cart Travel Behaviour").value()
        stg_func.set_graphic_items_visibility(self.path_lines, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(self.extrude_meshes, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(self.extrude_lines , hrly_cart_bool)
        #=============================================
        #retrieve the parking data
        #=============================================
        parking_meshes = self.parking_meshes
        parking_dir = self.parking_dir
        parking_mesh = stg_func.retrieve_parking_data(hour_index, parking_dir, parking_meshes, self.view3d, self.min_val, self.max_val)
        if parking_mesh != None:
            stg_func.viz_graphic_items([parking_mesh], self.view3d)
        
        self.parking_meshes = [parking_mesh]
        if self.is_parking_layer:
            hrly_park_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Parking Spots").value()
            stg_func.set_graphic_items_visibility(self.parking_meshes, hrly_park_bool)
    
    def forward(self):
        current_index = self.current_index
        current_date = self.current_date
        forward = current_index + 1
        forward_date = current_date + timedelta(hours=1)
        #=============================================
        #retrieve the solar data from the date index
        #=============================================
        solar_dir = self.solar_dir
        solar_mesh = self.colour_meshes
        stg_func.retrieve_solar_data(solar_mesh[0], forward, solar_dir, self.min_val, self.max_val)
        #=============================================
        #retrieve the travel data
        #=============================================
        path_lines = self.path_lines 
        extrude_meshes = self.extrude_meshes
        extrude_lines = self.extrude_lines 
        
        travel_dir = self.travel_dir
        mesh_vis, bdry_vis, path_vis = stg_func.retrieve_travel_data(forward, travel_dir, extrude_meshes, extrude_lines, path_lines, self.view3d)
        
        if mesh_vis !=None:
            stg_func.viz_graphic_items([mesh_vis], self.view3d)
            stg_func.viz_graphic_items([bdry_vis], self.view3d)
            
        if path_vis !=None:
            stg_func.viz_graphic_items([path_vis], self.view3d)
            
        self.path_lines = [path_vis]
        self.extrude_meshes = [mesh_vis]
        self.extrude_lines = [bdry_vis]
        
        hrly_cart_bool = self.params.param('Layers').param('Extrusion Layer').param("Hourly Cart Travel Behaviour").value()
        stg_func.set_graphic_items_visibility(self.path_lines, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(self.extrude_meshes, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(self.extrude_lines , hrly_cart_bool)
        #=============================================
        #retrieve the parking data
        #=============================================
        parking_meshes = self.parking_meshes
        parking_dir = self.parking_dir
        parking_mesh = stg_func.retrieve_parking_data(forward, parking_dir, parking_meshes, self.view3d, self.min_val, self.max_val)
        if parking_mesh != None:
            stg_func.viz_graphic_items([parking_mesh], self.view3d)
        
        self.parking_meshes = [parking_mesh]
        
        if self.is_parking_layer:
            hrly_park_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Parking Spots").value()
            stg_func.set_graphic_items_visibility(self.parking_meshes, hrly_park_bool)
        #=============================================
        #update the dates
        #=============================================
        self.current_index = forward
        self.current_date = forward_date
        str_date = forward_date.strftime("%Y-%m-%d %H:%M:%S")
        self.params.param('Load Result').param('Data Loaded').setValue(str_date)
        self.params.param('Load Result').param('Data Loaded').setValue(str_date)
        self.params.param('Load Result').param('Date of Interest').param("Year:").setValue(int(forward_date.strftime("%Y")))
        self.params.param('Load Result').param('Date of Interest').param("Month:").setValue(int(forward_date.strftime("%m")))
        self.params.param('Load Result').param('Date of Interest').param("Day:").setValue(int(forward_date.strftime("%d")))
        self.params.param('Load Result').param('Date of Interest').param("Hour:").setValue(int(forward_date.strftime("%H")))
        
    def backward(self):
        current_index = self.current_index
        current_date = self.current_date
        backward = current_index - 1
        backward_date = current_date - timedelta(hours=1)
        #=============================================
        #retrieve the solar data from the date index
        #=============================================
        solar_dir = self.solar_dir
        solar_mesh = self.colour_meshes
        stg_func.retrieve_solar_data(solar_mesh[0], backward, solar_dir, self.min_val, self.max_val)
        #=============================================
        #retrieve the travel data
        #=============================================
        path_lines = self.path_lines 
        extrude_meshes = self.extrude_meshes
        extrude_lines = self.extrude_lines 
        
        travel_dir = self.travel_dir
        mesh_vis, bdry_vis, path_vis = stg_func.retrieve_travel_data(backward, travel_dir, extrude_meshes, extrude_lines, path_lines, self.view3d)
        
        if mesh_vis !=None:
            stg_func.viz_graphic_items([mesh_vis], self.view3d)
            stg_func.viz_graphic_items([bdry_vis], self.view3d)
            
        if path_vis !=None:
            stg_func.viz_graphic_items([path_vis], self.view3d)
            
        self.path_lines = [path_vis]
        self.extrude_meshes = [mesh_vis]
        self.extrude_lines = [bdry_vis]
        
        hrly_cart_bool = self.params.param('Layers').param('Extrusion Layer').param("Hourly Cart Travel Behaviour").value()
        stg_func.set_graphic_items_visibility(self.path_lines, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(self.extrude_meshes, hrly_cart_bool)
        stg_func.set_graphic_items_visibility(self.extrude_lines , hrly_cart_bool)
        
        #=============================================
        #retrieve the parking data
        #=============================================
        parking_meshes = self.parking_meshes
        parking_dir = self.parking_dir
        parking_mesh = stg_func.retrieve_parking_data(backward, parking_dir, parking_meshes, self.view3d, self.min_val, self.max_val)
        if parking_mesh != None:
            stg_func.viz_graphic_items([parking_mesh], self.view3d)
        
        self.parking_meshes = [parking_mesh]
        
        if self.is_parking_layer:
            hrly_park_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Parking Spots").value()
            stg_func.set_graphic_items_visibility(self.parking_meshes, hrly_park_bool)
        
        #=============================================
        #update the dates
        #=============================================
        self.current_index = backward
        self.current_date = backward_date
        str_date = backward_date.strftime("%Y-%m-%d %H:%M:%S")
        self.params.param('Load Result').param('Data Loaded').setValue(str_date)
        self.params.param('Load Result').param('Date of Interest').param("Year:").setValue(int(backward_date.strftime("%Y")))
        self.params.param('Load Result').param('Date of Interest').param("Month:").setValue(int(backward_date.strftime("%m")))
        self.params.param('Load Result').param('Date of Interest').param("Day:").setValue(int(backward_date.strftime("%d")))
        self.params.param('Load Result').param('Date of Interest').param("Hour:").setValue(int(backward_date.strftime("%H")))
    
    def load_data_range(self):
        #get the start date
        s_year = self.params.param('Date Range').param('Start Date').param("Year:").value()
        s_mth = self.params.param('Date Range').param('Start Date').param("Month:").value()
        s_day = self.params.param('Date Range').param('Start Date').param("Day:").value()
        s_hour = self.params.param('Date Range').param('Start Date').param("Hour:").value()
        s_min = 0
        s_sec = 0
        str_sp_date = str(s_year) + "-" + str(s_mth) + "-" + str(s_day) + "-" +\
                        str(s_hour) + ":" + str(s_min) + ":" + str(s_sec)
                                
        #get the end date
        e_year = self.params.param('Date Range').param('End Date').param("Year:").value()
        e_mth = self.params.param('Date Range').param('End Date').param("Month:").value()
        e_day = self.params.param('Date Range').param('End Date').param("Day:").value()
        e_hour = self.params.param('Date Range').param('End Date').param("Hour:").value()
        e_min = 0
        e_sec = 0
        str_e_date = str(e_year) + "-" + str(e_mth) + "-" + str(e_day) + "-" +\
                        str(e_hour) + ":" + str(e_min) + ":" + str(e_sec)
        
        self.str_start_date = str_sp_date
        self.str_end_date = str_e_date
        
        self.params.param('Date Range').param('Data Range Loaded').setValue(str_sp_date + " to " + str_e_date)
    
    def play_data(self):
        str_start_date = self.str_start_date
        str_end_date = self.str_end_date
        current_path = os.path.dirname(__file__)
        ani_file = os.path.join(current_path, "stg_animation.py")
        
        terrain_bool = self.params.param('Layers').param('Static Layer').param("Terrain").value()
        building_bool = self.params.param('Layers').param('Static Layer').param("Buildings").value()
        tree_bool = self.params.param('Layers').param('Static Layer').param("Trees").value()
        road_bool = self.params.param('Layers').param('Static Layer').param("Roads").value()
        
        #get all the settings for dynamic layers
        hrly_solar_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Grd Solar Irradiation").value()
        hrly_cart_bool = self.params.param('Layers').param('Extrusion Layer').param("Hourly Cart Travel Behaviour").value()
        
        #get all the visible layers
        layer_list = []
        
        if terrain_bool:
            layer_list.append("terrains")
        
        if tree_bool:
            layer_list.append("trees")
        
        if road_bool:
            layer_list.append("roads")
        
        if building_bool:
            layer_list.append("buildings")
        
        if hrly_solar_bool:
            layer_list.append("irradiations")
            
        if hrly_cart_bool:
            layer_list.append("travels")
            
        if self.is_parking_layer:
            hrly_park_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Parking Spots").value()
            if hrly_park_bool:
                layer_list.append("parkings")
            
        call_list = ["python", ani_file, str_start_date, str_end_date, str(self.min_val), str(self.max_val)]
        for lay in layer_list:
            call_list.append(lay)
            
        call_list.append(self.data_dir)
        call_list.append(self.midpt_str)
        subprocess.Popen(call_list)
        
    def change_min_max(self):
        solar_dir = self.solar_dir
        self.min_val = self.params2.param('Min Max').param('Min Value').value()
        self.max_val = self.params2.param('Min Max').param('Max Value').value()
        
        #change the falsecolour bar first 
        param2 = self.params2
        stg_func.edit_falsecolour(param2, self.min_val, self.max_val)
        
        #then change the colours on the model
        hour_index = self.current_index 
        solar_mesh = self.colour_meshes
        stg_func.retrieve_solar_data(solar_mesh[0], hour_index, solar_dir, self.min_val, self.max_val)
        
        parking_meshes = self.parking_meshes
        parking_dir = self.parking_dir
        parking_mesh = stg_func.retrieve_parking_data(hour_index, parking_dir, parking_meshes, self.view3d, self.min_val, self.max_val)
        if parking_mesh != None:
            stg_func.viz_graphic_items([parking_mesh], self.view3d)
        
        self.parking_meshes = [parking_mesh]
        
        if self.is_parking_layer:
            hrly_park_bool = self.params.param('Layers').param('Falsecolour Layer').param("Hourly Parking Spots").value()
            stg_func.set_graphic_items_visibility(self.parking_meshes, hrly_park_bool)