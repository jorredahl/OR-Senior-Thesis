"""
Model exported as python.
Name : model
Group : 
With QGIS : 33410
"""

from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterFile

import pandas as pd
import os
import processing


class Model(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('csv_directory', 'CSV directory', behavior=QgsProcessingParameterFile.Folder, fileFilter='All files (*.*)', defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        results = {}
        outputs = {}
        
        dfs = []
        
        for filename in os.listdir(parameters['csv_directory']):
            file_path = os.path.join(parameters['csv_directory'], filename)
        
            df = pd.read_csv(file_path)

            df = df[df['Coordinates'].notnull() & (df['Coordinates'] != '')]
        
            df[['Latitude', 'Longitude']] = df['Coordinates'].str.split(',', expand=True)
            
            df['Latitude'] = df['Latitude'].astype(float)
            df['Longitude'] = df['Longitude'].astype(float)
            
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df.to_csv("C:\\Users\\jdahl\\Downloads\\temp_files\\combined_df.csv", index=False)

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
