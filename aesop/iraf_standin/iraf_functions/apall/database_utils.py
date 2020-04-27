__all__ = ['read_iraf_database']

def parseAperture(ap):

    """
    Parses a single entry in a apall-styled IRAF database into a
    dictionary of parameters
    
    Parameters
    ----------
    ap : str
        String representation of the database entry
    
    Returns
    -------
    res : dictionary
        Dictionary of all of the parameters contained in the daatbase,
        indexed over aperture number
    """

    lines = ap.splitlines()

    res = {}

    res['image'] = lines[2].split()[1]

    res['aperture'] = int(lines[3].split()[1])

    res['beam'] = int(lines[4].split()[1])

    res['center'] = {'x': float(lines[5].split()[1]),
                    'y' : float(lines[5].split()[2])}

    res['low'] = {'x': float(lines[6].split()[1]),
                    'y' : float(lines[6].split()[2])}
    
    res['high'] = {'x': float(lines[7].split()[1]),
                    'y' : float(lines[7].split()[2])}
    
    res['background'] = {
        'xmin' : float(lines[9].split()[1]),
        'xmax' : float(lines[10].split()[1]),
        'function' : lines[11].split()[1],
        'order' : float(lines[12].split()[1]),
        'sample' : lines[13].split()[1],
        'naverage' : float(lines[14].split()[1]),
        'niterate' : float(lines[15].split()[1]),
        'low_reject' : float(lines[16].split()[1]),
        'high_reject' : float(lines[17].split()[1]),
        'grow' : float(lines[18].split()[1]),
    }
    
    res['axis'] = int(lines[19].split()[1])
    
    res['curve'] = {"num" : float(lines[20].split()[1]), 
            "params" : [float(lines[21]),
            float(lines[22]),
            float(lines[23]),
            float(lines[24]),
            float(lines[25]),
            float(lines[26]),
            float(lines[27]),
            float(lines[28]),
            float(lines[29]),
            float(lines[30]),
            float(lines[31]),
            float(lines[32]),
            float(lines[33]),
            float(lines[34])]
    }

    return res

def read_iraf_database(filename):

    """
    Parses an apall-styled IRAF database into a apeture-indexed
    dictionary
    
    Parameters
    ----------
    filename : str
        Path to database
    
    Returns
    -------
    apertures : list of dictionary
        List of all of the parameters contained in the database, indexed
        over aperture number
    """

    with open(filename, 'r') as file:

        data = file.read()

        lines = data.split('\n\n')

        apertures = list()

        for line in lines:

            ap = parseAperture(line)

            apertures.append(ap)

        return apertures
