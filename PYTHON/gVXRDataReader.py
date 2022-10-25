import os
import numpy as np

from cil.io import TIFFStackReader
from cil.framework import AcquisitionGeometry, AcquisitionData

from gvxrPython3 import gvxr


class gVXRDataReader: 

    def __init__(self, file_name, angle_set, rotation_axis_position=[0,0,0]):
        self.file_name = file_name
                
        if gvxr.getSourceShape() == "PARALLEL":
            self.use_parallel_beam = True
        else:
            self.use_parallel_beam = False
            
        self.angle_set = angle_set
        self.rotation_axis_position = rotation_axis_position
        
    def read(self):
        
        # Get the absolute path of the JSON file
        TIFF_file_name = os.path.abspath(self.file_name)
        
        # Get the source position in mm
        source_position_mm = -np.array(gvxr.getSourcePosition("mm"))

        # Get the detector position in mm
        detector_position_mm = -np.array(gvxr.getDetectorPosition("mm"))
        
        # Compute the ray direction
        ray_direction = (detector_position_mm - source_position_mm)
        ray_direction /= np.linalg.norm(ray_direction)
        
        # Get the pixel spacing in mm
        detector_number_of_pixels = np.array(gvxr.getDetectorNumberOfPixels())
        detector_size = gvxr.getDetectorSize("mm")
        pixel_spacing_mm = [
            detector_size[0] / detector_number_of_pixels[0],
            detector_size[0] / detector_number_of_pixels[0]
        ]
        
        # Parallel beam
        if self.use_parallel_beam:
            acquisition_geometry = AcquisitionGeometry.create_Parallel3D(ray_direction,
                detector_position_mm,
                rotation_axis_position=self.rotation_axis_position,
                rotation_axis_direction=np.array(gvxr.getDetectorUpVector()))
            
            print(ray_direction)
            print(detector_position_mm)
            print(self.rotation_axis_position)
            print(gvxr.getDetectorUpVector())
        # It is cone beam
        else:
            acquisition_geometry = AcquisitionGeometry.create_Cone3D(source_position_mm,
                detector_position_mm,
                rotation_axis_position=self.rotation_axis_position,
                rotation_axis_direction=np.array(gvxr.getDetectorUpVector()))

        acquisition_geometry.set_angles(self.angle_set)
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