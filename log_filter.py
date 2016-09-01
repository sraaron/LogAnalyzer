import os
import re
import sys
import util
import json
import shutil
import string
import zipfile
import logging
from datetime import timedelta
from cStringIO import StringIO

logger = logging.getLogger(__name__)


class Filter(object):
    """Filter will filter log information"""

    def __init__(self, arg, filter_type="techdump"):
        super(Filter, self).__init__()
        logger.info("Initialize Filter")
        self.filter_type = filter_type
        self.channel_number = arg["channel_number"]
        self.timestamp_filter_rv = False
        self.cur_path = os.path.dirname(__file__)
        if self.filter_type == "techdump":
            self.techdump_name = arg["filename"]
            self.filter_settings_file_path = os.path.join(self.cur_path, "settings", "filter_settings.json")
            self.techdump_path = os.path.join(self.cur_path, "techdumps", self.techdump_name)
        elif self.filter_type == "txt_result":
            self.src_txt_result_dir_path = arg["src_txt_result_dir_path"]
            self.techdump_name = arg["techdump_name"]
            self.output_dir_path = os.path.join(self.cur_path, "techdumps", arg["test_result_dir"])
            self.filter_settings_file_path = os.path.join(self.cur_path, "settings", "txt_filter_settings.json")
            self.techdump_path = os.path.join(self.output_dir_path, self.techdump_name)
        self.rel_path_filter_settings = self.convert_filter_settings(self.filter_settings_file_path,
                                                                     "", self.channel_number)
        self.abs_path_filter_settings = self.convert_filter_settings(self.filter_settings_file_path,
                                                                     self.techdump_path, self.channel_number)
        # print self.techdump_name
        # print self.channel_number

    def convert_filter_settings(self, filter_settings_file_path, techdump_path, channel_number):
        rv = {}
        with open(filter_settings_file_path) as data_file:
            filter_json = json.load(data_file)
            if os.path.isfile(techdump_path):
                techdump_path = os.path.splitext(techdump_path)[0]
            rv = filter_json
            for key in filter_json:
                rv[key]["path"] = os.path.normpath(os.path.join(techdump_path,
                                                                string.replace(filter_json[key]["path"], "#",
                                                                               channel_number)))
        return rv

    def get_filter_settings(self):
        return self.abs_path_filter_settings

    def filter_logs(self):
        if self.channel_number > 0 and self.techdump_path != "":
            # need to first extract selected files and then filter
            # since recursive file traversal path might not always take the same route
            # and we need the channel pid from oplan for filtering log
            if self.filter_type == "techdump" and os.path.isfile(self.techdump_path) and \
                            ".zip" == os.path.splitext(self.techdump_path)[1]:
                self.extract_files()
            elif self.filter_type == "txt_result":
                self.copy_files()
            self.log_filtering()

    def copy_files(self):
        for file_name, filter_setting in self.rel_path_filter_settings.iteritems():
            if "..\\" in filter_setting["path"]:
                filter_path = filter_setting["path"].replace("..\\", "")
                src_file_path = os.path.join(os.path.dirname(self.src_txt_result_dir_path), filter_path)
                dst_file_path = os.path.join(self.output_dir_path, filter_path)
            else:
                src_file_path = os.path.join(self.src_txt_result_dir_path, filter_setting["path"])
                dst_file_path = os.path.join(self.techdump_path, filter_setting["path"])
            util.mkdir_p(os.path.dirname(dst_file_path))
            try:
                shutil.copy2(src_file_path, dst_file_path)
            except IOError as e:
                logger.exception("src file path %s, dst file path %s" % (src_file_path, dst_file_path))

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
                    for key in self.abs_path_filter_settings:
                        if whole_file_path == self.abs_path_filter_settings[key]["path"]:
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
                        start_time = util.get_timestamp(line)
                    else:
                        stop_time = util.get_timestamp(line)
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
        log_timestamp = util.get_timestamp(line)
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
        extract_dir = os.path.dirname(self.techdump_path)
        self.read_zip_file(self.techdump_path, extract_dir)

    def log_filtering(self):
        # get channel pid
        channel_pid = self.get_pid(self.abs_path_filter_settings["oplan"]["path"])

        if channel_pid > 0:
            # get start/stop time of channel run (from transcoder.log)
            start_time, stop_time = self.filter_by_pid(self.abs_path_filter_settings["transcoder.log"]["path"], channel_pid, True)
            # set 5 minutes offset for start, stop time
            start_time -= timedelta(minutes=5)
            stop_time += timedelta(minutes=5)
            for key in self.abs_path_filter_settings:
                    if key == "transcoder.log":
                        continue
                    # filter logs by channel pid
                    if "pid" == self.abs_path_filter_settings[key]["filter_mode"]:
                        self.filter_by_pid(self.abs_path_filter_settings[key]["path"], channel_pid)
                    # extract logs within start/stop this time
                    elif "time" == self.abs_path_filter_settings[key]["filter_mode"]:
                        self.filter_by_timestamp(self.abs_path_filter_settings[key]["path"], start_time, stop_time)

if __name__ == "__main__":
    Filter(sys.argv[1:])
