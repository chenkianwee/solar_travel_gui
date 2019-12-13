import os
import json
import datetime
import math
from dateutil.tz import gettz
from dateutil.parser import parse

import shapefile
from pyproj import Proj
from py4design import py3dmodel
import stg_function as stg_func

#========================================================================
#functions
#========================================================================
def normalise(val_list, minval, maxval):
    norm_list = []
    rangex = maxval-minval
    for v in val_list:
        norm = (v-minval)/float(rangex)
        norm_list.append(norm)
            
    return norm_list

def id_terrain(boundary_face, terrain_compound):
    shells = py3dmodel.fetch.topo_explorer(terrain_compound, "shell")
    id_list = []
    for shell in shells:    
        xmin,ymin,zmin, xmax,ymax,zmax = py3dmodel.calculate.get_bounding_box(shell)
        terrain_bdry = py3dmodel.construct.make_polygon([[xmin, ymin, 0], [xmax, ymin, 0], [xmax, ymax, 0], [xmin, ymax, 0]])
        common = py3dmodel.construct.boolean_common(boundary_face, terrain_bdry)
        is_null = py3dmodel.fetch.is_compound_null(common)
        if not is_null:
            id_list.append(shell)
    
    return id_list

def proj_pt_onto_terrains(pypt, terrain_list):
    proj_pt = pypt
    tcnt=0
    for terrain in terrain_list:
        xmin,ymin,zmin,xmax,ymax,zmax = py3dmodel.calculate.get_bounding_box(terrain)
        is_in = stg_func.is_pyptlist_in_bdry([pypt], [xmin, xmax], [ymin, ymax])
        if is_in:
            interpt, interface = py3dmodel.calculate.intersect_shape_with_ptdir(terrain, pypt, (0,0,1))
            if interpt:
                proj_pt = interpt
                break
        tcnt+=1
    return proj_pt
    
def construct_path_edges(pyptlist):
    print("***************** Create path geometry for the points*****************" )
    wire = py3dmodel.construct.make_wire(pyptlist)
    edges = py3dmodel.fetch.topo_explorer(wire, "edge")
    return edges, wire

def calc_duration(loc_dict_list):
    new_pt_list = []
    total_hour = 0
    cnt = 0
    for loc in loc_dict_list:
        if cnt != len(loc_dict_list)-1:
            pt_dict = {}
            pypt = loc["pypt"]
            date = parse(loc["date"])
            
            loc2 = loc_dict_list[cnt+1]
            pypt2 = loc2["pypt"]
            date2 = parse(loc2["date"])
            
            dist = py3dmodel.calculate.distance_between_2_pts(pypt, pypt2)
            td = date2-date
            hour = td.seconds/3600.0
            total_hour = total_hour + hour
            pt_dict["pypt"] = pypt2
            pt_dict["duration"] = hour
            pt_dict["dist2prev"] = dist
            pt_dict["date1"] = date
            pt_dict["date2"] = date2
            new_pt_list.append(pt_dict)
        cnt+=1
        
    return new_pt_list
        
def get_z_from_pts(pyptlist):
    maxz = -10000
    for pypt in pyptlist:
        z = pypt[2]
        if z > maxz:
            maxz = z
    return maxz
    
def construct_grids(pyptlist, xdim, ydim):
    if len(pyptlist) == 1:
        grid = py3dmodel.construct.make_rectangle(xdim, ydim)
        loc_pt = [pyptlist[0][0], pyptlist[0][1], 0]
        grid = py3dmodel.fetch.topo2topotype(py3dmodel.modify.move([0,0,0], loc_pt, grid))
        grids = [grid]
    else:
        verts = py3dmodel.construct.make_occvertex_list(pyptlist)
        cmpd = py3dmodel.construct.make_compound(verts)
        xmin, ymin, zmin, xmax, ymax, zmax = py3dmodel.calculate.get_bounding_box(cmpd)
        bdry_face = py3dmodel.construct.make_polygon([[xmin, ymin, 0], [xmax, ymin, 0], [xmax, ymax, 0], [xmin, ymax, 0]])
        area = py3dmodel.calculate.face_area(bdry_face)
        if area < xdim*ydim:
            grid = py3dmodel.construct.make_rectangle(xdim, ydim)
            centre_pt = py3dmodel.calculate.points_mean(pyptlist)
            centre_pt = [centre_pt[0], centre_pt[1], 0]
            grid = py3dmodel.fetch.topo2topotype(py3dmodel.modify.move([0,0,0], centre_pt, grid))
            grids = [grid]
        else:
            rangex = xmax-xmin
            xint = int(math.ceil(rangex/50.0))
            xmax = xint*50 + xmin
            
            rangey = ymax-ymin
            yint = int(math.ceil(rangey/50.0))
            ymax = yint*50 + ymin
            
            bdry_face2 = py3dmodel.construct.make_polygon([[xmin, ymin, 0], [xmax, ymin, 0], [xmax, ymax, 0], [xmin, ymax, 0]])
            grids = py3dmodel.construct.grid_face(bdry_face2, 50, 50)
    return grids

def calc_normalise_freq_extrude(duration_dict_list, grids, max_extrude=300):
    
    print("***************** Calculate the frequency of the points in the grid *****************")
    grid_freq_list = []
    for g in grids:
        grid_freq_list.append({"shape":g, "duration":0, "points":[]})
    
    for d in duration_dict_list:
        pypt = d["pypt"]
        for g in grid_freq_list:
            in_face = py3dmodel.calculate.point_in_face([pypt[0], pypt[1], 0], g["shape"])
            #py3dmodel.utility.visualise([[g["shape"]], ])
            if in_face:
                dur = g["duration"]
                new_dur = dur + d["duration"]
                g["duration"] = new_dur 
                g["points"].append(pypt)
                break
            
    new_gdict_list = []
    all_durs = []
    for gd in grid_freq_list:
        f = gd["duration"]
        if f !=0:
            all_durs.append(f)
            new_gdict_list.append(gd)
        
    print("***************** Normalise the frequency and extrude the grid *****************")
    extrude_list = []
    ccnt = 0
    for gd2 in new_gdict_list:
        grid = gd2["shape"]
        ptsingrid = gd2["points"]
        gridz = get_z_from_pts(ptsingrid)
        grid = py3dmodel.fetch.topo2topotype(py3dmodel.modify.move([0,0,0], [0,0,gridz], grid))
        gd2["shape"] = grid
        gd2["max_extrude"] = max_extrude
        norm_val = gd2["duration"]
        if norm_val !=0:
            extrude = py3dmodel.construct.extrude(grid, [0,0,1], norm_val*max_extrude)
            extrude_list.append(extrude)
        ccnt+=1
    
    extrude_cmpd = py3dmodel.construct.make_compound(extrude_list)
    
    return extrude_cmpd, new_gdict_list
      
def append_hour_index2dict_list(gdict_list, hour_index):
    for d in gdict_list:
        d["hour_index"] = hour_index
     
def write_poly_shpfile_with_dict(dict_list, shp_filepath):
    grid_list = []
    att_2dlist = []
    attname_list = ["hour_index", "norm_val"]
    for d in dict_list:
        grid = d["shape"]
#        mx_extrude = d["max_extrude"]
        norm_val = d["duration"]
        hour_index = d["hour_index"]
        grid_list.append(grid)
        atts = [hour_index, norm_val]
        att_2dlist.append(atts)
    
    write_poly_shpfile(grid_list, shp_filepath, attname_list, att_2dlist)
    
def write_poly_shpfile(occface_list, shp_filepath, attname_list, att_2dlist):
    w = shapefile.Writer(shp_filepath, shapeType = 5)
    for attname in attname_list:
        w.field(attname,'N', decimal=5)
         
    cnt=0
    for occface in occface_list:
        wires = py3dmodel.fetch.topo_explorer(occface, "wire")
        nwires = len(wires)
        atts = att_2dlist[cnt]
        if nwires > 1:
            nrml = py3dmodel.calculate.face_normal(occface)
            poly_shp_list = []
            for wire in wires:
                pyptlist = py3dmodel.fetch.points_frm_wire(wire)
                is_anticlockwise = py3dmodel.calculate.is_anticlockwise(pyptlist, nrml)
                is_anticlockwise2 = py3dmodel.calculate.is_anticlockwise(pyptlist, (0,0,1))
                if is_anticlockwise: #means its a face not a hole
                    if is_anticlockwise2:
                        pyptlist.reverse()
                else: #means its a hole not a face
                    if not is_anticlockwise2:
                        pyptlist.reverse()
                
                pyptlist2d = []
                for pypt in pyptlist:
                    x = pypt[0]
                    y = pypt[1]
                    pypt2d = [x,y]
                    pyptlist2d.append(pypt2d)
                poly_shp_list.append(pyptlist2d)
                
            w.record(atts[0], atts[1])
            w.poly(poly_shp_list)
                    
        else:
            pyptlist = py3dmodel.fetch.points_frm_occface(occface)
            is_anticlockwise = py3dmodel.calculate.is_anticlockwise(pyptlist, (0,0,1))
            if is_anticlockwise:
                pyptlist.reverse()
            pyptlist2d = []
            for pypt in pyptlist:
                x = pypt[0]
                y = pypt[1]
                pypt2d = [x,y]
                pyptlist2d.append(pypt2d)
                
            w.record(atts[0], atts[1])
            w.poly([pyptlist2d])
            
        cnt+=1
    w.close()
    
def write_polyline_shpfile(occwire_list, shp_filepath, attname_list, att_2dlist):
    w = shapefile.Writer(shp_filepath, shapeType = 3)
    for attname in attname_list:
        w.field(attname,'N', decimal=5)
    
    cnt=0
    for occwire in occwire_list:
        pyptlist = py3dmodel.fetch.points_frm_wire(occwire)
        flat_pyptlist = []
        for pypt in pyptlist:
            flat_pyptlist.append([pypt[0], pypt[1]])
            
        atts = att_2dlist[cnt]
        w.line([flat_pyptlist])            
        w.record(atts[0], atts[1])
    
        cnt+=1
    w.close()

#========================================================================
#main script
#========================================================================
def read_process_loc_json(location_filepath):
    print("*****************Reading the files*****************")
    #read the location file
    location_f = open(location_filepath , "r")
    #=====================================================================
    #CHANGE THE JSON DATA HERE WHEN CODING
    #=====================================================================
    json_data = json.load(location_f)
    #json_data = json_data[1100:1200]
    location_f.close()
    
    #setup the time
    timezone = gettz()
    start_date = parse('2019-01-01T00:00:00.0Z')
    start_date = start_date.replace(tzinfo=timezone)
    
    hourly_list = []
    for _ in range(8760):
        hourly_list.append({"locations":[]})
        
    #set up the projection
    p = Proj(proj='utm',zone=18,ellps='GRS80', preserve_units=False)

    #process the location points 
    print("***************** Processing location points*****************")
    date_str_list = []
    loc_pyptlist = []
    for loc in json_data:
        timestamp = int(loc["timestampMs"])/1000
        date = datetime.datetime.fromtimestamp(timestamp)  # using the local timezone
        date = date.replace(tzinfo=timezone)
        date_str = date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        td = date-start_date
        hour_index = td.total_seconds()/3600
        hour_index = int(math.floor(hour_index))
        hour_date = stg_func.index2date(hour_index)
        hour_date_str = hour_date.strftime("%Y-%m-%d %H:0:0")
        if hour_date_str not in date_str_list:
            date_str_list.append(hour_date_str)
        
        lon = float(loc["longitudeE7"])/10**7
        lat = float(loc["latitudeE7"])/10**7
        x,y = p(lon, lat)
        pypt = [x,y,0]
        loc["date"] = date_str
        loc["pypt"] = pypt    
        loc_pyptlist.append(pypt)
        
        hourly_list[hour_index]["locations"].append(loc)
        
    return hourly_list, loc_pyptlist, date_str_list

def id_terrains_with_loc_pts(terrain_filepath, loc_pyptlist):
    print("***************** Constructing the boundary based on the location points*****************")
    verts = py3dmodel.construct.make_occvertex_list(loc_pyptlist)
    cmpd = py3dmodel.construct.make_compound(verts)
    xmin, ymin, zmin, xmax, ymax, zmax = py3dmodel.calculate.get_bounding_box(cmpd)
    bdry_face = py3dmodel.construct.make_polygon([[xmin, ymin, 0], [xmax, ymin, 0], [xmax, ymax, 0], [xmin, ymax, 0]])
    
    print("***************** Id the terrains *****************")
    #get all the terrain shells
    terrain_cmpd = py3dmodel.utility.read_brep(terrain_filepath)
    id_terrain_list = id_terrain(bdry_face, terrain_cmpd)
    # print("NUMBER OF TERRAINS", len(id_terrain_list))
    return id_terrain_list

def process_hourly_loc(hour_index, locd, id_terrain_list, gdict_list, path_wire_list, path_att_2dlist, travel_dir):
    locs_list = locd["locations"]
    week_index = stg_func.id_week(hour_index)
    proj_pts = []
    print("LOC list", len(locs_list))
    #=================================================================
    #FIRST PROCESS THE LIST AND PROJECT THE POINTS 
    #=================================================================
    for loc in locs_list:
        pypt = loc["pypt"]
        proj_pt = proj_pt_onto_terrains(pypt, id_terrain_list)
        loc["pypt"] = proj_pt
        proj_pts.append(proj_pt)
    #=================================================================
    #CALCULATE THE DURATION AND EXTRUDE THE GRIDS
    #=================================================================
    proj_pts2 = py3dmodel.modify.rmv_duplicated_pts(proj_pts)
    grids = construct_grids(proj_pts2, 50,50)
    # py3dmodel.utility.visualise([grids], ["WHITE"])
    duration_dict_list = calc_duration(locs_list)
    ext_cmpd, gdicts = calc_normalise_freq_extrude(duration_dict_list, grids, max_extrude=300)
    
    append_hour_index2dict_list(gdicts, hour_index)
    gdict_list.extend(gdicts)

    # py3dmodel.utility.visualise([[ext_cmpd]],["GREEN"])
    ext_att_dict = {"hour_index":hour_index}
    
    #draw the path of the travelling
    nproj_pts = len(proj_pts2)
    
    if nproj_pts > 1:
        #print "proj list", nproj_pts
        path_edges, wire = construct_path_edges(proj_pts)
        path_wire_list.append(wire)
        
        wire_dist = py3dmodel.calculate.wirelength(wire)
        path_att_2dlist.append([hour_index, wire_dist])
        
        path_cmpd = py3dmodel.construct.make_compound(path_edges)
        path_att_dict = {"hour_index":hour_index, "dist": wire_dist}
        # py3dmodel.utility.visualise([[ext_cmpd], verts, [path_cmpd]], ["WHITE", "BLUE", "RED"])
        
        path_edges_json = os.path.join(travel_dir, "viz", "path_wk" + str(week_index) + ".json")
        edge_mesh_dict = stg_func.draw_edge(path_cmpd, att_dict = path_att_dict)
        stg_func.append2json(path_edges_json, edge_mesh_dict, hour_index)
    
    print("***************** Writing week" + str(week_index) + " hour " + str(hour_index) + " *****************")
    ext_json = os.path.join(travel_dir, "viz", "extrude_meshes_wk" + str(week_index) + ".json")
    ext_cmpd_null = py3dmodel.fetch.is_compound_null(ext_cmpd)
    if ext_cmpd_null:
        mesh_dict = {}
    else:
        mesh_dict = stg_func.topo2mesh_dict(ext_cmpd, att_dict = ext_att_dict)
    stg_func.append2json(ext_json, mesh_dict, hour_index)
                    
    ext_edges_json = os.path.join(travel_dir, "viz", "extrude_bdry_wk" + str(week_index) + ".json")
    if ext_cmpd_null:
        bdry_edge_mesh_dict = {}
    else:                    
        bdry_edge_mesh_dict = stg_func.draw_boundary_edge(ext_cmpd, att_dict = ext_att_dict)
        
    stg_func.append2json(ext_edges_json, bdry_edge_mesh_dict, hour_index)
    
    #write the location history file
    loc_json = os.path.join(travel_dir, "analysis", "locations_wk" + str(week_index) + ".json")
    stg_func.append2json(loc_json, locd, hour_index)
    
    #write the shp file 
    shp_filepath = os.path.join(travel_dir, "analysis", "extrusions_week" + str(week_index) + ".shp")
    write_poly_shpfile_with_dict(gdict_list, shp_filepath)
    
    path_shp_filepath = os.path.join(travel_dir, "analysis", "paths_week" + str(week_index)+ ".shp")
    path_att_name_list = ["hour_index", "dist"]
    write_polyline_shpfile(path_wire_list, path_shp_filepath, path_att_name_list, path_att_2dlist)
    print("***************** Wrote week" + str(week_index) + " hour " + str(hour_index) + " *****************")
    
if __name__ == '__main__':
    
    #========================================================================
    #filepaths
    #========================================================================
    #location_filepath = "F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\campus_as_a_lab\\data\\location\\ckw_json\\LocationHistory\\loc2019jan2sep.json"
    location_filepath = "F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\campus_as_a_lab\\data\\location\\ckw_json\\LocationHistory\\loc_sep.json"
    terrain_filepath = "F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\campus_as_a_lab\\data\\solar_travel_data\\context3d\\terrain.brep"
    travel_dir = "F:\\kianwee_work\\princeton\\2019_06_to_2019_12\\campus_as_a_lab\\data\\solar_travel_data\\travel"
    
    hourly_list, loc_pyptlist, date_str_list = read_process_loc_json(location_filepath)
    id_terrain_list = id_terrains_with_loc_pts(terrain_filepath, loc_pyptlist)
    
    path_att_2dlist = []
    path_wire_list = []    
    gdict_list = []
    ndates = len(date_str_list)
    
    progress_cnt = 0
    hcnt = 0
    for locd in hourly_list:    
        locs_list = locd["locations"]
        if locs_list:
            # if hcnt >= 6526:
            print(hcnt, "/8760")
            if 5832<= hcnt <= 5838:
                process_hourly_loc(hcnt, locd, id_terrain_list, gdict_list, path_wire_list, path_att_2dlist, travel_dir)
            progress_cnt+=1
        hcnt+=1
    print("DONE")