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
from dateutil import parser


logger = logging.getLogger('georectify')
# =============================================================================
def Usage():
    print "Usage: georectify.py [-d] <inputs> [<profile>]"
    print " "
    print "    inputs: a file.lst containing the full paths of the input folders " 
    print "            of each product to be processed, a line for each product "
    print "        -d: optional 'directory' option to specify that the <inputs> "
    print "            parameter is not a file.lst but a directory containing   "
    print "            input folders instead                                    " 
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
    numParams = len(argv)
    if numParams < 2:
        Usage()
    
    paramIndex = 1
    param = argv[paramIndex]
    isDirectory = False
    if param == '-d':
        isDirectory = True
        paramIndex+=1
    inputs = argv[paramIndex]
    paramIndex+=1
    profile = argv[paramIndex] if numParams > (paramIndex) else None

    # Parse configuration
    configuration = setup_config()
    mosaicker = Mosaicker(configuration)
    fileList = []
    if isDirectory:
        for name in os.listdir(inputs):
            subdir = os.path.join(inputs, name)
            if os.path.isdir(subdir):
                fileList.append(os.path.join(subdir, manifestFile))
    else:    
        with open(inputs) as f:
            for line in f:
                line = line.rstrip('\n')
                if (len(line) > 0):
                    fileList.append(os.path.join(line, manifestFile))
    if len(fileList) == 0:
        logger.warn("No input files available, exit")
        return
    timestamp = int(round(time.time()*1000))
    directory = configuration.outputFolder
    folderExists = os.path.exists(directory)
    if not folderExists:
        os.makedirs(directory)
    listFileName = os.path.join(directory, str(timestamp) + '_run.txt')
    listFile =  open(listFileName, "w")
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
        listFile.write(summary.summaryFileName + "\n")
        if configuration.deleteFiles:
            os.remove(graphFile)
        if configuration.doMosaic:
            mosaicker.add(summary)
    listFile.close()
    if configuration.doMosaic:
        mosaicker.mosaic()

if __name__ == '__main__':
    main()
