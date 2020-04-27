import os
import pickle
import importlib
from shutil import copyfile

from astropy.io import fits
import matplotlib.pyplot as plt 
import numpy as np

import database_utils as db_utils
import trace

__all__ = ['apall']

def generate_mask_from_background_sample(b_sample):
    """
    Generates a boolean mask as defined by a region

    Parameters
    -------
    b_sample: str
        Region to fit the mask over, in the format "low_min:low_max:high_min:high_max"
    
    Returns
    -------
    mask: array of bool
        A boolean mask with True values for the regions defined by each comma separated region
    """
    below, above = b_sample.split(",")
    
    below_low, below_high = [int(i) for i in below.split(":")]
    
    above_low, above_high = [int(i) for i in above.split(":")]
    
    diff = 0 - below_low
    
    below_low += diff
    
    below_high += diff
    
    above_low += diff
    
    above_high += diff
    
    mask = np.full((above_high - below_low) + 1, False)
    
    mask[:below_high+1] = True
    
    mask[above_low:] = True
    
    return mask

def fit_background(data, plot=False, b_sample="-22:-15,15:22"):
    """
    Generates a boolean mask as defined by a region

    Parameters
    -------
    b_sample: str
        Region to fit the mask over, in the format "low_min:low_max:high_min:high_max"
    
    Returns
    -------
    mask: array of bool
        A boolean mask with True values for the regions defined by each comma separated region
    """
    
    cheb = np.polynomial.chebyshev

    x_vals = np.arange(-22, 23)
    
    if plot:
    
        plt.figure()
    
        plt.plot(x_vals, data, color="blue")
    
    mask = generate_mask_from_background_sample(b_sample)
    
    y_background = data[mask]
    
    x_background = x_vals[mask]
    
    coeffs = cheb.chebfit(x_background, y_background, 2)
    
    data_index = 0
    
    result = np.array([])
    
    for i in x_vals:
    
        fit_val = cheb.chebval(i, coeffs)
    
        if plot:
    
            plt.scatter(i, data[data_index]-fit_val, color='red')
    
        result = np.append(result, (data[data_index] - fit_val))
    
        data_index += 1
    
    return result
    
def extract_summing_region(data, b_sample="-22:-15,15:22"):
    '''
    Extracts the values between the specified background regions in an input array

    Parameters
    -------
    data: array of int
        Line of pixels to extract from
    b_sample: str
        String representation of the background and region of interest
    
    Returns
    -------
    output: array of int
        The data contained in the region of interest
    '''
    mask = np.invert(generate_mask_from_background_sample(b_sample))
    
    return data[mask]

def isInBounds(image, x, y):
    '''
    Determines if a given coordinate is within the bounds of a 2D array

    Parameters
    -------
    image: 2d array of int
        Image to be checked against
    x: int
        X coordinate to check
    y: int
        Y coordinate to check

    Returns
    -------
    True if (x,y) is in bounds, False otherwise
    '''

    h = len(image)
    
    w = len(image[0])
    
    return x > 0 and x < w and y > 0 and y < h

def trace_apertures(bl, retrace=False):
    '''
    Finds and traces every aperture in an image based on the IRAF database
    template. If the file has already traced, the previous trace will be used
    unless otherwise specified

    Parameters
    -------
    bl: 2D array of int
        Image to trace
    retrace: bool
        If True, any existing traces will be ignored and then overwritten
    
    Returns
    -------
    db: List of dict
        List of all the apertures with the coordinates of several points along
        each aperture
    '''
    if (os.path.exists('./traceDB.pkl') and not retrace):
    
        f = open("traceDB.pkl", "rb" )
    
        db = pickle.load(f)
    
        f.close()
    
    else:
    
        db = db_utils.readIRAFDatabase('apech.db')

        for ap in db:

            apX, apY = trace.traceAperture(bl, ap, 10, 10, 3)

            ap['xTrace'] = apX

            ap['yTrace'] = apY

        f = open("traceDB.pkl", "wb")

        pickle.dump(db, f)

        f.close()

    return db

def fit_traces(db, plot_all_traces=False):
    '''
    Takes in a list of aperture traces and fits a 10th order legendre
    polynomial to each.

    Parameters
    -------
    db: list of dict
        database of the format returned by trace_aperture()
    plot_all_traces: bool
        If true, plot each fitted function
    
    Returns
    -------
    db: list of dict
        The input database with the coefficients of the legendre polynomial
        added to each aperture
    '''
    leg = np.polynomial.legendre

    for ap in db:

        if plot_all_traces:

            plt.scatter(ap['xTrace'], ap['yTrace'], s=1, color='purple')

        c, full = leg.legfit(ap['xTrace'],ap['yTrace'],10, full=True)

        ap['leg_coef'] = c

    return db

def generate_output(bl, db, plot_output = False):    
    '''
    Takes an image and an appropriate list of fitted apertures, and extracts
    a background subtracted output using those fits.

    Parameters
    -------
    bl: 2D array of int
        Image to extract the spectra from
    db: list of dict
        List that contains the legendre polynomial for each aperture
    plot_output: bool
        If true, plots the output
    
    Returns
    -------
    output: 2D array of int
        The extraced spectra
    '''
    leg = np.polynomial.legendre

    output = np.empty(( len(db), (len(bl[0])) ))

    for col_num in range(len(output[0])):

        for row_num in range(len(output)):

            if row_num < 4:

                continue

            coefs = db[row_num]['leg_coef']

            y = int(leg.legval(col_num, coefs))

            r = fit_background(bl[y-22:y+23, col_num], plot=False)

            data = extract_summing_region(r)

            output[row_num, col_num] = np.sum(data)

    if plot_output:

        plt.figure()

        plt.imshow(output, cmap='gray',vmin=np.min(output),vmax=np.max(output))

    return output

def apall(input_name, output_name, plot_input=False,plot_output=True):
    '''
    Takes in a raw echelle spectra and extracts a compressed output

    Parameters
    -------
    input_name: pathlib.Path, str
        Filepath pointing to the raw echelle spectra
    output_name: pathlib.Path or str
        Filepath pointing to where the output should be saved
    plot_input: bool
        If true, plot the input spectra
    plot_output: bool
        If true, plot the output
    
    Returns
    -------
    output:
        2D array of int storing the output of the spectral extraction
    '''
    copyfile(input_name, output_name)
    
    hdul = fits.open(input_name)
    
    img = hdul[0].data
    
    hdul.close()
    
    db = trace_apertures(img)
    
    db = fit_traces(db)
    
    output = generate_output(img, db, plot_output=plot_output)
    
    plt.show()
    
    if plot_input:
    
        plt.figure()
    
        plt.imshow(img, cmap='gray',vmin=1200,vmax=2000)
    
        plt.figure()
    
        plt.imshow(output, cmap='gray',vmin=1200,vmax=2000)
    
        plt.show()
    
    hdul = fits.open(output_name)
    
    hdul[0].data = output
    
    hdul.writeto(open(output_name, "wb"))
    
    hdul.close()

    return output
