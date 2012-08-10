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

	def __init__(self, name, value):
		self.name  = name
		self.value = value

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
		self.camera           = Camera()
		self.assembly         = Assembly()
		self.assemblyInstance = AssemblyInstance()


##
#
class Assembly(Node):

	NAME = 'name'

	def __init__(self):
		super(Assembly, self).__init__()

		self.objects = {}
		self.objectInstances = {}


##
#
class AssemblyInstance(Node):

	NAME     = 'name'
	ASSEMBLY = 'assembly'

	def __init__(self):
		super(AssemblyInstance, self).__init__()

		self.attrs[AssemblyInstance.NAME]     = Attr(AssemblyInstance.NAME,     'assembly_inst')
		self.attrs[AssemblyInstance.ASSEMBLY] = Attr(AssemblyInstance.ASSEMBLY, 'assembly')

		self.transform = Transform()


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

		self.attrs[Object.FILENAME] = Attr(Object.FILENAME, os.path.join('.', os.path.basename(companionDir), objFileName))

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
		self.attrs[Object.NAME] = Attr(Object.NAME, sopPath.replace('/', '__'))

		self.attrs[Object.MODEL] = Attr(Object.MODEL, 'mesh_object')

		sohoGeometry = sohog.SohoGeometry(sopPath, moments[0])
		objFilePath = self.SaveToWavefrontObj(sopPath, sohoGeometry)
		

##
#
class ObjectInstance(Assembly):
	
	##
	# <object> used attributes.
	NAME     = 'name'
	OBJECT   = 'object'

	def __init__(self):
		super(ObjectInstance, self).__init__()

		self.transform = Transform()

	def Resolve(self, sohoObject, moments):
		sopPath = sohoObject.getDefaultedString('object:soppath', sohoObject, [''])[0]
		name = sopPath.replace('/', '__')
		self.attrs[ObjectInstance.NAME] = Attr(ObjectInstance.NAME, name)
		self.attrs[ObjectInstance.OBJECT] = Attr(ObjectInstance.OBJECT, name + '.' + name)

		sohoObject.evalFloat('space:world', moments[0], self.transform.matrix.data)
		self.transform.matrix.data = hou.Matrix4(self.transform.matrix.data).transposed().asTuple()


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

	def Resolve(self, sohoObject, moments):
		self.attrs[Transform.TIME] = Attr(Transform.TIME, 0)


##
#
class LookAt(Node):

	ORIGIN = 'origin'
	TARGET = 'target'
	UP     = 'up'

	def __init__(self):
		super(LookAt, self).__init__()


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
	APERTURE        = 'aperture'
	FOCAL           = 'focal'
	RESX            = 'resx'
	RESY            = 'resy'
	
	SUPPORTED_SOHO_PARAMS = {
		APERTURE : soho.SohoParm(APERTURE, 'float', [25], False),
		FOCAL    : soho.SohoParm(FOCAL,    'float', [35.0], False),
		RESX     : soho.SohoParm(RESX,     'int',   [640],  False),
		RESY     : soho.SohoParm(RESY,     'int',   [480],  False),
	}

	def __init__(self):
		super(Camera, self).__init__()

		self.transform = Transform()

	def Resolve(self, sohoObject, moments):
		self.attrs[Camera.NAME] = Attr(Camera.NAME, sohoObject.getName())

		self.attrs[Camera.MODEL] = Attr(Camera.MODEL, 'pinhole_camera')

		sohoParmsValues = sohoObject.evaluate(Camera.SUPPORTED_SOHO_PARAMS, moments[0])

		resx = sohoParmsValues[Camera.RESX].Value[0]
		resy = sohoParmsValues[Camera.RESY].Value[0]

		aperture = sohoParmsValues[Camera.APERTURE].Value[0] / 1000.0
		self.attrs[Camera.FILM_DIMENSIONS] = Attr(Camera.FILM_DIMENSIONS, (aperture, float(resy) /  float(resx) * aperture))

		self.attrs[Camera.FOCAL_LENGTH] = Attr(Camera.FOCAL_LENGTH, sohoParmsValues[Camera.FOCAL].Value[0])

		sohoObject.evalFloat('space:world', moments[0], self.transform.matrix.data)
		self.transform.matrix.data = hou.Matrix4(self.transform.matrix.data).transposed().asTuple()


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

	def Resolve(self, sohoObject, moments):
		(basicName, extensionName) = os.path.splitext(os.path.basename(hou.hipFile.name()))
		frameNumber = int(moments[0] * 24 + 1)
		self.attrs[Frame.NAME] = Attr(Frame.NAME, '%s.%.4d' % (basicName, frameNumber))

		sohoParmsValues = soho.sohoglue.evaluate(Frame.SUPPORTED_SOHO_PARAMS, None, None)
		self.attrs[Frame.CAMERA] = Attr(Frame.CAMERA, sohoParmsValues[Frame.CAMERA].Value[0])
		cameraHouNode = hou.node(sohoParmsValues[Frame.CAMERA].Value[0])
		resx = cameraHouNode.evalParm('resx')
		resy = cameraHouNode.evalParm('resy')
		self.attrs[Frame.RESOLUTION] = Attr(Frame.RESOLUTION, (resx, resy))

		if sohoParmsValues.has_key(Frame.TILE_SIZE):
			self.attrs[Frame.TILE_SIZE] = Attr(Frame.TILE_SIZE, sohoParmsValues[Frame.TILE_SIZE].Value[0])


##
#
class Configurations(Node):

	NAME                  = 'name'
	BASE                  = 'base'
	BASE_FINAL            = 'base_final'
	BASE_INTERACTIVE       = 'base_interactive'

	BF_LIGHTING_ENGINE    = 'bf_lighting_engine'
	BF_MIN_SAMPLES        = 'bf_min_samples'
	BF_MAX_SAMPLES        = 'bf_max_samples'
	BF_SAMPLE_FILTER_SIZE = 'bf_sample_filter_size'
	BF_SAMPLE_FILTER_TYPE = 'bf_sample_filter_type'

	BI_LIGHTING_ENGINE    = 'bi_lighting_engine'
	BI_MIN_SAMPLES        = 'bi_min_samples'
	BI_MAX_SAMPLES        = 'bi_max_samples'
	BI_SAMPLE_FILTER_SIZE = 'bi_sample_filter_size'
	BI_SAMPLE_FILTER_TYPE = 'bi_sample_filter_type'

	SUPPORTED_SOHO_PARAMS = {
		BF_LIGHTING_ENGINE      : soho.SohoParm(BF_LIGHTING_ENGINE,    'string', ['pt'],       True),
		BF_MIN_SAMPLES          : soho.SohoParm(BF_MIN_SAMPLES,        'int',    [1],          True),
		BF_MAX_SAMPLES          : soho.SohoParm(BF_MAX_SAMPLES,        'int',    [1],          True),
		BF_SAMPLE_FILTER_SIZE   : soho.SohoParm(BF_SAMPLE_FILTER_SIZE, 'int',    [4],          True),
		BF_SAMPLE_FILTER_TYPE   : soho.SohoParm(BF_SAMPLE_FILTER_TYPE, 'string', ['mitcheal'], True),

		BI_LIGHTING_ENGINE      : soho.SohoParm(BI_LIGHTING_ENGINE,    'string', ['pt'],  True),
		BI_MIN_SAMPLES          : soho.SohoParm(BI_MIN_SAMPLES,        'int',    [1],     True),
		BI_MAX_SAMPLES          : soho.SohoParm(BI_MAX_SAMPLES,        'int',    [1],     True),
		BI_SAMPLE_FILTER_SIZE   : soho.SohoParm(BI_SAMPLE_FILTER_SIZE, 'int',    [1],     True),
		BI_SAMPLE_FILTER_TYPE   : soho.SohoParm(BI_SAMPLE_FILTER_TYPE, 'string', ['box'], True),
	}

	def __init__(self):
		super(Configurations, self).__init__()

	def Resolve(self, sohoObject, moments):
		sohoParmsValues = soho.sohoglue.evaluate(Configurations.SUPPORTED_SOHO_PARAMS, None, None)
		for key, value in sohoParmsValues.iteritems():
			self.attrs[key] = Attr(key, value.Value[0])


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
		matrixNode.text = ''
		for i in xrange(16):
			matrixNode.text += '%f ' % camera.transform.matrix.data[i]

		## Serialize project:scene:assembly
		#
		assemblyNode = SubElement(sceneNode, 'assembly')
		assemblyNode.attrib[Assembly.NAME] = 'assembly'

		## Serialize project:scene:assembly:object and project:scene:assembly:object_instance
		#
		for (objectName, object) in project.scene.assembly.objects.iteritems():
			objectNode = SubElement(assemblyNode, 'object')

			objectNode.attrib[Object.NAME] = object.attrs[Object.NAME].value
			objectNode.attrib[Object.MODEL] = object.attrs[Object.MODEL].value

			parameterNode = SubElement(objectNode, 'parameter')
			parameterNode.attrib[Attr.NAME]  = Object.FILENAME
			parameterNode.attrib[Attr.VALUE] = object.attrs[Object.FILENAME].value

		## Serialize project:scene:assembly:object_instance
		#
		for (objectInstanceName, objectInstance) in project.scene.assembly.objectInstances.iteritems():
			objectInstanceNode = SubElement(assemblyNode, 'object_instance')

			objectInstanceNode.attrib[ObjectInstance.NAME]   = objectInstance.attrs[ObjectInstance.NAME].value
			objectInstanceNode.attrib[ObjectInstance.OBJECT] = objectInstance.attrs[ObjectInstance.OBJECT].value

			transformNode = SubElement(objectInstanceNode, 'transform')
			matrixNode = SubElement(transformNode, 'matrix')
			matrixNode.text = ''
			for i in xrange(16):
				matrixNode.text += '%f ' % objectInstance.transform.matrix.data[i]

		## Serialize project:scene:assembly_instance
		#
		assemblyInstanceNode = SubElement(sceneNode, 'assembly_instance')
		assemblyInstanceNode.attrib[AssemblyInstance.NAME]     = project.scene.assemblyInstance.attrs[AssemblyInstance.NAME].value
		assemblyInstanceNode.attrib[AssemblyInstance.ASSEMBLY] = project.scene.assemblyInstance.attrs[AssemblyInstance.ASSEMBLY].value
		transformNode = SubElement(assemblyInstanceNode, 'transform')
		matrixNode = SubElement(transformNode, 'matrix')
		matrixNode.text = ''
		for i in xrange(16):
			matrixNode.text += '%f ' % project.scene.assemblyInstance.transform.matrix.data[i]

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

		## Serialize project:configurations
		#
		configurationsNode = SubElement(projectNode, 'configurations')

		bfConfigurationsNode = SubElement(configurationsNode, 'configuration')
		bfConfigurationsNode.attrib[Configurations.NAME] = 'final'
		bfConfigurationsNode.attrib[Configurations.BASE] = Configurations.BASE_FINAL

		biConfigurationsNode = SubElement(configurationsNode, 'configuration')
		biConfigurationsNode.attrib[Configurations.NAME] = 'interactive'
		biConfigurationsNode.attrib[Configurations.BASE] = Configurations.BASE_INTERACTIVE

		for (k, attr) in project.configurations.attrs.iteritems():
			if k.find('bf_') == 0:
				parameterNode = SubElement(bfConfigurationsNode, 'parameter')
				parameterNode.attrib[Attr.NAME]  = k[3:]
				parameterNode.attrib[Attr.VALUE] = '%d' % attr.value
			elif k.find('bi_') == 0:
				parameterNode = SubElement(biConfigurationsNode, 'parameter')
				parameterNode.attrib[Attr.NAME]  = k[3:]
				parameterNode.attrib[Attr.VALUE] = '%d' % attr.value		

		## Output the XML file.
		#
		ElementTree(projectNode).write(sys.stdout, encoding = 'UTF-8')

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

		objectInstance = ObjectInstance()
		objectInstance.Resolve(sohoGeometry, moments)
		if not project.scene.assembly.objectInstances.has_key(objectName):
			project.scene.assembly.objectInstances[objectName] = objectInstance

	frame = Frame()
	frame.Resolve(None, moments)
	project.output.frames[frame.attrs[Frame.NAME].value] = frame

	project.configurations.Resolve(None, moments)

	serializer = XmlSerializer()
	serializer.Serialize(project)
