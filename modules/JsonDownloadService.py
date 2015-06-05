import hf, threading, time, os, subprocess, shutil, traceback, shlex, re, logging

logger = logging.getLogger(__name__)


class JsonDownloadSlave(hf.downloadservice.DownloadSlave):
    print('JsonDownloadSlave')
    def __init__(self, file, global_options, archive_dir):
        threading.Thread.__init__(self)
        self.file = file
        self.archive_dir = archive_dir
        self.global_options = global_options

    def run(self):
        print('jsonrun')
        try:
            if self.file.url.startswith("file://"):
                path = self.file.url[len("file://"):]
                shutil.copy(path, self.file.getTmpPath(True))
            else:
                '''
                agent="Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6"
                header1="Accept: text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5"
                header2="Accept-Language: en-us,en;q=0.5"
                header3="Accept-Encoding: gzip,deflate"
                header4="Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7"
                header5="Keep-Alive: 300"
wget --quiet --no-cookies --referer="$ref" --user-agent="$agent" --header="$header1" --header="$header2" --header="$header3" --header="$header4" --header="$header5" --header="$cookie_header" "$url" -O $filename
                '''
                command = "wget --output-document=\"%s\" %s %s \"%s\"" % (self.file.getTmpPath(True), "" if self.file.config_source == "local" else self.global_options, self.file.options, self.file.url)
                process = subprocess.Popen(shlex.split(command), stderr=subprocess.PIPE)
                stderr = process.communicate()[1]
                if process.returncode != 0:
                    print('Err4')
                    match = re.search("ERROR ([0-9][0-9][0-9])", stderr)
                    http_errorcode = 0
                    if match:
                        http_errorcode = int(match.group(1))
                    self.file.error = "Downloading failed"
                    if http_errorcode != 0:
                         self.file.error += " with error code %i" % http_errorcode
                    try:
                        os.unlink(self.file.getTmpPath(True))
                    except Exception:
                        print('Err3')
                        pass
        except Exception, e:
            print('Err1')
            self.file.error += "Failed to download file: %s" % e
            traceback.print_exc()
        except:
            print('Err2')
            self.file.error += "Failed to download file"
            traceback.print_exc()



class JsonDownloadService(hf.downloadservice.DownloadService):

    def __init__(self):#, html_application_parameter):
        self.logger = logging.getLogger(self.__module__)
        self.file_list = {}
        self.archive_dir = None
        self.archive_url = None
        self.runtime = None
#        self.html_application_parameter

    def addDownload(self, download_command):
        print('jsonaddDownload')
        if download_command in self.file_list:
            return self.file_list[download_command]
        self.file_list[download_command] = DownloadFile(download_command)
        return self.file_list[download_command]


    def performDownloads(self, runtime):
        print('jsonperformDownloads')
        print('json_file_list')
        print(self.file_list)
        try:
            print('1')
            self.global_options = hf.config.get("downloadService", "global_options")
            print('2')
            self.runtime = runtime
            print('3')
            self.archive_dir = os.path.join(hf.config.get("paths", "archive_dir"), runtime.strftime("%Y/%m/%d/%H/%M"), 'extra') #append 'extra' to archive_dir
            print('4')
            self.archive_url = os.path.join(hf.config.get("paths", "archive_url"), runtime.strftime("%Y/%m/%d/%H/%M"), 'extra')
            print('5')

            try:
                #pass
                os.makedirs(self.archive_dir)
                print('6')
            except Exception, e:
                self.logger.error("Cannot create archive directory")
                self.logger.error(traceback.format_exc())
                raise Exception("Cannot create archive directory")
            print('7')
            slaves = [JsonDownloadSlave(file, self.global_options, self.archive_dir) for file in self.file_list.itervalues()] # DOES NOT WORK
            print('8')
            print('json_slaves')
            print(slaves)
            tmp_dir = hf.config.get("paths", "tmp_dir")
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            
            file_prefix = os.path.join(tmp_dir, runtime.strftime("%Y%m%d_%H%M%s_"))
            
            timeout = hf.config.getint("downloadService", "timeout")
            
            for number, slave in enumerate(slaves):
                slave.file.tmp_filename = os.path.abspath(file_prefix + "%03i.download"%number)
                slave.start()
            
            for slave in slaves:
                start_time = int(time.time())
                slave.join(timeout)
                timeout -= int(time.time()) - start_time
                if timeout <= 0 or slave.isAlive():
                    self.logger.info("Download timeout!")
                    break

            for slave in slaves:
                if slave.isAlive():
                    slave.file.error += "Download didn't finish in time"
                    slave._Thread__stop()
                    self.logger.info("Download timeout for %s" % slave.file.download_command)
                elif not slave.file.errorOccured():
                    slave.file.is_downloaded = True
        except Exception, e:
            for file in self.file_list.itervalues():
                file.error = str(e)
            raise


class DownloadFile(hf.downloadservice.DownloadFile):
    print('JsonDownloadFile')
    
class File(hf.downloadservice.File):
    print('JsonFile')
    

jsonDownloadService = JsonDownloadService()

