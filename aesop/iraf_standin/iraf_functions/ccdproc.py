from astropy.nddata import CCDData
import ccdproc

__all__ = ['ccdproc']

def ccdproc(input, output, zero_file, badpix_file, trimsec):
    '''
    Emulates the IRAF command ccdproc by trimming the input image to the given
    size, subtracting a bias image, and removing bad pixels

    Parameters
    -------
    input: pathlib.Path or str
        Filepath to the input .FITS file
    output: pathlib.Path or str
        Filepath to the output .FITS file
    zero_file: pathlib.Path or str
        Filepath to the bias image to be subtracted
    badpix_file: pathlib.Path or str
        Filepath to the file defining the bad pixel regions
    trimsec: str
        IRAF formatted subarray used to define the size of of the output
    '''
    input = CCDData.read(input, unit=u.dimensionless_unscaled)
    
    zero = CCDData.read(zero_file, unit=u.dimensionless_unscaled)
    
    f = open(badpix_file, "r")
    
    for region in f:
    
        output = remove_bad_region(input, region)
    
    output = ccdproc.subtract_bias(output, zero)
    
    output = ccdproc.trim_image(output, fits_section=trimsec)
    
    output.write(output)


def remove_bad_region(image, region):
    '''
    Takes an input image, removes a specified region, and replaces each
    pixel with a linear interpolation from the edges

    Parameters
    -------
    image: 2D array of int
        Image to have pixels removed from
    region: str
        Region to be removed, in the format x_min x_max y_min y_max
    
    Returns
    -------
    image: 2D array of int
        Input image with bad pixels removed
    '''
    
    start_col = region.split()[0]
    
    end_col = region.split()[1]
    
    start_row = region.split()[2]
    
    end_row = region.split()[3]

    cols = np.arange(start_col, end_col+1)
    
    rows = np.arange(start_row, end_row+1)
    
    for row in rows:
    
        left_edge = image[row, cols[0]-1]
    
        right_edge = image[row, cols[-1] + 1]
    
        slope = (right_edge - left_edge) / len(cols)
    
        def func(x): 
    
            return (slope * x) + left_edge
    
        for col in cols:

            image[row, col] = func(col)
    
    return image