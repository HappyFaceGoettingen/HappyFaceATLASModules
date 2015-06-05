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

class Lino(hf.module.ModuleBase):
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
	Column('number', TEXT),
    ], []

    subtable_columns = {
        'subtable_name': ([
        Column('sub_json', TEXT),
        ], []),
    }

    def prepareAcquisition(self):        
#	xml_url = self.config['xml_url']
	self.json_url = self.config['json_url']
	self.number = self.config['json_url']

	self.source = hf.downloadService.addDownload(self.json_url)

        self.subtable_name_db_value_list = []
#	self.services_db_value_list = []
	

    def extractData(self):
        data = {
#	    'source_xml_url': self.xml_url.getSourceUrl(),
	    'json_url': self.json_url,
	    'number': self.number,
        }

        content = open(self.source.getTmpPath()).read()

	data['json_url'] = self.json_url
	data['number'] = self.number	

	self.subtable_name_db_value_list = [
	    {
		'sub_json': 'entry',
	    }
	]

        return data

    def fillSubtables(self, parent_id):
	self.subtables['subtable_name'].insert().execute([dict(parent_id=parent_id, **row) for row in self.subtable_name_db_value_list])
	


    def getTemplateData(self):
	data = hf.module.ModuleBase.getTemplateData(self)
	details = self.subtables['subtable_name'].select().where(self.subtables['subtable_name'].c.parent_id==self.dataset['id']).execute().fetchal()
	data['details'] = map(dict, details)

	return data





