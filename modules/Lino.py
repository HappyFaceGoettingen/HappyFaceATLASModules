# Copyright 2013 II. Physikalisches Institut - Georg-August-Universitaet Goettingen
# Author: Lino Gerlach (lino.gerlach@stud.uni-goettingen.de)
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import hf
from sqlalchemy import *
import json
from datetime import datetime

class Lino3(hf.module.ModuleBase):
    config_keys = {
#        'key': ('description', 'default value'),
	'xml_url': ('url to xml file', 'http://dashb-atlas-data.cern.ch/dashboard/request.py/activity-summary.xml'),
	'json_url': ('url to json file', 'http://dashb-atlas-data.cern.ch/dashboard/request.py/activity-summary.json')
    }

    config_hint = 'Adjust the parameters.'

    table_columns = [
        Column('xml_url', TEXT),
	Column('json_url', TEXT),
	Column('source_json_url', TEXT),
    ], []

    subtable_columns = {
        'subtable_columns': ([
        Column('column_name', TEXT),
        ], []),
    }

    def prepareAcquisition(self):
        
#	xml_url = self.config['xml_url']
	self.json_url = self.config['json_url']
#       self.xml_url = hf.downloadService.addDownload(xml_url)
	self.source = hf.downloadService.addDownload(self.json_url)

        self.subtable_name_db_value_list = []
#	self.services_db_value_list = []
	

    def extractData(self):
        data = {
            'column_name': 'ihihkhkh',
#	    'source_xml_url': self.xml_url.getSourceUrl(),
#	    'json_url': self.json_url,
#	    'json_url': self.config['json_url'],
        }
        '''
#	source_tree = etree.parse(open(self.xml_url.getTmpPath()))
#	source_tree = etree.parse(open(self.json_url.getTmpPath()))
#        root = source_tree.getroot()
        content = open(self.source.getTmpPath()).read()
        '''
       # list = {}
       # list['column_name'] = 'sfsdf'

#	self.subtable_name_db_value_list = [{'column_name':'entry'}]
	#self.subtable_name_db_value_list.append({})
	#self.subtable_name_db_value_list[0] = list

	self.services_db_value_list = []
        
        return data

    def fillSubtables(self, parent_id):
     
       self.subtables['subtable_columns'].insert().execute([dict(parent_id=parent_id, **row) for row in self.subtable_name_db_value_list])

    def getTemplateData(self):
       
       data = hf.module.ModuleBase.getTemplateData(self)
       
       #details = self.subtables['subtable_columns'].select().where(self.subtables['subtable_columns'].c.parent_id==self.dataset['id']).execute().fetchal()
       #data['details'] = map(dict, details)
       
       return data





