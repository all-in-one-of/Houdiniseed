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

import soho
import sohog

from xml.etree.ElementTree import Element, ElementTree


##
#
class Attr(object):

	def __init__(self, name, required, default, value):
		self.name     = name
		self.required = required
		self.defualt  = default
		self.value    = value


##
#
class Node(object):

	def __init__(self):
		self.name     = None
		self.attrs    = {}
		self.children = {}

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
	MODEL           = 'model'
	FILM_DIMENSIONS = 'film_dimensions'
	FOCAL_LENGTH    = 'focal_length'

	##
	# Houdini used parameters.
	FOCAL = 'focal'
	POS   = 'pos'
	
	SUPPORTED_SOHO_PARAMS = {
		FOCAL : soho.SohoParm(FOCAL, 'float', [35.0],          False),
		POS   : soho.SohoParm(POS,   'float', [0.0, 0.0, 0.0], False),
	}

	def __init__(self):
		super(Camera, self).__init__()

		self.attrs[Camera.MODEL]           = Attr(Camera.MODEL,           True, 'pinhole_camera', 'pinhole_camera')
		self.attrs[Camera.FILM_DIMENSIONS] = Attr(Camera.FILM_DIMENSIONS, True, (0.025, 0.025),   (0.025, 0.025))
		self.attrs[Camera.FOCAL_LENGTH]    = Attr(Camera.FOCAL_LENGTH,    True,  35.0,             35.0)

		self.transform = Transform()

	def Resolve(self, sohoObject, moments):
		self.name = sohoObject.getName()
		sohoParmsValues = sohoObject.evaluate(Camera.SUPPORTED_SOHO_PARAMS, moments[0])
		self.attrs[Camera.FOCAL_LENGTH].value = sohoParmsValues[Camera.FOCAL].Value[0]
		print sohoParmsValues[Camera.POS].Value[0]

		sohoObject.evalFloat('space:world', moments[0], self.transform.matrix.transformation)
		print self.transform.matrix.transformation


##
#
class Object(Node):

	def __init__(self):
		pass

	def Resolve(self, sohoObject, moments):
		pass


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

	for sohoObject in soho.objectList('objlist:camera'):
		camera = Camera()
		camera.Resolve(sohoObject, moments)
