from astropy import units as u
from astropy.nddata import CCDData
import ccdproc

__all__ = ['divide', 'average']

def divide(image1_name, image2_name, output_name):
    '''
    Divides one .FITS files by another, and saves the output

    Parameters
    -------
    image1_name: pathlib.Path or str
        Filepath to the first .FITS file
    image2_name: pathlib.Path or str
        Filepath to the second .FITS file
    output_name: pathlib.Path or str
        Filepath to where the output should be saved
    '''
    img1 = CCDData.read(image1_name, unit=u.dimensionless_unscaled)
    
    img2 = CCDData.read(image2_name, unit=u.dimensionless_unscaled)
    
    output = ccdproc.flat_correct(image1_name, image2_name)
    
    output.write(output_name)

def average(image1_name, image2_name, output_name):
    '''
    Averages two fits files together, and saves the output

    Parameters
    -------
    image1_name: pathlib.Path or str
        Filepath to the first .FITS file
    image2_name: pathlib.Path or str
        Filepath to the second .FITS file
    output_name: pathlib.Path or str
        Filepath to where the output should be saved
    '''
    img1 = CCDData.read(image1_name, unit=u.dimensionless_unscaled)
    
    img2 = CCDData.read(image2_name, unit=u.dimensionless_unscaled)
    
    combiner = Combiner([img1, img2])
    
    avg = combiner.average_combine()
    
    avg.write(output_name)