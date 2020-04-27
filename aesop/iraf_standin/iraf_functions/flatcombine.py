from astropy import units as u
from astropy.nddata import CCDData
from ccdproc import Combiner

__all__ = ['flatcombine']

def flatcombine(filenames, output_name):
    '''
    Combines flat field images into one superflat using medians

    Parameters
    -------
    filenames: list of str or pathlib.Path
        Filepaths pointing to each of the flat files to be combined
    output_name: pathlib.Path or str
        Filepath pointing to location to save combined flat
    '''
    ccds = list(map(lambda x : CCDData.read(x, unit=u.dimensionless_unscaled), filenames))
    
    combiner = Combiner(ccds)
    
    combiner.sigma_clipping(low_thresh=3, high_thresh=3, func=np.ma.median)
    
    med = combiner.median_combine()
    
    med.write(output_name)
    
    return med