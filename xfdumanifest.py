from settings import *
from utilities import *
from xml.dom import minidom
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError  # XML formatting errors
import settings

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
            imageTags = self.tree.findall(tag)
            return imageTags[0]
        imageSizeNodes = self.tree.findall(tag)
        for imageSizeNode in imageSizeNodes:
            attributes = imageSizeNode.attrib
            if 'grid' in attributes:
               value = attributes['grid']
               if (value == attribute):
                  return imageSizeNode

    def rows(self, imageSizeTag):
        item = self._getImageSize(imageSizeTag)
        return int(item.find(settings.xfduRowsKey).text)

    def columns(self, imageSizeTag):
        item = self._getImageSize(imageSizeTag)
        return int(item.find(settings.xfduColumnsKey).text)

    @property
    def orbitNumber(self):
        return int(self.tree.find(settings.xfduOrbitKey).text)

    @property
    def startTime(self):
        return formatTime(self.tree.find(settings.xfduStartTimeKey).text)

    @property
    def stopTime(self):
        return formatTime(self.tree.find(settings.xfduStopTimeKey).text)
