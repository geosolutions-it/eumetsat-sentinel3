import settings
import ConfigParser
from utilities import *
from settings import *

class ComputationSummary:
    def __init__(self, bandNames, nodata, fileNameBuilder=None):
        if (fileNameBuilder):
            self.fileNameBuilder = fileNameBuilder
            self.directory = fileNameBuilder.directory
            self.summaryFileName = fileNameBuilder.summaryFileName
            self.graphFileName = fileNameBuilder.graphFileName if hasattr(fileNameBuilder, 'graphFileName') else None 
            self.location = fileNameBuilder.outputFolder
            self.orbit = fileNameBuilder.orbit
            self.startTime = fileNameBuilder.startTime
            self.stopTime = fileNameBuilder.stopTime
            self.splitByBand = fileNameBuilder.splitbyband
            self.productType = fileNameBuilder.productType
            self.configProfile = fileNameBuilder.configProfile
            
        self.bandNames = bandNames
        self.nodata = nodata
        self.chunks = ''

    def updateChunks(self, chunk):
        self.chunks = chunk if len(self.chunks) == 0 else self.chunks + "," + chunk

    # Write the summary file
    def writeSummary(self):
        config = ConfigParser.RawConfigParser()
        config.optionxform = str
        section = settings.summarySection
        config.add_section(section)
        config.set(section, settings.locationKey, self.fileNameBuilder.outputFolder)
        config.set(section, settings.chunksKey, self.chunks)
        config.set(section, settings.splitbybandKey, self.splitByBand)
        config.set(section, settings.bandnamesKey, self.bandNames)
        config.set(section, settings.orbitKey, self.orbit)
        config.set(section, settings.productTypeKey, self.fileNameBuilder.productType)
        config.set(section, settings.startTimeKey, self.startTime)
        config.set(section, settings.stopTimeKey, self.stopTime)
        config.set(section, settings.nodataKey, self.nodata)
        config.set(section, settings.directoryKey, self.directory)
        config.set(section, settings.profileKey, self.configProfile)
        
        with open(self.summaryFileName, 'wb') as configfile:
            config.write(configfile)

def parseComputationSummary(file, outputFolder):
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    config.read(file)
    section = settings.summarySection
    bandNames = config.get(section, settings.bandnamesKey)
    nodata = config.get(section, settings.nodataKey)
    configProfile = config.get(section, settings.profileKey)
    splitbyband = config.getboolean(section, settings.splitbybandKey)
    productType = config.get(section, settings.productTypeKey)
    
    fileNameBuilder = FileNameBuilder(outputFolder, productType, splitbyband, configProfile)
    fileNameBuilder.location = config.get(section, settings.locationKey)
    fileNameBuilder.orbit = config.get(section, settings.orbitKey)
    fileNameBuilder.startTime = config.get(section, settings.startTimeKey)
    fileNameBuilder.stopTime = config.get(section, settings.stopTimeKey)
    fileNameBuilder.directory = config.get(section, settings.directoryKey)
    fileNameBuilder.summaryFileName = file
    summary = ComputationSummary(bandNames, nodata, fileNameBuilder)
    summary.chunks = config.get(section, settings.chunksKey)
    
    return summary
