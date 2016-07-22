from settings import *
from utilities import *
from xml.dom import minidom
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError  # XML formatting errors
import settings

idPrefix = '[@ID="'
idSuffix = '"]/'

class XfduManifest:

    def __init__(self, inputFile):
        self.tree = ElementTree.parse(inputFile)
        self.rootNode = self.tree.getroot()
        self.productType = self.rootNode.get('version')

    def _getImageSize(self, imageSizeTag):
        tag = imageSizeTag
        attribute = None
        if "#" in imageSizeTag:
           tagAndAttribute = imageSizeTag.split('#')
           tag = tagAndAttribute[0]
           attribute = tagAndAttribute[1]
        if (attribute is None):
            return self._findElement(tag)
        return self._findElement(tag,'grid=' + attribute)

    def rows(self, imageSizeTag):
        item = self._getImageSize(imageSizeTag)
        return int(item.find(settings.xfduRowsKey).text)

    def columns(self, imageSizeTag):
        item = self._getImageSize(imageSizeTag)
        return int(item.find(settings.xfduColumnsKey).text)

    @property
    def orbitNumber(self):
        element = self._findElement(settings.xfduOrbitKey)
        if element is not None:
            return int(element.text)
        raise ValueError('Unable to find the startTime node value')

    @property
    def startTime(self):
        element = self._findElement(settings.xfduStartTimeKey)
        if element is not None:
            return formatTime(element.text)
        raise ValueError('Unable to find the startTime node value')

    @property
    def stopTime(self):
        element = self._findElement(settings.xfduStopTimeKey)
        if element is not None:
            return formatTime(element.text)
        raise ValueError('Unable to find the stopTime node value')
    
    def _findElement(self, key, attrib = None):
        # This function has been added to work on python 2.6 which uses
        # ElementTree 1.2.6 doesn't support attribute xpath features 
        if idPrefix in key:
            keyComponent = key.split(idPrefix)
            parentNode = keyComponent[0]
            keyComponent = keyComponent[1].split(idSuffix)
            requestedID = keyComponent[0]
            childNode = keyComponent[1]
            nodes = self.tree.findall(parentNode)
            for node in nodes:
                nodeID = node.get('ID')
                # Looking for the node having the requested ID
                if (requestedID == nodeID):
                    subNodes = node.findall(childNode)
                    if subNodes is not None and len(subNodes)>0:
                        if attrib is None:
                            return subNodes[0]
                        else:
                            #attributes are specified in the form
                            #attribute=value
                            index = attrib.find('=')
                            if index > -1:
                                attribKey = attrib[:index]
                                attribValue = attrib[index+1:]
                                for subNode in subNodes:
                                    attributes = subNode.attrib
                                    if attribKey in attributes:
                                       value = attributes[attribKey]
                                       if (value == attribValue):
                                          return subNode  
        else:
            return self.tree.find(key)
        
        
