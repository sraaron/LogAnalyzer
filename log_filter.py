import os
import re
import sys
import json
import string
import zipfile
from datetime import datetime, timedelta
from cStringIO import StringIO

class Filter(object):
    """Filter will filter log information"""

    def __init__(self, arg):
        super(Filter, self).__init__()
        # self.arg = arg
        self.filename = arg["filename"]
        self.channel_number = arg["channel_number"]
        self.timestamp_filter_rv = False
        self.cur_path = os.path.dirname(__file__)
        self.techdump_file_path = os.path.join(self.cur_path, "techdumps", self.filename)
        self.filter_settings_file_path = os.path.join(self.cur_path, "settings", "filter_settings.json")
        self.filter_settings = self.convert_filter_settings(self.filter_settings_file_path,
                                                            self.techdump_file_path, self.channel_number)
        # print self.filename
        # print self.channel_number

    def convert_filter_settings(self, filter_settings_file_path, techdump_file_path, channel_number):
        rv = {}
        with open(filter_settings_file_path) as data_file:
            filter_json = json.load(data_file)
            techdump_file_path = os.path.splitext(techdump_file_path)[0]
            rv = filter_json
            for key in filter_json:
                rv[key]["path"] = os.path.normpath(os.path.join(techdump_file_path,
                                                                string.replace(filter_json[key]["path"], "#",
                                                                               channel_number)))
        return rv

    def get_filter_settings(self):
        return self.filter_settings

    def filter_logs(self):
        if self.channel_number > 0 and self.filename != "":
            # need to first extract selected files and then filter
            # since recursive file traversal path might not always take the same route
            # and we need the channel pid from oplan for filtering log
            self.extract_files()
            self.log_filtering()

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
                    for key in self.filter_settings:
                        if whole_file_path == self.filter_settings[key]["path"]:
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


    def get_timestamp(self, txt):
        timestamp = ""

        re1 = '((?:2|1)\\d{3}(?:-|\\/)(?:(?:0[1-9])|(?:1[0-2]))(?:-|\\/)(?:(?:0[1-9])|(?:[1-2][0-9])|(?:3[0-1]))' \
              '(?:T|\\s)(?:(?:[0-1][0-9])|(?:2[0-3])):(?:[0-5][0-9]):(?:[0-5][0-9]))'  # Time Stamp 1
        re2 = '(.|,)'  # Any Single Character 1
        re3 = '(\\d)'  # Any Single Digit 1
        re4 = '(\\d)'  # Any Single Digit 2
        re5 = '(\\d)'  # Any Single Digit 3
        rg = re.compile(re1 + re2 + re3 + re4 + re5, re.IGNORECASE | re.DOTALL)
        m = rg.search(txt)

        '''
        # UTC time offset handling
        re6 = '(\\+)'  # Any Single Character 2
        re7 = '((?:(?:[0-1][0-9])|(?:[2][0-3])|(?:[0-9])):(?:[0-5][0-9])(?::[0-5][0-9])?)'  # HourMinuteSec 1
        rg_utc = re.compile(re1 + re2 + re3 + re4 + re5 + re6 + re7, re.IGNORECASE | re.DOTALL)
        m_utc = rg_utc.search(txt)
        '''

        if m:
            timestamp1 = m.group(1)
            c1 = m.group(2)
            d1 = m.group(3)
            d2 = m.group(4)
            d3 = m.group(5)
            timestamp = string.replace(timestamp1, "T", " ") + "." + d1 + d2 + d3
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
            '''
            # UTC time offset handling
            if m_utc:
                sign = m_utc.group(6)
                time1 = m_utc.group(7)
                utc_offset = timedelta(hours=int(time1[0:2]), minutes=int(time1[3:5]))
                if sign == "+":
                    timestamp += utc_offset
                elif sign == "-":
                    timestamp -= utc_offset
            '''
        return timestamp

    def generic_filter(self, file_path, filter_func, get_start_stop_time=False, *filter_func_args):
        start_time = 0
        stop_time = 0
        with open(file_path, "r+") as f:
            # To DO: need to read line by line as log files might be huge, and loading into memory may cause
            # all the memory to be used up
            # TO DO: optimization (chunking of file)
            lines = f.readlines()
            f.seek(0)
            for line in lines:
                if line != "" and filter_func(line, *filter_func_args):
                    if 0 == start_time:
                        start_time = self.get_timestamp(line)
                    else:
                        stop_time = self.get_timestamp(line)
                    f.write(line)
            f.truncate()
        return start_time, stop_time

    def pid_filter(self, line, pid):
        return pid in line

    def filter_by_pid(self, file_path, pid, get_start_stop_time=False):
        pid = "P" + pid
        return self.generic_filter(file_path, self.pid_filter, get_start_stop_time, pid)

    def timestamp_filter(self, line, start_time, stop_time):
        # controller logs may start earlier compared to transcoder.log start time, need another way to find
        # controller start time or set an offset (5 minutes?) before to get controller channel start time
        log_timestamp = self.get_timestamp(line)
        if log_timestamp != "":
            if start_time <= log_timestamp <= stop_time:
                self. timestamp_filter_rv = True
            else:
                self.timestamp_filter_rv = False
        # return previously saved state if no timestamp in log
        return self. timestamp_filter_rv

    def filter_by_timestamp(self, file_path, start_time, stop_time):
        return self.generic_filter(file_path, self.timestamp_filter, False, start_time, stop_time)

    def extract_files(self):
        extract_dir = os.path.dirname(self.techdump_file_path)
        self.read_zip_file(self.techdump_file_path, extract_dir)

    def log_filtering(self):
        # get channel pid
        channel_pid = self.get_pid(self.filter_settings["oplan"]["path"])

        if channel_pid > 0:
            # get start/stop time of channel run (from transcoder.log)
            start_time, stop_time = self.filter_by_pid(self.filter_settings["transcoder.log"]["path"], channel_pid, True)
            # set 5 minutes offset for start, stop time
            start_time -= timedelta(minutes=5)
            stop_time += timedelta(minutes=5)
            for key in self.filter_settings:
                    if key == "transcoder.log":
                        continue
                    # filter logs by channel pid
                    if "pid" == self.filter_settings[key]["filter_mode"]:
                        self.filter_by_pid(self.filter_settings[key]["path"], channel_pid)
                    # extract logs within start/stop this time
                    elif "time" == self.filter_settings[key]["filter_mode"]:
                        self.filter_by_timestamp(self.filter_settings[key]["path"], start_time, stop_time)

if __name__ == "__main__":
    Filter(sys.argv[1:])
