import os
import util
import json
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
        self.output_folder = os.path.join(self.cur_path, "outputs", self.techdump_folder_name)
        if not os.path.isdir(self.output_folder):
            os.mkdir(self.output_folder)

    def extract_transcode_pack_features(self, log_file_path, template):
        transcoder_parser = TranscoderLogParser(debug_msg_template=template)
        return transcoder_parser.parse_file(log_file_path=log_file_path, parse_debug_msg=True)


    def dump_analysis(self, analysis, log_filename):
        log_filename += ".analysis.json"
        with open(os.path.join(self.output_folder, log_filename), "w") as f:
            json.dump(analysis, f, indent=2)

    def extract_features(self):
        output_analysis = {}
        for log_file, log_file_settings in self.filter_settings.iteritems():
            if "component" in log_file_settings:
                log_file_path = os.path.join(self.techdump_folder_path, log_file_settings["path"])
                component = log_file_settings["component"]
                if component in self.component_template:
                    template = self.component_template[component]
                    if component == "RmpSpTranscodePack":
                        output_analysis[component] = self.extract_transcode_pack_features(log_file_path=log_file_path,
                                                                                          template=template)

                        self.dump_analysis(analysis=output_analysis[component],
                                           log_filename=os.path.splitext(os.path.basename(log_file_path))[0])

        return output_analysis
