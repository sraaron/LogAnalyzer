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
        if os.path.isfile(techdump_filename):
            self.techdump_folder_name = os.path.splitext(techdump_filename)[0]
        else:
            self.techdump_folder_name = techdump_filename
        self.filter_settings = filter_settings
        self.cur_path = os.path.dirname(__file__)
        self.techdump_folder_path = os.path.join(self.cur_path, "techdumps", self.techdump_folder_name)
        self.output_folder = os.path.join(self.cur_path, "outputs", self.techdump_folder_name)
        if not os.path.isdir(self.output_folder):
            util.mkdir_p(self.output_folder)

    def extract_transcode_pack_features(self, log_file_path, template):
        transcoder_parser = TranscoderLogParser(debug_msg_template=template)
        return transcoder_parser.parse_file(log_file_path=log_file_path, parse_debug_msg=True)

    def get_analysis(self, output_file_path):
        with open(os.path.join(self.output_folder, output_file_path), "r") as f:
            return json.load(f)

    def dump_analysis(self, analysis, output_file_path):
        with open(os.path.join(self.output_folder, output_file_path), "w") as f:
            json.dump(analysis, f, indent=2)

    def extract_features(self):
        output_analysis = {}
        for log_file, log_file_settings in self.filter_settings.iteritems():
            if "component" in log_file_settings:
                log_file_path = os.path.join(self.techdump_folder_path, log_file_settings["path"])
                output_file_path = os.path.join(self.output_folder,
                                                os.path.splitext(os.path.basename(log_file_path))[0]) + ".analysis.json"
                component = log_file_settings["component"]
                if component in self.component_template:
                    template = self.component_template[component]
                    if component == "RmpSpTranscodePack":
                        if os.path.isfile(output_file_path):
                            output_analysis[component] = self.get_analysis(output_file_path)
                        else:
                            output_analysis[component] = self.extract_transcode_pack_features(log_file_path=log_file_path,
                                                                                              template=template)

                            self.dump_analysis(analysis=output_analysis[component],
                                               output_file_path=output_file_path)
        return output_analysis
