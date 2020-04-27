from astropy.io import fits

__all__ = ['update_header']

def update_header(file, key, value):
    '''
    Updates the given key-value pair in the given FITS file header.
    Overwrites any existing value associated with the key if it
    exists

    Parameters
    -------
    file: pathlib.Path, str
        filepath to the .FITS file to update
    key: str
        Key to update
    value: str
        value to associate with the given key
    '''
    hdul = fits.open(filename)
    
    header = hdul[0].header
    
    header[str(key)] = value
    
    hdul.close()