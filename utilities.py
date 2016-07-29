import time
import os
from os.path import isfile, join
from dateutil import parser
import ConfigParser
import datetime
import subprocess
import logging
import settings

logger = logging.getLogger('utilities')
coordinates = ['lat','lon','latitude','longitude','latitude_tx','longitude_tx','latitude_an','longitude_an','latitude_ao','longitude_ao','latitude_bo','longitude_bo','latitude_bn','longitude_bn']

class FileNameBuilder:
    def __init__(self, outputFolder, productType, splitbyband, configProfile, xfduManifest=None):
        self.outputFolder = outputFolder
        self.productType = productType
        self.splitbyband = splitbyband
        self.configProfile = configProfile
        if xfduManifest is not None:
            self.orbit = str(xfduManifest.orbitNumber)
            self.startTime = xfduManifest.startTime
            self.stopTime = xfduManifest.stopTime
            self.directory = self._buildDirectory()
            self.graphFileName = self._getGraphFile()
            self.summaryFileName = self._getSummaryFile()

    def buildFilePath(self, band, chunk):
        bandPrefix = (band if str(self.splitbyband).upper() == 'TRUE' else self.configProfile) + "_"
        return os.path.join(self.directory, bandPrefix + self.orbit + "_" + self.startTime + chunk + ".tif")

    def _buildDirectory (self):
        directory = os.path.join(self.outputFolder, self.productType, self.orbit)
        if not os.path.exists(directory):
           os.makedirs(directory)
        return directory
        
    def _getGraphFile(self):
        timestamp = int(round(time.time()*1000))
        return os.path.join(self.directory, self.startTime + '_' + str(timestamp) + 'graph.xml')
        
    def _getSummaryFile(self):
        return os.path.join(self.directory, self.startTime + 'summary.properties')

def formatTime(time):
  mytime = parser.parse(time)
  #round seconds if microseconds are > 500000
  if mytime.microsecond > 500000:
     mytime = mytime + datetime.timedelta(seconds=1)
  return mytime.strftime('%Y') + mytime.strftime('%m') + mytime.strftime('%d') + 'T' + mytime.strftime('%H') + mytime.strftime('%M') + mytime.strftime('%S') 

def getDeltaSeconds(newTime, oldTime):
    old = parser.parse(oldTime)
    new = parser.parse(newTime)
    return (new - old).seconds

def splitBands(splitbyband):
    return str(splitbyband).upper() == 'TRUE'

def skipBand (band):
    if (band):
        bandName = band.lower()
        if (bandName not in coordinates):
            return False
    return True
    
def setGPTCommand(GPTArguments, graphFile):
    command = ["gpt.sh"]
    #command = ["java","-cp","\"../modules/*:../lib/*\"",
    #           "-Dsnap.mainClass=org.esa.snap.core.gpf.main.GPT",
    #           "-Dsnap.home=\"../\"","-Xmx2400M","org.esa.snap.runtime.Launcher"]
    
    command = appendOptions(GPTArguments, command)
    command.append(graphFile)
    return command

def appendOptions(options, command):
    if (options is not None):
        options = options.replace('\"','')
        options = options.split(' ')
        for option in options:
            command.append(option)
    return command

def fileNotExists(inputFile, action):
    if not os.path.exists(inputFile):
        message = inputFile + "Doesn't exist. " + action
        return message

def execute(command):
    logger.info('Executing: ' + getCommandString(command))
    try:
        command_line_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        process_output, _ =  command_line_process.communicate()
        logger.info(process_output)
    except (OSError) as exception:
        logger.error('Exception occured', exc_info=True)
        logger.info('Subprocess failed: ' + getCommandString(command))
        raise
    else:
        # no exception was raised
        logger.info('Done')
    return True

def getCommandString(command):
    if (command):
        return ' '.join(str(e) for e in command)
    return ''
