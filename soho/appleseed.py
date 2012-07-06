# Copyright (c) 2012 Bo Zhou<bo.schwarzstein@gmail.com>

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

from xml.etree.ElementTree import Element, ElementTree, SubElement, tostring


##
#
class Attr(object):

	NAME  = 'name'
	VALUE = 'value'

	def __init__(self, name, required, default, value):
		self.name     = name
		self.required = required
		self.defualt  = default
		self.value    = value

##
#
class Node(object):

	def __init__(self):
		self.attrs = {}

	def Resolve(self, sohoObject, moments):
		pass


##
#
class Project(Node):

	def __init__(self):
		self.scene          = Scene()
		self.output         = Output()
		self.configurations = Configurations()


##
#
class Scene(Node):

	def __init__(self):
		self.assembly = Assembly()
		self.camera   = Camera()

##
#
class Assembly(Node):

	NAME = 'name'

	def __init__(self):
		super(Assembly, self).__init__()

		self.objects = {}


##
# Represents the <object> in the XML scene description.
#
class Object(Assembly):

	##
	# <object> used attributes.
	NAME     = 'name'
	MODEL    = 'model'

	FILENAME = 'filename'


	def __init__(self):
		super(Object, self).__init__()
		self.attrs[Object.NAME]     = Attr(Object.NAME,  True, 'object', 'object')
		self.attrs[Object.MODEL]    = Attr(Object.MODEL, True, 'mesh_object', 'mesh_object')
		self.attrs[Object.FILENAME] = Attr(Object.MODEL, True, 'NOT-FOUND',   'NOT-FOUND')

	def SaveToWavefrontObj(self, sopPath, sohoGeometry):
		splittedSopPath = sopPath.split('/')

		## Check if the asset folder exists.
		#
		sohoDiskFilePath = soho.getDefaultedString('soho_diskfile', [''])[0]
		sohoDiskFileDir = os.path.dirname(sohoDiskFilePath)
		sohoDiskFileBaseName = os.path.basename(sohoDiskFilePath)
		companionDir = '%s%s-assets' % (sohoDiskFileDir, sohoDiskFileBaseName.split('.')[0])
		if not os.path.exists(companionDir):
			os.mkdir(companionDir)

		formattedSopPath = sopPath.replace('/', '__')
		objFileName = formattedSopPath + '.obj'
		objFilePath = os.path.join(companionDir, objFileName)

		self.attrs[Object.FILENAME].value = os.path.join('.', os.path.basename(companionDir), objFileName)

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
		self.attrs[Object.NAME].value = sopPath

		sohoGeometry = sohog.SohoGeometry(sopPath, moments[0])
		objFilePath = self.SaveToWavefrontObj(sopPath, sohoGeometry)
		

##
#
class Matrix(Node):

	def __init__(self):
		self.data = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


##
#
class Transform(Node):

	TIME = 'time'

	def __init__(self):
		super(Transform, self).__init__()

		self.matrix = Matrix()

		self.attrs[Transform.TIME] = Attr(Transform.TIME, True, 0.0, 0.0)


##
#
class LookAt(Node):

	ORIGIN = 'origin'
	TARGET = 'target'
	UP     = 'up'

	def __init__(self):
		super(LookAt, self).__init__()

		self.attrs[LookAt.ORIGIN] = Attr(LookAt.ORIGIN, True, (0, 0,   0), (0, 0,   0))
		self.attrs[LookAt.TARGET] = Attr(LookAt.TARGET, True, (0, 0, - 1), (0, 0, - 1))
		self.attrs[LookAt.UP]     = Attr(LookAt.UP,     True, (0, 1,   0), (0, 1,   0))


##
#
class Camera(Node):

	##
	# <camera> used attributes.
	NAME            = 'name'
	MODEL           = 'model'

	FILM_DIMENSIONS = 'film_dimensions'
	FOCAL_LENGTH    = 'focal_length'

	##
	# Houdini used parameters.
	FOCAL           = 'focal'
	
	SUPPORTED_SOHO_PARAMS = {
		FOCAL : soho.SohoParm(FOCAL, 'float', [35.0], False),
	}

	def __init__(self):
		super(Camera, self).__init__()
		
		self.attrs[Camera.NAME]            = Attr(Camera.NAME,            True, 'default',        'default')
		self.attrs[Camera.MODEL]           = Attr(Camera.MODEL,           True, 'pinhole_camera', 'pinhole_camera')

		self.attrs[Camera.FILM_DIMENSIONS] = Attr(Camera.FILM_DIMENSIONS, True, (0.025, 0.025),   (0.025, 0.025))
		self.attrs[Camera.FOCAL_LENGTH]    = Attr(Camera.FOCAL_LENGTH,    True,  35.0,             35.0)

		self.transform = Transform()

	def Resolve(self, sohoObject, moments):
		self.attrs[Camera.NAME].value = sohoObject.getName()

		sohoParmsValues = sohoObject.evaluate(Camera.SUPPORTED_SOHO_PARAMS, moments[0])
		self.attrs[Camera.FOCAL_LENGTH].value = sohoParmsValues[Camera.FOCAL].Value[0]

		sohoObject.evalFloat('space:world', moments[0], self.transform.matrix.data)

##
#
class XmlSerializer(object):

	def __init__(self):
		pass

	def Serialize(self, project):
		projectNode = Element('project')
		sceneNode = SubElement(projectNode, 'scene')

		## Serialize project:scene:camera.
		#
		camera = project.scene.camera

		cameraNode = SubElement(sceneNode, 'camera')

		cameraNode.attrib[Camera.NAME]  = camera.attrs[Camera.NAME].value
		cameraNode.attrib[Camera.MODEL] = camera.attrs[Camera.MODEL].value

		parameterNode = SubElement(cameraNode, 'parameter')
		parameterNode.attrib[Attr.NAME]  = Camera.FILM_DIMENSIONS
		parameterNode.attrib[Attr.VALUE] = '%f %f' % (camera.attrs[Camera.FILM_DIMENSIONS].value)

		parameterNode = SubElement(cameraNode, 'parameter')
		parameterNode.attrib[Attr.NAME]  = Camera.FOCAL_LENGTH
		parameterNode.attrib[Attr.VALUE]    = '%f' % (camera.attrs[Camera.FOCAL_LENGTH].value / 1000)

		transformNode = SubElement(cameraNode, 'transform')
		matrixNode = SubElement(transformNode, 'matrix')
		matrixNode.text = '%f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f' % (camera.transform.matrix.data[0],  camera.transform.matrix.data[1],  camera.transform.matrix.data[2],  camera.transform.matrix.data[3],
																			   camera.transform.matrix.data[4],  camera.transform.matrix.data[5],  camera.transform.matrix.data[6],  camera.transform.matrix.data[7],
																			   camera.transform.matrix.data[8],  camera.transform.matrix.data[9],  camera.transform.matrix.data[10], camera.transform.matrix.data[11],
																			   camera.transform.matrix.data[11], camera.transform.matrix.data[12], camera.transform.matrix.data[13], camera.transform.matrix.data[14])

		## Serialize project:scene:assembly
		#
		assemblyNode = SubElement(sceneNode, 'assembly')
		assemblyNode.attrib[Assembly.NAME] = 'assembly'

		## Serialize project:scene:assembly:object.
		#
		for (objectName, object) in project.scene.assembly.objects.iteritems():
			objectNode = SubElement(assemblyNode, 'object')

			objectNode.attrib[Object.NAME] = object.attrs[Object.NAME].value
			objectNode.attrib[Object.MODEL] = object.attrs[Object.MODEL].value

			parameterNode = SubElement(objectNode, 'parameter')
			parameterNode.attrib[Attr.NAME]  = Object.FILENAME
			parameterNode.attrib[Attr.VALUE] = object.attrs[Object.FILENAME].value

		## Serialize project:output
		#
		outputNode = SubElement(projectNode, 'output')
		for (frameName, frame) in project.output.frames.iteritems():
			frameNode = SubElement(outputNode, 'frame')
			frameNode.attrib[Frame.NAME] = frame.attrs[Frame.NAME].value

			parameterNode = SubElement(frameNode, 'parameter')
			parameterNode.attrib[Attr.NAME] = Frame.CAMERA
			parameterNode.attrib[Attr.VALUE] = frame.attrs[Frame.CAMERA].value

			(resx, resy) = frame.attrs[Frame.RESOLUTION].value
			parameterNode = SubElement(frameNode, 'parameter')
			parameterNode.attrib[Attr.NAME]  = Frame.RESOLUTION
			parameterNode.attrib[Attr.VALUE] = '%d %d' % (resx, resy)
			

		ElementTree(projectNode).write(sys.stdout, encoding = 'UTF-8')


##
#
class Output(Node):

	def __init__(self):
		self.frames = {}


##
#
class Frame(Node):

	NAME      = 'name'
	CAMERA    = 'camera'
	RESOLUTION = 'resolution'

	#
	COLOR_SPACE = 'color_space'
	TILE_SIZE = 'tile_size'
	

	SUPPORTED_SOHO_PARAMS = {
		CAMERA      : soho.SohoParm(CAMERA,      'string', ['/obj/cam1'],  False),
		COLOR_SPACE : soho.SohoParm(COLOR_SPACE, 'string', ['linear_rgb'], True),
		TILE_SIZE   : soho.SohoParm(TILE_SIZE,   'int',    [32],           True),
	}

	def __init__(self):
		super(Frame, self).__init__()

		self.attrs[Frame.NAME]       = Attr(Frame.NAME,      True,  None, '')
		self.attrs[Frame.CAMERA]     = Attr(Frame.CAMERA,    True,  None, '')
		self.attrs[Frame.RESOLUTION] = Attr(Frame.TILE_SIZE, True,  None, ())
		self.attrs[Frame.TILE_SIZE]  = Attr(Frame.TILE_SIZE, False, 32,   32)

	def Resolve(self, sohoObject, moments):
		(basicName, extensionName) = os.path.splitext(os.path.basename(hou.hipFile.name()))
		frameNumber = int(moments[0] * 24 + 1)
		self.attrs[Frame.NAME].value = '%s.%.4d' % (basicName, frameNumber)

		sohoParmsValues = soho.sohoglue.evaluate(Frame.SUPPORTED_SOHO_PARAMS, None, None)
		self.attrs[Frame.CAMERA].value = sohoParmsValues[Frame.CAMERA].Value[0]
		cameraHouNode = hou.node(sohoParmsValues[Frame.CAMERA].Value[0])
		resx = cameraHouNode.evalParm('resx')
		resy = cameraHouNode.evalParm('resy')
		self.attrs[Frame.RESOLUTION].value = (resx, resy)

		if sohoParmsValues.has_key(Frame.TILE_SIZE):
			tile_size = self.attrs[Frame.TILE_SIZE]
			tile_size.required = True
			tile_size.value    = sohoParmsValues[Frame.TILE_SIZE].Value[0]
			

##
#
class Configurations(Node):

	def __init__(self):
		pass

##
#
class Configuration(Node):

	def __init__(self):
		super(Configuration, self).__init__()

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

	project = Project()

	for sohoCamera in soho.objectList('objlist:camera'):
		camera = Camera()
		camera.Resolve(sohoCamera, moments)
		project.scene.camera = camera
		break

	for sohoGeometry in soho.objectList('objlist:instance'):
		object = Object()
		object.Resolve(sohoGeometry, moments)

		objectName = object.attrs[Object.NAME]
		if not project.scene.assembly.objects.has_key(objectName):
			project.scene.assembly.objects[objectName] = object

	frame = Frame()
	frame.Resolve(None, moments)
	project.output.frames[frame.attrs[Frame.NAME].value] = frame

	serializer = XmlSerializer()
	serializer.Serialize(project)
