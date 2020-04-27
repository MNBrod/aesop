from astropy.nddata import CCDData
import ccdproc

__all__ = ['cosmicrays']

def cosmicrays(input_name, output_name, npasses=20):
    '''
    Removes cosmic rays from the input .FITS file using a medianing
    method

    Parameters
    -------
    input_name: pathlib.Path or str
        Filepath to the .FITS file with cosmic rays to be removed
    output_name: pathlib.Path or str
        Filepath to where the output should be saved
    '''
    input = CCDData.read(input, unit=u.dimensionless_unscaled)
    
    for i in range(npasses):
    
        output = ccdproc.cosmicray_median(input, mbox=5, rbox=5)
    
    output.write(output_name)
    
    return output