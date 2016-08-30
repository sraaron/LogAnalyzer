import os
import logging
from transcoder_log_parser import TranscoderLogParser

logger = logging.getLogger(__name__)

class FeatureExtractor(object):
    """Extract Features from Techdump"""

    def __init__(self, component_template, techdump_filename, filter_settings):
        logger.info("Initialize Feature Extractor")
        self.component_template = component_template
        self.techdump_folder_name = os.path.splitext(techdump_filename)[0]
        self.filter_settings = filter_settings
        self.cur_path = os.path.dirname(__file__)
        self.techdump_folder_path = os.path.join(self.cur_path, "techdumps", self.techdump_folder_name)

    def extract_transcode_pack_features(self, log_file_path, template):
        transcoder_parser = TranscoderLogParser(debug_msg_template=template)
        with open(log_file_path, "r") as f:
            # read each line in log file
            for line in f:
                transcoder_parser.parse_line(line, parse_debug_msg=True)


    def extract_features(self):
        for log_file, log_file_settings in self.filter_settings.iteritems():
            if "component" in log_file_settings:
                log_file_path = os.path.join(self.techdump_folder_path, log_file_settings["path"])
                component = log_file_settings["component"]
                template = {}
                if component in self.component_template:
                    template = self.component_template[component]
                    if component == "RmpSpTranscodePack":
                        self.extract_transcode_pack_features(log_file_path=log_file_path, template=template)

