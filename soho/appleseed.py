# Copyright (c) 2012 Bo Zhou

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import os
import sys

import hou
import soho
import sohog

from xml.etree.ElementTree import Element, ElementTree

##
#
class Attribute(object):

	def __init__(self, name, required, default, value):
		self.name     = name
		self.required = required
		self.defualt  = default
		self.value    = value


##
#
class Parameter(object):

	def __init__(self, name, required, default, value):
		self.name     = name
		self.required = required
		self.defualt  = default
		self.value    = value

##
#
class Node(object):

	def __init__(self):
		self.attributes = {}
		self.parameters = {}

	def Resolve(self, sohoObject, moments):
		pass


##
#
class Matrix(Node):

	def __init__(self):
		self.transformation = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


##
#
class Transform(Node):

	TIME = 'time'

	def __init__(self):
		super(Transform, self).__init__()

		self.matrix = Matrix()

		self.attributes[Transform.TIME] = Attribute(Transform.TIME, True, 0.0, 0.0)


##
#
class LookAt(Node):

	ORIGIN = 'origin'
	TARGET = 'target'
	UP     = 'up'

	def __init__(self):
		super(LookAt, self).__init__()

		self.attributes[LookAt.ORIGIN] = Attribute(LookAt.ORIGIN, True, (0, 0,   0), (0, 0,   0))
		self.attributes[LookAt.TARGET] = Attribute(LookAt.TARGET, True, (0, 0, - 1), (0, 0, - 1))
		self.attributes[LookAt.UP]     = Attribute(LookAt.UP,     True, (0, 1,   0), (0, 1,   0))


##
#
class Camera(Node):

	##
	# <camera> used attributes.
	NAME            = 'name'
	MODEL           = 'model'

	##
	# <camera> used parameters.
	FILM_DIMENSIONS = 'film_dimensions'
	FOCAL_LENGTH    = 'focal_length'

	##
	# Houdini used parameters.
	FOCAL           = 'focal'
	
	SUPPORTED_SOHO_PARAMS = {
		FOCAL : soho.SohoParm(FOCAL, 'float', [35.0],          False),
	}

	def __init__(self):
		super(Camera, self).__init__()

		self.attributes[Camera.MODEL]           = Attribute(Camera.MODEL,           True, 'pinhole_camera', 'pinhole_camera')

		self.parameters[Camera.FILM_DIMENSIONS] = Parameter(Camera.FILM_DIMENSIONS, True, (0.025, 0.025),   (0.025, 0.025))
		self.parameters[Camera.FOCAL_LENGTH]    = Parameter(Camera.FOCAL_LENGTH,    True,  35.0,             35.0)

		self.transform = Transform()

	def Resolve(self, sohoObject, moments):
		self.attributes[Camera.NAME] = sohoObject.getName()

		sohoParmsValues = sohoObject.evaluate(Camera.SUPPORTED_SOHO_PARAMS, moments[0])
		self.attributes[Camera.FOCAL_LENGTH] = sohoParmsValues[Camera.FOCAL].Value[0]
		print sohoParmsValues[Camera.FOCAL].Value[0]

		sohoObject.evalFloat('space:world', moments[0], self.transform.matrix.transformation)
		print self.transform.matrix.transformation


##
# Represents the <object> in the XML scene description.
#
class Geometry(Node):

	##
	# <object> used attributes.
	NAME  = 'name'
	MODEL = 'model'

	def __init__(self):
		super(Geometry, self).__init__()

	def SaveToWavefrontObj(self, sopPath, sohoGeometry):
		splittedSopPath = sopPath.split('/')

		## Check if the asset folder exists.
		#
		diskFilePath = soho.getDefaultedString('soho_diskfile', [''])[0]
		diskFileDir = os.path.dirname(diskFilePath)
		diskFileName = os.path.basename(diskFilePath)
		companionDir = '%s%s-assets' % (diskFileDir, diskFileName.split('.')[0])
		print companionDir
		if not os.path.exists(companionDir):
			if not os.path.isdir(companionDir):
				os.remove(companionDir)
			os.mkdir(companionDir)

		formattedSopPath = sopPath.replace('/', '__')
		objFileName = formattedSopPath + '.obj'
		objFilePath = os.path.join(companionDir, objFileName)
		print objFilePath

		## Export out the polygons.
		#
		file = open(objFilePath, 'w')

		file.write('# %s\n' % sopPath)
		file.write('g %s\n' % formattedSopPath)

		geoPointCount = sohoGeometry.globalValue('geo:pointcount')[0]
		geoPrimCount = sohoGeometry.globalValue('geo:primcount')[0]

		file.write('# %d vertices, %d primitives.\n' % (geoPointCount, geoPrimCount))

		# v		
		geoPointP = sohoGeometry.attribute('geo:point', 'P')
		for i in xrange(geoPointCount):
			v = sohoGeometry.value(geoPointP, i)
			file.write('v %.10f %.10f %.10f\n' % (v[0], v[1], v[2]))

		# vt
		hasUV = False
		geoPrimVertexCount = sohoGeometry.attribute('geo:prim', 'geo:vertexcount')
		geoVertexAttribs = sohoGeometry.globalValue('geo:vertexattribs')
		for geoVertexAttrib in geoVertexAttribs:
			if geoVertexAttrib == 'uv':
				geoVertexUV = sohoGeometry.attribute('geo:vertex', 'uv')
				for i in xrange(geoPrimCount):
					for j in xrange(sohoGeometry.value(geoPrimVertexCount, i)[0]):
						v = sohoGeometry.vertex(geoVertexUV, i, j)
						file.write('vt %.10f %.10f\n' % (v[0], v[1]))
				hasUV = True

		# f
		fakeUVIndex = 1;
		geoVertexPointRef = sohoGeometry.attribute('geo:vertex', 'geo:pointref')

		if hasUV:
			for i in xrange(geoPrimCount):
				file.write('f')
				for j in xrange(sohoGeometry.value(geoPrimVertexCount, i)[0]):
					v = sohoGeometry.vertex(geoVertexPointRef, i, j)
					file.write(' %d/%d' % (v[0] + 1, fakeUVIndex))
					fakeUVIndex += 1
				file.write('\n')
		else:
			for i in xrange(geoPrimCount):
				file.write('f')
				for j in xrange(sohoGeometry.value(geoPrimVertexCount, i)[0]):
					v = sohoGeometry.vertex(geoVertexPointRef, i, j)
					file.write(' %d' % (v[0] + 1))
				file.write('\n')

		file.close()

		return objFilePath

	def Resolve(self, sohoObject, moments):
		sopPath = sohoObject.getDefaultedString('object:soppath', sohoObject, [''])[0]
		self.attributes[Geometry.NAME] = sopPath

		sohoGeometry = sohog.SohoGeometry(sopPath, moments[0])
		objFilePath = self.SaveToWavefrontObj(sopPath, sohoGeometry)


##
#
if __name__ == '__builtin__':

	moments = soho.getDefaultedFloat('state:time', [0.0])
	cameras = soho.getDefaultedString('camera', ['/obj/cam1'])

	if soho.initialize(moments[0], cameras[0]):
		if soho.addObjects(moments[0], '*', '*', '*'):
			pass
		else:
			soho.error('Unable to add objects.')
	else:
		soho.error('Unable to initialize.')

	soho.lockObjects(moments[0])

	for sohoCamera in soho.objectList('objlist:camera'):
		camera = Camera()
		camera.Resolve(sohoCamera, moments)

	for sohoGeometry in soho.objectList('objlist:instance'):
		geometry = Geometry()
		geometry.Resolve(sohoGeometry, moments)
