import ConfigParser
from utilities import *
import os
import json
import logging
import logging.config
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

#Properties
summaryPropertiesFile = 'summary.properties'
loggingPropertiesFile = 'logging.properties'
manifestFile = 'xfdumanifest.xml'
configFile = 'config.xml'

blocksize                 = None
gdalOptions               = None
overviews                 = 0

#Default values
defaultInterpolationValue = 'Nearest' 
defaultNodataValue        = float('NaN')
defaultOutputFormatValue  = 'GeoTIFF'
defaultSplitByBand        = 'True'
defaultGranulesPerMosaic  = -1
defaultTimePeriod         = -1
defaultResolutionValue    = 0.01
defaultGDALCreateOptions  = 'TILED=YES SPARSE_OK=TRUE COMPRESS=DEFLATE'
defaultGPTArguments       = '-c 1200M'
defaultOverlapping        = 5
defaultOverviews          = 5
defaultDeleteFiles        = False
defaultCleanupOnFailure   = True
defaultWriteSummary       = None
defaultDoMosaic           = True

gdalWarpCommand = 'gdalwarp -wo SKIP_NOSOURCE=YES -srcnodata $SRC_NODATA_VALUE -dstnodata $DST_NODATA_VALUE'
gdalVRTCommand  = 'gdalbuildvrt -srcnodata $SRC_NODATA_VALUE -vrtnodata $VRT_NODATA_VALUE'
gdalAddoCommand = 'gdaladdo -r average' 
gdalrgbCommand  = 'gdal_translate -OT Byte -CO TILED=YES $PARAMETERS'


#Keys
nodataKey           = 'nodata'
interpolationKey    = 'interpolation'
stopTimeKey         = 'stoptime'
startTimeKey        = 'starttime'
orbitKey            = 'orbit'
bandnamesKey        = 'bandNames'
productTypeKey      = 'producttype'
resolutionKey       = 'resolution'
splitbybandKey      = 'splitbyband'
controlbandsKey     = 'controlBands'
blocksizeKey        = 'blocksize'
directoryKey        = 'directory'
chunksKey           = 'chunks'
locationKey         = 'location'

#Profile keys
flagsManagementKey  = 'flagsManagement'
outputBandKey       = 'outputBand'
targetBandKey       = 'targetBand'
preMosaicProcessKey = 'preMosaicProcess'
methodKey           = 'method'
parametersKey       = 'parameters'
profileKey          = 'profile'
defaultProfileKey   = 'defaultProfile'
outputbandsKey      = 'outputBands'

#Processing element keys
deleteFilesKey      = 'deleteFiles'
cleanupOnFailureKey = 'cleanupOnFailure'
writeSummaryKey     = 'writeSummary'
mosaickKey          = 'mosaic'
overlappingKey      = 'overlapping'

#XFDU Manifest keys
xfduRowsKey         = '{http://www.esa.int/safe/sentinel/sentinel-3/1.0}rows'
xfduColumnsKey      = '{http://www.esa.int/safe/sentinel/sentinel-3/1.0}columns'
xfduOrbitKey        = 'metadataSection/metadataObject[@ID="measurementOrbitReference"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/1.1}orbitReference/{http://www.esa.int/safe/sentinel/1.1}orbitNumber'
xfduStartTimeKey    = 'metadataSection/metadataObject[@ID="acquisitionPeriod"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/1.1}acquisitionPeriod/{http://www.esa.int/safe/sentinel/1.1}startTime'
xfduStopTimeKey     = 'metadataSection/metadataObject[@ID="acquisitionPeriod"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/1.1}acquisitionPeriod/{http://www.esa.int/safe/sentinel/1.1}stopTime'

OLCIL1VersionKey    = 'esa/safe/sentinel/sentinel-3/olci/level-1/1.0'
OLCIL2VersionKey    = 'esa/safe/sentinel/sentinel-3/olci/level-2/1.0'
SLSTRL1VersionKey   = 'esa/safe/sentinel/sentinel-3/slstr/level-1/1.0'
SLSTRL2VersionKey   = 'esa/safe/sentinel/sentinel-3/slstr/level-2/1.0'

#Sections
defaultSection      = 'DEFAULT'
processingSection   = 'processing'
mosaickingSection   = 'mosaicking'
summarySection      = 'Summary'


def getElementValue(referenceNode, tag):
    value = None
    if referenceNode is not None:
        node = referenceNode.find(tag);
        if node is not None:
            value = node.text
    return value

def getNode(referenceNode, tag):
    returnedNode = None
    if referenceNode is not None:
        returnedNode = referenceNode.find(tag);
    return returnedNode

def getOptionalElementValue(referenceNode, tag):
    value = None
    if referenceNode is not None:
        node = referenceNode.find(tag);
        if node is not None:
            value = node.text
    return value

def getControlBands(flagsManagementNode):
    controlBands = None
    if flagsManagementNode is not None:
        controlBands = getElementValue(flagsManagementNode, controlbandsKey)
    return controlBands

def getOutputBands(flagsManagementNode):
    outputBands = None
    if flagsManagementNode is not None:
        outputBands = getNode(flagsManagementNode, outputbandsKey)
    return outputBands

def buildTargetBands(outputBands):
    xmlString = ET.tostring(outputBands)
    xmlString = xmlString.replace(outputBandKey, targetBandKey)
    xmlString = xmlString.replace('<targetBands>', '')
    xmlString = xmlString.replace('</targetBands>', '')
    
    #insert the type element
    xmlString = xmlString.replace('<name>','<type>Float32</type><name>')
    return xmlString

def getOutputBandnames(outputBandsNode):
    outputBandnames = ""
    if outputBandsNode is not None:
        outputBandNodes = outputBandsNode.findall('outputBand')
        for outputBandNode in outputBandNodes:
            bandName = outputBandNode.find('name')
            if bandName is not None:
                outputBandnames += (bandName.text + ',')
    return outputBandnames[:-1]

def _setBooleanValue(defaultElement, defaultValue):
        return str(defaultElement.text).upper() == 'TRUE' if defaultElement is not None else defaultValue

class ProductConfig:
    
    def __init__(self, versionName, shortName, imageSizeTag):
        self.versionName = versionName
        self.shortName = shortName
        self.imageSizeTag = imageSizeTag

productConfigs = {
    OLCIL1VersionKey: ProductConfig(OLCIL1VersionKey,'OLCIL1',
    'metadataSection/metadataObject[@ID="olciProductInformation"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/sentinel-3/olci/1.0}olciProductInformation/{http://www.esa.int/safe/sentinel/sentinel-3/olci/1.0}imageSize'),

    OLCIL2VersionKey: ProductConfig(OLCIL2VersionKey,'OLCIL2',
    'metadataSection/metadataObject[@ID="olciProductInformation"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/sentinel-3/olci/1.0}olciProductInformation/{http://www.esa.int/safe/sentinel/sentinel-3/olci/1.0}imageSize'),
    
    SLSTRL1VersionKey: ProductConfig(SLSTRL1VersionKey,'SLSTRL1',
    'metadataSection/metadataObject[@ID="slstrProductInformation"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/sentinel-3/slstr/1.0}slstrProductInformation/{http://www.esa.int/safe/sentinel/sentinel-3/slstr/1.0}nadirImageSize'),

    SLSTRL2VersionKey: ProductConfig(SLSTRL2VersionKey,'SLSTRL2',
    'metadataSection/metadataObject[@ID="slstrProductInformation"]/metadataWrap/xmlData/{http://www.esa.int/safe/sentinel/sentinel-3/slstr/1.0}slstrProductInformation/{http://www.esa.int/safe/sentinel/sentinel-3/slstr/1.0}nadirImageSize')}

class Configuration:

    def _parseGDALOptions(self, gdalOptionsNode):
        nodes = gdalOptionsNode.findall('*')
        if gdalOptionsNode is not None and len(nodes) > 0:
            gdalOptions = []
            for gdalOption in gdalOptionsNode:
                gdalCreateOption = gdalOption.tag + "=" + gdalOption.text
                appendOptions(gdalCreateOption, gdalOptions)
            return gdalOptions
        return None

    def _parseGPTArguments(self, gptArgumentsNode):
        if (gptArgumentsNode is not None):
            GPTArguments = ''
            tileCacheMemoryNode = gptArgumentsNode.find('tileCacheMemory')
            if tileCacheMemoryNode is not None:
                GPTArguments += (' -c ' + tileCacheMemoryNode.text)
            flushCacheNode = gptArgumentsNode.find('flushCache')
            if flushCacheNode is not None and (str(flushCacheNode.text).upper() == 'TRUE'):
                GPTArguments += ' -x'

            threadsNode = gptArgumentsNode.find('threads')
            if threadsNode is not None:
                GPTArguments += (' -q ' + threadsNode.text)
                
            JVMArgumentsNode = gptArgumentsNode.find('JVMArguments')
            if JVMArgumentsNode is not None:
                GPTArguments += ' ' + JVMArgumentsNode.text
            return GPTArguments.strip()
        return defaultGPTArguments

    def _parseProfiles(self, profilesNode):
        self.profileDefinition = {}
        for profileNode in profilesNode:
            self.profileDefinition[profileNode.tag] = profileNode

    def _parseProducts(self, productsNode):
        # Setting defaults
        self.productDefinition = {}
        self.defaultNoData = defaultNodataValue
        self.defaultInterpolation = defaultInterpolationValue
        self.defaultOutputFormat = defaultOutputFormatValue
        self.defaultResolution = defaultResolutionValue
        for productNode in productsNode:
            # Parsing defaults
            if productNode.tag.lower() == 'default':
                noDataElement = productNode.find(nodataKey)
                self.defaultNodata = noDataElement.text if noDataElement is not None else defaultNodataValue
                interpolationElement = productNode.find(interpolationKey)
                self.defaultInterpolation = interpolationElement.text if interpolationElement is not None else defaultInterpolationValue
                formatElement = productNode.find('format')
                self.defaultOutputFormat = formatElement.text if formatElement is not None else defaultOutputFormatValue
                resolutionElement = productNode.find(resolutionKey)
                self.defaultResolution = resolutionElement.text if resolutionElement is not None else defaultResolutionValue
            else:
                self.productDefinition[productNode.tag] = productNode

    def __init__(self, inputFile):
        rootConfig = ET.parse(inputFile).getroot()
        mosaickingNode = rootConfig.find(mosaickingSection)
        mainNode = rootConfig.find(processingSection)
        productsNode = rootConfig.find('products')
        profilesNode = rootConfig.find('profiles')

        # Parse mosaicking settings
        maxGranulesElement = mosaickingNode.find('maxGranulesPerMosaic')
        self.granulesPerMosaic = int(maxGranulesElement.text) if maxGranulesElement is not None else defaultGranulesPerMosaic
        overviewsElement = mosaickingNode.find('overviews')
        self.overviews = int(overviewsElement.text) if overviewsElement is not None else defaultOverviews
        maxTimeElement = mosaickingNode.find('maxTimePeriodPerMosaic')
        self.timePeriod = int(maxTimeElement.text) if maxTimeElement is not None else defaultTimePeriod
        self.gdalOptions = self._parseGDALOptions(mosaickingNode.find('GDALCreateOptions'))
        self.defaultSplitByBand = defaultSplitByBand

        # Parse processing settings
        deleteElement = mainNode.find(deleteFilesKey)
        self.deleteFiles = _setBooleanValue(deleteElement, defaultDeleteFiles)
        cleanupOnFailureElement = mainNode.find(cleanupOnFailureKey)
        self.cleanupOnFailure = _setBooleanValue(cleanupOnFailureElement, defaultCleanupOnFailure) 
        writeSummaryElement = mainNode.find(writeSummaryKey)
        self.writeSummary = _setBooleanValue(writeSummaryElement, defaultWriteSummary)  
        mosaicElement = mainNode.find(mosaickKey)
        self.doMosaic = _setBooleanValue(mosaicElement, defaultDoMosaic)
        
        overlappingElement = mainNode.find(overlappingKey)
        self.overlapping = int(overlappingElement.text) if overlappingElement is not None else defaultOverlapping
        self.GPTArguments = self._parseGPTArguments(mainNode.find('GPTArguments'))
        outputFolderElement = mainNode.find('outputRootFolder')
        if outputFolderElement is None:
            raise IOError("<config><processing><outputRootFolder> is mandatory in " + configFile)
        self.outputFolder = outputFolderElement.text

        # Parse products settings
        self._parseProducts(productsNode)

        # Parse profiles settings
        self._parseProfiles(profilesNode)



    def _getProductNode(self, productTypeKey):
        if productTypeKey is not None and productTypeKey in self.productDefinition and self.productDefinition[productTypeKey] is not None:
            return self.productDefinition[productTypeKey]

    def getProfileNode(self, profileKey):
        if profileKey is not None and profileKey in self.profileDefinition and self.profileDefinition[profileKey] is not None:
            return self.profileDefinition[profileKey]

    def _getProductElementValue(self, productTypeKey, tag, defaultValue=None):
        productDefinitionNode = self._getProductNode(productTypeKey)
        value = defaultValue
        if productDefinitionNode is not None:
            node = productDefinitionNode.find(tag);
            if node is not None:
                value = node.text
        if (value == None and defaultValue == None):
            raise IOError("The specified element doesn\'t exist " + tag + " for the product " + productTypeKey)
        return value

    def getProductConfiguration(self, productTypeKey, profile = None):
        productType = productConfigs[productTypeKey].shortName
        imageSizeTag = productConfigs[productTypeKey].imageSizeTag
        interpolation = self.defaultInterpolation
        nodata = self.defaultNodata
        outputFormat = self.defaultOutputFormat
        splitbyband = self.defaultSplitByBand

        # Parse product type values
        resolution = self._getProductElementValue(productType, resolutionKey, self.defaultResolution)

        # Override defaults
        nodata = self._getProductElementValue(productType, nodataKey, self.defaultNodata)
        interpolation = self._getProductElementValue(productType, interpolationKey, self.defaultInterpolation)
        outputFormat = self._getProductElementValue(productType, 'format', self.defaultOutputFormat)
        productDefinitionNode = self._getProductNode(productType)
        blocksize = getOptionalElementValue(productDefinitionNode, blocksizeKey)
        configProfile = profile if profile is not None else getOptionalElementValue(productDefinitionNode, defaultProfileKey)

        configValues = {
            nodataKey : nodata, 
            interpolationKey : interpolation,
            resolutionKey : resolution, 
            'outputFormat' : outputFormat, 
            blocksizeKey : blocksize,
            'profile' : configProfile
            }
        
        #Retrieving profile overrides and additional settings
        readerFormat = None
        profileBandNames = None
        flagsManagement = None    
        if configProfile is not None:
            profileNode = self.getProfileNode(configProfile)
            if profileNode is None:
                raise Exception("The specified profile doesn't exist on configuration: " + configProfile
                                + "\nAvailable profiles: " + str(self.profileDefinition.keys()))
            split = getElementValue(profileNode, splitbybandKey)
            if split is not None:
                splitbyband = split
            readerFormat = getElementValue(profileNode, 'readerFormat')
            grid = getElementValue(profileNode, 'grid')
            if grid is not None:
                imageSizeTag += ('#' + grid)
            profileBandNames = getElementValue(profileNode, bandnamesKey)
            flagsManagement = getNode(profileNode, flagsManagementKey ) 
                
            
        inputFormat = readerFormat if readerFormat is not None else getOptionalElementValue(productDefinitionNode, 'readerFormat')

        bandNames = self._getProductElementValue(productType, bandnamesKey) if profileBandNames is None else profileBandNames
        configValues[splitbybandKey] = splitbyband    
        configValues['inputFormat'] = inputFormat
        configValues['imageSizeTag'] = imageSizeTag
        configValues[bandnamesKey] = bandNames
        configValues[flagsManagementKey] = flagsManagement

        logger.debug("Product Type: " + productType)
        logger.debug("Parsed configuration: " + str(configValues))
        return configValues


def setup_config():
    return Configuration(configFile)


def setup_logging(
    default_path=loggingPropertiesFile, 
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    '''Setup logging configuration

    '''
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        logging.config.fileConfig(path)
    else:
        logging.basicConfig(level=default_level)

setup_logging()
setup_config()


