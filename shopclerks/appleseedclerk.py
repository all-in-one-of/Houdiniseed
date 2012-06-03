import hou
import clerkutil


class AppleseedClerk(object):

	def __init__(self):
		self.__name = 'appleseed'

		self.__shaderSupported = {
			'light'   : ['shop_appleseedLight'],
			'surface' : ['shop_appleseedBSDF',  'shop_appleseedMaterial'],
			'texture' : ['shop_appleseedColor', 'shop_appleseedTexture'],
		}

	def getName(self):
		return self.__name

	def isShaderSupported(self, style):
		return self.__shaderSupported.has_key(style)

	def buildShaderString(self, style, shopName, time, parmNames, options):
		return 'AppleseedClerk::buildShaderString %s %s %s %s %s' % (style, shopName, time, parmNames, options)

theAppleseedClerk = AppleseedClerk()


def getName():
	return theAppleseedClerk.getName()

def getLabel():
	return theAppleseedClerk.getName()

def getKeywords():
	return theAppleseedClerk.getName()

def shaderSupported(style):
	return theAppleseedClerk.isShaderSupported(style)

def buildShaderString(style, shopName, time, parmNames, options):
	return theAppleseedClerk.buildShaderString(style, shopName, time, parmNames, options)
