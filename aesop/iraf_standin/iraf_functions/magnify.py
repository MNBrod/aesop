from scipy import ndimage
from astropy.io import fits
from shutil import copyfile
import numpy as np
import matplotlib.pyplot as plt

__all__ = ['magnify_y']

def magnify_y(input_name, output_name, mag=4):
    '''
    Magnifies an image in the y-direction by the given factor.

    Implementes rough conservation of flux by scaling each image pizel
    by the ratio out input/output image area (e.g. magnifying by 4 will
    scale each pixel by .25)

    Parameters
    -------
    input_name: pathlib.Path or str
        Filepath pointing to the input .FITS files
    output_name: pathlib.Path or str
        Filepath pointing to where the output should be saved
    mag: int
        magnification factor 
    '''
    copyfile(input_name, output_name)
    
    hdul = fits.open(input_name)
    
    image = hdul[0].data

    # Trim image based on known detector size (ignore overscan region)
    image = image[0:2048,0:2048]

    magnified = ndimage.zoom(image, (mag, 1), order=1,
        mode='nearest')
    
    magnified = magnified // mag

    hdul[0].data = magnified

    hdul.writeto(open(output_name, "wb"))
    
    hdul.close()