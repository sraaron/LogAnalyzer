import os
import re
import sys
import json
import string
import zipfile
from cStringIO import StringIO

class Filter(object):
    """Filter will filter log information"""

    def __init__(self, arg):
        super(Filter, self).__init__()
        self.arg = arg
        self.filename = arg["filename"]
        self.channel_number = arg["channel_number"]
        self.file_filter = {}
        # print self.filename
        # print self.channel_number

    def filter_logs(self):
        if self.channel_number > 0 and self.filename != "":
            # need to first extract selected files and then filter
            # since recursive file traversal path might not always take the same route
            # and we need the channel pid from oplan for filtering log
            self.extract_files()
            self.log_filtering()

    def get_filter_settings(self, techdump_filepath, filter_settings_filepath):
        rv = {}
        with open(filter_settings_filepath) as data_file:
            filter_json = json.load(data_file)
            techdump_filepath = os.path.splitext(techdump_filepath)[0]
            rv = filter_json
            for key in filter_json:
                rv[key]["path"] = os.path.normpath(os.path.join(techdump_filepath, string.replace(filter_json[key]["path"], "#",
                                                                                          self.channel_number)))
        return rv

    '''
    Implementation of a recursive zip file reader and extracter.
    Will extract file from nested zip file if file specified in setting exists inside.
    '''
    def read_zip_file(self, zip_file_path, extract_dir):
        with zipfile.ZipFile(zip_file_path, "r") as z:
            for file_path in zipfile.ZipFile.namelist(z):
                filename, extension = os.path.splitext(file_path)

                if ".zip" == extension:
                    with z.open(file_path) as z2:
                        z2_filedata = StringIO(z2.read())
                        extract_dir_path = os.path.join(extract_dir, filename)
                        self.read_zip_file(z2_filedata, extract_dir_path)
                else:
                    whole_file_path = os.path.normpath(os.path.join(extract_dir, file_path))
                    for key in self.file_filter:
                        if whole_file_path == self.file_filter[key]["path"]:
                            z.extract(file_path, extract_dir)

    def get_pid(self, oplan_file_path):
        pid = -1
        with open(oplan_file_path, "r") as f:
            txt = f.read()
            re1 = '.*?'  # Non-greedy match on filler
            re2 = '(PID)'  # Word 1
            re3 = '.*?'  # Non-greedy match on filler
            re4 = '(\\d+)'  # Integer Number 1

            rg = re.compile(re1 + re2 + re3 + re4, re.IGNORECASE | re.MULTILINE)
            m = rg.search(txt)
            if m:
                # pid_word = m.group(1)
                pid = m.group(2)
        return pid

    def filter_by_pid(self, file_path, pid):
        pid = "P" + pid
        with open(file_path, "r+") as f:
            # need to read line by line as log files might be huge, and loading into memory will cause
            # all the memory to be used up
            # TO DO: speed optimization to load chunks of lines into memory
            seek_count = 0
            for line in f:
                if pid in line:
                    f.seek(seek_count)
                    f.write(line)
                    f.truncate()
                    seek_count += len(line)


    def extract_files(self):
        cur_path = os.path.dirname(__file__)
        techdump_filepath = os.path.join(cur_path, "techdumps", self.filename)
        self.file_filter = self.get_filter_settings(techdump_filepath, os.path.join(cur_path, "settings", "filter_settings.json"))
        extract_dir = os.path.dirname(techdump_filepath)
        self.read_zip_file(techdump_filepath, extract_dir)

    def log_filtering(self):
        # get channel pid
        channel_pid = self.get_pid(self.file_filter["oplan"]["path"])
        # filter logs by channel pid
        if channel_pid > 0:
            for key in self.file_filter:
                if "pid" == self.file_filter[key]["filter_mode"]:
                    self.filter_by_pid(self.file_filter[key]["path"], channel_pid)


        # if no pid dumped in log, get start/stop time of channel run (from transcoder.log)
        # extract logs within this time
        return

if __name__ == "__main__":
    Filter(sys.argv[1:])
