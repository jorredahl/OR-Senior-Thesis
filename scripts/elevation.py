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

import processing
import geopandas as gpd
import math


class Model(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('raster', 'raster', defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('roads', 'roads', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterString('file_name_of_roads', 'file name of roads', multiLine=False, defaultValue="C://Users//jdahl//Downloads//test_roads.shp"))
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
            
            temp = QgsVectorLayer("LineString?crs=epsg:32145", "temp", "memory")
            temp_pr = temp.dataProvider()
            temp_pr.addAttributes(road_layer.fields())
            temp_pr.addFeatures([feature])

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

            # Zonal statistics
            alg_params = {
                'COLUMN_PREFIX': 'elev_',
                'INPUT': outputs['Buffer']['OUTPUT'],
                'INPUT_RASTER': parameters['raster'],
                'RASTER_BAND': 1,
                'STATISTICS': [2,3,4,7],  # Mean,Median,St dev,Range
                'OUTPUT': 'C://Users//jdahl//Downloads//temp_files//temp_stats.shp'
            }
            outputs['ZonalStatistics'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            stats_layer = gpd.read_file('C://Users//jdahl//Downloads//temp_files//temp_stats.shp')
            
            if 'elev_mean' not in road_gdf.columns:
                road_gdf['elev_mean'] = None
            if 'elev_media' not in road_gdf.columns:
                road_gdf['elev_media'] = None
            if 'elev_stdev' not in road_gdf.columns:
                road_gdf['elev_stdev'] = None
            if 'elev_range' not in road_gdf.columns:
                road_gdf['elev_range'] = None
            
            object_id = feature['OBJECTID']
            
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'elev_mean'] = stats_layer.loc[0, 'elev_mean']
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'elev_media'] = stats_layer.loc[0, 'elev_media']
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'elev_stdev'] = stats_layer.loc[0, 'elev_stdev']
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'elev_range'] = stats_layer.loc[0, 'elev_range']
            
            i = i + 1
            
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
