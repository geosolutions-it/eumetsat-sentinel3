import math
import string
import sys
import time
import os
import logging
import settings
from utilities import *
from os import listdir
from settings import *

# Initialize definition nodes
global readNode 
global subsetRegionNode
global selectBandNode
global bandMathsNode
global writeNode
global reprojectNode

readFile = open("nodes/readNode.xml")
readNode = readFile.readlines();
readFile.close()

subsetRegionFile = open("nodes/subsetRegionNode.xml")
subsetRegionNode = subsetRegionFile.readlines()
subsetRegionFile.close()

selectBandFile = open("nodes/selectBandNode.xml")
selectBandNode = selectBandFile.readlines()
selectBandFile.close()

bandMathsFile = open("nodes/bandMathsNode.xml")
bandMathsNode = bandMathsFile.readlines()
bandMathsFile.close()

writeFile = open("nodes/writeNode.xml")
writeNode = writeFile.readlines()
writeFile.close()

reprojectFile = open("nodes/reprojectNode.xml")
reprojectNode = reprojectFile.readlines()
reprojectFile.close()

logger = logging.getLogger('graphbuilder')
#logger.setLevel(logging.DEBUG)
minChunkSize = 100

class GraphBuilder():
    
    def __init__(self, graphFileName, configuration):
        self.graphFileName = graphFileName
        self.configuration = configuration

    def generateGraph(self, inputFile, inputFormat, chunksManager, templateDictionary, productSummary):
        try:
            logger.info("Creating the Graph: " + str(self.graphFileName))
            self.graphFile =  open(self.graphFileName, "w")
            self.graphFile.write("<graph>\n<version>1.0</version>\n")
            self._appendReadNode(inputFile, inputFormat)
            self._appendChunks(chunksManager, templateDictionary, productSummary)
            self._endGraph()
        except Exception:
            if self.configuration.cleanupOnFailure and self.graphFile is not None:
                os.remove(graphFileName)
            raise

    def _appendReadNode(self, inputFile, inputFormat):
        logger.debug("Appending read node for: " + inputFile)
        for line in readNode:
            if '$INPUTFILE' in line:
                line = line.replace('$INPUTFILE', inputFile)
            if '$FORMAT' in line:
                if inputFormat:
                    line = line.replace('$FORMAT', inputFormat)
                else:
                    line = ""
            self.graphFile.write(line)

    def _appendChunks(self, chunksManager, templateDictionary, productSummary):
        for verticalIndex in range(0, chunksManager.verticalChunks):
            for horizontalIndex in range(0, chunksManager.horizontalChunks):
                #Appending chunk nodes
                self._appendChunkNode(chunksManager, horizontalIndex, verticalIndex, templateDictionary, productSummary)

    # Append the whole definition of a chunk processing
    def _appendChunkNode(self, chunksManager, horizontalIndex, verticalIndex, templateDictionary, productSummary):
        chunkDefinition = chunksManager.getChunk(horizontalIndex, verticalIndex)
        logger.debug("Appending Chunk node. " + chunksManager.getChunkInformation(chunkDefinition))
        subsetId = "SUBSET" + chunkDefinition.chunkID 
        for line in subsetRegionNode:
            if '$SUBSETREGIONID' in line:
                line = line.replace('$SUBSETREGIONID', subsetId)
            if '$REGION' in line:
                line = line.replace('$REGION', chunkDefinition.region)
            if '$BANDNAMES' in line:
                bands = templateDictionary['$BANDNAMES']
                flagsManagement = templateDictionary['$FLAGS']
                controlBands = getControlBands(flagsManagement)
                if controlBands is not None:
                    bands += ("," + controlBands)
                line = line.replace('$BANDNAMES', bands)
            self.graphFile.write(line)
        
        reprojectId = subsetId.replace("SUBSET", "REPROJECT")
        self.appendReprojectNode(reprojectId, subsetId, templateDictionary)
        self.appendBandOpAndWriteNode(reprojectId, templateDictionary, chunkDefinition.chunkID, productSummary)

    # Append the definition of a Reprojection Node    
    def appendReprojectNode(self, reprojectId, subsetId, templateDictionary):
        for line in reprojectNode:
            if '$REPROJECTID' in line:
                line = line.replace('$REPROJECTID', reprojectId)
            if '$REFID' in line:
                line = line.replace('$REFID', subsetId)
            else:
                for dictionaryKey in templateDictionary:
                    if dictionaryKey in line:
                        line = line.replace(dictionaryKey, templateDictionary[dictionaryKey])
            self.graphFile.write(line)
        
    # Append the definition of a Subset Node (to isolate a band) and related write
    def appendBandOpAndWriteNode(self, reprojectId, templateDictionary, chunk, productSummary):
        bandNames = templateDictionary['$BANDNAMES']
        fileNameBuilder = productSummary.fileNameBuilder
        splitbyband = fileNameBuilder.splitbyband
        flagsManagement = templateDictionary['$FLAGS']
        outputBands = getOutputBands(flagsManagement)
        if (len(chunk)>0):
            productSummary.updateChunks(chunk)
            
        if outputBands is not None:
            bandNames = getOutputBandnames(outputBands)
            productSummary.bandNames = bandNames
        bands = bandNames.split(',')    
        if splitBands(splitbyband):
            for band in bands:
                if skipBand(band):
                    continue
                bandId = reprojectId.replace("REPROJECT", "BAND") + "_" + band
                logger.debug("Appending select and write nodes for band: " + band)
                self.appendBandNode(reprojectId, bandId, band, outputBands)
                self.appendWriteNode(bandId, band, templateDictionary, fileNameBuilder, chunk)
        else:
            bandNames = ""
            for band in bands:
                if not skipBand(band):
                    bandNames += (band + ',')
            bandNames = bandNames[:-1]
            bandId = reprojectId.replace("REPROJECT", "BAND")
            logger.debug("Appending select and write nodes for band: " + bandId)
            self.appendBandNode(reprojectId, bandId, bandNames, outputBands)
            self.appendWriteNode(bandId, bandNames, templateDictionary, fileNameBuilder, chunk)

    def appendBandNode(self, reprojectId, bandId, band, outputBands = None):
        if outputBands is None:
            self.appendBandSelectNode(reprojectId, bandId, band)
        else:
            self.appendBandMathsNode(reprojectId, bandId, band, outputBands)
            
    def appendBandMathsNode(self, reprojectId, bandId, band, outputBands):
        for line in bandMathsNode:
            if '$BANDMATHID' in line:
                line = line.replace('$BANDMATHID', bandId)
            if '$TARGETBANDS' in line:
                bandMaths = buildTargetBands(outputBands);
                line = line.replace('$TARGETBANDS', bandMaths)
            if '$REFID' in line:
                line = line.replace('$REFID', reprojectId)
            self.graphFile.write(line)


    def appendBandSelectNode(self, reprojectId, bandId, band):
        for line in selectBandNode:
            if '$SELECTBANDID' in line:
                line = line.replace('$SELECTBANDID', bandId)
            if '$BANDNAMES' in line:
                line = line.replace('$BANDNAMES', band)
            if '$REFID' in line:
                line = line.replace('$REFID', reprojectId)
            self.graphFile.write(line)

    # Append the definition of a Write node with proper outputFile naming
    def appendWriteNode(self, bandId, band, templateDictionary, fileNameBuilder, chunk):
        writeId = "WRITE_" + bandId
        outputfile = fileNameBuilder.buildFilePath (band, chunk)
        for line in writeNode:
            if '$WRITEID' in line:
                line = line.replace('$WRITEID', writeId)
            elif '$REFID' in line:
                line = line.replace('$REFID', bandId)
            elif '$FORMAT' in line:
                line = line.replace('$FORMAT', templateDictionary['$FORMAT'])
            if '$OUTPUTFILE' in line:
                line = line.replace('$OUTPUTFILE', outputfile)
            self.graphFile.write(line)

    def _endGraph(self):
        self.graphFile.write("\n</graph>")
        self.graphFile.close()

class ChunkDefinition:
    def __init__ (self, chunkID, region, width, height, horizontalIndex, verticalIndex):
        self.chunkID = chunkID
        self.region = region
        self.width = width
        self.height = height
        self.horizontalIndex = horizontalIndex
        self.verticalIndex = verticalIndex
                
class ChunksManager:
    def __init__(self, columns, rows, blocksize, config):
        self.columns = columns
        self.rows = rows
        self.configuration = config
        self.blocksize = blocksize

        # Get chunk sizes if defined
        chunkWidth = columns
        chunkHeight = rows
        if (blocksize is not None):
            blocksizes = blocksize.split(',')
            
            # TODO: Make sure to handle wrong conditions
            if (len(blocksizes) == 2):
                if (blocksizes[0] == 'fullswath'):
                    chunkWidth = columns
                else: 
                    chunkWidth = int(blocksizes[0])
                chunkHeight = int(blocksizes[1]) 

        self.subRegion = chunkWidth != columns or chunkHeight != rows
        self.regions = 1
        horizontalChunks = 1
        verticalChunks = 1
        lastChunkWidth = chunkWidth
        lastChunkHeight = chunkHeight
        if (self.subRegion):
            if (chunkWidth != self.columns):
                horizontalChunks = 1 + int(math.ceil(((self.columns - chunkWidth) / float(chunkWidth - self.configuration.overlapping))))
                if (horizontalChunks > 1):
                    lastChunkWidth = columns + ((horizontalChunks - 1) * self.configuration.overlapping) - ((horizontalChunks-1) * chunkWidth)
                    if (lastChunkWidth < minChunkSize):
                        horizontalChunks -= 1
                        lastChunkWidth = chunkWidth + lastChunkWidth - self.configuration.overlapping
            if (chunkHeight != self.rows):
                verticalChunks = 1 + int(math.ceil(((self.rows - chunkHeight) / float(chunkHeight - self.configuration.overlapping))))
                if (verticalChunks > 1):
                    lastChunkHeight = rows + ((verticalChunks - 1) * self.configuration.overlapping) - ((verticalChunks-1) * chunkHeight)
                    if (lastChunkHeight < minChunkSize):
                        verticalChunks -= 1
                        lastChunkHeight = chunkHeight + lastChunkHeight - self.configuration.overlapping

        self.regions = horizontalChunks * verticalChunks
        self.chunkWidth = chunkWidth
        self.chunkHeight = chunkHeight
        self.lastChunkHeight = lastChunkHeight
        self.lastChunkWidth = lastChunkWidth
        self.horizontalChunks = horizontalChunks
        self.verticalChunks = verticalChunks

    def getChunk(self, horizontalIndex, verticalIndex):
        overlapping = self.configuration.overlapping
        width = self.chunkWidth
        height = self.chunkHeight
        if (self.regions == 1):
            region = "0,0," + str(width) + "," + str(height)
            chunk = "_"
        else:
            xOffset = 0 if (horizontalIndex == 0) else (horizontalIndex * (self.chunkWidth - overlapping))
            xOffset = self.columns if (xOffset > self.columns) else xOffset
            yOffset = 0 if (verticalIndex == 0) else (verticalIndex * (self.chunkHeight - overlapping))
            yOffset = self.rows if (yOffset > self.rows) else yOffset
            width = self.columns - xOffset if (horizontalIndex == self.horizontalChunks - 1) else self.chunkWidth
            height = self.rows - yOffset if (verticalIndex == self.verticalChunks - 1) else self.chunkHeight
            region = str(xOffset) + "," + str(yOffset) + "," + str(width) + "," + str(height)
            chunk = "_R" + str(verticalIndex + 1).zfill(2) + "C" + str(horizontalIndex + 1).zfill(2)
        return ChunkDefinition(chunk, region, width, height, horizontalIndex, verticalIndex)

    def getChunkInformation(self, chunkDefinition):
        #TODO return more info
        return "Chunking details (" + chunkDefinition.chunkID + "): horizontalChunk=" + str(chunkDefinition.horizontalIndex+1) + " of " +\
               str(self.horizontalChunks) + " ; verticalChunk=" + str(chunkDefinition.verticalIndex+1) + " of " +\
               str(self.verticalChunks) + " rows=" + str(self.rows) + " columns=" + str(self.columns) +\
               " region: " + chunkDefinition.region
