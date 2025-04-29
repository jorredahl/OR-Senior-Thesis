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
        
        raster_layer = self.parameterAsRasterLayer(parameters, 'raster', context)
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
            
            # Points along geometry
            alg_params = {
                'DISTANCE': 1,
                'END_OFFSET': 0,
                'INPUT': temp,
                'START_OFFSET': 0,
                'OUTPUT': 'C://Users//jdahl//Downloads//temp_files//temp_points.shp'
            }
            outputs['PointsAlongGeometry'] = processing.run('native:pointsalonglines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            points_layer = gpd.read_file('C://Users//jdahl//Downloads//temp_files//temp_points.shp')
            
            vals = []
            
            for index, row in points_layer.iterrows():
                geom = row['geometry']
                
                val, res = raster_layer.dataProvider().sample(QgsPointXY(geom.x, geom.y), 1)
                
                vals.append(val)
                
            slopes = []
            
            for index in range(len(vals)):
                if (index != 0):
                    slopes.append(abs(vals[index] - vals[index-1]))
            
            med_slope = 0
            mean_slope = 0
            max_slope = 0
            uq_slope = 0
            if (len(slopes) > 0):
                slopes = sorted(slopes)
                mean_slope = abs(vals[0] - vals[len(vals) - 1]) / len(vals)
                max_slope = slopes[len(slopes) - 1]
                if(len(slopes) > 1):
                    med_slope = slopes[len(slopes) // 2 - 1]
                    if(len(slopes) > 3):
                        uq_slope = slopes[3 * (len(slopes) // 4) - 1]
            
            if 'med slope' not in road_gdf.columns:
                    road_gdf['med slope'] = None
            if 'mean slope' not in road_gdf.columns:
                    road_gdf['mean slope'] = None
            if 'max slope' not in road_gdf.columns:
                    road_gdf['max slope'] = None
            if 'uq slope' not in road_gdf.columns:
                    road_gdf['uq slope'] = None
            
            object_id = feature['OBJECTID']
            
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'med slope'] = med_slope
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'mean slope'] = mean_slope
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'max slope'] = max_slope
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'uq slope'] = uq_slope
            
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
