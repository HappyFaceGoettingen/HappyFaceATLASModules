# Copyright 2013 II. Physikalisches Institut - Georg-August-Universitaet Goettingen
# Author: Christian Georg Wehrberger (christian@wehrberger.de)
# Edited by Lino Gerlach (lino.gerlach@stud.uni-goettingen.de)
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
import urllib2,json
from datetime import datetime

class Panda2(hf.module.ModuleBase):
    config_keys = {
        'schedconfig_url': ('Schedconfig link', ''),
        'panda_analysis_url': ('Panda analysis URL', ''),
        'panda_analysis_interval': ('Interval for analysis queue in hours', '3'),
        'panda_production_url': ('Panda production URL', ''),
        'panda_production_interval': ('Interval for production queue in hours', '3'),
        'site_names': ('Site names', 'praguelcg2,LRZ-LMU,CSCS-LCG2,GoeGrid,FZK-LCG2,PSNC,HEPHY-UIBK,UNI-FREIBURG,wuppertalprod,TUDresden-ZIH,MPPMU,DESY-HH,DESY-ZN,CYFRONET-LCG2,UNI-DORTMUND,FMPhI-UNIBA,IEPSAS-Kosice'),
        'failed_warning': ('Failed rate that triggers warning status', '30'),
        'failed_critical': ('Failed rate that triggers critical status', '50'),
        'wns_url': ('Worker node information table link', ''),
    }

    config_hint = 'Specify one or multiple queues of sites you would like to monitor. A queue <queue> of type <analysis|production> for site <site> (that has to be mentioned in parameter site_names in order to be taken into account) is specified as follows: <site>_<analysis|production> = <queue>. Several queues for the same site are given in the same parameter, separated by commas.'

    table_columns = [
        Column('site_names', TEXT),
    ], []

    subtable_columns = {
        'site_details': ([
        Column('wns_failed', TEXT),#New columns for worker node graphs (plotting data is saved as string)
        Column('wns_finished', TEXT),
        Column('filename_failed_plot', TEXT),
        Column('filename_finished_plot', TEXT),
        Column('site_name', TEXT),
        Column('queue_name', TEXT),
        Column('queue_link', TEXT),
        Column('queue_type', TEXT),
        Column('efficiency', FLOAT),
        Column('status', TEXT),
        Column('active_jobs', INT),
        Column('running_jobs', INT),
        Column('defined_jobs', INT),
        Column('assigned_jobs', INT),
        Column('holding_jobs', INT),
        Column('finished_jobs', INT),
        Column('failed_jobs', INT),
        Column('cancelled_jobs', INT),
        Column('transferring_jobs', INT),
        Column('merging_jobs', INT),
    ], ['filename_failed_plot', 'filename_finished_plot'])}

    def prepareAcquisition(self):

        self.source_url = self.config['schedconfig_url'].split('|')[2]
        # get the site names from the configuration file
        self.site_names_nolist = ''
        try:
            self.site_names_nolist = self.config['site_names']
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        self.site_names = self.site_names_nolist.split(',')
        self.queue_names = {}

        for site in self.site_names:
            self.queue_names[site] = {}
            (self.queue_names[site])['analysis'] = []
            (self.queue_names[site])['production'] = []
            try:
                analysis_queues = self.config[site.lower()+'_analysis'].split(',') # for each site get the analysis queues
                (self.queue_names[site])['analysis'] = analysis_queues
                if not analysis_queues:
                    print('WARNING: Site '+site+' does not specify any analysis queues!')
                else:
                    all_empty = 1 # check whether list objects are empty strings
                    for queue in analysis_queues:
                        if queue != '':
                            all_empty = False
                    if all_empty == 1:
                        print('WARNING: Site '+site+' does not specify any analysis queues!')
            except hf.ConfigError, ex:
                pass
                #raise hf.exceptions.ConfigError('"%s"' % str(ex))
            try:
                production_queues = self.config[site.lower()+'_production'].split(',') # for each site get the production queues
                (self.queue_names[site])['production'] = production_queues
                if not production_queues:
                    print('WARNING: Site '+site+' does not specify any production queues!')
                else:
                    all_empty = 1 # check whether list objects are empty strings
                    for queue in production_queues:
                        if queue != '':
                            all_empty = False
                    if all_empty == 1:
                        print('WARNING: Site '+site+' does not specify any production queues!')
            except hf.ConfigError, ex:
                pass
                #raise hf.exceptions.ConfigError('"%s"' % str(ex))

        # get all urls from the configuration file and queue them for downloading
        schedconfig_url = ''
        try:
            schedconfig_url = self.config['schedconfig_url']
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        self.schedconfig_source = hf.downloadService.addDownload(schedconfig_url) ##


        self.wns_url = ''
        try:
            self.wns_url = self.config['wns_url'] # New worker node url
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        self.panda_production_url = ''
        try:
            self.panda_production_url = self.config['panda_production_url']
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        self.panda_production_interval = ''
        try:
            self.panda_production_interval = self.config['panda_production_interval']
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        self.panda_analysis_url = ''
        try:
            self.panda_analysis_url = self.config['panda_analysis_url']
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        self.panda_analysis_interval = ''
        try:
            self.panda_analysis_interval = self.config['panda_analysis_interval']
        except hf.ConfigError, ex:
            raise hf.exceptions.ConfigError('"%s"' % str(ex))

        # assemble the urls for all queues and queue them for downloading (for job list and worker node)
        self.site_sources = {}
        self.wns_sources = {}
        for site in self.site_names:
            self.site_sources[site] = {}
            self.wns_sources[site] = {}
            (self.site_sources[site])['analysis'] = []
            (self.site_sources[site])['production'] = []
            (self.wns_sources[site])['analysis'] = []
            (self.wns_sources[site])['production'] = []
            for analysis_queue in (self.queue_names[site])['analysis']:
                analysis_url = self.panda_analysis_url+analysis_queue+'&hours='+self.panda_analysis_interval
                download = hf.downloadService.addDownload(analysis_url)
                (self.site_sources[site])['analysis'].append(download)
                wns_url = self.wns_url+analysis_queue
                download = hf.downloadService.addDownload(wns_url)
                self.wns_sources[site]['analysis'].append(download)
            for production_queue in (self.queue_names[site])['production']:
                production_url = self.panda_production_url+production_queue+'&hours='+self.panda_production_interval
                download = hf.downloadService.addDownload(production_url)
                (self.site_sources[site])['production'].append(download)
                wns_url = self.wns_url+production_queue
                download = hf.downloadService.addDownload(wns_url)
                self.wns_sources[site]['production'].append(download)
        
        self.details_db_value_list = []

    def extractData(self):

        data = {
            'site_names':(self.site_names_nolist),
            'status':1,
        }

        # check for download errors
        schedconfig_content = ''
        if self.schedconfig_source.errorOccured():
            print('WARNING: The url '+self.schedconfig_source.getSourceUrl()+' could not be downloaded!')
        else:
            schedconfig_content = open(self.schedconfig_source.getTmpPath()).read()

        for site in self.site_names:
            for source in (self.site_sources[site])['analysis']:
                if source.errorOccured():
                    print('WARNING: The url '+source.getSourceUrl()+' could not be downloaded!')
            for source in (self.site_sources[site])['production']:
                if source.errorOccured():
                    print('WARNING: The url '+source.getSourceUrl()+' could not be downloaded!')
            for source in (self.wns_sources[site])['analysis']:
                if source.errorOccured():
                    print('WARNING: The url '+source.getSourceUrl()+' could not be downloaded!')
            for source in (self.wns_sources[site])['production']:
                if source.errorOccured():
                    print('WARNING: The url '+source.getSourceUrl()+' could not be downloaded!')

        queue_details = {}
        for site in self.site_names:
            grid_site_info = cloud_class2(datetime.now(),schedconfig_content)
            # parse information from the file for each analysis queue
            for source, queue, wns in map(None, (self.site_sources[site])['analysis'], (self.queue_names[site])['analysis'], self.wns_sources[site]['analysis']):
                queue_info = {}
                source_content = open(source.getTmpPath()).read()
                wns_content = open(wns.getTmpPath()).read()
                queue_info['wns_failed'] = grid_site_info.get_wns_failed(wns_content)
                queue_info['wns_finished'] = grid_site_info.get_wns_finished(wns_content)
                bigpanda_info = bigpanda_class(datetime.now(),source_content)
                analysis_info=grid_site_info.get_queue_status(queue)
                queue_info['site_name'] = site
                queue_info['queue_name'] = queue
                queue_info['queue_link'] = self.panda_analysis_url.split('|')[2]+queue+'&hours='+self.panda_analysis_interval
                queue_info['queue_type'] = 'analysis'
                queue_info['status'] = analysis_info[1]
                queue_info['active_jobs'] = bigpanda_info.get_numberof_activated_jobs()
                queue_info['running_jobs'] = bigpanda_info.get_numberof_running_jobs()
                queue_info['defined_jobs'] = bigpanda_info.get_numberof_defined_jobs()
                queue_info['assigned_jobs'] = bigpanda_info.get_numberof_assigned_jobs()
                queue_info['holding_jobs'] = bigpanda_info.get_numberof_holding_jobs()
                queue_info['finished_jobs'] = bigpanda_info.get_numberof_finished_jobs()
                queue_info['failed_jobs'] = bigpanda_info.get_numberof_failed_jobs()
                queue_info['cancelled_jobs'] = bigpanda_info.get_numberof_cancelled_jobs()
                queue_info['transferring_jobs'] = bigpanda_info.get_numberof_transferring_jobs()
                queue_info['merging_jobs'] = bigpanda_info.get_numberof_merging_jobs()
                # calculate the efficiency
                if (queue_info['finished_jobs'] + queue_info['failed_jobs']) != 0:
                    queue_info['efficiency'] = (queue_info['finished_jobs']*100)/(queue_info['finished_jobs'] + queue_info['failed_jobs'])
                else:
                    queue_info['efficiency'] = 0
                # determine the module status
                if 100. - float(queue_info['efficiency']) >= int(self.config['failed_warning']) and 100. - float(queue_info['efficiency']) < int(self.config['failed_critical']):
                    data['status'] = min(data['status'],0.5)
                elif 100. - float(queue_info['efficiency']) >= int(self.config['failed_critical']):
                    data['status'] = min(data['status'],0.)
                queue_info['filename_failed_plot'] = grid_site_info.wns_plot(queue,queue_info['wns_failed'],'Failed',self.run,self.instance_name)
                queue_info['filename_finished_plot'] = grid_site_info.wns_plot(queue,queue_info['wns_finished'],'Finished',self.run,self.instance_name)

                # add to array
                queue_details[site+'_'+queue+'_analysis'] = queue_info


            # parse information from the file for each production queue
            for source, queue, wns in map(None, (self.site_sources[site])['production'], (self.queue_names[site])['production'], self.wns_sources[site]['production']):
                queue_info = {}
                source_content = open(source.getTmpPath()).read()
                wns_content = open(wns.getTmpPath()).read()
                queue_info['wns_failed'] = grid_site_info.get_wns_failed(wns_content)
                queue_info['wns_finished'] = grid_site_info.get_wns_finished(wns_content)
                bigpanda_info = bigpanda_class(datetime.now(),source_content)
                production_info=grid_site_info.get_queue_status(queue)
                queue_info['site_name'] = site
                queue_info['queue_name'] = queue
                queue_info['queue_link'] = self.panda_production_url.split('|')[2]+queue+'&hours='+self.panda_production_interval
                queue_info['queue_type'] = 'production'
                queue_info['status'] = production_info[1]
                if queue_info['status'].lower() == 'online':
                    data['status'] = min(data['status'], 1)
                elif (queue_info['status'].lower()) == 'offline' or (queue_info['status'].lower()) == 'brokeroff':
                    data['status'] = min(data['status'], 0.5)
                else:
                    data['status'] = min(data['status'], 0)
                queue_info['active_jobs'] = bigpanda_info.get_numberof_activated_jobs()
                queue_info['running_jobs'] = bigpanda_info.get_numberof_running_jobs()
                queue_info['defined_jobs'] = bigpanda_info.get_numberof_defined_jobs()
                queue_info['assigned_jobs'] = bigpanda_info.get_numberof_assigned_jobs()
                queue_info['holding_jobs'] = bigpanda_info.get_numberof_holding_jobs()
                queue_info['finished_jobs'] = bigpanda_info.get_numberof_finished_jobs()
                queue_info['failed_jobs'] = bigpanda_info.get_numberof_failed_jobs()
                queue_info['cancelled_jobs'] = bigpanda_info.get_numberof_cancelled_jobs()
                queue_info['transferring_jobs'] = bigpanda_info.get_numberof_transferring_jobs()
                queue_info['merging_jobs'] = bigpanda_info.get_numberof_merging_jobs()
                # calculate the efficiency
                if (queue_info['finished_jobs'] + queue_info['failed_jobs']) != 0:
                    queue_info['efficiency'] = (queue_info['finished_jobs']*100)/(queue_info['finished_jobs'] + queue_info['failed_jobs'])
                else:
                    queue_info['efficiency'] = 0
                queue_info['filename_failed_plot'] = grid_site_info.wns_plot(queue,queue_info['wns_failed'],'Failed',self.run,self.instance_name)
                queue_info['filename_finished_plot'] = grid_site_info.wns_plot(queue,queue_info['wns_finished'],'Finished',self.run,self.instance_name)

                # add to array
                queue_details[site+'_'+queue+'_production'] = queue_info

        self.details_db_value_list = [{'wns_failed':(queue_details[queue])['wns_failed'], 'wns_finished':(queue_details[queue])['wns_finished'], 'site_name':(queue_details[queue])['site_name'], 'queue_type':(queue_details[queue])['queue_type'], 'queue_name':(queue_details[queue])['queue_name'], 'queue_link':(queue_details[queue])['queue_link'],'efficiency':(queue_details[queue])['efficiency'], 'status':(queue_details[queue])['status'], 'active_jobs':(queue_details[queue])['active_jobs'], 'running_jobs':(queue_details[queue])['running_jobs'], 'defined_jobs':(queue_details[queue])['defined_jobs'],'assigned_jobs':(queue_details[queue])['assigned_jobs'], 'holding_jobs':(queue_details[queue])['holding_jobs'], 'finished_jobs':(queue_details[queue])['finished_jobs'], 'failed_jobs':(queue_details[queue])['failed_jobs'], 'cancelled_jobs':(queue_details[queue])['cancelled_jobs'], 'transferring_jobs':(queue_details[queue])['transferring_jobs'], 'merging_jobs':(queue_details[queue])['merging_jobs'],'filename_failed_plot':(queue_details[queue])['filename_failed_plot'],'filename_finished_plot':(queue_details[queue])['filename_finished_plot'],} for queue in queue_details]


        return data

    def fillSubtables(self, parent_id):
        self.subtables['site_details'].insert().execute([dict(parent_id=parent_id, **row) for row in self.details_db_value_list])

    def getTemplateData(self):
        data = hf.module.ModuleBase.getTemplateData(self)

        site_details = self.subtables['site_details'].select().where(self.subtables['site_details'].c.parent_id==self.dataset['id']).execute().fetchall()

        # calculate the number of queues for each site in order to determine the rowspan for the table
        site_names = self.dataset['site_names']
        rowspan = {}
        for site in site_names.split(','):
            rowspan[site] = 0
            for detail in site_details:
                if detail['site_name'] == site:
                    rowspan[site] += 1

        data['site_details'] = map(dict, site_details)
        data['rowspan'] = rowspan

        data['config'] = {}
        data['config']['failed_warning'] = int(self.config['failed_warning'])
        data['config']['failed_critical'] = int(self.config['failed_critical'])

        return data



class bigpanda_class:#new class for json-files from bigpanda
    def __init__(self,time_now,bigpanda_content):
        content = bigpanda_content
        self.json_source=json.loads(content, 'utf-8')
        self.resource=[]

    def get_numberof_activated_jobs(self):
        activated_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="activated":
                activated_jobs+=1
        return activated_jobs

    def get_numberof_running_jobs(self):
        running_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="running":
                running_jobs+=1
        return running_jobs

    def get_numberof_defined_jobs(self):
        defined_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="defined":
                defined_jobs+=1
        return defined_jobs

    def get_numberof_assigned_jobs(self):
        assigned_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="assigned":
                assigned_jobs+=1
        return assigned_jobs

    def get_numberof_holding_jobs(self):
        holding_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="holding":
                holding_jobs+=1
        return holding_jobs

    def get_numberof_cancelled_jobs(self):
        cancelled_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="cancelled":
                cancelled_jobs+=1
        return cancelled_jobs

    def get_numberof_finished_jobs(self):
        finished_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="finished":
                finished_jobs+=1
        return finished_jobs

    def get_numberof_failed_jobs(self):
        failed_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="failed":
                failed_jobs+=1
        return failed_jobs

    def get_numberof_transferring_jobs(self):
        transferring_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="transferring":
                transferring_jobs+=1
        return transferring_jobs

    def get_numberof_merging_jobs(self):
        merging_jobs=0
        for i in range(len(self.json_source)):
            if self.json_source[i]["jobstatus"]=="merging":
                merging_jobs+=1
        return merging_jobs

    


class cloud_class2:
    def __init__(self,time_now,schedconfig_content):
        content = schedconfig_content
        self.json_source=json.loads(content,'utf-8')
        self.resource=[]

    def get_wns_failed(self,html_content):
        src_text=html_content
        src_text=src_text.split("var data = google.visualization.arrayToDataTable([")[1]#Jump to relevant data
        src_text=src_text.split("])")[0]
        return src_text

    def get_wns_finished(self,html_content):
        src_text=html_content
        src_text=src_text.split("var data2 = google.visualization.arrayToDataTable([")[1]
        src_text=src_text.split("])")[0]
        return src_text

    #The following function creates the plots and returns their destination
    def wns_plot(self,queue,wns_content,option,a,b):#option='Failed' or 'Finished', a and b to get self.run and self.instance_name
        import matplotlib
        import matplotlib.pyplot as plt
        self.plt = plt
        ind = ""
        numbers = ""
        ind_failed = wns_content.split("'Count'],")[1]#queue_info['wns_failed'].split("'Count'],")[1]# Cut off names of variables
        ind_failed = ind_failed.replace("\n", "")# Delete all new lines, tabulators and spacebars
        ind_failed = ind_failed.replace("\t", "")
        ind_failed = ind_failed.replace(" ", "")
        ind_failed = ind_failed.split(',')# Create array out of string
        for i in range(len(ind_failed)):
            if i%2==0:# Iterate over all even entries (name of wn)
                ind = ind + ind_failed[i]
            else:# Iterate over all odd entries (number of jobs)
                numbers = numbers + ind_failed[i]
        ind = ind.split("'['")
        numbers = numbers.split("]")
        numbers = numbers[0:(len(numbers)-1)]# Cut off last entry as it's always empty
        for i in range(len(numbers)):
            numbers[i]=int(numbers[i])
 
        fig_abs = self.plt.figure()
        plt.bar(range(len(numbers)), numbers, color='violet')                
        plt.xticks(range(len(numbers)), ind, size=5, rotation=90)
        plt.show()
        axis_abs = fig_abs.add_subplot(111)                
        axis_abs.set_ylabel('Number of jobs')
        axis_abs.set_xlabel('Name of WN')
        axis_abs.set_title(option+' jobs per worker node at '+queue)
        fig_abs.savefig(hf.downloadService.getArchivePath(a, b+"_"+queue+"_"+option+'.png'), dpi=60)
        plt.close()
        dest = "/"+hf.downloadService.getArchivePath(a, b+"_"+queue+"_"+option+'.png')
        return dest

    def get_queue_status(self,queue):
        queue_status="unknown"
        analysis_queues=[]
        production_queues=[]
        if "analy" in queue.lower():
            for item in range(len(self.json_source)):
		if queue == self.json_source[item]["panda_resource"]:
		    for i in range(len(self.json_source[item]["queues"])):
			if str(self.json_source[item]["queues"][i]["ce_endpoint"])!="Unknown" and str(self.json_source[item]["queues"][i]["ce_endpoint"])!="to.be.set":
			    analysis_queues.append("%s %s"%(str(self.json_source[item]["queues"][i]["ce_endpoint"]),str(self.json_source[item]["status"])))
                    	else:
                       	    analysis_queues.append("%s %s"%(str(self.json_source[item]["panda_resource"]),str(self.json_source[item]["status"])))
                    	if self.json_source[item]["status"]=="online":
                       	    queue_status="online"
                    	elif queue_status!="online" and self.json_source[item]["status"]!="online":
			    queue_status=self.json_source[item]["status"]
                else:
                    continue
            return analysis_queues,queue_status
        else:
            for item in range(len(self.json_source)):
                if queue == self.json_source[item]["panda_resource"]:
		    for i in range(len(self.json_source[item]["queues"])):
                        production_queues.append("%s %s"%(str(self.json_source[item]["queues"][i]["ce_endpoint"]),str(self.json_source[item]["status"])))
                        if self.json_source[item]["status"]=="online":
                            queue_status="online"
                        elif queue_status!="online" and self.json_source[item]["status"]!="online":
                            queue_status=self.json_source[item]["status"]
                else:
                    continue
            return production_queues,queue_status
        return queue_status

    def get_queue_gatekeeper_info(self,queue):
        return 0
