from __future__ import print_function

import sys

import numpy as np

from netCDF4 import Dataset, MFDataset

def readFVCOM(file, varList=None, clipDims=False, noisy=False, atts=False):
    """
    Read in the FVCOM results file and spit out numpy arrays for each of the
    variables specified in the varList list.

    Optionally specify a dict with keys whose names match the dimension names
    in the NetCDF file and whose values are strings specifying alternative
    ranges or lists of indices. For example, to extract the first hundred time
    steps, supply clipDims as:

        clipDims = {'time':'0:100'}

    To extract the first, 400th and 10,000th values of any array with nodes:

        clipDims = {'node':'[0, 3999, 9999]'}

    Any dimension not given in clipDims will be extracted in full.

    Specify atts=True to extract the variable attributes.

    Parameters
    ----------
    file : str, list
        If a string, the full path to an FVCOM NetCDF output file. If a list,
        a series of files to be loaded. Data will be concatenated into a single
        dict.
    varList : list, optional
        List of variable names to be extracted. If omitted, all variables are
        returned.
    clipDims : dict, optional
        Dict whose keys are dimensions and whose values are a string of either
        a range (e.g. {'time':'0:100'}) or a list of individual indices (e.g.
        {'time':'[0, 1, 80, 100]'}). Slicing is supported (::5 for every fifth
        value) but it is not possible to extract data from the end of the array
        with a negative index (e.g. 0:-4).
    noisy : bool, optional
        Set to True to enable verbose output.
    atts : bool, optional
        Set to True to enable output of the attributes (defaults to False).

    Returns
    -------
    FVCOM : dict
        Dict of data extracted from the NetCDF file. Keys are those given in
        varList and the data are stored as ndarrays.
    attributes : dict, optional
        If atts=True, returns the attributes as a dict for each
        variable in varList. The key 'dims' contains the array dimensions (each
        variable contains the names of its dimensions) as well as the shape of
        the dimensions defined in the NetCDF file. The key 'global' contains
        the global attributes.

    See Also
    --------
    readProbes : read in FVCOM ASCII probes output files.

    """

    # If we have a list, assume it's lots of files and load them all.
    if isinstance(file, list):
        try:
            try:
                rootgrp = MFDataset(file, 'r')
            except IOError as e:
                raise IOError('Unable to open file {}. Aborting.'.format(file))
        except:
            # Try aggregating along a 'time' dimension (for POLCOMS, for example)
            try:
                rootgrp = MFDataset(file, 'r', aggdim='time')
            except IOError as e:
                raise IOError('Unable to open file {}. Aborting.'.format(file))

    else:
        rootgrp = Dataset(file, 'r')


    # Create a dict of the dimension names and their current sizes
    dims = {}
    for key, var in list(rootgrp.dimensions.items()):
        # Make the dimensions ranges so we can use them to extract all the
        # values.
        dims[key] = '0:' + str(len(var))

    # Compare the dimensions in the NetCDF file with those provided. If we've
    # been given a dict of dimensions which differs from those in the NetCDF
    # file, then use those.
    if clipDims:
        commonKeys = set(dims).intersection(list(clipDims.keys()))
        for k in commonKeys:
            dims[k] = clipDims[k]

    if noisy:
        print("File format: {}".format(rootgrp.file_format))

    if not varList:
        varList = iter(list(rootgrp.variables.keys()))

    FVCOM = {}

    # Save the dimensions in the attributes dict.
    if atts:
        attributes = {}
        attributes['dims'] = dims
        attributes['global'] = {}
        for g in rootgrp.ncattrs():
            attributes['global'][g] = getattr(rootgrp, g)

    for key, var in list(rootgrp.variables.items()):
        if noisy:
            print('Found ' + key, end=' ')
            sys.stdout.flush()

        if key in varList:
            vDims = rootgrp.variables[key].dimensions

            toExtract = [dims[d] for d in vDims]

            # If we have no dimensions, we must have only a single value, in
            # which case set the dimensions to empty and append the function to
            # extract the value.
            if not toExtract:
                toExtract = '.getValue()'

            # Thought I'd finally figured out how to replace the eval approach,
            # but I still can't get past the indexing needed to be able to
            # subset the data.
            #FVCOM[key] = rootgrp.variables.get(key)[0:-1]
            # I know, I know, eval() is evil.
            getData = 'rootgrp.variables[\'{}\']{}'.format(key,str(toExtract).replace('\'', ''))
            FVCOM[key] = eval(getData)

            # Add the units and dimensions for this variable to the list of
            # attributes.
            if atts:
                attributes[key] = {}
                try:
                    attributes[key]['units'] = rootgrp.variables[key].units
                except:
                    pass

                try:
                    attributes[key]['dims'] = rootgrp.variables[key].dimensions
                except:
                    pass

            if noisy:
                if len(str(toExtract)) < 60:
                    print('(extracted {})'.format(str(toExtract).replace('\'', '')))
                else:
                    print('(extracted given indices)')

        elif noisy:
                print()

    # Close the open file.
    rootgrp.close()

    if atts:
        return FVCOM, attributes
    else:
        return FVCOM


def ncread(file, vars=None, dims=False, noisy=False, atts=False):
    """
    Read in a netCDF file and return numpy arrays for each of the variables
    specified in the vars list.

    Optionally specify a dict with keys whose names match the dimension names
    in the NetCDF file and whose values are strings specifying alternative
    ranges or lists of indices. For example, to extract the first hundred time
    steps, supply clipDims as:

        dims = {'time':'0:100'}

    To extract the first, 400th and 10,000th values of any array with nodes:

        dims = {'node':'[0, 3999, 9999]'}

    Any dimension not given in dims will be extracted in full.

    Specify atts=True to extract attributes.

    Parameters
    ----------
    file : str, list
        If a string, the full path to an FVCOM NetCDF output file. If a list,
        a series of files to be loaded. Data will be concatenated into a single
        dict.
    vars : list, optional
        List of variable names to be extracted. If omitted, all variables are
        returned.
    dims : dict, optional
        Dict whose keys are dimensions and whose values are a string of either
        a range (e.g. {'time':'0:100'}) or a list of individual indices (e.g.
        {'time':'[0, 1, 80, 100]'}). Slicing is supported (::5 for every fifth
        value) but it is not possible to extract data from the end of the array
        with a negative index (e.g. 0:-4).
    noisy : bool, optional
        Set to True to enable verbose output.
    atts : bool, optional
        Set to True to enable output of the attributes (defaults to False).

    Returns
    -------
    nc : dict
        Dict of data extracted from the NetCDF file. Keys are those given in
        varList and the data are stored as ndarrays.
    attributes : dict, optional
        If True, returns the attributes as a dict for each variable in varList.
        The key 'dims' contains the array dimensions (each variable contains
        the names of its dimensions) as well as the shape of the dimensions
        defined in the NetCDF file.

    Notes
    -----
    This is actually a wrapper for the readFVCOM function, but since that
    function is actually not specific to FVCOM, it seemed sensible to have this
    generic function. Eventually I imagine this will be the underlying version
    and the readFVCOM function will call this one i.e. the roles will be
    swapped.

    """

    if atts:
        nc, attributes = readFVCOM(file, varList=vars, clipDims=dims, noisy=noisy, atts=atts)
        return nc, attributes
    else:
        nc = readFVCOM(file, varList=vars, clipDims=dims, noisy=noisy, atts=atts)
        return nc


class ncwrite():
    """
    Save data in a dict to a netCDF file.

    Notes
    -----
    1. Unlimited dimension can only be time and MUST be the 1st dimension in
       the variable dimensions list (or tuple).
    2. Variable dimensions HAVE to BE lists ['time']

    Parameters
    ----------
    data : dict
        Dict of dicts with keys 'dimension', 'variables' and
        'global_attributes'.
    file : str
        Path to output file name.

    Author(s)
    ---------
    Stephane Saux-Picart
    Pierre Cazenave

    Examples
    --------
    >>> lon = np.arange(-10, 10)
    >>> lat = np.arange(50, 60)
    >>> Times = ['2010-02-11 00:10:00.000000', '2010-02-21 00:10:00.000000']
    >>> p90 = np.sin(400).reshape(20, 10, 2)
    >>> data = {}
    >>> data['dimensions'] = {
    ...     'lat': np.size(lat),
    ...     'lon':np.size(lon),
    ...     'time':np.shape(timeStr)[1],
    ...     'DateStrLen':26
    ... }
    >>> data['variables'] = {
    ... 'latitude':{'data':lat,
    ...     'dimensions':['lat'],
    ...     'attributes':{'units':'degrees north'}
    ... },
    ... 'longitude':{
    ...     'data':lon,
    ...     'dimensions':['lon'],
    ...     'attributes':{'units':'degrees east'}
    ... },
    ... 'Times':{
    ...     'data':timeStr,
    ...     'dimensions':['time','DateStrLen'],
    ...     'attributes':{'units':'degrees east'},
    ...     'fill_value':-999.0,
    ...     'data_type':'c'
    ... },
    ... 'p90':{'data':data,
    ...     'dimensions':['lat','lon'],
    ...     'attributes':{'units':'mgC m-3'}}}
    ... data['global attributes'] = {
    ...     'description': 'P90 chlorophyll',
    ...     'source':'netCDF3 python',
    ...     'history':'Created {}'.format(time.ctime(time.time()))
    ... }
    >>> ncwrite(data, 'test.nc')

    """

    def __init__(self, input_dict, filename_out, Quiet=False):
        self.filename_out = filename_out
        self.input_dict = input_dict
        self.Quiet = Quiet
        self.createNCDF()

    def createNCDF(self):
        """
        Function to create and write the data to the specified netCDF file.

        """

        rootgrp = Dataset(self.filename_out, 'w', format='NETCDF3_CLASSIC', clobber=True)

        # Create dimensions.
        if self.input_dict.has_key('dimensions'):
            for k,v in self.input_dict['dimensions'].iteritems():
                rootgrp.createDimension(k, v)
        else:
            if self.Quiet == False:
                print('No netCDF created:')
                print('  No dimension key found (!! has to be \"dimensions\"!!!)')
            return()

        # Create global attributes.
        if self.input_dict.has_key('global attributes'):
            for k,v in self.input_dict['global attributes'].iteritems():
                rootgrp.setncattr(k,v)
        else:
            if self.Quiet == False:
                print('  No global attribute key found (!! has to be \"global attributes\"!!!)')


        # Create variables.
        for k,v in self.input_dict['variables'].iteritems():
            dims = self.input_dict['variables'][k]['dimensions']
            data = v['data']
            # Create correct data type if provided
            if self.input_dict['variables'][k].has_key('data_type'):
                data_type = self.input_dict['variables'][k]['data_type']
            else:
                data_type = 'f4'
            # Check whether we've been given a fill value.
            if self.input_dict['variables'][k].has_key('fill_value'):
                fill_value = self.input_dict['variables'][k]['fill_value']
            else:
                fill_value = None
            # Create ncdf variable
            if self.Quiet == False:
                print('  Creating variable: {} {} {}'.format(k, data_type, dims))
            var = rootgrp.createVariable(k, data_type, dims, fill_value=fill_value)
            if len(dims) > np.ndim(data):
                # If number of dimensions given to netCDF is greater than the
                # number of dimension of the data, then  fill the netCDF
                # variable accordingly.
                if 'time' in dims:
                    # Check for presence of time dimension (which can be
                    # unlimited variable: defined by None).
                    try:
                        var[:] = data
                    except IndexError:
                        raise(IndexError(('Supplied data shape {} does not match the specified'
                        ' dimensions {}, for variable \'{}\'.'.format(data.shape, var.shape, k))))
                else:
                    if self.Quiet == False:
                        print('Problem in the number of dimensions')
            else:
                try:
                    var[:] = data
                except IndexError:
                    raise(IndexError(('Supplied data shape {} does not match the specified'
                    ' dimensions {}, for variable \'{}\'.'.format(data.shape, var.shape, k))))

            # Create attributes for variables
            if self.input_dict['variables'][k].has_key('attributes'):
                for ka,va in self.input_dict['variables'][k]['attributes'].iteritems():
                    var.setncattr(ka,va)

        rootgrp.close()


def readProbes(files, noisy=False, locations=False):
    """
    Read in FVCOM probes output files. Reads both 1 and 2D outputs. Currently
    only sensible to import a single station with this function since all data
    is output in a single array.

    Parameters
    ----------
    files : list, tuple
        List of file paths to load.
    noisy : bool, optional
        Set to True to enable verbose output.
    locations : bool, optional
        Set to True to export position and depth data for the sites.

    Returns
    -------
    times : ndarray
        Modified Julian Day times for the extracted time series.
    values : ndarray
        Array of the extracted time series values.
    positions : ndarray, optional
        If locations has been set to True, return an array of the positions
        (lon, lat, depth) for each site.

    See Also
    --------
    readFVCOM : read in FVCOM netCDF output.

    TODO
    ----

    Add support to multiple sites with a single call. Perhaps returning a dict
    with the keys based on the file name is most sensible here?

    """

    if len(files) == 0:
        raise Exception('No files provided.')

    if not (isinstance(files, list) or isinstance(files, tuple)):
        files = [files]

    for i, file in enumerate(files):
        if noisy: print('Loading file {} of {}...'.format(i + 1, len(files)), end=' ')

        # Get the header so we can extract the position data.
        with open(file, 'r') as f:
            # Latitude and longitude is stored at line 15 (14 in sPpython
            # counting). Eastings and northings are at 13 (12 in Python
            # indexing).
            lonlatz = [float(pos.strip()) for pos in filter(None, f.readlines()[14].split(' '))]

        data = np.genfromtxt(file, skip_header=18)

        if i == 0:
            times = data[:, 0]
            values = data[:, 1:]
            positions = lonlatz
        else:
            times = np.hstack((times, data[:, 0]))
            values = np.vstack((values, data[:, 1:]))
            positions = np.vstack((positions, lonlatz))

        if noisy: print('done.')

    # It may be the case that the files have been supplied in a random order,
    # so sort the values by time here.
    sidx = np.argsort(times)
    times = times[sidx]
    values = values[sidx, ...] # support both 1 and 2D data

    if locations:
        return times, values, positions
    else:
        return times, values


def elems2nodes(elems, tri, nvert):
    """
    Calculate a nodal value based on the average value for the elements
    of which it a part. This necessarily involves an average, so the
    conversion from nodes2elems and elems2nodes is not necessarily
    reversible.

    Parameters
    ----------
    elems : ndarray
        Array of unstructured grid element values to move to the element
        nodes.
    tri : ndarray
        Array of shape (nelem, 3) comprising the list of connectivity
        for each element.
    nvert : int
        Number of nodes (vertices) in the unstructured grid.

    Returns
    -------
    nodes : ndarray
        Array of values at the grid nodes.

    """

    count = np.zeros(nvert, dtype=int)

    # Deal with 1D and 2D element arrays separately
    if np.ndim(elems) == 1:
        nodes = np.zeros(nvert)
        for i, indices in enumerate(tri):
            n0, n1, n2 = indices
            nodes[n0] = nodes[n0] + elems[i]
            nodes[n1] = nodes[n1] + elems[i]
            nodes[n2] = nodes[n2] + elems[i]
            count[n0] = count[n0] + 1
            count[n1] = count[n1] + 1
            count[n2] = count[n2] + 1

    elif np.ndim(elems) > 1:
        # Horrible hack alert to get the output array shape for multiple
        # dimensions.
        nodes = np.zeros((list(np.shape(elems)[:-1]) + [nvert]))
        for i, indices in enumerate(tri):
            n0, n1, n2 = indices
            nodes[..., n0] = nodes[..., n0] + elems[..., i]
            nodes[..., n1] = nodes[..., n1] + elems[..., i]
            nodes[..., n2] = nodes[..., n2] + elems[..., i]
            count[n0] = count[n0] + 1
            count[n1] = count[n1] + 1
            count[n2] = count[n2] + 1

    # Now calculate the average for each node based on the number of
    # elements of which it is a part.
    nodes = nodes / count

    return nodes


def nodes2elems(nodes, tri):
    """
    Calculate a element centre value based on the average value for the
    nodes from which it is formed. This necessarily involves an average,
    so the conversion from nodes2elems and elems2nodes is not
    necessarily reversible.

    Parameters
    ----------
    nodes : ndarray
        Array of unstructured grid node values to move to the element
        centres.
    tri : ndarray
        Array of shape (nelem, 3) comprising the list of connectivity
        for each element.

    Returns
    -------
    elems : ndarray
        Array of values at the grid nodes.

    """

    nvert = np.shape(tri)[0]

    if np.ndim(nodes) == 1:
        elems = nodes[tri].mean(axis=-1)
    elif np.ndim(nodes) == 2:
        elems = nodes[..., tri].mean(axis=-1)
    else:
        raise Exception('Too many dimensions (maximum of two)')

    return elems


def getSurfaceElevation(Z, idx):
    """
    Extract the surface elevation from Z at index ind. If ind is multiple
    values, extract and return the surface elevations at all those locations.

    Z is usually extracted from the dict created when using readFVCOM() on a
    NetCDF file.

    Parameters
    ----------
    Z : ndarray
        Unstructured array of surface elevations with time.
    idx : list
        List of indices from which to extract time series of surface
        elevations.

    Returns
    -------
    surfaceElevation : ndarray
        Time series of surface elevations at the indices supplied in
        idx.

    """

    nt, nx = np.shape(Z)

    surfaceElevation = np.empty([nt,np.shape(idx)[0]])
    for cnt, i in enumerate(idx):
        if not np.isnan(i):
            surfaceElevation[:,cnt] = Z[:,i]

    return surfaceElevation
