"""
Model exported as python.
Name : model
Group : 
With QGIS : 33410
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsVectorLayer
from qgis.core import QgsPointXY
from qgis.core import QgsGeometry

import processing
import geopandas as gpd
import math


class Model(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
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
            
            # Points along geometry
            alg_params = {
                'DISTANCE': 10,
                'END_OFFSET': 0,
                'INPUT': temp,
                'START_OFFSET': 0,
                'OUTPUT': 'C://Users//jdahl//Downloads//temp_files//temp_points.shp'
            }
            outputs['PointsAlongGeometry'] = processing.run('native:pointsalonglines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            points_layer = gpd.read_file('C://Users//jdahl//Downloads//temp_files//temp_points.shp')
            
            ps = []
            
            for index, row in points_layer.iterrows():
                geom = row['geometry']
                
                qgs_point = QgsPointXY(geom.x, geom.y)
                    
                point_geom = QgsGeometry.fromPointXY(qgs_point)
                    
                point = point_geom.asPoint()
                    
                ps.append(point)
                
            radii = []
            
            for index in range(len(ps)):
                if (index != 0 and index != len(ps) - 1):
                    p1 = ps[index - 1]
                    p2 = ps[index]
                    p3 = ps[index + 1]
                    
                    a = p1.distance(p2)
                    b = p2.distance(p3)
                    c = p3.distance(p1)
                    
                    area = abs(p1.x()*(p2.y() - p3.y()) + p2.x()*(p3.y() - p1.y()) + p3.x()*(p1.y() - p2.y())) / 2
                    
                    if (area == 0.0):
                        radii.append(100000.0)
                    else:
                        radii.append((a * b * c) / (4 * area))
            
            med_curve = 100000.0
            min_curve = 100000.0
            lq_curve = 100000.0
            if (len(radii) > 0):
                radii = sorted(radii)
                min_curve = radii[0]
                if(len(radii) > 1):
                    med_curve = radii[len(radii) // 2 - 1]
                    if(len(radii) > 3):
                        lq_curve = radii[len(radii) // 4 - 1]
            
            if 'med curve' not in road_gdf.columns:
                    road_gdf['med curve'] = None
            if 'min curve' not in road_gdf.columns:
                    road_gdf['min curve'] = None
            if 'lq curve' not in road_gdf.columns:
                    road_gdf['lq curve'] = None
            
            object_id = feature['OBJECTID']
            
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'med curve'] = med_curve
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'min curve'] = min_curve
            road_gdf.loc[road_gdf['OBJECTID'] == object_id, 'lq curve'] = lq_curve
            
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
