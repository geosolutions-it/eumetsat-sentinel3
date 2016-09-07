#!/usr/bin/env python

import sys
import logging
import os
import settings
import processing
import utilities
import summary
from summary import *
from settings import *
from utilities import *
from processing import *
from osgeo import gdal, osr

logger = logging.getLogger('mosaicking')
missingFileMessage = " doesn't exist. check the GPT logs for errors occurred while computing the graph"

def Usage():
    print 'Usage: mosaicking.py <path_to_input_summarieslist> [<outputDirectory>] ' 
    sys.exit(1)


class Mosaicker:
    def __init__(self, configuration, outputFolder = None):
        self.summaries =[]
        self.configuration = configuration
        self.outputFolder = outputFolder
    
    def add(self, summary):
        self.summaries.append(summary)

    # Parse summaries to collect the bandNames to be handled
    def collectOutputNames(self):
        bands = set()
        for summary in self.summaries:
            configProfile = summary.configProfile
            if not splitBands(summary.splitByBand):
                # In case bands don't need to be splitted 
                # the bandName will be the profile itself
                bands.add(configProfile)
                return bands
            bandNames = summary.bandNames
            bandNames = bandNames.split(',')
            for band in bandNames:
                if (skipBand(band)):
                    continue
                bands.add(band)
        return bands

    def preProcess(self, summary, filePath):
        configProfile = summary.configProfile
        if configProfile is not None:
            profileNode = self.configuration.getProfileNode(configProfile)
            preMosaicProcessNode = getNode(profileNode, settings.preMosaicProcessKey)
            if preMosaicProcessNode is not None:
                method = getElementValue(preMosaicProcessNode, settings.methodKey)
                parameters = getElementValue(preMosaicProcessNode, settings.parametersKey)
                if method is not None and parameters is not None:
                    outputFile = filePath
                    if not os.path.exists(filePath):
                        message = filePath + missingFileMessage
                        logger.error(message)
                        raise IOError(message)
                    
                    processedFile = filePath.replace('.tif', '_pre.tif')
                    os.rename(filePath, processedFile)
                    processingMethod = getattr(processing, method)
                    controlValues = processingMethod(processedFile, outputFile, parameters)
                    if self.configuration.deleteFiles:
                        os.remove(processedFile)
                    #Update controlValues
                    if 'nodata' in controlValues:
                        summary.nodata = controlValues['nodata']

    # Mosaic the collected pieces together
    def mosaic(self):
        # Group summaries by orbit
        orbits = self.groupSummaries()
        sortedOrbits = sorted(orbits)
        outputNames = self.collectOutputNames()
        logger.debug("available bands: " + str(outputNames))
        granulesPerMosaic = self.configuration.granulesPerMosaic
        timePeriod = self.configuration.timePeriod
        deltaSeconds = -1
        logger.info("Start Mosaicking with maxGranulesPerMosaic:" + str(granulesPerMosaic) + " timePeriod:" + str(timePeriod) + " seconds")
        for band in outputNames:
            for orbitSet in sortedOrbits:
                summaries = orbits[orbitSet]
                # Sort orbits by starttime
                summaries.sort(key=lambda x: x.startTime, reverse=False)
                filesPerMosaic = 0
                filesList = []
                summariesLength = len(summaries)
                minTime = None
                maxTime = None
                
                # Loop over processed products
                for summary in summaries:
                    starttime = summary.startTime
                    stoptime = summary.stopTime
                    chunks = summary.chunks
                    productType = summary.productType
                    splitbyband = summary.splitByBand
                    location = summary.location
                    
                    # Computing current time period
                    minTime = starttime if minTime is None else minTime if minTime < starttime else starttime
                    maxTime = stoptime if maxTime is None else maxTime if maxTime > stoptime else stoptime
                    chunkPieces = chunks.split(',') if (len(chunks)> 0) else ['']
                    for chunkPiece in chunkPieces:
                        directory = summary.directory
                        filePath = summary.fileNameBuilder.buildFilePath(band, chunkPiece)
                        self.preProcess(summary, filePath)
                        
                        filesList.append(filePath)
                    filesPerMosaic+=1
                    if (timePeriod > 1):
                        deltaSeconds = getDeltaSeconds(maxTime, minTime)
                    
                    # Mosaic collected pieces since now in case the granules limit or the time period have been exceeded
                    if (filesPerMosaic == granulesPerMosaic or filesPerMosaic == summariesLength or (timePeriod > 0 and deltaSeconds > timePeriod)):
                        message = "Going to mosaic " + str(filesPerMosaic) + " granules "
                        if (timePeriod > 1):
                            message = message + " with mosaic time range = " + str(deltaSeconds) + " seconds"
                        logger.info(message) 
                        outputFolder = self.outputFolder if self.outputFolder is not None else directory
                        self.mosaicFiles(filesList, outputFolder, band, summary.nodata, summary.orbit, minTime)
                        minTime = None
                        maxTime = None
                        filesPerMosaic = 0
                        deltaSeconds = -1
                        added = 0
                        filesList = []
#        if self.deleteFiles:
#            for summaryFile in summaryFiles:
#                os.remove(summaryFile)

    def groupSummaries(self):
        # Regroup summaries by orbit
        orbits = {}
        for summary in self.summaries:
            orbit = summary.orbit
            orbitSet = None
            if orbit in orbits:
               orbitSet = orbits[orbit]
            else:
               orbitSet = []
            orbitSet.append(summary)
            orbits[orbit] = orbitSet
        return orbits

    def mosaicFiles(self, inputFiles, directory, band, nodata, orbit, minTime):
        tifFiles = []
        for inputFile in inputFiles:
            if not os.path.exists(inputFile):
                message = inputFile + missingFileMessage
                logger.error(message)
                raise IOError(message)
            tifFiles.append(inputFile)
        fileprefix = band.replace('_','') + '_' + orbit + '_' + minTime
        vrtFileName = fileprefix + '.vrt'
        emptyTifName = fileprefix + '.tif'
        
        # Create a VRT on top of all the files to be mosaicked
        vrtFile = vrtFileName if (directory is None) else os.path.join(directory, vrtFileName)
        outputTif = emptyTifName if (directory is None) else os.path.join(directory, emptyTifName)
        command = settings.gdalVRTCommand.replace('$SRC_NODATA_VALUE', str(nodata).lower()).replace('$VRT_NODATA_VALUE', str(nodata).lower())
        vrtArguments = []
        vrtArguments = appendOptions(command, vrtArguments)
        vrtArguments.append(vrtFile)
        vrtArguments.extend(tifFiles)
        logger.debug("Calling gdalbuildvrt:" + getCommandString(vrtArguments))
        execute(vrtArguments)
        
        # Create an empty tif files with same structure of the VRT and warp the input
        # files on that 
        if not os.path.exists(vrtFile):
            message = vrtFile + " hasn't been created"
            logger.error(message)
            raise IOError(message)
        numBands = self.setEmptyTif(vrtFile, outputTif, nodata)
        self.warpFiles(inputFiles, outputTif, nodata)
        self.setNoDataValues(outputTif, nodata, numBands)
        self.addOverviews(outputTif)

    #Pre-Create a TIF for future mosaicking. Empty tifs allow dealing with empty tiles
    #to minimize disk usage
    def setEmptyTif(self, vrtFile, outputTif, nodata):
        logger.debug("Opening VRT:" + vrtFile)
        srcRaster = gdal.Open(vrtFile)
        numBands = srcRaster.RasterCount
        band = srcRaster.GetRasterBand(1)
        driver = gdal.GetDriverByName('GTiff')

        logger.debug("Creating empty TIFF:" + outputTif)
        outRaster = driver.Create(outputTif, srcRaster.RasterXSize, srcRaster.RasterYSize, numBands, band.DataType, self.configuration.gdalOptions)
        outRaster.SetGeoTransform(srcRaster.GetGeoTransform())
        outRaster.SetProjection(srcRaster.GetProjection())
        for bandIndex in range(0, numBands):
            bandIndex += 1
            outputBand = outRaster.GetRasterBand(bandIndex)
            outputBand.SetNoDataValue(float(nodata))
            outputBand = None
        outRaster = None
        if self.configuration.deleteFiles:
            os.remove(vrtFile)
        return numBands

    def setNoDataValues(self, outputTif, nodata, numBands):
        if numBands > 1:
            #command = settings.gdalEditCommand.replace('$NODATA', "0 0 0")  
            commandArguments = ['gdal_edit.py', '-mo', '"NODATA_VALUES=0 0 0"']
	    commandArguments.append(outputTif)
	    print str(commandArguments)
            execute(commandArguments)

    #Place granules to the final tif through a warping operation
    def warpFiles(self, inputFiles, output, nodata):
        command = settings.gdalWarpCommand.replace('$SRC_NODATA_VALUE', str(nodata).lower()).replace('$DST_NODATA_VALUE', str(nodata).lower()) + " "
        for inputFile in inputFiles:
            command = command + inputFile + ' ' 
        command = command + output
        logger.info("GDAL Warping: " + command)
        commandArguments = command.split()
        execute(commandArguments)
        if self.configuration.deleteFiles:
            for inputFile in inputFiles:
                os.remove(inputFile)

    #Add Overviews (if needed)
    def addOverviews(self, output):
        overviews = self.configuration.overviews
        if (overviews > 0):
            command = settings.gdalAddoCommand + ' ' + output
            factor = int(1)
            for ov in range (1, overviews):
                factor = factor * 2
                command = command + ' ' + str(factor)
            commandArguments = command.split()
            logger.info("Adding overviews: " + command)
            execute(commandArguments)

def main():
    argv = sys.argv
    files = argv[1]
#    band = argv[2]
#    nodata = argv[3]
#    orbit = argv[4]
#    minTime = argv[5]

    numParams = len(argv)
    outputDirectory = argv[2] if numParams == 3 else None
    
    configuration = setup_config()
    mosaicker = Mosaicker(configuration, outputDirectory)
    # Parse configuration
    with open(files) as f:
        for line in f:
            inputFile = line.strip() 
            message = fileNotExists(inputFile, 'skipping it')
            if message is not None:
                logger.warn(message)
                continue
            summary = parseComputationSummary(inputFile, mosaicker.outputFolder)
            mosaicker.add(summary)
    mosaicker.mosaic()

if __name__ == '__main__':
    main()

