from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


import warnings
from pathlib import Path
from shutil import copyfile

from astropy.io import fits

from .iraf_functions import *

class EchelleReducer:
    '''
    Class for reducing a directory of calibration files and data into
    one output file.
    '''
    
    def __init__(self, directory='.'):
        '''
        Creates an instance of Echelle Reducer.

        Parameters
        -------
        directory: pathlib.Path or str
            Filepath pointing to the directory containing the .FITS
            files. Directory must contain biases, red and blue flats,
            ThAr images, and at least one target image for the reduce
            method to work
        '''
        self.directory = Path(directory)

    
    def reduce(self):
        '''
        Processes all of the images in the directory.

        Raises:
        -------
        MissingFileException:
            Raised when the directory lacks one of the needed filetypes
        '''
        self.check_files()

        for fits in self.directory.glob('*.fits'):
            update_header(fits, 'dispaxis', 1)

        # Remove cosmic rays
        for image in self.directory.glob('*.fits'):
            if 'bias' not in image.stem:
                output_name = image.name.replace('.fits', '.c.fits')
                cosmicrays(image.name, output_name)

        # Create the master bias file
        biaslist = self.directory.glob('bias*fits')
        zerocombine(biaslist, 'Zero.fits')

        # Bias correct, remove pad pixles, and trim
        for image in self.directory.glob('*.c.fits'):
            output_name = image.name.replace('.c.fits', '.pc.fits')
            badpix_loc=self.directory / 'processing_files/badpix.txt'
            ccdproc(image.name,
                    output_name,
                    'Zero.fits',
                    badpix_file=badpix_loc,
                    trimsec='[200:1850,1:2048]'
                    )
        
        # Remove cosmic rays again
        for image in self.directory.glob('*.fits'):
            if '.pc.' in image.name:
                output_name = image.name.replace('.pc', '.cpc')
                cosmicrays(image.name, output_name)

        # Create master flat
        redflats = self.directory.glob('redflat*.cpc.fits')
        blueflats = self.directory.glob('blueflat*.cpc.fits')

        flatcombine(redflats, 'redflat.fits')
        flatcombine(blueflats, 'blueflat.fits')

        average('redflat.fits', 'blueflat.fits', 'superflat.fits')

        # Magnify the superflat
        magnify_y('superflat.fits', 'superflatmag.fits')

        update_header('superflatmag.fits', 'CCDSEC', '[200:1850,1:8189]')
        
        # Extract spectra from superflat
        apall('superflatmag.fits', 'superflatmagr.fits', plot_output=False)
        
        # Normalize the superflat
        # print('sfit not implemented')
        warnings.warn(
        '''
        sfit is not implemented!
        Copying files to appropriate location to allow program to
        continue...
        '''
        )
        copyfile('superflatmagr.fits', 'normflat.fits')

        # Magnify each image in the directory that isn't a flat
        for image in self.directory.glob('.fits'):
            if 'flat' not in image.stem:
                output_name = image.name.replace('.cpc', '.mcpc')
                magnify_y(image.name, output_name)
                update_header(output_name, 'CCDSEC', '[200:1850,1:8189]')
        
        for image in self.directory.glob('ThAr'):
            output_name = image.name.replace('mcpc', 'rmcpc')
            apall(image.name, output_name, plot_output=False)
        
        for image in self.directory.glob('*.fits'):
            if 'ThAr' not in image.stem:
                noscat_name = output_name.replace('mcpc', 'noscat')
                copyfile(image.name, noscat_name)

                output_name = image.name.replace('mpcp', 'rmcpc')
                apall(image.name, output_name)

                os.delete(image.name)
        
        
        warnings.warn('apscat1 is not implemented!')
        warnings.warn('apscat2 is not implemented!')
        warnings.warn('apscatter is not implemented!')
        warnings.warn('ecreidentify is not implemented!')
        warnings.warn('refspectra is not implemented!')
        warnings.warn('dispcor is not implemented!')
        warnings.warn('setjd is not implemented!')

    def check_files():
        '''
        Examines the directory and counts the number of each type of
        file found:
            - Bias
            - Red Flat
            - Blue Flat
            - ThAr 
            - Target

        Returns
        -----
        True if there is at least one of each type of file is found

        Raises
        -------
        MissingFileException

        '''
        bias_num = 0
        redflat_num = 0
        blueflat_num = 0
        ThAr_num = 0
        target_num = 0
        for fits in self.directory.glob('*.fits'):
            if 'blueflat' in fits.stem:
                blueflat_num += 1
            if 'redflat' in fits.stem:
                redflat_num += 1
            if 'bias' in fits.stem:
                bias_num += 1
            if 'ThAr' in fits.stem:
                ThAr_num += 1
            else:
                target_num += 1
        
        if not bias_num:
            raise MissingFileException('Nothing found with *bias*.fits')
        if not redflat_num:
            raise MissingFileException('Nothing found with *blueflat*.fits')
        if not blueflat_num:
            raise MissingFileException('Nothing found with *redflat*.fits')
        if not ThAr_num:
            raise MissingFileException('Nothing found with *ThAr*.fits')
        if not target_num:
            raise MissingFileException('No non-calibration .fits found')

        return true


class MissingFileException(Exception):
    pass