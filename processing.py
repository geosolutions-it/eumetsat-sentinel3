#!/usr/bin/env python

import sys
import logging
import os
import settings
from settings import *
from utilities import *

logger = logging.getLogger('mosaicking')
supportedMethods = ['gdalrgb']

def Usage():
    print 'Usage: processing.py <method> <inputfile> <outputfile> <parameters>' 
    sys.exit(1)

#implemented methods will return a control values dictionary
def gdalrgb(inputfile, outputfile, parameters):
    result = {}
    command = settings.gdalrgbCommand.replace('$PARAMETERS', parameters) + " " + inputfile + " " + outputfile
    logger.debug("GDAL RGB creation: " + command)
    commandArguments = command.split()
    execute(commandArguments)

    #Extracting nodata and returning its value 
    if '-a_nodata' in parameters:
        #look for the whitespace after the nodata value
        #so I can isolate the nodatavalue 
        index1 = parameters.find("-a_nodata") + 10 #10 is the key lenght plus the first space
        index2 = parameters.find(" ", index1)
        nodata = parameters[index1:index2]
        print nodata 
        result['nodata'] = nodata
    return result 

def main():
    argv = sys.argv
    method = argv[1]
    inputfile = argv[2]
    outputfile = argv[3]
    parameters = argv[4]
    
    print "Usage: processing.py <method> <inputfile> <outputfile> <parameters>" 
    #At the moment, only gdalrgb method is supported
    if method not in supportedMethods:
        print "the provided method is not supported: " + method + "\nCurrently supported methods: " + str(supportedMethods)
        sys.exit(1)
    if method == 'gdalrgb':
       gdalrgb(inputfile, outputfile, parameters)  

if __name__ == '__main__':
    main()

