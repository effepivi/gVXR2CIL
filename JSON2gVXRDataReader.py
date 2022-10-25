import json # Load the JSON file
import os
import numpy as np

from cil.io import TIFFStackReader
from cil.framework import AcquisitionGeometry, AcquisitionData

from gvxrPython3 import gvxr


class JSON2gVXRDataReader: 

    def __init__(self, file_name):
        self.file_name = file_name
        
    def read(self):
        
        # Load the JSON file
        with open(self.file_name) as f:
            gVXR_params = json.load(f)
        
        # Get the absolute path of the JSON file
        cmd = os.path.abspath(self.file_name)

        # Get the path where the projections are
        projection_path = gVXR_params["Scan"]["OutFolder"]

        # Is an absolute path?
        if projection_path[0] == "/":
            TIFF_file_name = projection_path
        
        # It is a relative path
        else:
            # Get the absolute path of the JSON file
            file_abs_path = os.path.abspath(self.file_name)
            file_path = os.path.dirname(file_abs_path)
            TIFF_file_name = file_path + "/" + projection_path
        
        # Get the source position in mm
        temp = gVXR_params["Source"]["Position"]
        source_position_mm = np.array([
            -temp[0] * gvxr.getUnitOfLength(temp[3]) / gvxr.getUnitOfLength("mm"),
            -temp[1] * gvxr.getUnitOfLength(temp[3]) / gvxr.getUnitOfLength("mm"),
            -temp[2] * gvxr.getUnitOfLength(temp[3]) / gvxr.getUnitOfLength("mm")
        ])

        # Get the detector position in mm
        temp = gVXR_params["Detector"]["Position"]
        detector_position_mm = np.array([
            -temp[0] * gvxr.getUnitOfLength(temp[3]) / gvxr.getUnitOfLength("mm"),
            -temp[1] * gvxr.getUnitOfLength(temp[3]) / gvxr.getUnitOfLength("mm"),
            -temp[2] * gvxr.getUnitOfLength(temp[3]) / gvxr.getUnitOfLength("mm")
        ])
        
        # Compute the ray direction
        ray_direction = (detector_position_mm - source_position_mm)
        ray_direction /= np.linalg.norm(ray_direction)
        
        # Get the shape of the beam (parallel vs cone beam)
        source_shape = gVXR_params["Source"]["Shape"]
        
        # Is it a parallel beam
        use_parallel_beam = False
        if type(source_shape) == str:
            if source_shape.upper() == "PARALLELBEAM" or source_shape.upper() == "PARALLEL":
                use_parallel_beam = True

        # Get the pixel spacing in mm
        detector_number_of_pixels = gVXR_params["Detector"]["NumberOfPixels"]
        if "Spacing" in gVXR_params["Detector"].keys() == list and "Size" in gVXR_params["Detector"].keys():
            raise ValueError("Cannot use both 'Spacing' and 'Size' for the detector")

        if "Spacing" in gVXR_params["Detector"].keys():
            temp = gVXR_params["Detector"]["Spacing"]
            pixel_spacing_mm = [
                temp[0] * gvxr.getUnitOfLength(temp[2]) / gvxr.getUnitOfLength("mm"),
                temp[1] * gvxr.getUnitOfLength(temp[2]) / gvxr.getUnitOfLength("mm")
             ]

        elif "Size" in gVXR_params["Detector"].keys():
            detector_size = gVXR_params["Detector"]["Size"];
            pixel_spacing_mm = [
                (detector_size[0] / detector_number_of_pixels[0]) * gvxr.getUnitOfLength(detector_size[2]) / gvxr.getUnitOfLength("mm"),
                (detector_size[0] / detector_number_of_pixels[0]) * gvxr.getUnitOfLength(detector_size[2]) / gvxr.getUnitOfLength("mm")
            ]
        else:
            raise ValueError("'Spacing' and 'Size' were not defined for the detector, we canno determined the pixel spacing")

        # Get the angles
        include_final_angle = False
        if "IncludeFinalAngle" in gVXR_params["Scan"]:
            include_final_angle = gVXR_params["Scan"]["IncludeFinalAngle"]

        angle_set = np.linspace(
            0, 
            gVXR_params["Scan"]["FinalAngle"], 
            gVXR_params["Scan"]["NumberOfProjections"], 
            include_final_angle
        )
        
        # Get the roation parameters
        rotation_axis_direction = gVXR_params["Detector"]["UpVector"]
        rotation_axis_position = gVXR_params["Scan"]["CenterOfRotation"]
        
        # Parallel beam
        if use_parallel_beam:
            acquisition_geometry = AcquisitionGeometry.create_Parallel3D(ray_direction,
                detector_position_mm,
                rotation_axis_position=rotation_axis_position,
                rotation_axis_direction=rotation_axis_direction)
            print(ray_direction)
            print(detector_position_mm)
            print(rotation_axis_position)
            print(rotation_axis_direction)
        # It is cone beam
        else:
            acquisition_geometry = AcquisitionGeometry.create_Cone3D(source_position_mm,
                detector_position_mm,
                rotation_axis_position=rotation_axis_position,
                rotation_axis_direction=rotation_axis_direction)

        acquisition_geometry.set_angles(angle_set)
        acquisition_geometry.set_panel(detector_number_of_pixels, pixel_spacing_mm)
        acquisition_geometry.set_labels(['angle','vertical','horizontal'])  
        print(detector_number_of_pixels)
        print(pixel_spacing_mm)
        
        # Create the reader
        TIFF_reader = TIFFStackReader(file_name=TIFF_file_name)
        
        # Load the image data
        TIFF_data = TIFF_reader.read()

        data = AcquisitionData(TIFF_data, deep_copy=False, geometry=acquisition_geometry)
        
        return data