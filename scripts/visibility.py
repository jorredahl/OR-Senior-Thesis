"""
Model exported as python.
Name : model
Group : 
With QGIS : 33410
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsVectorLayer
from qgis.core import QgsPointXY
from qgis.core import QgsGeometry

import processing
import os
import geopandas as gpd


class Model(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('dem', 'dem', defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('dsm_central', 'dsm_central', defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('roads', 'roads', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterString('file_name_of_roads', 'file name of roads', multiLine=False, defaultValue="C://Users//jdahl//Downloads//output_prev.shp"))
        self.addParameter(QgsProcessingParameterString('output', 'output', multiLine=False, defaultValue="C://Users//jdahl//Downloads//output.shp"))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        results = {}
        outputs = {}
        
        road_layer = self.parameterAsVectorLayer(parameters, 'roads', context)
        road_gdf = gpd.read_file(parameters['file_name_of_roads'])
        road_gdf.to_file(parameters['output'])
        
        feedback = QgsProcessingMultiStepFeedback(road_layer.featureCount(), model_feedback)
        
        i = 0
        for feature in road_layer.getFeatures():
            i = i + 1
            object_id = feature['OBJECTID']
            road_gdf = gpd.read_file(parameters['output'])
            featuredone = True
            if 'min viz' not in road_gdf.columns:
                featuredone = False
            else:
                if road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'min viz'].isna().any():
                    featuredone = False
            
            if (not featuredone):
                temp = QgsVectorLayer("LineString?crs=epsg:32145", "temp", "memory")
                temp_pr = temp.dataProvider()
                temp_pr.addAttributes(road_layer.fields())
                temp_pr.addFeatures([feature])
                
                # Bounding boxes
                alg_params = {
                    'INPUT': temp, #parameters['roads']
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['BoundingBoxes'] = processing.run('native:boundingboxes', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Buffer
                alg_params = {
                    'DISSOLVE': False,
                    'DISTANCE': 5,
                    'END_CAP_STYLE': 0,  # Round
                    'INPUT': temp,
                    'JOIN_STYLE': 0,  # Round
                    'MITER_LIMIT': 2,
                    'SEGMENTS': 5,
                    'SEPARATE_DISJOINT': False,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Points along geometry
                alg_params = {
                    'DISTANCE': 10,
                    'END_OFFSET': 0,
                    'INPUT': temp,
                    'START_OFFSET': 0,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['PointsAlongGeometry'] = processing.run('native:pointsalonglines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Clip dem by extent
                alg_params = {
                    'DATA_TYPE': 0,  # Use Input Layer Data Type
                    'EXTRA': '',
                    'INPUT': parameters['dem'],
                    'NODATA': None,
                    'OPTIONS': '',
                    'OVERCRS': False,
                    'PROJWIN': outputs['BoundingBoxes']['OUTPUT'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['ClipDemByExtent'] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Clip central dsm by extent
                alg_params = {
                    'DATA_TYPE': 0,  # Use Input Layer Data Type
                    'EXTRA': '',
                    'INPUT': parameters['dsm_central'],
                    'NODATA': None,
                    'OPTIONS': '',
                    'OVERCRS': False,
                    'PROJWIN': outputs['BoundingBoxes']['OUTPUT'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['ClipCentralDsmByExtent'] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Clip raster by mask layer
                alg_params = {
                    'ALPHA_BAND': False,
                    'CROP_TO_CUTLINE': True,
                    'DATA_TYPE': 0,  # Use Input Layer Data Type
                    'EXTRA': '',
                    'INPUT': outputs['ClipDemByExtent']['OUTPUT'],
                    'KEEP_RESOLUTION': False,
                    'MASK': outputs['Buffer']['OUTPUT'],
                    'MULTITHREADING': False,
                    'NODATA': None,
                    'OPTIONS': '',
                    'SET_RESOLUTION': False,
                    'SOURCE_CRS': 'ProjectCrs',
                    'TARGET_CRS': 'ProjectCrs',
                    'TARGET_EXTENT': None,
                    'X_RESOLUTION': None,
                    'Y_RESOLUTION': None,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['ClipRasterByMaskLayer'] = processing.run('gdal:cliprasterbymasklayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Merge
                alg_params = {
                    'DATA_TYPE': 5,  # Float32
                    'EXTRA': '',
                    'INPUT': [outputs['ClipCentralDsmByExtent']['OUTPUT'],outputs['ClipRasterByMaskLayer']['OUTPUT']],
                    'NODATA_INPUT': None,
                    'NODATA_OUTPUT': None,
                    'OPTIONS': '',
                    'PCT': False,
                    'SEPARATE': False,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['Merge'] = processing.run('gdal:merge', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Clip composite raster by extent
                alg_params = {
                    'DATA_TYPE': 0,  # Use Input Layer Data Type
                    'EXTRA': '',
                    'INPUT': outputs['Merge']['OUTPUT'],
                    'NODATA': None,
                    'OPTIONS': '',
                    'OVERCRS': False,
                    'PROJWIN': outputs['BoundingBoxes']['OUTPUT'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['ClipCompositeRasterByExtent'] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                
                # Extract layer extent
                alg_params = {
                    'INPUT': outputs['ClipCompositeRasterByExtent']['OUTPUT'],
                    'ROUND_TO': 0,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['ExtractLayerExtent'] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                # Clip
                alg_params = {
                    'INPUT': outputs['PointsAlongGeometry']['OUTPUT'],
                    'OVERLAY': outputs['ExtractLayerExtent']['OUTPUT'],
                    'OUTPUT': 'C://Users//jdahl//Downloads//temp_files//temp_points.shp'
                }
                outputs['PointsClip'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                
                points_layer = gpd.read_file('C://Users//jdahl//Downloads//temp_files//temp_points.shp')
                min_viz = 1.0
                viz_sum = 0.0
                for index, row in points_layer.iterrows():
                    geom = row['geometry']
                    
                    qgs_point = QgsPointXY(geom.x, geom.y)
                    
                    point_geom = QgsGeometry.fromPointXY(qgs_point)
                    
                    point = point_geom.asPoint()
                    
                    alg_params = {
                        'BAND': 1,
                        'EXTRA': '',
                        'INPUT': outputs['ClipCompositeRasterByExtent']['OUTPUT'],
                        'MAX_DISTANCE': 250,
                        'OBSERVER': point,
                        'OBSERVER_HEIGHT': 2,
                        'OPTIONS': '',
                        'TARGET_HEIGHT': 1,
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['Viewshed'] = processing.run('gdal:viewshed', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                    
                    # Polygonize (raster to vector)
                    alg_params = {
                        'BAND': 1,
                        'EIGHT_CONNECTEDNESS': False,
                        'EXTRA': '',
                        'FIELD': 'DN',
                        'INPUT': outputs['Viewshed']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['PolygonizeRasterToVector'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Create layer from point
                    alg_params = {
                        'INPUT': point,
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['CreateLayerFromPoint'] = processing.run('native:pointtolayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Buffer
                    alg_params = {
                        'DISSOLVE': False,
                        'DISTANCE': 250,
                        'END_CAP_STYLE': 0,  # Round
                        'INPUT': outputs['CreateLayerFromPoint']['OUTPUT'],
                        'JOIN_STYLE': 0,  # Round
                        'MITER_LIMIT': 2,
                        'SEGMENTS': 5,
                        'SEPARATE_DISJOINT': False,
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['BufferPoint'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Select by attribute
                    alg_params = {
                        'FIELD': 'DN',
                        'INPUT': outputs['PolygonizeRasterToVector']['OUTPUT'],
                        'METHOD': 0,  # creating new selection
                        'OPERATOR': 0,  # =
                        'VALUE': '255'
                    }
                    outputs['SelectByAttribute'] = processing.run('qgis:selectbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Extract selected features
                    alg_params = {
                        'INPUT': outputs['SelectByAttribute']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['ExtractSelectedFeatures'] = processing.run('native:saveselectedfeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # all line length
                    alg_params = {
                        'COUNT_FIELD': 'COUNT',
                        'LEN_FIELD': 'lengthall',
                        'LINES': temp,
                        'POLYGONS': outputs['BufferPoint']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['AllLineLength'] = processing.run('native:sumlinelengths', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Dissolve
                    alg_params = {
                        'FIELD': [''],
                        'INPUT': outputs['ExtractSelectedFeatures']['OUTPUT'],
                        'SEPARATE_DISJOINT': False,
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['Dissolve'] = processing.run('native:dissolve', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Field calculator all
                    alg_params = {
                        'FIELD_LENGTH': 0,
                        'FIELD_NAME': 'Id',
                        'FIELD_PRECISION': 0,
                        'FIELD_TYPE': 2,  # Text (string)
                        'FORMULA': "'1'",
                        'INPUT': outputs['AllLineLength']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['FieldCalculatorAll'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # visible line length
                    alg_params = {
                        'COUNT_FIELD': 'COUNT',
                        'LEN_FIELD': 'lengthviz',
                        'LINES': temp,
                        'POLYGONS': outputs['Dissolve']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['VisibleLineLength'] = processing.run('native:sumlinelengths', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Field calculator viz
                    alg_params = {
                        'FIELD_LENGTH': 0,
                        'FIELD_NAME': 'id',
                        'FIELD_PRECISION': 0,
                        'FIELD_TYPE': 2,  # Text (string)
                        'FORMULA': "'1'",
                        'INPUT': outputs['VisibleLineLength']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['FieldCalculatorViz'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                    # Join attributes by field value
                    alg_params = {
                        'DISCARD_NONMATCHING': False,
                        'FIELD': 'Id',
                        'FIELDS_TO_COPY': [''],
                        'FIELD_2': 'Id',
                        'INPUT': outputs['FieldCalculatorAll']['OUTPUT'],
                        'INPUT_2': outputs['FieldCalculatorViz']['OUTPUT'],
                        'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
                        'PREFIX': '',
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    outputs['JoinAttributesByFieldValue'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                    
                    # Field calculator
                    alg_params = {
                        'FIELD_LENGTH': 0,
                        'FIELD_NAME': 'lenrat',
                        'FIELD_PRECISION': 0,
                        'FIELD_TYPE': 0,  # Decimal (double)
                        'FORMULA': '"lengthviz" / "lengthall"',
                        'INPUT': outputs['JoinAttributesByFieldValue']['OUTPUT'],
                        'OUTPUT': 'C://Users//jdahl//Downloads//temp_files//visibility.shp'
                    }
                    outputs['FieldCalculator'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                    
                    viz_val = gpd.read_file('C://Users//jdahl//Downloads//temp_files//visibility.shp').loc[0, 'lenrat']
                    
                    if viz_val < min_viz:
                        min_viz = viz_val
                    viz_sum = viz_sum + viz_val
                    
                if (len(points_layer) == 0):
                    avg_viz = 1.0
                else:
                    avg_viz = viz_sum / len(points_layer)
                
                if 'min viz' not in road_gdf.columns:
                    road_gdf['min viz'] = None
                if 'avg viz' not in road_gdf.columns:
                    road_gdf['avg viz'] = None
                    
                road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'min viz'] = min_viz
                road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'avg viz'] = avg_viz
            
            feedback.setCurrentStep(i)
            if feedback.isCanceled():
                return {}
            outputs = {}
            
            road_gdf.to_file(parameters['output'])
            
        return results

    def name(self):
        return 'model'

    def displayName(self):
        return 'model'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Model()
