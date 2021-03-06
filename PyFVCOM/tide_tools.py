"""
A series of tools with which tidal data can be extracted from FVCOM NetCDF
model results. Also provides a number of tools to interrogate the SQLite
database of tidal data collated from a range of sources across the north-west
European continental shelf.

Some of the tidal analysis functions require TAPPy to be installed and in
/usr/bin/ as tappy.py. Alter the path if your version of TAPPy lives elsewhere.

"""

from __future__ import print_function

def julianDay(gregorianDateTime, mjd=False):
    """
    For a given gregorian date format (YYYY,MM,DD,hh,mm,ss) get the
    Julian Day.

    Output array precision is the same as input precision, so if you
    want sub-day precision, make sure your input data are floats.

    Parameters
    ----------
    gregorianDateTime : ndarray
        Array of Gregorian dates formatted as [[YYYY, MM, DD, hh, mm,
        ss],...,[YYYY, MM, DD, hh, mm, ss]]. If hh, mm, ss are missing
        they are assumed to be zero (i.e. midnight).
    mjd : boolean, optional
        Set to True to convert output from Julian Day to Modified Julian
        Day.

    Returns
    -------
    jd : ndarray
        Modified Julian Day or Julian Day (depending on the value of
        mjd).

    Notes
    -----
    Julian Day epoch: 12:00 January 1, 4713 BC, Monday
    Modified Julain Day epoch: 00:00 November 17, 1858, Wednesday

    Modified after code at http://paste.lisp.org/display/73536 and
    http://home.online.no/~pjacklam/matlab/software/util/timeutil/date2jd.m

    """

    try:
        import numpy as np
    except ImportError:
        raise ImportError('Failed to import NumPy')

    try:
        nr, nc = np.shape(gregorianDateTime)
    except:
        nc = np.shape(gregorianDateTime)[0]
        nr = 1

    if nc < 6:
        # We're missing some aspect of the time. Let's assume it's the least
        # significant value (i.e. seconds first, then minutes, then hours).
        # Set missing values to zero.
        numMissing = 6 - nc
        if numMissing > 0:
            extraCols = np.zeros([nr, numMissing])
            if nr == 1:
                gregorianDateTime = np.hstack([gregorianDateTime, extraCols[0]])
            else:
                gregorianDateTime = np.hstack([gregorianDateTime, extraCols])

    if nr > 1:
        year   = gregorianDateTime[:, 0]
        month  = gregorianDateTime[:, 1]
        day    = gregorianDateTime[:, 2]
        hour   = gregorianDateTime[:, 3]
        minute = gregorianDateTime[:, 4]
        second = gregorianDateTime[:, 5]
    else:
        year   = gregorianDateTime[0]
        month  = gregorianDateTime[1]
        day    = gregorianDateTime[2]
        hour   = gregorianDateTime[3]
        minute = gregorianDateTime[4]
        second = gregorianDateTime[5]

    timeut = hour + (minute / 60.0) + (second / 3600.0)

    # For common era (CE), anno domini (AD). From the MATLAB function greg2julian.
    jd = (367.0 * year) - np.floor(7.0 * (year + np.floor((month + 9.0) / 12.0)) / 4.0) - \
                      np.floor(3.0 * (np.floor((year + (month - 9.0) / 7.0) / 100.0) + 1.0) / 4.0) + \
                      np.floor((275.0 * month) / 9.0) + day + 1721028.5 + (timeut / 24.0)

    if mjd:
        return jd - 2400000.5
    else:
        return jd

def gregorianDate(julianDay, mjd=False):
    """
    For a given Julian Day convert to Gregorian date (YYYY, MM, DD, hh, mm,
    ss). Optionally convert from modified Julian Day with mjd=True).

    This function is adapted to Python from the MATLAB julian2greg.m function
    (http://www.mathworks.co.uk/matlabcentral/fileexchange/11410).

    Parameters
    ----------
    julianDay : ndarray
        Array of Julian Days
    mjd : boolean, optional
        Set to True if the input is Modified Julian Days.

    Returns
    -------
    greg : ndarray
        Array of [YYYY, MM, DD, hh, mm, ss].

    Example
    -------
    >>> greg = gregorianDate(np.array([53583.00390625, 55895.9765625]), mjd=True)
    >>> greg.astype(int)
    array([[2005,    8,    1,    0,    5,   38],
           [2011,   11,   30,   23,   26,   15])

    """

    try:
        import numpy as np
    except ImportError:
        raise ImportError('Failed to import NumPy')

    if mjd:
        julianDay = julianDay + 2400000.5

    I = np.floor(julianDay + 0.5)
    Fr = np.abs(I - (julianDay + 0.5))

    if np.any(I < 2299160):
        B = I
    else:
        A = np.floor((I - 1867216.25) / 36524.25)
        a4 = np.floor(A / 4)
        B = I + 1.0 + A - a4

    C = B + 1524.0
    D = np.floor((C - 122.1) / 365.25)
    E = np.floor(365.25 * D)
    G = np.floor((C - E) / 30.6001)
    day = np.floor(C - E + Fr - np.floor(30.6001 * G))

    if np.any(G > 13.5):
        month = G - 13
    else:
        month = G - 1

    if np.any(month <= 2.5):
        year = D - 4715
    else:
        year = D - 4716

    hour = np.floor(Fr * 24)
    minu = np.floor(np.abs(hour - (Fr * 24)) * 60)
    minufrac = (np.abs(hour - (Fr * 24)) * 60)
    sec = np.ceil(np.abs(minu - minufrac) * 60)

    # Fix some months being negative. This only happens if the input is larger
    # than ~30 elements in the array. No idea why.
    if month.min() < 1:
        month[month < 1] = month[month < 1] + 12

    greg = np.column_stack((year, month, day, hour, minu, sec))

    return greg

def addHarmonicResults(db, stationName, constituentName, phase, amplitude, speed, inferred, noisy=False):
    """
    Add data to an SQLite database.

    Parameters
    ----------
    db : str
        Full path to an SQLite database. If absent, it will be created.
    stationName : str
        Short name for the current station. This is the table name.
    constituentName : str
        Name of the current tidal constituent being added.
    phase : float
        Tidal constituent phase (in degrees).
    amplitude : float
        Tidal constituent amplitude (in metres).
    speed : float
        Tidal constituent speed (in degrees per hour).
    inferred : str
        'true' or 'false' indicating whether the values are inferred
        (i.e. the time series is too short to perform a robust harmonic
        analysis).
    noisy : bool
        Set to True to enable verbose output.

    """

    try:
        import sqlite3
    except ImportError:
        raise ImportError('Failed to import the SQLite3 module')

    conn = sqlite3.connect(db)
    c = conn.cursor()


    # Create the necessary tables if they don't exist already
    c.execute('CREATE TABLE IF NOT EXISTS TidalConstituents (\
        shortName TEXT COLLATE nocase,\
        amplitude FLOAT(10),\
        phase FLOAT(10),\
        speed FLOAT(10),\
        constituentName TEXT COLLATE nocase,\
        amplitudeUnits TEXT COLLATE nocase,\
        phaseUnits TEXT COLLATE nocase,\
        speedUnits TEXT COLLATE nocase,\
        inferredConstituent TEXT COLLATE nocase\
        )')

    if noisy:
        print('amplitude, phase and speed.', end=' ')
    for item in range(len(inferred)):
        c.execute('INSERT INTO TidalConstituents VALUES (?,?,?,?,?,?,?,?,?)',\
            (stationName, amplitude[item], phase[item], speed[item], constituentName[item], 'metres', 'degrees', 'degrees per mean solar hour', inferred[item]))

    conn.commit()

    conn.close()

def getObservedData(db, table, startYear=False, endYear=False, noisy=False):
    """
    Extract the tidal data from the SQLite database for a given station.
    Specify the database (db), the table name (table) which needs to be the
    short name version of the station of interest.

    Optionally supply a start and end year (which if equal give all data from
    that year) to limit the returned data. If no data exists for that station,
    the output is returned as False.

    Parameters
    ----------
    db : str
        Full path to the tide data SQLite database.
    table : str
        Name of the table to be extracted (e.g. 'AVO').
    startYear : bool, optional
        Year from which to start extracting data (inclusive).
    endYear : bool, optional
        Year at which to end data extraction (inclusive).
    noisy : bool, optional
        Set to True to enable verbose output.

    See Also
    --------
    tide_tools.getObservedMetadata : extract metadata for a tide station.

    Notes
    -----
    Search is not fuzzy, so "NorthShields" is not the same as "North Shields".
    Search is case insensitive, however.

    """

    try:
        import sqlite3
    except ImportError:
        raise ImportError('Failed to import the SQLite3 module')

    if noisy:
        print('Getting data for {} from the database...'.format(table), end=' ')

    try:
        con = sqlite3.connect(db)

        with con:
            c = con.cursor()
            if startYear and endYear:
                # We've been given a range of data
                if startYear == endYear:
                    # We have the same start and end dates, so just do a
                    # simpler version
                    c.execute('SELECT * FROM ' + table + ' WHERE ' + \
                    table + '.year == ' + str(startYear) + \
                    ' ORDER BY year, month, day, hour, minute, second')
                else:
                    # We have a date range
                    c.execute('SELECT * FROM ' + table + ' WHERE ' + \
                    table + '.year > ' + str(startYear) + \
                    ' AND ' + table + '.year < ' + str(endYear) + \
                    ' ORDER BY year, month, day, hour, minute, second')
            else:
                # Return all data
                c.execute('SELECT * FROM ' + table + \
                    ' ORDER BY year, month, day, hour, minute, second')
            # Now get the data in a format we might actually want to use
            data = c.fetchall()

        con.close()

        if noisy:
            print('done.')

    except sqlite3.Error as e:
        if con:
            con.close()
            print('Error {}:'.format(e.args[0]))
            data = [False]

    return data

def getObservedMetadata(db, originator=False):
    """
    Extracts the meta data from the tidal elevations database. If the
    supplied originator is False (default), then information from all
    stations is returned.

    Parameters
    ----------
    db : str
        Full path to the tide data SQLite database.
    originator : str, optional
        Specify an originator (e.g. 'NTSLF', 'NSTD', 'REFMAR') to
        extract only that data. Defaults to all data.

    Returns
    -------
    lat, lon : list
        Latitude and longitude of the requested station(s).
    site : list
        Short names (e.g. 'AVO' for 'Avonmouth') of the tide stations.
    longName : list
        Long names of the tide stations (e.g. 'Avonmouth').

    """

    try:
        import sqlite3
    except ImportError:
        raise ImportError('Failed to import the SQLite3 module')

    try:
        con = sqlite3.connect(db)

        c = con.cursor()

        if originator is not False:
            out = c.execute('SELECT * from Stations where originatorName is ? or originatorLongName is ?',\
                [originator, originator])
        else:
            out = c.execute('SELECT * from Stations')

        # Convert it to a set of better formatted values.
        metadata = out.fetchall()
        lat = [float(m[0]) for m in metadata]
        lon = [float(m[1]) for m in metadata]
        site = [str(m[2]) for m in metadata]
        longName = [str(m[3]) for m in metadata]

    except sqlite3.Error as e:
        if con:
            con.close()
            print('Error {}:'.format(e.args[0]))
            lat, lon, site, longName = [False, False, False, False]

    return lat, lon, site, longName

def cleanObservedData(data, removeResidual=False):
    """
    Process the observed raw data to a more sensible format. Also
    convert from Gregorian dates to Modified Julian Day (to match FVCOM
    model output times).

    Parameters
    ----------
    data : ndarray
        Array of [YYYY, MM, DD, hh, mm, ss, zeta, flag] data output by
        getObservedData().
    removeResidual : bool, optional
        If True, remove any residual values. Where such data are absent
        (marked by values of -9999 or -99.0), no removal is performed.

    Returns
    -------
    dateMJD : ndarray
        Modified Julian Days of the input data.
    tideDataMSL : ndarray
        Time series of surface elevations from which the mean surface
        elevation has been subtracted. If removeResidual is True, these
        values will omit the atmospheric effects, leaving a harmonic
        signal only.
    npFlagsData : ndarray
        Flag values from the SQLite database (usually -9999, or P, N
        etc. if BODC data).
    allDateTimes : ndarray
        Original date data in [YYYY, MM, DD, hh, mm, ss] format.

    """

    try:
        import numpy as np
    except:
        raise ImportError('Failed to import NumPy')

    npObsData = []
    npFlagData = []
    for row in data:
        npObsData.append(row[0:-1]) # eliminate the flag from the numeric data
        npFlagData.append(row[-1]) # save the flag separately

    # For the tidal data, convert the numbers to floats to avoid issues
    # with truncation.
    npObsData = np.asarray(npObsData, dtype=float)
    npFlagData = np.asarray(npFlagData)

    # Extract the time and tide data
    allObsTideData = np.asarray(npObsData[:,6])
    allObsTideResidual = np.asarray(npObsData[:, 7])
    allDateTimes = np.asarray(npObsData[:,0:6], dtype=float)

    dateMJD = julianDay(allDateTimes, mjd=True)

    # Apply a correction (of sorts) from LAT to MSL by calculating the
    # mean (excluding nodata values (-99 for NTSLF, -9999 for SHOM))
    # and removing that from the elevation.
    tideDataMSL = allObsTideData - np.mean(allObsTideData[allObsTideData>-99])

    if removeResidual:
        # Replace the residuals to remove with zeros where they're -99
        # or -9999 since the net effect at those times is "we don't have
        # a residual, so just leave the original value alone".
        allObsTideResidual[allObsTideResidual <= -99] = 0
        tideDataMSL = tideDataMSL - allObsTideResidual

    return dateMJD, tideDataMSL, npFlagData, allDateTimes

def TAPPy(data, noisy=False):
    """
    Uses a slightly modified version of TAPPy which can be imported as a module
    to perform the harmonic analysis. The returned arrays are identical in
    format to those from runTAPPy (which calls tappy.py externally and reads in
    the XML file generated by TAPPy).

    Parameters
    ----------
    data : ndarray
        Array of [YYYY, MM, DD, hh, mm, ss, ZZ], where ZZ is time series data
        (e.g. surface elevation, velocity components etc.).

    Returns
    -------
    cName : list
        Tidal constituent names.
    cSpeed : list
        Tidal constituent speeds (in degrees per hour).
    cPhase : list
        Tidal constituent phases (in degrees).
    cAmplitude : list
        Tidal constituent amplitudes (in metres).
    cInference : list
        Flag of whether the tidal constituent was inferred due to a
        short time series for the given constituent (True/False).

    """

    try:
        import numpy as np
    except ImportError:
        raise ImportError('Failed to import NumPy')

    try:
        import tappy
    except:
        raise ImportError('Failed to import TAPPy')

    try:
        import datetime
    except:
        raise ImportError('Failed to import datetime')

    # Set up the bits needed for TAPPy. This is mostly lifted from
    # tappy.py in the baker function "analysis" (around line 1721).
    quiet = noisy
    debug = False
    outputts = False
    outputxml = False
    ephemeris = False
    rayleigh = 1.0
    print_vau_table = False
    missing_data = 'ignore'
    linear_trend = False
    remove_extreme = False
    zero_ts = None
    filter = None
    pad_filters = None
    include_inferred = True

    # Create a tappy object.
    x = tappy.tappy(
        outputts = outputts,
        outputxml = outputxml,
        quiet=quiet,
        debug=debug,
        ephemeris=ephemeris,
        rayleigh=rayleigh,
        print_vau_table=print_vau_table,
        missing_data=missing_data,
        linear_trend=linear_trend,
        remove_extreme=remove_extreme,
        zero_ts=zero_ts,
        filter=filter,
        pad_filters=pad_filters,
        include_inferred=include_inferred,
        )

    # Add the time series to the TAPPy object
    x.dates = []
    x.elevation = []
    for v in data:
        ttt = ([int(i) for i in v[:-1]])
        x.dates.append(datetime.datetime(*ttt))
        x.elevation.append(v[-1])

    x.dates = np.asarray(x.dates)
    x.elevation = np.asarray(x.elevation)

    package = x.astronomic(x.dates)
    (x.zeta, x.nu, x.nup, x.nupp, x.kap_p, x.ii, x.R, x.Q, x.T, x.jd, x.s, x.h, x.N, x.p, x.p1) = package

    if rayleigh:
        ray = float(rayleigh)
    else:
        ray = 1.0
    (x.speed_dict, x.key_list) = x.which_constituents(len(x.dates),
                                                      package,
                                                      rayleigh_comp = ray)

    x.constituents() # the analysis

    # Format output to match that returned by runTAPPy().
    cName = []
    cSpeed = []
    cInference = []
    cPhase = []
    cAmplitude = []

    # Fully resolved constituents
    ndict = {}
    for k in x.key_list:
        ndict[k] = x.speed_dict[k]['speed']
    klist = [i[0] for i in x.sortbyvalue(ndict)]
    for i in klist:
        cName.append(i)
        cSpeed.append(x.speed_dict[i]['speed'] * tappy.rad2deg)
        cPhase.append(x.phase[i])
        cAmplitude.append(x.r[i])
        cInference.append(False)

    # Inferred constituents
    ndict = {}
    for k in x.inferred_key_list:
        ndict[k] = x.tidal_dict[k]['speed']
    klist = [i[0] for i in x.sortbyvalue(ndict)]
    for i in klist:
        cName.append(i)
        cSpeed.append(x.tidal_dict[i]['speed'] * tappy.rad2deg)
        cPhase.append(x.inferred_phase[i])
        cAmplitude.append(x.inferred_r[i])
        cInference.append(True)

    return cName, cSpeed, cPhase, cAmplitude, cInference

def runTAPPy(data, sparseDef=False, noisy=False, deleteFile=True, tappy='/usr/bin/tappy.py'):
    """
    A simple wrapper to perform a harmonic analysis on the supplied data.
    Input data format is YYYY, MM, DD, hh, mm, ss, ZZ as a numpy array.

    TAPPy is called as follows:

        tappy.py analysis --def_filename=sparse.def --outputxml=tempfile.xml --quiet tempinput.txt

    The output XML file is parsed with parseTAPPyXML to return a series of
    variables containing the analysis output. The input file tempinput.txt is
    deleted once the analysis is complete, unless deleteFile is set to False,
    in which case it is left where it is. To find it, pass noisy=True to be
    given more verbose output.

    By default, tappy.py is expected in /usr/bin. If yours lives elsewhere,
    pass tappy='/path/to/tappy.py'.

    The default sparse definition file is:

        /users/modellers/pica/Data/proc/tides/sparse.def

    Pass an alternate value to sparseDef to use a different one.

    Parameters
    ----------
    data : ndarray
        Array of [YYYY, MM, DD, hh, mm, ss, ZZ], where ZZ is surface elevation.
    sparseDef : str, optional
        Path to a TAPPy definition file. The default is
        /users/modellers/pica/Data/proc/tides/sparse.def.
    noisy : bool, optional
        Set to True to enable verbose output.
    deleteFile : bool, optional
        By default the output file created by TAPPy is deleted
        automatically. Set to False to keep the file.
    tappy : str, optional
        Specify an alternate path to the TAPPy script.

    Returns
    -------
    cName : list
        Tidal constituent names.
    cSpeed : list
        Tidal constituent speeds (in degrees per hour).
    cPhase : list
        Tidal constituent phases (in degrees).
    cAmplitude : list
        Tidal constituent amplitudes (in metres).
    cInference : list
        Flag of whether the tidal constituent was inferred due to a
        short time series for the given constituent.

    """

    try:
        import subprocess
    except ImportError:
        raise ImportError('Failed to import the subprocess module')

    try:
        import tempfile
    except ImportError:
        raise ImportError('Failed to import the tempfile module')

    try:
        import numpy as np
    except:
        raise ImportError('Failed to import NumPy')

    if not sparseDef:
        sparseDef = '/users/modellers/pica/Data/proc/tides/sparse.def'

    tFile = tempfile.NamedTemporaryFile(delete=deleteFile)
    if noisy:
        if not deleteFile:
            print('Saving to temporary file {}...'.format(tFile.name))
        else:
            print('Saving to temporary file...', end=' ')


    np.savetxt(tFile.name, data, fmt='%4i/%02i/%02i %02i:%02i:%02i %.3f')

    if noisy:
        print('done.')
        print('Running TAPPy on the current station...', end=' ')

    xFile = tempfile.NamedTemporaryFile()
    subprocess.call([tappy, 'analysis', '--def_filename=' + sparseDef, '--outputxml=' + xFile.name, '--quiet', tFile.name])

    [cName, cSpeed, cPhase, cAmplitude, cInference] = parseTAPPyXML(xFile.name)

    if noisy:
        print('done.')

    return cName, cSpeed, cPhase, cAmplitude, cInference

def parseTAPPyXML(file):
    """
    Extract values from an XML file created by TAPPy.

    TODO: Allow a list of constituents to be specified when calling
    parseTAPPyXML.

    Parameters
    ----------
    file : str
        Full path to a TAPPy output XML file.

    Returns
    -------
    constituentName : list
        Tidal constituent names.
    constituentSpeed : list
        Tidal constituent speeds (in degrees per hour).
    constituentPhase : list
        Tidal constituent phases (in degrees).
    constituentAmplitude : list
        Tidal constituent amplitudes (in metres).
    constituentInference : list
        Flag of whether the tidal constituent was inferred due to a
        short time series for the given constituent.

    """

    try:
        from lxml import etree
    except ImportError:
        raise ImportError('Failed to load the lxml library')

    tree = etree.parse(open(file, 'r'))

    constituentName = []
    constituentSpeed = []
    constituentInference = []
    constituentPhase = []
    constituentAmplitude = []

    for harmonic in tree.iter('Harmonic'):

        # Still not pretty
        for item in harmonic.iter('name'):
            constituentName.append(item.text)

        for item in harmonic.iter('speed'):
            constituentSpeed.append(item.text)

        for item in harmonic.iter('inferred'):
            constituentInference.append(item.text)

        for item in harmonic.iter('phaseAngle'):
            constituentPhase.append(item.text)

        for item in harmonic.iter('amplitude'):
            constituentAmplitude.append(item.text)

    return constituentName, constituentSpeed, constituentPhase, constituentAmplitude, constituentInference

def getHarmonics(db, stationName, noisy=False):
    """
    Use the harmonics database to extract the results of the harmonic analysis
    for a given station (stationName).

    Parameters
    ----------
    db : str
        Full path to the tidal harmonics SQLite database.
    stationName : str
        Station short name (i.e. table name).
    noisy : bool, optional
        Set to True to enable verbose output.

    Returns
    -------
    siteHarmonics : dict
        Contains all the harmonics data for the given tide station. Keys and units are:
            - 'stationName' (e.g. 'AVO')
            - 'amplitude' (m)
            - 'phase' (degrees)
            - 'speed' (degrees per mean solar hour)
            - 'constituentName' (e.g. 'M2')
            - 'inferredConstituent' ('true'|'false')

    """

    try:
        import sqlite3
    except ImportError:
        raise ImportError('Failed to import the SQLite3 module')

    try:
        import numpy as np
    except:
        raise ImportError('Failed to import NumPy')

    if noisy:
        print('Getting harmonics data for site {}...'.format(stationName), end=' ')

    try:
        con = sqlite3.connect(db)

        with con:
            c = con.cursor()
            c.execute('SELECT * FROM TidalConstituents WHERE shortName = \'' + stationName + '\'')
            data = c.fetchall()

        con.close()
    except sqlite3.Error as e:
        if con:
            con.close()
            print('Error %s:' % e.args[0])
            data = [False]

        if noisy:
            print('extraction failed.')

    # Convert data to a dict of value pairs
    dictNames = ['amplitude', 'phase', 'speed', 'constituentName', 'inferredConstituent']
    siteHarmonics = {}
    tAmp = np.empty(np.shape(data)[0])
    tPhase = np.empty(np.shape(data)[0])
    tSpeed = np.empty(np.shape(data)[0])
    tConst = np.empty(np.shape(data)[0], dtype="|S7")
    tInfer = np.empty(np.shape(data)[0], dtype=bool)
    for i, constituent in enumerate(data):
        tAmp[i] = constituent[1]
        tPhase[i] = constituent[2]
        tSpeed[i] = constituent[3]
        tConst[i] = str(constituent[4])
        if str(constituent[-1]) == 'false':
            tInfer[i] = False
        else:
            tInfer[i] = True
    siteHarmonics['amplitude'] = tAmp
    siteHarmonics['phase'] = tPhase
    siteHarmonics['speed'] = tSpeed
    siteHarmonics['constituentName'] = tConst
    siteHarmonics['inferredConstituent'] = tInfer

    if noisy:
        print('done.')

    return siteHarmonics

def readPOLPRED(harmonics, noisy=False):
    """
    Load a POLPRED data file into a NumPy array. This can then be used by
    getHarmonicsPOLPRED to extract the harmonics at a given loaction, or
    otherwise can be used to simply extract the positions of the POLCOMS grid.

    Parameters
    ----------
    harmonics : str
        Full path to the POLPRED ASCII data file.
    noisy : bool, optional
        Set to True to enable verbose output.

    Returns
    -------
    header : dict
        Contains the header data from the POLPRED ASCII file.
    values : ndarray
        Harmonic constituent data formatted as [x, y, nConst * [zZ, zG,
        uZ, uG, vZ, vG]], where nConst is the number of constituents in
        the POLPRED data (15) and z, u and v refer to surface elevation,
        u-vector and v-vector components, respectively. The suffixes Z
        and G refer to amplitude and phase of the z, u and v data.

    See Also
    --------
    tide_tools.gridPOLPRED : Converts the POLPRED data into a rectangular
        gridded data set with values of -999.9 outside the POLPRED domain.

    """

    import numpy as np

    # Open the harmonics file
    f = open(harmonics, 'r')
    polpred = f.readlines()
    f.close()

    # Read the header into a dict.
    readingHeader = True
    header = {}
    values = []

    if noisy:
        print('Parsing POLPRED raw data...', end=' ')

    for line in polpred:
        if readingHeader:
            if not line.strip():
                # Blank line, which means the end of the header
                readingHeader = False
            else:
                key, parameters = line.split(':')
                header[key.strip()] = parameters.strip()
        else:
            # Remove duplicate whitespaces and split on the resulting
            # single spaces.
            line = line.strip()
            line = ' '.join(line.split())
            values.append(line.split(' '))

    # Make the values into a numpy array
    values = np.asarray(values, dtype=float)

    if noisy:
        print('done.')

    return header, values

def gridPOLPRED(values, noisy=False):
    """
    The POLPRED data are stored as a 2D array, with a single row for each
    location. As such, the lat and long positions are stored in two 1D arrays.
    For the purposes of subsampling, it is much more convenient to have a
    rectangular grid. However, since the POLCOMS model domain is not
    rectangular, it is not possible to simply reshape the POLPRED data.

    To create a rectangular grid, this function builds a lookup table which
    maps locations in the 1D arrays to the equivalent in the 2D array. This is
    achieved as follows:

    1. Create a vector of the unique x and y positions.
    2. Use those positions to search through the 1D array to find the index of
    that position.
    3. Save the 1D index and the 2D indices in a lookup table.
    4. Create a rectangular array whose dimensions match the extent of the
    POLPRED data.
    5. Populate that array with the data, creating a 3D array (x by y by z,
    where z is the number of harmonics).
    6. Use meshgrid to create a rectangular position array (for use with
    pcolor, for example).

    This approach means the grid can be more readily subsampled without the
    need for interpolation (which would change the harmonic constituents).

    Where no data exist (i.e. outside the POLPRED domain), set all values as
    -999.9 (as per POLPRED's land value).

    Parameters
    ----------
    values : ndarray
        Output from readPOLPRED(). See `tide_tools.readPOLPRED'.
    noisy : bool, optional
        Set to True to enable verbose output.

    Returns
    -------
    PX : ndarray
        X values created using np.meshgrid.
    PY : ndarray
        Y values created using np.meshgrid.
    PZ : ndarray
        3D array of harmonic constituent values for the 15 harmonics in
        the POLPRED data at each location in PX and PY. The first two
        dimensions are x and y values (in latitude and longitdue) and
        the third dimension is the amplitude and phases for each of the
        15 constituents for z, u and v data.

    See Also
    --------
    tide_tools.readPOLPRED : Reads in the POLPRED ASCII data.
    tide_tools.getHarmonicsPOLPRED : Extract tidal harmonics within a
        threshold distance of a supplied coordinate.

    """

    import numpy as np

    # Create rectangular arrays of the coordinates in the POLCOMS domain.
    px = np.unique(values[:,1])
    py = np.unique(values[:,0])
    PX, PY = np.meshgrid(px, py)

    # I think appending to a list is faster than a NumPy array.
    arridx = []
    for i, (xx, yy) in enumerate(values[:, [1, 0]]):
        if noisy:
            # Only on the first, last and every 1000th line.
            if i == 0 or np.mod(i + 1, 1000) == 0 or i == values[:, 0].shape[0] - 1:
                print('{} of {}'.format(i + 1, np.shape(values)[0]))
        arridx.append([i, px.tolist().index(xx), py.tolist().index(yy)])

    # Now use the lookup table to get the values out of values and into PZ.
    PZ = np.ones([np.shape(py)[0], np.shape(px)[0], np.shape(values)[-1]]) * -999.9
    for idx, xidx, yidx in arridx:
        # Order is the other way around in arridx.
        PZ[yidx, xidx, :] = values[idx, :]

    return PX, PY, PZ

def getHarmonicsPOLPRED(harmonics, constituents, lon, lat, stations, noisy=False, distThresh=0.5):
    """
    Function to extract the given constituents at the positions defined
    by lon and lat from a given POLPRED text file.

    The supplied list of names for the stations will be used to generate a
    dict whose structure matches that I've used in the plot_harmonics.py
    script.

    Parameters
    ----------
    harmonics : str
        Full path to the POLPRED ASCII harmonics data.
    constituents : list
        List of tidal constituent names to extract (e.g. ['M2', 'S2']).
    lon, lat : ndarray
        Longitude and latitude positions to find the closest POLPRED
        data point. Uses grid_tools.findNearestPoint to identify the
        closest point. See distThresh below.
    stations : list
        List of tide station names (or coordinates) which are used as
        the keys in the output dict.
    noisy : bool, optional
        Set to True to enable verbose output.
    distThresh : float, optional
        Give a value (in the units of lon and lat) which limits the
        distance to which POLPRED points are returned. Essentially gives
        an upper threshold distance beyond which a point is considered
        not close enough.

    Returns
    -------
    out : dict
        A dict whose keys are the station names. Within each of those
        dicts is another dict whose keys are 'amplitude', 'phase' and
        'constituentName'.
        In addition to the elevation amplitude and phases, the u and v
        amplitudes and phases are also extracted into the dict, with the
        keys 'uH', 'vH', 'uG' and 'vG'.
        Finally, the positions from the POLPRED data is stored with the
        keys 'latitude' and 'longitude'. The length of the arrays within
        each of the secondary dicts is dependent on the number of
        constituents requested.

    See Also
    --------
    tide_tools.readPOLPRED : Read in the POLPRED data to split the ASCII
        file into a header dict and an ndarray of values.
    grid_tools.findNearestPoint : Find the closest point in one set of
        coordinates to a specified point or set of points.

    """

    import sys

    import numpy as np

    from grid_tools import findNearestPoint

    header, values = readPOLPRED(harmonics, noisy=noisy)

    # Find the nearest points in the POLCOMS grid to the locations
    # requested.
    nearestX, nearestY, distance, index = findNearestPoint(values[:, 1], values[:, 0], lon, lat, maxDistance=distThresh)

    # Get a list of the indices from the header for the constituents we're
    # extracting.
    ci = np.empty([np.shape(constituents)[0], 6], dtype=int)
    for i, con in enumerate(constituents):
        tmp = header['Harmonics'].split(' ').index(con)
        # Times 6 because of the columns per constituent
        ci[i, :] = np.repeat(tmp * 6, 6)
        # Add the offsets for the six harmonic components (amplitude and phase
        # of z, u and v).
        ci[i, :] = ci[i, :] + np.arange(6)

    # Plus 3 because of the lat, long and flag columns.
    ci = ci + 3

    # Make a dict of dicts for each station supplied.
    out = {}

    # Find the relevant data for the current site.
    for c, key in enumerate(stations):
        if noisy:
            print('Extracting site {}...'.format(key), end=' ')
            sys.stdout.flush()

        data = {}
        if np.isnan(index[c]):
            if noisy:
                print('skipping (outside domain).')
        else:
            keys = ['amplitude', 'phase', 'uH', 'ug', 'vH', 'vg']
            for n, val in enumerate(keys):
                data[val] = values[index[c], ci[:, n]]

            data['constituentName'] = constituents
            data['latitude'] = values[index[c], 0]
            data['longitude'] = values[index[c], 1]

            out[key] = data

            if noisy:
                print('done.')
                sys.stdout.flush()


    return out
