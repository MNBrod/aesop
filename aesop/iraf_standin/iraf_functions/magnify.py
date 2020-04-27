from scipy import ndimage
from astropy.io import fits
from shutil import copyfile

__all__ = ['magnify_y']

def magnify_y(input_name, output_name, mag=4):
    '''
    Magnifies an image in the y-direction by the given factor. Does NOT
    conserve flux.

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
    
    hdul[0].data = ndimage.zoom(image, (mag, 1), order=1,
        mode='nearest')
    
    hdul.writeto(open(output_name, "wb"))
    
    hdul.close()