bl_info = {
    "name": "Alignment Profile Viewer",
    "author": "Brice",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Alignment Viewer Tab",
    "description": "Graphs alignment profiles.",
    "category": "BIM",
}

import bpy
import os
import sys
import site
import tempfile
import subprocess
import importlib

# Fix Python path
if sys.platform == "win32":
    site_packages_path = os.path.expanduser('~') + "/AppData/Roaming/Python/Python311/site-packages"
elif sys.platform == "darwin":
    site_packages_path = os.path.expanduser('~') + "/Library/Python/3.11/lib/python/site-packages"
else:  # Linux and other Unix-like
    site_packages_path = os.path.expanduser('~') + "/.local/lib/python3.11/site-packages"
if site_packages_path not in sys.path:
    sys.path.append(site_packages_path)

def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        python_executable = sys.executable
        subprocess.check_call([python_executable, "-m", "ensurepip"])
        subprocess.check_call([python_executable, "-m", "pip", "install", package, "--user"])
    finally:
        globals()[package] = importlib.import_module(package)

# Install missing packages
install_and_import('matplotlib')


import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.alignment
import bonsai.tool as tool

# Add this after the imports section
def register_properties():
    pass

def unregister_properties():
    pass

# --- Utility Functions ---

def get_selected_ifc_class():
    
    obj = bpy.context.active_object
    if obj is None:
        return None
    ifc_model = tool.Ifc.get()
    ifc_class=None
    if ifc_model is None:
        print("No IFC file loaded.")
        return None
    else: 
        print('found model ')

    if ifc_model:
        if hasattr(obj, "BIMObjectProperties") and obj.BIMObjectProperties.ifc_definition_id:
            ifc_id = int(obj.BIMObjectProperties.ifc_definition_id)
            print(f"Found BIMObjectProperties id: {ifc_id}")
            ifc_entity = ifc_model.by_id(ifc_id)
            if ifc_entity:
                print(f"IFC Class: {ifc_entity.is_a()}")
                return(ifc_entity.is_a())
        elif "ifc_definition_id" in obj:
            ifc_id = int(obj["ifc_definition_id"])
            print(f"Found custom property id: {ifc_id}")
            ifc_entity = ifc_model.by_id(ifc_id)
            if ifc_entity:
                print(f"IFC Class: {ifc_entity.is_a()}")
                
        else:
            print("No IFC linkage found.")
    else:
        print("No IFC file loaded.")

    
    return None

def load_image_in_blender(name,png_path):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.load(png_path)
    img.name = name

    for area in bpy.context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            area.spaces.active.image = img
            break
    else:
        print("No IMAGE_EDITOR open.")




# --- Blender Operator ---

class IFC_OT_AlignmentGraph(bpy.types.Operator):
    bl_idname = "ifc.generate_profile"
    bl_label = "Generate Profile"
    bl_description = "Generate vertical profile"

    def execute(self, context):
        ifc_class = get_selected_ifc_class()
        if not ifc_class:
            self.report({'ERROR'}, "No IFC class found for selected object.")
            return {'CANCELLED'}

        ifc_entity = tool.Ifc.get().by_id(int(bpy.context.active_object.BIMObjectProperties.ifc_definition_id))
        if not ifc_entity.is_a("IfcAlignment"):
            self.report({'ERROR'},"Selected object must be an IfcAlignment")
            return {'CANCELLED'}
        
        file = tool.Ifc.get()
        curve = ifcopenshell.api.alignment.get_curve(ifc_entity)
        start_station = ifcopenshell.api.alignment.get_alignment_start_station(file,ifc_entity)

        def station_formatter(x,pos):
            return ifcopenshell.util.alignment.station_as_string(file,x+start_station)

        def plot_profile(file,curve):
            unit_scale = ifcopenshell.util.unit.calculate_unit_scale(file)
            settings = ifcopenshell.geom.settings()
            gradient_fn = ifcopenshell.ifcopenshell_wrapper.map_shape(settings,curve.wrapped_data)
            vertical = gradient_fn.get_vertical()
            evaluator = ifcopenshell.ifcopenshell_wrapper.function_item_evaluator(settings,vertical)
            distances = evaluator.evaluation_points()
            d = []
            z = []
            for s in distances:
                p = evaluator.evaluate(s)
                d.append(s/unit_scale)
                z.append(p[1][3]/unit_scale)
            
            fig,ax = plt.subplots()
            ax.plot(d,z)
            ax.set_title("Profile",fontsize=12)
            fig.suptitle(f"Alignment: {ifc_entity.Name}",fontsize=16)
            
            
            ax.xaxis.set_major_formatter(FuncFormatter(station_formatter))
            ax.tick_params(axis='x',labelrotation=90)
            ax.set_ylabel("Elevation")
            ax.grid(True)
            ax.set_box_aspect(0.25)

            script_dir = os.path.dirname(os.path.realpath(__file__))
            png_path = os.path.join(script_dir, "profile.png")
            plt.savefig(png_path)
            load_image_in_blender("Profile",png_path)

        def plot_cant(file,curve):
            unit_scale = ifcopenshell.util.unit.calculate_unit_scale(file)
            settings = ifcopenshell.geom.settings()
            cant_fn = ifcopenshell.ifcopenshell_wrapper.map_shape(settings,curve.wrapped_data)
            cant = cant_fn.get_cant()
            evaluator = ifcopenshell.ifcopenshell_wrapper.function_item_evaluator(settings,cant)
            distances = evaluator.evaluation_points()
            d = []
            z = []
            for s in distances:
                p = evaluator.evaluate(s)
                d.append(s/unit_scale)
                z.append(p[1][3]/unit_scale)
            
            fig,ax = plt.subplots()
            ax.plot(d,z)
            ax.set_title("Cant",fontsize=12)
            fig.suptitle(f"Alignment: {ifc_entity.Name}",fontsize=16)
            
            
            ax.xaxis.set_major_formatter(FuncFormatter(station_formatter))
            ax.tick_params(axis='x',labelrotation=90)
            ax.set_ylabel("Deviating Elevation")
            ax.grid(True)
            ax.set_box_aspect(0.25)

            script_dir = os.path.dirname(os.path.realpath(__file__))
            png_path = os.path.join(script_dir, "cant.png")
            plt.savefig(png_path)
            load_image_in_blender("Cant",png_path)


        if curve.is_a("IfcSegmentedReferenceCurve"):
            plot_cant(file,curve)
            plot_profile(file,curve.BaseCurve)
        elif curve.is_a("IfcGradientCurve"):
            plot_profile(file,curve)


        self.report({'INFO'}, f"Profile for {ifc_class}")
        return {'FINISHED'}

# --- Blender Panel ---

class IFC_PT_AlignmentPanel(bpy.types.Panel):
    bl_label = "Alignment Profile Viewer"
    bl_idname = "IFC_PT_alignment_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Alignment Profile Viewer'

    def draw(self, context):
        layout = self.layout
        
        # Class hierarchy section
        box = layout.box()
        box.label(text="Vertical Profile")
        box.operator("ifc.generate_profile", text="Graph Profile")

# --- Registration ---

classes = [
    IFC_OT_AlignmentGraph,  
    IFC_PT_AlignmentPanel,
]

def register():
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_properties()

if __name__ == "__main__":
    register()
