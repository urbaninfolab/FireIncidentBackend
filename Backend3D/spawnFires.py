import asyncio
import datetime
import os
import shutil
from time import sleep

import requests
import bpy
import json

def console_get():
    for area in bpy.context.screen.areas:
        if area.type == 'CONSOLE':
            for space in area.spaces:
                if space.type == 'CONSOLE':
                    return area, space
    return None, None


def console_write(text):
    area, space = console_get()
    if space is None:
        return

    context = bpy.context.copy()
    context.update(dict(
        space=space,
        area=area,
    ))
    for line in text.split("\n"):
        bpy.ops.console.scrollback_append(context, text=line, type='OUTPUT')


# Get today's firemap from the server, with todays date in YYYY-MM-DD format
req = requests.get('http://smartcity.tacc.utexas.edu/data/' + str(datetime.date.today()) + '-FireMap.json')
req = req.json()

fires = {}

fires = req["rss"]["channel"]["item"]

# Testing
fires = []
fires.append({"title": "Test", "link": "http://maps.google.com/maps?q=30.286217,-97.741576"})

print("Fires: " + str(len(fires)))

# Global offsets, unique to each city. For Austin, this is UT Tower.
# (offsets because Blender does not support long number formats)
crsx = -10880302.0
crsy = 3540300.5
                                
for fire in fires:

    print(fire["title"])
    print(fire["link"])
    link = fire["link"]
    link = link.replace("http://maps.google.com/maps?q=","").split(",")
    lat = float(link[0])
    lon = float(link[1])

    print("https://epsg.io/srs/transform/" + str(lon) + "," + str(lat) + ".json?key=default&s_srs=4326&t_srs=3857")
    # get XY from EPSG
    request = requests.get("https://epsg.io/srs/transform/" + str(lon) + "," + str(lat) + ".json?key=default&s_srs=4326&t_srs=3857")
    json = request.json()["results"][0]
    print(json)
    x = json["x"]
    y = json["y"]
    print("X = " + str(x) + " Y = " + str(y))
    

    # Get relative location to CRS
    x = x - crsx
    y = y - crsy

    print(str(x) + " " + str(y))
    

    # Add cube, named "Cube"
    bpy.ops.mesh.primitive_cube_add(location=(x, y, 0))
    bpy.context.object.name = "Cube"

    # set fluid settings using Blender 3.0 API
    fluid = bpy.context.object.modifiers.new(name="Fluid", type='FLUID')
    fluid.fluid_type = 'DOMAIN'
    fluid.domain_settings.resolution_max = 64
    fluid.domain_settings.simulation_method = 'FLIP'
    fluid.domain_settings.use_speed_vectors = True

    # Get local path of Blender file
    path = os.path.dirname(bpy.data.filepath)

    # Cache settings
    direct = path + fluid.domain_settings.cache_directory.replace("//", "\\")

    # Get the cache directory
    print(direct)

    # set the frame start and end
    fluid.domain_settings.cache_frame_start = 1
    fluid.domain_settings.cache_frame_end = 230
    # set the cache type
    fluid.domain_settings.cache_type = 'MODULAR'
    # set the cache file format
    fluid.domain_settings.cache_data_format = 'OPENVDB'

    
    # scale cube to 10x10x10
    bpy.ops.transform.resize(value=(500, 500, 300))

    # Add UV sphere, named "Sphere"
    bpy.ops.mesh.primitive_uv_sphere_add(location=(x, y, 0))
    bpy.context.object.name = "Sphere"

    # add fluid modifier to sphere
    fluid1 = bpy.context.object.modifiers.new(name="Fluid", type='FLUID')
    fluid1.fluid_type = 'FLOW'
    fluid1.flow_settings.flow_type = 'BOTH'
    fluid1.flow_settings.flow_behavior = 'INFLOW'


    # bake fluid simulation of specific fluid object   
    highpolyname = "Cube"
    bpy.data.objects[highpolyname].hide_set(False)
    bpy.data.objects[highpolyname].hide_render = False
    bpy.data.objects[highpolyname].select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[highpolyname]
    bpy.data.objects[highpolyname].select_set(True)
    
    # Bake fluid
    bpy.ops.fluid.bake_all()


    bpy.data.objects[highpolyname].hide_render = True
    bpy.data.objects[highpolyname].hide_set(True)


    # Add Volume object, named "Volume"
    bpy.ops.object.volume_add(location=(0, 0, 0))
    bpy.context.object.name = "Cache"

    # set the OpenVDB cache file
    bpy.context.object.data.filepath = direct + "//data//fluid_data_0001.vdb".replace("//", "\\")
    print(bpy.context.object.data.filepath)

    # print attributes of the volume object
    attr = dir(bpy.context.object.data)

    bpy.context.object.data.is_sequence = True

    # set the frame start and end
    bpy.context.object.data.frame_start = 1

    # set number of frames
    bpy.context.object.data.frame_duration = 250



    # spawn new cube called "volume2mesh"
    bpy.ops.mesh.primitive_cube_add(location=(x, y, 0))
    bpy.context.object.name = "volume2mesh"

    # add volume to mesh modifier to cube
    vol2mesh = bpy.context.object.modifiers.new(name="VolumeToMesh", type='VOLUME_TO_MESH')

    # set volume to mesh settings
    vol2mesh.voxel_size = 0.5

    # lower the threshold to 0.001 to get a more detailed mesh
    vol2mesh.threshold = 0.001

    # make volume to mesh target the fluid domain
    vol2mesh.object = bpy.data.objects["Cache"]

    # export at frame 100, as an .obj file

    print(dir(bpy.context.scene))

    bpy.context.scene.frame_current = 75
    bpy.ops.export_scene.fbx(filepath="generated/" + str(lat) + "," + str(lon) + ".fbx", axis_forward='-Z', axis_up='Y', object_types={'MESH'}, use_selection=True)

    bpy.context.scene.frame_current = 150
    bpy.ops.export_scene.fbx(filepath="generated/" + str(lat) + "," + str(lon) + ".fbx2", axis_forward='-Z', axis_up='Y', object_types={'MESH'}, use_selection=True)


    bpy.context.scene.frame_current = 225
    bpy.ops.export_scene.fbx(filepath="generated/" + str(lat) + "," + str(lon) + ".fbx3", axis_forward='-Z', axis_up='Y', object_types={'MESH'}, use_selection=True)

    # clear RAM, directory, and cache
    #bpy.ops.wm.read_homefile(use_empty=True)
    #shutil.rmtree(direct)
    #bpy.ops.ptcache.free_bake_all()
    


print("Done!")


    




