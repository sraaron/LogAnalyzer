import os
import util
import logging
from log_filter import Filter
from templatizer import Templatizer
from feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class TxtResultImporter(object):
    """TXT Result Import"""

    def __init__(self, params, mode="train"):
        logger.info("Starting TXT Result Importer")
        self.mode = mode
        self.channel_number = params["channel_number"]
        self.start_path = params["start_txt_path"]
        self.end_path = params["end_txt_path"]

    @staticmethod
    def parse_results(dir_result_path):
        results_json_path = os.path.join(dir_result_path, "results.json")
        test_info_json_path = os.path.join(dir_result_path, "test_info.json")

        # get ACP build version
        acp_version = util.load_json(test_info_json_path)["acpBuild"]
        # get test case labels
        test_results = util.load_json(results_json_path)
        test_case_labels = {}
        for test_case, validator in test_results.iteritems():
            if test_case not in test_case_labels:
                test_case_labels[test_case] = {}
            for validator_name, validator_result in validator.iteritems():
                test_case_labels[test_case][validator_name] = validator_result["result"]
        return acp_version, test_case_labels

    def extract_results(self):
        overall_extracted_log_features = []
        overall_test_case_labels = []
        component_template = {}
        base_path = os.path.basename(self.start_path).split("-")
        if len(base_path) == 2:
            start_index = int(base_path[1])
            end_index = int(os.path.basename(self.end_path).split("-")[1])
            base_path = os.path.join(os.path.dirname(self.start_path), base_path[0]) + "-"
            for index in range(start_index, end_index+1):
                test_result = base_path + str(index)
                acp_version, test_case_labels = self.parse_results(test_result)
                overall_test_case_labels.append(test_case_labels)
                extracted_log_features = {}
                for test in test_case_labels:
                    test_path = os.path.join(test_result, test)
                    if os.path.isdir(test_path):
                        test_result_dir = os.path.join(self.mode, os.path.basename(test_result))
                        techdump_rel_path = os.path.join(test_result_dir, test)
                        params = {"channel_number": self.channel_number, "src_txt_result_dir_path": test_path,
                                  "techdump_name": test, "test_result_dir": test_result_dir}
                        log_filter = Filter(params, filter_type="txt_result")
                        filter_settings = log_filter.get_filter_settings()
                        log_filter.filter_logs()
                        templatizer = Templatizer(acp_version=acp_version)
                        component_template = templatizer.gen_template()
                        # extract features from log, using template
                        extractor = FeatureExtractor(component_template=component_template,
                                                     techdump_filename=techdump_rel_path,
                                                     filter_settings=filter_settings)
                        extracted_log_features.update({test: extractor.extract_features()})
                overall_extracted_log_features.append(extracted_log_features)

        else:
            logger.error("Invalid start path provided. Needs to contain '-' in last directory %s" % self.start_path)
        return component_template, overall_extracted_log_features, overall_test_case_labels



