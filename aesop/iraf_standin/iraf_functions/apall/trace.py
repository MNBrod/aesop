import numpy as np 
import pandas as pd

import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def gauss(x, *p):
    A, mu, sigma = p

    return A*np.exp(-(x-mu)**2/(2.*sigma**2))

def findSinglePeak(img, centerX, centerY, minusX, plusX, minusY, plusY,
                    plot=False):
    """
    Finds the center of an aperture by summing the region defined by 
    [minusX, minusY, plusX, plusY] around [centerX, centerY] across 
    rows, and fitting a Gaussian to those points
    
    Parameters
    ----------
    img: 2D array of int
        Image containing the apertures
    centerX: float
        X coordinate of the guessed center
    centerY: float
        Y coordinate of the guessed center
    minusX: float
        Distance below centerX to fit the Gaussian too
    plusX: float
        Distance above centerX to fit the Gaussian too
    minusY: float
        Left-most bound of the region to sum rows across
    plusY: float
        Right-most bound of the region to sum rows across
    
    Returns
    -------
    res : int
        Y coordinate of the center of the aperture
    """
    minY = int(centerY+minusY)

    maxY = int(centerY+plusY)
    
    minX = int(centerX+minusX)
    
    maxX = int(centerX+plusX)

    # Extract the region to fit over
    subImg = img[minY:maxY,minX:maxX]
    
    summed = np.sum(subImg, axis=1)

    # Set baseline to ~0 to remove need for y-offset parameter
    summed = summed - np.min(summed)

    # Fit the given data
    p0 = [4000., 0., 2.]
    
    coeff, var_matrix = curve_fit(gauss, np.arange(len(summed)), summed, p0=p0)
    
    size = maxY - minY
    
    x = np.linspace(0, size, 100)
    
    fit = gauss(x, *coeff)


    if (plot):
        
        fig, (ax1, ax2) = plt.subplots(1,2)
        
        ax1.imshow(subImg, cmap='gray',vmin=0,vmax=2000)
        
        ax1.scatter((maxX-minX)/2, (maxY-minY)/2, color='red')
        
        ax1.scatter((maxX-minX)/2, coeff[1], color='blue')
        
        ax2.axvline((maxY-minY)/2, color='red')
        
        ax2.axvline(coeff[1], color='blue')
        
        ax2.scatter(np.arange(len(summed)), summed, color='red')
        
        ax2.plot(x, fit, color='blue')
        
        fig.show()

    return centerY + minusY + coeff[1]

def traceAperture(img, apDb, nsum, step, nlost):
    """
    Traces an aperture across its entire length
    
    Parameters
    ----------
    img : 2D array of int
        Image containing the aperture
    apDb: dictionary
        Parameters from the IRAF-like database for a specific aperture
    nsum: int
        Number of pixles to sum across when finding each center
    step: int
        Distance between each fitted point along the aperture
    nlost: int
        Depreceated
    
    Returns
    -------
    resX: array of int
        X coodinates of all fitted points
    resY: array of int
        Y coordinates of all the fitted points
    """
    
    img_width = len(img[0])
    
    resX = np.array([])
    
    resY = np.array([])

    # Parameters for first point
    pY = apDb['high']['y']
    
    mY = apDb['low']['y']
    
    pX = nsum/2
    
    mX = -nsum/2

    # Find the first point
    X = apDb['center']['x']
    
    initY = apDb['center']['y']
    
    Y = findSinglePeak(img, X, initY, mX, pX, mY, pY)
    
    startY = Y

    # Add the first point
    resX = np.append(resX, X)
    
    resY = np.append(resY, Y)
    
    while X < img_width:
        
        X = X + step
        # Look for a peak at the next X value, with the previous Y value
        try:
            
            Y = findSinglePeak(img, X, Y, mX, pX, mY, pY)
            
            resX = np.append(resX, X)
            
            resY = np.append(resY, Y)
        
        except RuntimeError:
            
            # If the fit is lost, break stop fitting this aperture
            break
    
    Y = startY
    
    X = apDb['center']['x']
    
    while X > 0:
        
        X = X - step
        
        # Look for a peak at the next X value, with the previous Y value
        try:
            
            Y = findSinglePeak(img, X, Y, mX, pX, mY, pY)
            
            resX = np.append(resX, X)
            
            resY = np.append(resY, Y)
        
        except RuntimeError:
            
            break
    
    return resX, resY

def getPerpLine(x_0, y_0, slope, length = 10):
    """
    Gets a line perpendicular to a tangent line running through the
    given points with the given slope, with the given length

    Parameters
    -------
    x_0: int
        X coordinate of where the perpendicular line should intersect 
        the given tangent
    y_0: int
        Y coordinate of where the perpendicular line should intersect 
        the given tangent
    slope: float
        Slope of the tangent line that the output should be 
        perpendicular too
    length: int
        number of points that should define the output line
    
    Returns
    -------
    x_vals: array of int
        X values of the perpendicular line
    y_vals: array of int
        Y values of the perpendicular line
    """
    inv = -1 / slope

    theta = np.arctan(inv)

    x_length = np.cos(theta) * length
    
    x_vals = np.linspace(x_0 - (x_length/2), x_0 + (x_length/2), 20)
    
    y_vals = inv * (x_vals - x_0) + y_0
    
    return x_vals, y_vals

def getTangentLine(x_0, y_0, slope, length = 10):
    """
    Gets a line of the given legnth tangent to the point and slope given

    Parameters
    -------
    x_0: int
        X coordinate of the middle of the tangent line
    y_0: int
        Y coordinate of the middle of the tangent line
    slope: float
        Slope of the tangent line
    length: int
        number of points that should define the output line
    
    Returns
    -------
    x_vals: array of int
        X values of the tangent line
    y_vals: array of int
        Y values of the tangent line
    """

    x_vals = np.linspace(x_0 - (length/2), x_0 + (length/2), 100)
    
    y_vals = slope * (x_vals - x_0) + y_0
    
    return x_vals, y_vals