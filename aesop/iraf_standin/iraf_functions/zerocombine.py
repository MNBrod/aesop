from astropy import units as u
from astropy.nddata import CCDData
from ccdproc import Combiner

__all__ = ['zerocombine']

def zerocombine(filenames, output_name):
    '''
    Combines zero/bias  images into one master file using an average

    Parameters
    -------
    filenames: list of str or pathlib.Path
        Filepaths pointing to each of the zero/bias files to be combined
    output_name: pathlib.Path or str
        Filepath pointing to location to save combined image
    '''
    
    ccds = list(map(lambda x : CCDData.read(x, unit=u.dimensionless_unscaled),
                                            filenames))
    
    combiner = Combiner(ccds)
    
    combiner.sigma_clipping(low_thresh=3, high_thresh=3, func=np.ma.median)
    
    med = combiner.average_combine()
    
    med.write(output_name)
    
    return med
    