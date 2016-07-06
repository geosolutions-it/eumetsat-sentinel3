#!/usr/bin/env python

import math
import string
import sys
import time
import os
import ConfigParser
import logging
from settings import *
from xfdumanifest import *
from graphbuilder import *
from utilities import *
from mosaicking import *
from os import listdir
from os.path import isfile, join
from subprocess import call
from dateutil import parser


logger = logging.getLogger('georectify')
# =============================================================================
def Usage():
    print 'Usage: georectify.py <path_to_input_filelist> <profile>' 
    sys.exit(1)

# =============================================================================

def createGraph(inputFile, configuration, profile=None):

    outputFolder = configuration.outputFolder
    # Extract dynamic values from Manifest (xfdumanifest.xml)
    xfduManifest = XfduManifest(inputFile)
    
    productType = xfduManifest.productType
    configDict = configuration.getProductConfiguration(productType, profile)
    # Parsing graph configuration elements
    blocksize = configDict[settings.blocksizeKey]
    bandNames = configDict[settings.bandnamesKey]
    flagsManagement = configDict[settings.flagsManagementKey]
    outputFormat = configDict['outputFormat']
    resolution = configDict[settings.resolutionKey]
    nodata = configDict[settings.nodataKey]
    interpolation = configDict[settings.interpolationKey]
    inputFormat = configDict['inputFormat']
    configProfile = configDict[settings.profileKey]
    imageSizeTag = configDict['imageSizeTag']
    
    rows = xfduManifest.rows(imageSizeTag)
    columns = xfduManifest.columns(imageSizeTag)
    chunksManager = ChunksManager(columns, rows, blocksize, configuration)

    templateDictionary = {
     '$BANDNAMES': bandNames,
     '$RESOLUTION': str(resolution),
     '$NODATA': str(nodata),
     '$RESAMPLING': interpolation,
     '$FORMAT': outputFormat,
     '$FLAGS': flagsManagement}

    splitbyband = configDict[splitbybandKey]
    shortName = productConfigs[productType].shortName
    fileNameBuilder = FileNameBuilder(outputFolder, shortName, splitbyband, configProfile, xfduManifest)

    graphFileName = fileNameBuilder.graphFileName
    graphBuilder = GraphBuilder(graphFileName, configuration)
    computationSummary = ComputationSummary(bandNames, nodata, fileNameBuilder)
    graphBuilder.generateGraph(inputFile, inputFormat, chunksManager, templateDictionary, computationSummary)

    if configuration.writeSummary:
        computationSummary.writeSummary()
    return computationSummary
    



def main():
    global verbose 
    verbose = False  

    # Parse command line arguments.
    argv = sys.argv
    
    files = argv[1]
    
    numParams = len(argv)
    profile = argv[2] if numParams == 3 else None

    # Parse configuration
    configuration = setup_config()
    mosaicker = Mosaicker(configuration)
    fileList = []
    with open(files) as f:
        for line in f:
            line = line.rstrip('\n')
            if (len(line) > 0):
                fileList.append(line)
    for inputFile in fileList:
        message = fileNotExists(inputFile, 'skipping it')
        if message is not None:
            logger.warn(message)
            continue
       
        logger.debug("Parsing inputFile: " + inputFile)
        summary = createGraph(inputFile, configuration, profile)
        graphFile = summary.graphFileName
        command = setGPTCommand(configuration.GPTArguments, graphFile)
        logger.info("Executing SNAP GPT with command: " + getCommandString(command))
        execute(command)
        if configuration.deleteFiles:
            os.remove(graphFile)
        if configuration.doMosaic:
            mosaicker.add(summary)
    if configuration.doMosaic:
        mosaicker.mosaic()

if __name__ == '__main__':
    main()
