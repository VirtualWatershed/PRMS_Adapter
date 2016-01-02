import linecache
import netCDF4    
import osr  
import sys
import os
import time

def find_output_variables(fileHandle, numberOfVariables):
    
    """
 
    Returns the names and array indices of the output variables in the file. 
    Two lists, outputVariableNames and outputVariableArrayIndices are created
    to append the names and indices respectively. 

    Args:
        numberOfVariables (int): is the total number of output variables. This
	value is indicated on the first line of the file.
    
    """
   
    outputVariableNames = []
    outputVariableArrayIndices = []  
    
    for index in range(numberOfVariables):    
	words = fileHandle.next().strip().split()
	outputVariableNames.append(words[0])
	outputVariableArrayIndices.append(words[1])	       

    return outputVariableNames, outputVariableArrayIndices

def find_column_values(statvarFile, numberOfVariables, numberOfDataValues, position):

    """
    
    Returns the values of variables in the file. 

    Args:
        numberOfVariables (int): is the total number of output variables. This
	value is indicated on the first line of the file.
	numberOfDataValues (int): is the number of values for each variable. This
        value is equal to the time-step value on the last line of the file.
	position (int): is the column position from where the values can be 
        retrieved.
    
    """

    values = []
    
    fileHandle = open(statvarFile, 'r')
    
    for i in range(numberOfVariables+1):
        fileHandle.next()
    
    for j in range(numberOfDataValues):
	valuesInLine = fileHandle.next().strip().split()[7:]
        values.append(valuesInLine[position])
   
    return values


def find_resolution(locationFile, outputVariableArrayIndices):

    """
    
    Returns the values of variables in the file. 

    Args:
        numberOfDays (int): is the total number of values for the variable
	position (int): is the column position from where the values can be 
        retrieved
    
    """

    latitudeValues = []
    longitudeValues = []
   
    fileHandle = open(locationFile, 'r')

    for i in outputVariableArrayIndices:
	values = linecache.getline(locationFile, int(i)).split()
	longitudeValues.append(float(values[1]))
	latitudeValues.append(float(values[2]))

    return latitudeValues, longitudeValues


def find_metadata(outputVariableName):

    projectRoot = os.path.dirname(os.path.dirname(__file__))
    fileLocation = os.path.join(projectRoot, 'variableDetails/outputVariables.txt')
    fileHandle = open(fileLocation, 'r')
    
    for line in fileHandle:
        if outputVariableName in line:
	    variableNameFromFile = line.strip()		
	    lengthOfVariableName = len(variableNameFromFile)
	    positionOfNameStart = variableNameFromFile.index(':') + 2
 	    variableName = variableNameFromFile[positionOfNameStart:lengthOfVariableName]
		
	    variableDescriptionFromFile = fileHandle.next().strip()
	    lengthOfVariableDescription = len(variableDescriptionFromFile)
	    positionOfDescriptionStart = variableDescriptionFromFile.index(':') + 2
	    variableDescription = variableDescriptionFromFile[positionOfDescriptionStart:lengthOfVariableDescription]
		
	    variableUnitFromFile = fileHandle.next().strip()
	    lengthOfVariableUnit = len(variableUnitFromFile)
	    positionOfUnitStart = variableUnitFromFile.index(':') + 2
	    variableUnit = variableUnitFromFile[positionOfUnitStart:lengthOfVariableUnit]

	    variableTypeFromFile = fileHandle.next().strip()
	    lengthOfVariableType = len(variableTypeFromFile)
	    positionOfTypeStart = variableTypeFromFile.index(':') + 2
	    variableType = variableTypeFromFile[positionOfTypeStart:lengthOfVariableType]
		
	    break;
          
    return variableName, variableDescription, variableUnit, variableType


def statvar_to_netcdf(statvarFile, locationFile, outputFileName, event_emitter=None, **kwargs):
   
    indexOfDataLine = []

    fileHandle = open(statvarFile, 'r')
    lastLine = fileHandle.readlines()[-1].split()
    lastTimeStepValue = int(lastLine[0])
    
    for index in range(1, lastTimeStepValue+1):
        indexOfDataLine.append(index)
    
    # Finding the number of variable values
    fileHandle = open(statvarFile, 'r')
    numberOfVariables = int(fileHandle.next().strip())
           
    # Finding the names and array indices of output variables
    outputVariables = find_output_variables(fileHandle, numberOfVariables)
    outputVariableNames = outputVariables[0]
    outputVariableArrayIndices = outputVariables[1]

    # Finding the first date
    firstDate = fileHandle.next().strip().split()[1:7]
    year = firstDate[0]
    month = firstDate[1]
    day = firstDate[2]
    hour = firstDate[3]
    minute = firstDate[4]
    second = firstDate[5]

    locationValues = find_resolution(locationFile, outputVariableArrayIndices)
    latitudeValues = locationValues[0]
    longitudeValues = locationValues[1]
            
    # Initialize new dataset
    ncfile = netCDF4.Dataset(outputFileName, mode='w')

    # Initialize dimensions
    time = ncfile.createDimension('time', lastTimeStepValue)  
   
    # Define time variable
    time = ncfile.createVariable('time', 'i4', ('time',))
    time.long_name = 'time'  
    time.units = 'days since '+year+'-'+month+'-'+day+' '+hour+':'+minute+':'+second
    time[:] = indexOfDataLine
   
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)
    crs = ncfile.createVariable('crs', 'S1',)
    crs.spatial_ref = sr.ExportToWkt()

    kwargs['event_name'] = 'statvar_to_nc'
    kwargs['event_description'] = 'creating netcdf file from output statistics variables file'
    kwargs['progress_value'] = 0.00

    '''
    print kwargs['event_name']
    print kwargs['event_description']
    print kwargs['progress_value']
    import time
    time.sleep(.3)   
    '''

    if event_emitter:
        event_emitter.emit('progress',**kwargs)

    prg = 0.10
    length = len(outputVariableNames)

    # Define other variables  
    for index in range(len(outputVariableNames)):

        metadata = find_metadata(outputVariableNames[index])
	variableName = metadata[0]
	variableDescription = metadata[1]
	variableUnit = metadata[2]
	variableType = metadata[3]
        
        if variableType == 'real':
	    value = 'f4'
	elif variableType == 'double':
	    value = 'f4'
	elif variableType == 'integer':
	    value = 'i4'
	
        ncfile.createDimension('lat_'+str(index), 1)
        ncfile.createDimension('lon_'+str(index), 1)
	
	var = ncfile.createVariable(outputVariableNames[index]+'_'+outputVariableArrayIndices[index], value, ('time', 'lat_'+str(index), 'lon_'+str(index)))
        var.layer_name = variableName
	var.hru = outputVariableArrayIndices[index]
	var.layer_desc = variableDescription
	var.layer_units = variableUnit

	var.latitude = latitudeValues[index]
	var.longitude = longitudeValues[index];
	var.grid_mapping = "crs" 
      
        columnValues = find_column_values(statvarFile, numberOfVariables, lastTimeStepValue, index)
        var[:] = columnValues

	progress_value = prg/length * 100

	kwargs['event_name'] = 'statvar_to_nc'
        kwargs['event_description'] = 'creating netcdf file from output statistics variables file'
        kwargs['progress_value'] = format(progress_value, '.2f')
	
        '''
        print kwargs['event_name']
        print kwargs['event_description']
        print kwargs['progress_value']
	time.sleep(.3)
	'''

	prg += 1
        event_emitter.emit('progress', **kwargs)
    
    kwargs['event_name'] = 'statvar_to_nc'
    kwargs['event_description'] = 'creating netcdf file from output statistics variables file'
    kwargs['progress_value'] = 100

    '''
    print kwargs['event_name']
    print kwargs['event_description']
    print kwargs['progress_value']
    time.sleep(.3)   
    '''

    if event_emitter:
        event_emitter.emit('progress',**kwargs)

    # Global attributes
    ncfile.title = 'Statistic Variables File'
    ncfile.bands = 1
    ncfile.bands_name = 'nsteps'
    ncfile.bands_desc = 'Output variable information for ' + statvarFile

    # Close the 'ncfile' object
    ncfile.close()
