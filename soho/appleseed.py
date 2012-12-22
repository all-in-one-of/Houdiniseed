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
import uuid

import hou
import soho
import sohog

from xml.etree.ElementTree import Element, ElementTree, SubElement, tostring

##
# Global variables.
#
theProject = None

##
# Global functions.
#
def ProcessColor(colorNodeName, project, moments):
	if not project.scene.assembly.colors.has_key(colorNodeName):
		colorNodePath = colorNodeName
		colorNode = hou.node(colorNodePath)
		color = Color()
		color.Resolve(colorNode, moments)
		project.scene.assembly.colors[colorNodeName] = color

def ProcessMaterial(materialNodeName, project, moments):
	materialNodePath = materialNodeName
	materialNode = hou.node(materialNodePath)
	if materialNode.type().name() != 'appleseedMaterial':
			soho.error('%s Must be appleseedMaterial.' % materialNode.path())

	if not project.scene.assembly.materials.has_key(materialNodeName):
		material = Material()
		material.Resolve(materialNode, moments)
		project.scene.assembly.materials[materialNodeName] = material

		if material.attrs.has_key(Material.BSDF):
			bsdfName = material.attrs[Material.BSDF]
			if not project.scene.assembly.bsdfs.has_key(bsdfName):
				bsdfShopNodePath = bsdfName
				bsdfShopNode = hou.node(bsdfShopNodePath)
				bsdf = BSDF()
				bsdf.Resolve(bsdfShopNode, moments)
				project.scene.assembly.bsdfs[bsdfName] = bsdf
				
				bsdfModel = bsdf.attrs[BSDF.MODEL]
				if bsdfModel == BSDF.ASHIKHMIN_BRDF:
					diffuseNodeName = bsdf.attrs[BSDF.ASHIKHMIN_DIFFUSE_REFLECTANCE]
					ProcessColor(diffuseNodeName, project, moments)
					glossyNodeName = bsdf.attrs[BSDF.ASHIKHMIN_GLOSSY_REFLECTANCE]
					ProcessColor(glossyNodeName, project, moments)
				elif bsdfModel == BSDF.KELEMEN_BRDF:
					matteNodeName = bsdf.attrs[BSDF.KELEMEN_MATTE_REFLECTANCE]
					ProcessColor(matteNodeName, project, moments)
					specularNodeName = bsdf.attrs[BSDF.KELEMEN_SPECULAR_REFLECTANCE]
					ProcessColor(specularNodeName, project, moments)
				elif bsdfModel == BSDF.BSDF_MIX:
					pass						
				elif bsdfModel == BSDF.LAMBERTIAN_BRDF:
					reflectanceNodeName = bsdf.attrs[BSDF.LAMBERTIAN_REFLECTANCE]
					ProcessColor(reflectanceNodeName, project, moments)
				elif bsdfModel == BSDF.SPECULAR_BRDF:
					reflectanceNodeName = bsdf.attrs[BSDF.SPECULAR_BRDF_REFLECTANCE]
					ProcessColor(reflectanceNodeName, project, moments)
				elif bsdfModel == BSDF.SPECULAR_BTDF:
					reflectanceNodeName = bsdf.attrs[BSDF.SPECULAR_BTDF_REFLECTANCE]
					ProcessColor(reflectanceNodeName, project, moments)

					transmittanceNodeName = bsdf.attrs[BSDF.SPECULAR_BTDF_TRANSMITTANCE]
					ProcessColor(transmittanceNodeName, project, moments)

		if material.attrs.has_key(Material.EDF):
			edfName = material.attrs[Material.EDF]
			if not project.scene.assembly.edfs.has_key(edfName):
				edfShopNodePath = edfName
				edfShopNode = hou.node(edfShopNodePath)
				edf = EDF()
				edf.Resolve(edfShopNode, moments)
				project.scene.assembly.edfs[edfName] = edf

				colorNodeName = edf.attrs[EDF.EXITANCE]
				ProcessColor(colorNodeName, project, moments)

		surfaceShaderName = material.attrs[Material.SURFACE_SHADER]
		if not project.scene.assembly.surfaceShaders.has_key(surfaceShaderName):
			surfaceShaderShopNode = hou.node(surfaceShaderName)
			surfaceShader = SurfaceShader()
			surfaceShader.Resolve(surfaceShaderShopNode, moments)
			project.scene.assembly.surfaceShaders[surfaceShaderName] = surfaceShader

			# Collect color from surface shader.
			model = surfaceShader.attrs[SurfaceShader.MODEL]
			if model == SurfaceShader.CONSTANT_SURFACE_SHADER:
				colorNodeName = surfaceShader.attrs[SurfaceShader.CONSTANT_COLOR]
				ProcessColor(colorNodeName, project, moments)
			elif model == SurfaceShader.FAST_SSS_SURFACE_SHADER:
				albedoNodeName = surfaceShader.attrs[SurfaceShader.FAST_SSS_ALBEDO]
				ProcessColor(albedoNodeName, project, moments)
			elif model == SurfaceShader.PHYSICAL_SURFACE_SHADER:
				if surfaceShader.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE] == SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE_SKY_COLOR:
					skyColorNodeName = surfaceShader.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_SKY_COLOR].value
					ProcessColor(skyColorNodeName, project, moments)


##
#
class Attr(object):

	NAME  = 'name'
	VALUE = 'value'

	def __init__(self, *args):
		self.value = list(args)

##
#
class Node(object):

	def __init__(self):
		self.attrs = {}

	def Resolve(self, materialShopNode, moments):
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

		self.lights = {}

		self.materials = {}
		self.bsdfs = {}
		self.edfs = {}
		self.colors = {}
		self.surfaceShaders = {}

		self.objects = {}
		self.objectInstances = {}


##
#
class AssemblyInstance(Node):

	NAME     = 'name'
	ASSEMBLY = 'assembly'

	def __init__(self):
		super(AssemblyInstance, self).__init__()

		self.attrs[AssemblyInstance.NAME]     = 'assembly_inst'
		self.attrs[AssemblyInstance.ASSEMBLY] = 'assembly'

		self.transform = Transform()

		
##
#
class BSDF(Assembly):

	NAME  = 'name'
	MODEL = 'model'

	ASHIKHMIN_BRDF = 'ashikhmin_brdf'
	ASHIKHMIN_DIFFUSE_REFLECTANCE = 'ashikhmin_diffuse_reflectance'
	ASHIKHMIN_GLOSSY_REFLECTANCE = 'ashikhmin_glossy_reflectance'
	ASHIKHMIN_SHININESS_U = 'ashikhmin_shininess_u'
	ASHIKHMIN_SHININESS_V = 'ashikhmin_shininess_v'

	BSDF_MIX = 'bsdf_mix'
	BSDF_MIX_BSDF0 = 'bsdf_mix_bsdf0'
	BSDF_MIX_WEIGHT0 = 'bsdf_mix_weight0'
	BSDF_MIX_BSDF1 = 'bsdf_mix_bsdf1'
	BSDF_MIX_WEIGHT1 = 'bsdf_mix_weight1'

	KELEMEN_BRDF = 'kelemen_brdf'
	KELEMEN_MATTE_REFLECTANCE = 'kelemen_matte_reflectance'
	KELEMEN_SPECULAR_REFLECTANCE = 'kelemen_specular_reflectance'
	KELEMEN_ROUGHNESS = 'kelemen_roughness'

	LAMBERTIAN_BRDF = 'lambertian_brdf'
	LAMBERTIAN_REFLECTANCE = 'lambertian_reflectance'

	SPECULAR_BRDF = 'specular_brdf'
	SPECULAR_BRDF_REFLECTANCE = 'specular_brdf_reflectance'

	SPECULAR_BTDF = 'specular_btdf'
	SPECULAR_BTDF_REFLECTANCE = 'specular_btdf_reflectance'
	SPECULAR_BTDF_TRANSMITTANCE = 'specular_btdf_transmittance'
	SPECULAR_BTDF_FROM_IOR = 'specular_btdf_from_ior'
	SPECULAR_BTDF_TO_IOR = 'specular_btdf_to_ior'

	def __init__(self):
		super(BSDF, self).__init__()

		self.bsdf0 = None
		self.bsdf1 = None

	def AsAshikhminBrdf(self, shopNode, moments):
		self.attrs[BSDF.ASHIKHMIN_DIFFUSE_REFLECTANCE] = shopNode.evalParm(BSDF.ASHIKHMIN_DIFFUSE_REFLECTANCE)
		self.attrs[BSDF.ASHIKHMIN_GLOSSY_REFLECTANCE] = shopNode.evalParm(BSDF.ASHIKHMIN_GLOSSY_REFLECTANCE)
		self.attrs[BSDF.ASHIKHMIN_SHININESS_U] = Attr(shopNode.evalParm(BSDF.ASHIKHMIN_SHININESS_U))
		self.attrs[BSDF.ASHIKHMIN_SHININESS_V] = Attr(shopNode.evalParm(BSDF.ASHIKHMIN_SHININESS_V))

	def AsKelemenBrdf(self, shopNode, moments):
		self.attrs[BSDF.KELEMEN_MATTE_REFLECTANCE] = shopNode.evalParm(BSDF.KELEMEN_MATTE_REFLECTANCE)
		self.attrs[BSDF.KELEMEN_SPECULAR_REFLECTANCE] = shopNode.evalParm(BSDF.KELEMEN_SPECULAR_REFLECTANCE)
		self.attrs[BSDF.KELEMEN_ROUGHNESS] = Attr(shopNode.evalParm(BSDF.KELEMEN_ROUGHNESS))

	def AsLambertianBrdf(self, shopNode, moments):
		self.attrs[BSDF.LAMBERTIAN_REFLECTANCE] = shopNode.evalParm(BSDF.LAMBERTIAN_REFLECTANCE)

	def AsSpecularBrdf(self, shopNode, moments):
		self.attrs[BSDF.SPECULAR_BRDF_REFLECTANCE] = shopNode.evalParm(BSDF.SPECULAR_BRDF_REFLECTANCE)

	def AsSpecularBtdf(self, shopNode, moments):
		self.attrs[BSDF.SPECULAR_BTDF_REFLECTANCE] = shopNode.evalParm(BSDF.SPECULAR_BTDF_REFLECTANCE)
		self.attrs[BSDF.SPECULAR_BTDF_TRANSMITTANCE] = shopNode.evalParm(BSDF.SPECULAR_BTDF_TRANSMITTANCE)
		self.attrs[BSDF.SPECULAR_BTDF_FROM_IOR] = shopNode.evalParm(BSDF.SPECULAR_BTDF_FROM_IOR)
		self.attrs[BSDF.SPECULAR_BTDF_TO_IOR] = shopNode.evalParm(BSDF.SPECULAR_BTDF_TO_IOR)

	def Resolve(self, shopNode, moments):
		self.attrs[BSDF.NAME] = shopNode.path()

		model = shopNode.evalParm(BSDF.MODEL)
		self.attrs[BSDF.MODEL] = model
		if model == BSDF.ASHIKHMIN_BRDF:
			self.AsAshikhminBRDF(shopNode, moments)
		if model == BSDF.BSDF_MIX:
			self.attrs[BSDF.BSDF_MIX_BSDF0] = shopNode.evalParm(BSDF.BSDF_MIX_BSDF0)
			self.attrs[BSDF.BSDF_MIX_WEIGHT0] = Attr(shopNode.evalParm(BSDF.BSDF_MIX_WEIGHT0))
			self.attrs[BSDF.BSDF_MIX_BSDF1] = shopNode.evalParm(BSDF.BSDF_MIX_BSDF1)
			self.attrs[BSDF.BSDF_MIX_WEIGHT1] = Attr(shopNode.evalParm(BSDF.BSDF_MIX_WEIGHT1))
		elif model == BSDF.KELEMEN_BRDF:
			self.AsKelemenBrdf(shopNode, moments)
		elif model == BSDF.LAMBERTIAN_BRDF:
			self.AsLambertianBrdf(shopNode, moments)
		elif model == BSDF.SPECULAR_BRDF:
			self.AsSpecularBrdf(shopNode, moments)
		elif model == BSDF.SPECULAR_BTDF:
			self.AsSpecularBtdf(shopNode, moments)


##
#
class EDF(Assembly):

	NAME = 'name'
	MODEL = 'model'

	EXITANCE = 'exitance'

	def __init__(self):
		super(EDF, self).__init__()

	def Resolve(self, shopNode, moments):
		self.attrs[EDF.NAME] = shopNode.path()
		self.attrs[EDF.MODEL] = 'diffuse_edf'
		self.attrs[EDF.MODEL] = 'diffuse_edf'
		self.attrs[EDF.EXITANCE] = shopNode.evalParm(EDF.EXITANCE)

##
#
class Light(Assembly):

	NAME = 'name'
	MODEL = 'model'

	POINT_LIGHT = 'point_light'
	SPOT_LIGHT = 'spot_light'

	EXITANCE = 'exitance'
	INNER_ANGLE = 'inner_angle'
	OUTER_ANGLE = 'outer_angle'

	CONE_ENABLE = 'coneenable'
	CONE_ANGLE = 'coneangle'
	CONE_DELTA = 'conedelta'
	LIGHT_COLOR = 'light_color'
	SUPPORTED_SOHO_PARAMS = {
		CONE_ENABLE : soho.SohoParm(CONE_ENABLE, 'int', [0], False),
		CONE_ANGLE : soho.SohoParm(CONE_ANGLE, 'float', [90], False),
		CONE_DELTA : soho.SohoParm(CONE_DELTA, 'float', [0], False),
		LIGHT_COLOR : soho.SohoParm(LIGHT_COLOR, 'real', [1, 1, 1], False)
	}

	def __init__(self):
		super(Light, self).__init__()

		self.transform = Transform()
		self.exitance = Color()

	def Resolve(self, sohoLight, moments):
		self.attrs[Light.NAME] = sohoLight.getName()
	
		sohoLight.evalFloat('space:world', moments[0], self.transform.matrix.data)
		self.transform.matrix.data = hou.Matrix4(self.transform.matrix.data).transposed().asTuple()

		sohoParamsValues = sohoLight.evaluate(Light.SUPPORTED_SOHO_PARAMS, moments[0])		
		if sohoParamsValues[Light.CONE_ENABLE].Value[0]:
			self.attrs[Light.MODEL] = Light.SPOT_LIGHT
			
			self.attrs[Light.INNER_ANGLE] = Attr(sohoParamsValues[Light.CONE_ANGLE].Value[0] - sohoParamsValues[Light.CONE_DELTA].Value[0])
			self.attrs[Light.OUTER_ANGLE]  = Attr(sohoParamsValues[Light.CONE_ANGLE].Value[0])
		else:
			self.attrs[Light.MODEL] = Light.POINT_LIGHT

		# TODO: Connect with SHOP
		self.exitance.attrs[Color.NAME] = sohoLight.getName() + str(uuid.uuid4())
		self.exitance.attrs[Color.COLOR_SPACE] = 'srgb'
		self.exitance.attrs[Color.VALUES] = Attr(sohoParamsValues[Light.LIGHT_COLOR].Value)
		

##
#
class Material(Assembly):

	NAME     = 'name'
	MODEL    = 'model'

	BSDF           = 'bsdf'
	EDF            = 'edf'
	SURFACE_SHADER = 'surface_shader'

	def __init__(self):
		super(Material, self).__init__()

	def Resolve(self, shopNode, moments):
		self.attrs[Material.NAME] = shopNode.path()

		self.attrs[Material.MODEL] = 'generic_material'
		
		bsdf = shopNode.evalParm(Material.BSDF)
		if bsdf != '':
			self.attrs[Material.BSDF] = bsdf

		edf = shopNode.evalParm(Material.EDF)
		if edf != '':
			self.attrs[Material.EDF] = edf

		surfaceShader = shopNode.evalParm(Material.SURFACE_SHADER)
		if surfaceShader == '':
			soho.error('Must set surface shader for %s' % shopNode.path())
		self.attrs[Material.SURFACE_SHADER] = surfaceShader

##
#
class Color(Node):

	COLOR = 'color'

	NAME = 'name'

	COLOR_SPACE = 'color_space'
	COLOR_VALUES = 'color_values'
	SPECTRAL_VALUES = 'spectral_values'
	VALUES = 'values'
	ALPHA = 'alpha'
	WAVELENGTH = 'wavelength'
	WAVELENGTH_RANGE_X = 'wavelength_rangex'
	WAVELENGTH_RANGE_Y = 'wavelength_rangey'
	MULTIPLIER = 'multiplier'

	def __init__(self):
		super(Color, self).__init__()

	def Resolve(self, shopNode, moments):
		self.attrs[Color.NAME] = shopNode.path()
	
		self.attrs[Color.COLOR_SPACE] = shopNode.evalParm(Color.COLOR_SPACE)
		if self.attrs[Color.COLOR_SPACE] != 'spectral':
			self.attrs[Color.VALUES] = Attr(shopNode.evalParmTuple(Color.COLOR_VALUES))
		else:
			self.attrs[Color.VALUES] = shopNode.evalParm(Color.SPECTRAL_VALUES)
			self.attrs[Color.WAVELENGTH] = (shopNode.evalParm(Color.WAVELENGTH_RANGE_X), shopNode.evalParm(Color.WAVELENGTH_RANGE_Y))

		self.attrs[Color.ALPHA] = Attr(shopNode.evalParm(Color.ALPHA))
		self.attrs[Color.MULTIPLIER] = Attr(shopNode.evalParm(Color.MULTIPLIER))

##
#
class SurfaceShader(Node):

	NAME  = 'name'
	MODEL = 'model'

	AO_SURFACE_SHADER  = 'ao_surface_shader'
	AO_SAMPLING_METHOD = 'ao_sampling_method'
	AO_SAMPLES         = 'ao_samples'
	AO_MAX_DISTANCE    = 'ao_max_distance'

	CONSTANT_SURFACE_SHADER = 'constant_surface_shader'
	CONSTANT_COLOR = 'constant_color'

	DIAGNOSTIC_SURFACE_SHADER = 'diagnostic_surface_shader'
	DIAGNOSTIC_MODE = 'diagnostic_mode'
	DIAGNOSTIC_AO = 'ambient_occlusion'
	DIAGNOSTIC_AO_SAMPLES = 'diagnostic_ao_samples'
	DIAGNOSTIC_AO_MAX_DISTANCE = 'diagnostic_ao_max_distance'

	FAST_SSS_SURFACE_SHADER = 'fast_sss_surface_shader'
	FAST_SSS_SCALE = 'fast_sss_scale'
	FAST_SSS_AMBIENT_SSS = 'fast_sss_ambient_sss'
	FAST_SSS_VIEW_DEP_SSS = 'fast_sss_view_dep_sss'
	FAST_SSS_DIFFUSE = 'fast_sss_diffuse'
	FAST_SSS_POWER = 'fast_sss_power'
	FAST_SSS_DISTORTION = 'fast_sss_distortion'
	FAST_SSS_ALBEDO = 'fast_sss_albedo'
	FAST_SSS_LIGHT_SAMPLES = 'fast_sss_light_samples'
	FAST_SSS_OCCLUSION_SAMPLES = 'fast_sss_occlusion_samples'

	PHYSICAL_SURFACE_SHADER = 'physical_surface_shader'
	PHYSICAL_COLOR_MULTIPLIER = 'physical_color_multiplier'
	PHYSICAL_ALPHA_MULTIPLIER = 'physical_alpha_multiplier'
	PHYSICAL_AERIAL_PERSP_MODE = 'physical_aerial_persp_mode'
	PHYSICAL_AERIAL_PERSP_MODE_NONE = 'none'
	PHYSICAL_AERIAL_PERSP_MODE_ENVIRONMENT_SHADER = 'environment_shader'
	PHYSICAL_AERIAL_PERSP_MODE_SKY_COLOR = 'sky_color'
	PHYSICAL_AERIAL_PERSP_SKY_COLOR = 'physical_aerial_persp_sky_color'
	PHYSICAL_AERIAL_PERSP_DISTANCE = 'physical_aerial_persp_distance'
	PHYSICAL_AERIAL_PERSP_INTENSITY = 'physical_aerial_persp_intensity'

	SMOKE_SURFACE_SHADER = 'smoke_surface_shader'
	SMOKE_BOUNDING_BOX = 'smoke_bounding_box'
	SMOKE_BOUNDING_BOX_MIN = 'smoke_bounding_box_min'
	SMOKE_BOUNDING_BOX_MAX = 'smoke_bounding_box_max'
	SMOKE_SHADING_MODE = 'smoke_shading_mode'
	SMOKE_INTERPOLATION_MODE = 'smoke_interpolation_mode'
	SMOKE_ISOSURFACE_THRESHOLD = 'smoke_isosurface_threshold'
	SMOKE_FILENAME = 'smoke_filename'
	SMOKE_STEP_SIZE = 'smoke_step_size'
	SMOKE_DENSITY_CUTOFF = 'smoke_density_cutoff'
	SMOKE_DENSITY_SCALE = 'smoke_density_scale'
	SMOKE_SMOKE_COLOR = 'smoke_smoke_color'
	SMOKE_FUEL_COLOR = 'smoke_fuel_color'
	SMOKE_FUEL_SCALE = 'smoke_fuel_scale'
	SMOKE_LIGHT_DIRECTION = 'smoke_light_direction'
	SMOKE_LIGHT_COLOR = 'smoke_light_color'
	SMOKE_COLOR_SCALE = 'smoke_color_scale'
	SMOKE_VOLUME_OPACITY = 'smoke_volume_opacity'
	SMOKE_SHADOW_OPACITY = 'smoke_shadow_opacity'

	def __init__(self):
		super(SurfaceShader, self).__init__()

	def Resolve(self, shopNode, moments):
		self.attrs[SurfaceShader.NAME] = shopNode.path()
		self.attrs[SurfaceShader.MODEL] = shopNode.evalParm(SurfaceShader.MODEL)

		model = self.attrs[SurfaceShader.MODEL]
		# AO
		if model == SurfaceShader.AO_SURFACE_SHADER:
			aoSamplingMethod = shopNode.evalParm(SurfaceShader.AO_SAMPLING_METHOD)
			if aoSamplingMethod != 'uniform':
				self.attrs[SurfaceShader.AO_SAMPLING_METHOD] = Attr(aoSamplingMethod)

			aoSamples = shopNode.evalParm(SurfaceShader.AO_SAMPLES)
			if aoSamplingMethod != 16:
				self.attrs[SurfaceShader.AO_SAMPLES] = Attr(aoSamples)

			aoMaxDistance = shopNode.evalParm(SurfaceShader.AO_MAX_DISTANCE)
			if aoSamplingMethod != 1.0:
				self.attrs[SurfaceShader.AO_MAX_DISTANCE] = Attr(aoMaxDistance)

		# Constant
		elif model == SurfaceShader.CONSTANT_SURFACE_SHADER:
			self.attrs[SurfaceShader.CONSTANT_COLOR] = shopNode.evalParm(SurfaceShader.CONSTANT_COLOR)

		# Diagnostic
		elif model == SurfaceShader.DIAGNOSTIC_SURFACE_SHADER:
			self.attrs[SurfaceShader.DIAGNOSTIC_MODE] = Attr(shopNode.evalParm(SurfaceShader.DIAGNOSTIC_MODE))
			
			if self.attrs[SurfaceShader.DIAGNOSTIC_MODE].value == SurfaceShader.DIAGNOSTIC_AO:
				diagAOSamples = shopNode.evalParm(SurfaceShader.DIAGNOSTIC_AO_SAMPLES)
				if diagAOSamples != 16:
					self.attrs[SurfaceShader.DIAGNOSTIC_AO_SAMPLES] = Attr(diagAOSamples)
				diagAOMaxDistance = shopNode.evalParm(SurfaceShader.DIAGNOSTIC_AO_MAX_DISTANCE)
				if diagAOMaxDistance != 1.0:
					self.attrs[SurfaceShader.DIAGNOSTIC_AO_MAX_DISTANCE] = Attr(diagAOMaxDistance)

		# Fast SSS
		elif model == SurfaceShader.FAST_SSS_SURFACE_SHADER:
			self.attrs[SurfaceShader.FAST_SSS_SCALE]        = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_SCALE))
			self.attrs[SurfaceShader.FAST_SSS_AMBIENT_SSS]  = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_AMBIENT_SSS))
			self.attrs[SurfaceShader.FAST_SSS_VIEW_DEP_SSS] = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_VIEW_DEP_SSS))
			self.attrs[SurfaceShader.FAST_SSS_DIFFUSE] = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_DIFFUSE))
			self.attrs[SurfaceShader.FAST_SSS_POWER] = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_POWER))
			self.attrs[SurfaceShader.FAST_SSS_DISTORTION] = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_DISTORTION))
			self.attrs[SurfaceShader.FAST_SSS_ALBEDO] = shopNode.evalParm(SurfaceShader.FAST_SSS_ALBEDO)
			self.attrs[SurfaceShader.FAST_SSS_LIGHT_SAMPLES] = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_LIGHT_SAMPLES))
			self.attrs[SurfaceShader.FAST_SSS_OCCLUSION_SAMPLES] = Attr(shopNode.evalParm(SurfaceShader.FAST_SSS_OCCLUSION_SAMPLES))
			
		# Physical
		elif model == SurfaceShader.PHYSICAL_SURFACE_SHADER:
			self.attrs[SurfaceShader.PHYSICAL_COLOR_MULTIPLIER] = Attr(shopNode.evalParm(SurfaceShader.PHYSICAL_COLOR_MULTIPLIER))
			self.attrs[SurfaceShader.PHYSICAL_ALPHA_MULTIPLIER] = Attr(shopNode.evalParm(SurfaceShader.PHYSICAL_ALPHA_MULTIPLIER))

			aerialPerspMode = shopNode.evalParm(SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE)
			self.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE] = aerialPerspMode
			if aerialPerspMode != SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE_NONE:
				if aerialPerspMode == SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE_SKY_COLOR:
					self.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_SKY_COLOR] = shopNode.evalParm(SurfaceShader.PHYSICAL_AERIAL_PERSP_SKY_COLOR)
			self.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_DISTANCE] = Attr(shopNode.evalParm(SurfaceShader.PHYSICAL_AERIAL_PERSP_DISTANCE))
			self.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_INTENSITY] = Attr(shopNode.evalParm(SurfaceShader.PHYSICAL_AERIAL_PERSP_INTENSITY))

		# Smoke
		elif model == SurfaceShader.SMOKE_SURFACE_SHADER:
			boundingBoxMin = (shopNode.evalParm(SurfaceShader.SMOKE_BOUNDING_BOX_MIN + 'x'), shopNode.evalParm(SurfaceShader.SMOKE_BOUNDING_BOX_MIN + 'y'), shopNode.evalParm(SurfaceShader.SMOKE_BOUNDING_BOX_MIN + 'z'))
			self.attrs[SurfaceShader.SMOKE_BOUNDING_BOX_MIN]     = Attr( boundingBoxMin)
			boundingBoxMax = (shopNode.evalParm(SurfaceShader.SMOKE_BOUNDING_BOX_MAX + 'x'), shopNode.evalParm(SurfaceShader.SMOKE_BOUNDING_BOX_MAX + 'y'), shopNode.evalParm(SurfaceShader.SMOKE_BOUNDING_BOX_MAX + 'z'))
			self.attrs[SurfaceShader.SMOKE_BOUNDING_BOX_MAX]     = Attr(boundingBoxMax)
			self.attrs[SurfaceShader.SMOKE_SHADING_MODE]         = Attr(shopNode.evalParm(SurfaceShader.SMOKE_SHADING_MODE))
			self.attrs[SurfaceShader.SMOKE_INTERPOLATION_MODE]   = Attr(shopNode.evalParm(SurfaceShader.SMOKE_INTERPOLATION_MODE))
			self.attrs[SurfaceShader.SMOKE_ISOSURFACE_THRESHOLD] = Attr(shopNode.evalParm(SurfaceShader.SMOKE_ISOSURFACE_THRESHOLD))
			self.attrs[SurfaceShader.SMOKE_FILENAME]             = Attr(shopNode.evalParm(SurfaceShader.SMOKE_FILENAME))
			self.attrs[SurfaceShader.SMOKE_STEP_SIZE]            = Attr(shopNode.evalParm(SurfaceShader.SMOKE_STEP_SIZE))
			self.attrs[SurfaceShader.SMOKE_DENSITY_CUTOFF]       = Attr(shopNode.evalParm(SurfaceShader.SMOKE_DENSITY_CUTOFF))
			self.attrs[SurfaceShader.SMOKE_DENSITY_SCALE]        = Attr(shopNode.evalParm(SurfaceShader.SMOKE_DENSITY_SCALE))
			smokeColor = (shopNode.evalParm(SurfaceShader.SMOKE_SMOKE_COLOR + 'r'), shopNode.evalParm(SurfaceShader.SMOKE_SMOKE_COLOR + 'g'), shopNode.evalParm(SurfaceShader.SMOKE_SMOKE_COLOR + 'b'))
			self.attrs[SurfaceShader.SMOKE_SMOKE_COLOR]          = Attr(smokeColor)
			fuelColor = (shopNode.evalParm(SurfaceShader.SMOKE_FUEL_COLOR + 'r'), shopNode.evalParm(SurfaceShader.SMOKE_FUEL_COLOR + 'g'), shopNode.evalParm(SurfaceShader.SMOKE_FUEL_COLOR + 'b'))
			self.attrs[SurfaceShader.SMOKE_FUEL_COLOR]           = Attr(fuelColor)
			self.attrs[SurfaceShader.SMOKE_FUEL_SCALE]           = Attr(shopNode.evalParm(SurfaceShader.SMOKE_FUEL_SCALE))
			lightDirection = (shopNode.evalParm(SurfaceShader.SMOKE_LIGHT_DIRECTION + 'x'), shopNode.evalParm(SurfaceShader.SMOKE_LIGHT_DIRECTION + 'y'), shopNode.evalParm(SurfaceShader.SMOKE_LIGHT_DIRECTION + 'z'))
			self.attrs[SurfaceShader.SMOKE_LIGHT_DIRECTION]      = Attr(lightDirection)
			lightColor = (shopNode.evalParm(SurfaceShader.SMOKE_LIGHT_COLOR + 'r'), shopNode.evalParm(SurfaceShader.SMOKE_LIGHT_COLOR + 'g'), shopNode.evalParm(SurfaceShader.SMOKE_LIGHT_COLOR + 'b'))
			self.attrs[SurfaceShader.SMOKE_LIGHT_COLOR]          = Attr(lightColor)
			self.attrs[SurfaceShader.SMOKE_COLOR_SCALE]          = Attr(shopNode.evalParm(SurfaceShader.SMOKE_COLOR_SCALE))
			self.attrs[SurfaceShader.SMOKE_VOLUME_OPACITY]       = Attr(shopNode.evalParm(SurfaceShader.SMOKE_VOLUME_OPACITY))
			self.attrs[SurfaceShader.SMOKE_SHADOW_OPACITY]       = Attr(shopNode.evalParm(SurfaceShader.SMOKE_SHADOW_OPACITY))


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

		self.attrs[Object.FILENAME] = os.path.join('.', os.path.basename(companionDir), objFileName)

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
				for j in reversed(xrange(sohoGeometry.value(geoPrimVertexCount, i)[0])):
					v = sohoGeometry.vertex(geoVertexPointRef, i, j)
					file.write(' %d/%d' % (v[0] + 1, fakeUVIndex))
					fakeUVIndex += 1
				file.write('\n')
		else:
			for i in xrange(geoPrimCount):
				file.write('f')
				for j in reversed(xrange(sohoGeometry.value(geoPrimVertexCount, i)[0])):
					v = sohoGeometry.vertex(geoVertexPointRef, i, j)
					file.write(' %d' % (v[0] + 1))
				file.write('\n')

		file.close()

		return objFilePath

	def Resolve(self, sohoObject, moments):
		sopPath = sohoObject.getDefaultedString('object:soppath', sohoObject, [''])[0]
		self.attrs[Object.NAME] = sopPath.replace('/', '__')

		self.attrs[Object.MODEL] = 'mesh_object'

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

		self.assignMaterial = AssignMaterial()

	def Resolve(self, sohoObject, moments):
		sopPath = sohoObject.getDefaultedString('object:soppath', sohoObject, [''])[0]
		name = sopPath
		self.attrs[ObjectInstance.NAME] = name
		self.attrs[ObjectInstance.OBJECT] = name.replace('/', '__') + '.' + name.replace('/', '__')

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
		self.attrs[Transform.TIME] = Attr(0)

		
##
#
class AssignMaterial(Node):

	SLOT = 'slot'
	SIDE = 'side'
	MATERIAL = 'material'

	def __init__(self):
		super(AssignMaterial, self).__init__()

		self.attrs[AssignMaterial.SLOT] = 0
		self.attrs[AssignMaterial.SIDE] = 'front'
		self.attrs[AssignMaterial.MATERIAL] = ''


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
		self.attrs[Camera.NAME] = sohoObject.getName()

		self.attrs[Camera.MODEL] = 'pinhole_camera'

		sohoParmsValues = sohoObject.evaluate(Camera.SUPPORTED_SOHO_PARAMS, moments[0])

		resx = sohoParmsValues[Camera.RESX].Value[0]
		resy = sohoParmsValues[Camera.RESY].Value[0]

		aperture = sohoParmsValues[Camera.APERTURE].Value[0] / 1000.0
		self.attrs[Camera.FILM_DIMENSIONS] = Attr((aperture, float(resy) /  float(resx) * aperture))

		self.attrs[Camera.FOCAL_LENGTH] = Attr(sohoParmsValues[Camera.FOCAL].Value[0] / 1000.0)

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
		self.attrs[Frame.NAME] = '%s.%.4d' % (basicName, frameNumber)

		sohoParmsValues = soho.sohoglue.evaluate(Frame.SUPPORTED_SOHO_PARAMS, None, None)
		self.attrs[Frame.CAMERA] = sohoParmsValues[Frame.CAMERA].Value[0]
		cameraHouNode = hou.node(sohoParmsValues[Frame.CAMERA].Value[0])
		resx = cameraHouNode.evalParm('resx')
		resy = cameraHouNode.evalParm('resy')
		self.attrs[Frame.RESOLUTION] = (resx, resy)

		if sohoParmsValues.has_key(Frame.TILE_SIZE):
			self.attrs[Frame.TILE_SIZE] = sohoParmsValues[Frame.TILE_SIZE].Value[0]


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
			self.attrs[key] = Attr(value.Value[0])


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

		cameraNode.attrib[Camera.NAME]  = camera.attrs[Camera.NAME]
		cameraNode.attrib[Camera.MODEL] = camera.attrs[Camera.MODEL]

		parameterNode = SubElement(cameraNode, 'parameter')
		parameterNode.attrib[Attr.NAME]  = Camera.FILM_DIMENSIONS
		parameterNode.attrib[Attr.VALUE] = '%f %f' % (camera.attrs[Camera.FILM_DIMENSIONS].value[0])

		parameterNode = SubElement(cameraNode, 'parameter')
		parameterNode.attrib[Attr.NAME]  = Camera.FOCAL_LENGTH
		parameterNode.attrib[Attr.VALUE]    = '%f' % (camera.attrs[Camera.FOCAL_LENGTH].value[0])

		transformNode = SubElement(cameraNode, 'transform')
		matrixNode = SubElement(transformNode, 'matrix')
		matrixNode.text = ''
		for i in xrange(16):
			matrixNode.text += '%f ' % camera.transform.matrix.data[i]

		## Serialize project:scene:assembly
		#
		assemblyNode = SubElement(sceneNode, 'assembly')
		assemblyNode.attrib[Assembly.NAME] = 'assembly'

		## Serialize project:scene:assembly:light
		#
		for (lightName, light) in project.scene.assembly.lights.iteritems():
			lightNode = SubElement(assemblyNode, 'light')

			lightNode.attrib[Light.NAME] = light.attrs[Light.NAME]

			lightNode.attrib[Light.MODEL] = light.attrs[Light.MODEL]

			parameterNode = SubElement(lightNode, 'parameter')
			parameterNode.attrib[Attr.NAME] = Light.EXITANCE
			parameterNode.attrib[Attr.VALUE] = light.exitance.attrs[Color.NAME]

			if light.attrs[Light.MODEL] == Light.SPOT_LIGHT:
				parameterNode = SubElement(lightNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = Light.INNER_ANGLE
				parameterNode.attrib[Attr.VALUE] = str(light.attrs[Light.INNER_ANGLE].value[0])

				parameterNode = SubElement(lightNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = Light.OUTER_ANGLE
				parameterNode.attrib[Attr.VALUE] = str(light.attrs[Light.OUTER_ANGLE].value[0])

			transformNode = SubElement(lightNode, 'transform')
			matrixNode = SubElement(transformNode, 'matrix')
			matrixNode.text = ''
			for i in xrange(16):
				matrixNode.text += '%f ' % light.transform.matrix.data[i]

		## Serialize project:scene:assembly:material
		#
		for (materialName, material) in project.scene.assembly.materials.iteritems():
			materialNode = SubElement(assemblyNode, 'material')

			materialNode.attrib[Material.NAME] = material.attrs[Material.NAME]

			materialNode.attrib[Material.MODEL] = material.attrs[Material.MODEL]

			if material.attrs.has_key(Material.BSDF):
				parameterNode = parameterNode = SubElement(materialNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = Material.BSDF
				parameterNode.attrib[Attr.VALUE] = material.attrs[Material.BSDF]

			if material.attrs.has_key(Material.EDF):
				parameterNode = parameterNode = SubElement(materialNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = Material.EDF
				parameterNode.attrib[Attr.VALUE] = material.attrs[Material.EDF]

			parameterNode = SubElement(materialNode, 'parameter')
			parameterNode.attrib[Attr.NAME] = Material.SURFACE_SHADER
			parameterNode.attrib[Attr.VALUE] = material.attrs[Material.SURFACE_SHADER]

		## Serialize project:scene:assembly:bsdf
		#
		for (bsdfName, bsdf) in project.scene.assembly.bsdfs.iteritems():
			bsdfNode = SubElement(assemblyNode, 'bsdf')

			bsdfNode.attrib[BSDF.NAME] = bsdf.attrs[BSDF.NAME]
			bsdfNode.attrib[BSDF.MODEL] = bsdf.attrs[BSDF.MODEL]

			model = bsdf.attrs[BSDF.MODEL]
			if model == BSDF.ASHIKHMIN_BRDF:
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.ASHIKHMIN_DIFFUSE_REFLECTANCE[10:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.ASHIKHMIN_DIFFUSE_REFLECTANCE]
	
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.ASHIKHMIN_GLOSSY_REFLECTANCE[10:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.ASHIKHMIN_GLOSSY_REFLECTANCE]

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.ASHIKHMIN_SHININESS_U[10:]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.ASHIKHMIN_SHININESS_U].value[0])

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.ASHIKHMIN_SHININESS_V[10:]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.ASHIKHMIN_SHININESS_V].value[0])
			elif model == BSDF.BSDF_MIX:
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.BSDF_MIX_BSDF0[9]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.BSDF_MIX_BSDF0]

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.BSDF_MIX_WEIGHT0[9]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.BSDF_MIX_WEIGHT0].value[0])
				
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.BSDF_MIX_BSDF1[9]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.BSDF_MIX_BSDF1]

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.BSDF_MIX_WEIGHT1[9]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.BSDF_MIX_WEIGHT1].value[0])
			elif model == BSDF.KELEMEN_BRDF:
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.KELEMEN_MATTE_REFLECTANCE[8:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.KELEMEN_MATTE_REFLECTANCE]
				
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.KELEMEN_SPECULAR_REFLECTANCE[8:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.KELEMEN_SPECULAR_REFLECTANCE]

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.KELEMEN_ROUGHNESS[8:]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.KELEMEN_ROUGHNESS].value[0])
			elif model == BSDF.LAMBERTIAN_BRDF:
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.LAMBERTIAN_REFLECTANCE[11:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.LAMBERTIAN_REFLECTANCE]
			elif model == BSDF.SPECULAR_BRDF:
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.SPECULAR_BRDF_REFLECTANCE[14:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.SPECULAR_BRDF_REFLECTANCE]
			elif model == BSDF.SPECULAR_BTDF:
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.SPECULAR_BTDF_REFLECTANCE[14:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.SPECULAR_BTDF_REFLECTANCE]

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.SPECULAR_BTDF_TRANSMITTANCE[14:]
				parameterNode.attrib[Attr.VALUE] = bsdf.attrs[BSDF.SPECULAR_BTDF_TRANSMITTANCE]

				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.SPECULAR_BTDF_FROM_IOR[14:]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.SPECULAR_BTDF_FROM_IOR])
				
				parameterNode = SubElement(bsdfNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = BSDF.SPECULAR_BTDF_TO_IOR[14:]
				parameterNode.attrib[Attr.VALUE] = str(bsdf.attrs[BSDF.SPECULAR_BTDF_TO_IOR])

		## Serialize project:scene:edf
		for (edfName, edf) in project.scene.assembly.edfs.iteritems():
			edfNode = SubElement(assemblyNode, 'edf')

			edfNode.attrib[EDF.NAME] = edf.attrs[EDF.NAME]
			edfNode.attrib[SurfaceShader.MODEL] = edf.attrs[EDF.MODEL]

			parameterNode = SubElement(edfNode, 'parameter')
			parameterNode.attrib[Attr.NAME] = EDF.EXITANCE
			parameterNode.attrib[Attr.VALUE] = edf.attrs[EDF.EXITANCE]

		## Serialize project:scene:assembly:color
		#
		for (colorName, color) in project.scene.assembly.colors.iteritems():
			colorNode = SubElement(assemblyNode, 'color')

			colorNode.attrib[Color.NAME] = color.attrs[Color.NAME]
			
			parameterNode = SubElement(colorNode, 'parameter')
			parameterNode.attrib[Attr.NAME] = Color.COLOR_SPACE
			parameterNode.attrib[Attr.VALUE] = color.attrs[Color.COLOR_SPACE]

			if color.attrs.has_key(Color.MULTIPLIER):
				parameterNode = SubElement(colorNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = Color.MULTIPLIER
				parameterNode.attrib[Attr.VALUE] = str(color.attrs[Color.MULTIPLIER].value[0])

			valueNode = SubElement(colorNode, Color.VALUES)
			if color.attrs[Color.COLOR_SPACE] != 'spectral':
				valueNode.text = '%f %f %f' % tuple(color.attrs[Color.VALUES].value[0])
			else:
				valueNode.text = color.attrs[Color.VALUES].value

			if color.attrs.has_key(Color.ALPHA):
				alphaNode = SubElement(colorNode, Color.ALPHA)
				alphaNode.text = str(color.attrs[Color.ALPHA].value[0])

		## Serialize project:scene:assembly:surface_shader
		#
		for (surfaceShaderName, surfaceShader) in project.scene.assembly.surfaceShaders.iteritems():
			surfaceShaderNode = SubElement(assemblyNode, 'surface_shader')

			surfaceShaderNode.attrib[SurfaceShader.NAME] = surfaceShader.attrs[SurfaceShader.NAME]

			model = surfaceShader.attrs[SurfaceShader.MODEL]
			surfaceShaderNode.attrib[SurfaceShader.MODEL] = model
			if model == SurfaceShader.AO_SURFACE_SHADER:
				if surfaceShader.attrs.has_key(SurfaceShader.AO_SAMPLING_METHOD):
					parameterNode = SubElement(surfaceShaderNode, 'parameter')
					parameterNode.attrib[Attr.NAME] = SurfaceShader.AO_SAMPLING_METHOD[3:]
					parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.AO_SAMPLING_METHOD]
				if surfaceShader.attrs.has_key(SurfaceShader.AO_SAMPLES):
					parameterNode = SubElement(surfaceShaderNode, 'parameter')
					parameterNode.attrib[Attr.NAME] = SurfaceShader.AO_SAMPLES[3:]
					parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.AO_SAMPLES].value[0])
				if surfaceShader.attrs.has_key(SurfaceShader.AO_MAX_DISTANCE):
					parameterNode = SubElement(surfaceShaderNode, 'parameter')
					parameterNode.attrib[Attr.NAME] = SurfaceShader.AO_MAX_DISTANCE[3:]
					parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.AO_MAX_DISTANCE].value[0])
			
			elif model == SurfaceShader.CONSTANT_SURFACE_SHADER:
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.CONSTANT_COLOR[9:]
				parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.CONSTANT_COLOR].value[0]

			elif model == SurfaceShader.DIAGNOSTIC_SURFACE_SHADER:
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.DIAGNOSTIC_MODE[11:]
				parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.DIAGNOSTIC_MODE].value[0]
				if surfaceShader.attrs[SurfaceShader.DIAGNOSTIC_MODE].value == SurfaceShader.DIAGNOSTIC_AO:
					if surfaceShader.attrs.has_key(SurfaceShader.DIAGNOSTIC_AO_SAMPLES):
						parameterNode = SubElement(surfaceShaderNode, 'parameter')
						parameterNode.attrib[Attr.NAME] = 'ambient_occlusion.samples'
						parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.DIAGNOSTIC_AO_SAMPLES].value[0])
					if surfaceShader.attrs.has_key(SurfaceShader.DIAGNOSTIC_AO_MAX_DISTANCE):
						parameterNode = SubElement(surfaceShaderNode, 'parameter')
						parameterNode.attrib[Attr.NAME] = 'ambient_occlusion.max_distance'
						parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.DIAGNOSTIC_AO_MAX_DISTANCE].value[0])
			
			elif model == SurfaceShader.FAST_SSS_SURFACE_SHADER:
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_SCALE[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_SCALE].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_AMBIENT_SSS[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_AMBIENT_SSS].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_VIEW_DEP_SSS[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_VIEW_DEP_SSS].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_DIFFUSE[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_DIFFUSE].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_POWER[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_POWER].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_DISTORTION[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_DISTORTION].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_ALBEDO[9:]
				parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.FAST_SSS_ALBEDO]

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_LIGHT_SAMPLES[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_LIGHT_SAMPLES].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.FAST_SSS_OCCLUSION_SAMPLES[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.FAST_SSS_OCCLUSION_SAMPLES].value[0])

			elif model == SurfaceShader.PHYSICAL_SURFACE_SHADER:
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_COLOR_MULTIPLIER[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.PHYSICAL_COLOR_MULTIPLIER].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_ALPHA_MULTIPLIER[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.PHYSICAL_ALPHA_MULTIPLIER].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_ALPHA_MULTIPLIER[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.PHYSICAL_ALPHA_MULTIPLIER].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE[9:]
				aerialPerspMode = surfaceShader.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE]
				if aerialPerspMode != SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE_NONE:
					if aerialPerspMode == SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE_SKY_COLOR:
						parameterNode.attrib[Attr.VALUE] = aerialPerspMode
					
						parameterNode = SubElement(surfaceShaderNode, 'parameter')
						parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_AERIAL_PERSP_SKY_COLOR[9:]
						parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_SKY_COLOR].value[0])
				else:
					parameterNode.attrib[Attr.VALUE] = SurfaceShader.PHYSICAL_AERIAL_PERSP_MODE_NONE

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_AERIAL_PERSP_DISTANCE[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_DISTANCE].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.PHYSICAL_AERIAL_PERSP_INTENSITY[9:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.PHYSICAL_AERIAL_PERSP_INTENSITY].value[0])

			elif model == SurfaceShader.SMOKE_SURFACE_SHADER:
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_BOUNDING_BOX[6:]
				parameterNode.attrib[Attr.VALUE] = '%f %f %f %f %f %f' % (surfaceShader.attrs[SurfaceShader.SMOKE_BOUNDING_BOX_MIN].value[0]) % (surfaceShader.attrs[SurfaceShader.SMOKE_BOUNDING_BOX_MAX].value[0])
				
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_SHADING_MODE[6:]
				parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.SMOKE_SHADING_MODE].value[0]

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_INTERPOLATION_MODE[6:]
				parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.SMOKE_INTERPOLATION_MODE].value[0]

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_ISOSURFACE_THRESHOLD[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_ISOSURFACE_THRESHOLD].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_FILENAME[6:]
				parameterNode.attrib[Attr.VALUE] = surfaceShader.attrs[SurfaceShader.SMOKE_FILENAME].value[0]

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_STEP_SIZE[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_STEP_SIZE].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_DENSITY_CUTOFF[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_DENSITY_CUTOFF].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_DENSITY_SCALE[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_DENSITY_SCALE].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_SMOKE_COLOR[6:]
				parameterNode.attrib[Attr.VALUE] = '%f %f %f' % tuple(surfaceShader.attrs[SurfaceShader.SMOKE_SMOKE_COLOR].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_FUEL_COLOR[6:]
				parameterNode.attrib[Attr.VALUE] = '%f %f %f' % tuple(surfaceShader.attrs[SurfaceShader.SMOKE_FUEL_COLOR].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_FUEL_SCALE[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_FUEL_SCALE].value)
				
				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_LIGHT_DIRECTION[6:]
				parameterNode.attrib[Attr.VALUE] = '%f %f %f' % tuple(surfaceShader.attrs[SurfaceShader.SMOKE_LIGHT_DIRECTION].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_LIGHT_COLOR[6:]
				parameterNode.attrib[Attr.VALUE] = '%f %f %f' % tuple(surfaceShader.attrs[SurfaceShader.SMOKE_LIGHT_COLOR].value[0])

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_COLOR_SCALE[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_COLOR_SCALE].value)

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_VOLUME_OPACITY[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_VOLUME_OPACITY].value)

				parameterNode = SubElement(surfaceShaderNode, 'parameter')
				parameterNode.attrib[Attr.NAME] = SurfaceShader.SMOKE_SHADOW_OPACITY[6:]
				parameterNode.attrib[Attr.VALUE] = str(surfaceShader.attrs[SurfaceShader.SMOKE_SHADOW_OPACITY].value)

		## Serialize project:scene:assembly:object and project:scene:assembly:object_instance
		#
		for (objectName, object) in project.scene.assembly.objects.iteritems():
			objectNode = SubElement(assemblyNode, 'object')

			objectNode.attrib[Object.NAME] = object.attrs[Object.NAME]

			objectNode.attrib[Object.MODEL] = object.attrs[Object.MODEL]

			parameterNode = SubElement(objectNode, 'parameter')
			parameterNode.attrib[Attr.NAME]  = Object.FILENAME
			parameterNode.attrib[Attr.VALUE] = object.attrs[Object.FILENAME]

		## Serialize project:scene:assembly:object_instance
		#
		for (objectInstanceName, objectInstance) in project.scene.assembly.objectInstances.iteritems():
			objectInstanceNode = SubElement(assemblyNode, 'object_instance')

			objectInstanceNode.attrib[ObjectInstance.NAME]   = objectInstance.attrs[ObjectInstance.NAME]
			objectInstanceNode.attrib[ObjectInstance.OBJECT] = objectInstance.attrs[ObjectInstance.OBJECT]

			transformNode = SubElement(objectInstanceNode, 'transform')
			matrixNode = SubElement(transformNode, 'matrix')
			matrixNode.text = ''
			for i in xrange(16):
				matrixNode.text += '%f ' % objectInstance.transform.matrix.data[i]

			# We assign both front and back with the material.
			assignMaterialNode = SubElement(objectInstanceNode, 'assign_material')
			assignMaterialNode.attrib[AssignMaterial.SLOT] = str(objectInstance.assignMaterial.attrs[AssignMaterial.SLOT])
			assignMaterialNode.attrib[AssignMaterial.SIDE] = 'front'
			assignMaterialNode.attrib[AssignMaterial.MATERIAL] = objectInstance.assignMaterial.attrs[AssignMaterial.MATERIAL]

			assignMaterialNode = SubElement(objectInstanceNode, 'assign_material')
			assignMaterialNode.attrib[AssignMaterial.SLOT] = str(objectInstance.assignMaterial.attrs[AssignMaterial.SLOT])
			assignMaterialNode.attrib[AssignMaterial.SIDE] = 'back'
			assignMaterialNode.attrib[AssignMaterial.MATERIAL] = objectInstance.assignMaterial.attrs[AssignMaterial.MATERIAL]
			

		## Serialize project:scene:assembly_instance
		#
		assemblyInstanceNode = SubElement(sceneNode, 'assembly_instance')
		assemblyInstanceNode.attrib[AssemblyInstance.NAME]     = project.scene.assemblyInstance.attrs[AssemblyInstance.NAME]
		assemblyInstanceNode.attrib[AssemblyInstance.ASSEMBLY] = project.scene.assemblyInstance.attrs[AssemblyInstance.ASSEMBLY]
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
			frameNode.attrib[Frame.NAME] = frame.attrs[Frame.NAME]

			parameterNode = SubElement(frameNode, 'parameter')
			parameterNode.attrib[Attr.NAME] = Frame.CAMERA
			parameterNode.attrib[Attr.VALUE] = frame.attrs[Frame.CAMERA]

			parameterNode = SubElement(frameNode, 'parameter')
			parameterNode.attrib[Attr.NAME]  = Frame.RESOLUTION
			parameterNode.attrib[Attr.VALUE] = '%d %d' % frame.attrs[Frame.RESOLUTION]

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

	theProject = Project()

	for sohoCamera in soho.objectList('objlist:camera'):
		camera = Camera()
		camera.Resolve(sohoCamera, moments)
		theProject.scene.camera = camera
		break

	# Export light.
	# TODO: Not use wrangler now
	#
	for sohoLight in soho.objectList('objlist:light'):
		sohoLightName = sohoLight.getDefaultedString('object:name', sohoLight, [''])[0]
		if not theProject.scene.assembly.lights.has_key(sohoLightName):
			light = Light()
			light.Resolve(sohoLight, moments)
			theProject.scene.assembly.lights[sohoLightName] = light

			exitanceName = light.exitance.attrs[Color.NAME]
			if not theProject.scene.assembly.colors.has_key(exitanceName):
				theProject.scene.assembly.colors[exitanceName] = light.exitance

	# Export geometry data.
	#
	for sohoObjectInstance in soho.objectList('objlist:instance'):
		object = Object()
		object.Resolve(sohoObjectInstance, moments)
		objectName = object.attrs[Object.NAME]
		if not theProject.scene.assembly.objects.has_key(objectName):
			theProject.scene.assembly.objects[objectName] = object

		objectSopNode = hou.node(sohoObjectInstance.getName())

		materialNodePath = objectSopNode.evalParm('shop_materialpath')
		materialNodeName = materialNodePath
		ProcessMaterial(materialNodeName, theProject, moments)
		
		if not theProject.scene.assembly.objectInstances.has_key(objectName):
			objectInstance = ObjectInstance()
			objectInstance.Resolve(sohoObjectInstance, moments)
			objectInstance.assignMaterial.attrs[AssignMaterial.MATERIAL] = materialNodeName
			theProject.scene.assembly.objectInstances[objectName] = objectInstance

	frame = Frame()
	frame.Resolve(None, moments)
	theProject.output.frames[frame.attrs[Frame.NAME]] = frame

	theProject.configurations.Resolve(None, moments)

	serializer = XmlSerializer()
	serializer.Serialize(theProject)
	
	theProject = None
