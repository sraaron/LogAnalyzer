import util
import logging
import numpy as np

logger = logging.getLogger(__name__)
missing_value = 'NaN'

class MLEngine(object):
    """Train ML Engine"""
    def __init__(self, feature_set, data_set, ground_truth=None):
        # TO DO need to have out of core learning if data set is very large
        # http://scikit-learn.org/stable/modules/scaling_strategies.html
        logger.info("Initialize ML Engine")
        self.feature_set = feature_set
        self.data_set = data_set
        self.ground_truth = ground_truth
        self.data, self.n_features, self.n_samples = self.format_data()
        self.target = self.format_target()

    def travese_cpp(self, cpp_feature, time_cpp_data=None):
        rv_data = []
        # if not a single instance of cpp in data
        if time_cpp_data is None:
            rv_data.append(missing_value)  # cpp feature doesn't exist in cpp data
            for debug_msgs_feature in cpp_feature:
                rv_data.append(missing_value)  # debug msg doesn't exist in cpp data
                if "debug_variables" in debug_msgs_feature and debug_msgs_feature["debug_variables"] != []:
                    #  variables don't exist in cpp data
                    rv_data.extend([missing_value] * len(debug_msgs_feature["debug_variables"]))
        else:
            rv_data.append(1)  # cpp feature exists in cpp data
            for tuple_time_cpp_data in time_cpp_data:
                for timedelta, cpp_data in tuple_time_cpp_data.iteritems():
                    # skip timedelta feature for now
                    rv_data.append(util.str_timedelta_to_float(timedelta))  # add timedelta as feature
                    for debug_msgs_feature in cpp_feature:
                        if debug_msgs_feature["only_debug_string"] == cpp_data["only_debug_string"]:
                            rv_data.append(1)  # debug msg exists in cpp data
                            if "debug_variables" in debug_msgs_feature:
                                variables_added = 0
                                for variable in debug_msgs_feature["debug_variables"]:
                                    if variable in cpp_data["debug_variables"]:
                                        variables_added -= 1
                                        try:
                                            rv_data.append(util.variable_eval(cpp_data["debug_variables"][variable]))
                                        except Exception as e:
                                            rv_data.append(missing_value)
                                            logger.exception(variable)
                                    else:
                                        # possibly there are more than one only debug strings with the same pattern
                                        variables_added -= 1
                                        rv_data = rv_data[:variables_added]  # actually this debug msg doesn't exist in cpp data
                                        rv_data.append(missing_value)
                                        if "debug_variables" in debug_msgs_feature and debug_msgs_feature[
                                            "debug_variables"] != []:
                                            rv_data.extend([missing_value] * len(debug_msgs_feature["debug_variables"]))
                                        break
                        else:
                            rv_data.append(missing_value)  # debug msg doesn't exist in cpp data
                            if "debug_variables" in debug_msgs_feature and debug_msgs_feature["debug_variables"] != []:
                                rv_data.extend([missing_value] * len(debug_msgs_feature["debug_variables"]))
        return rv_data

    def format_target(self):
        target = []
        for test_group in self.ground_truth:
            for test in test_group:
                # TO DO: multi class labelling
                if "Dolby - Metadata" in test_group[test]:
                    if test_group[test]["Dolby - Metadata"] == "fail":
                        target.append(1)
                    else:
                        target.append(0)
        return target

    def format_data(self):
        data = []
        n_features = 0
        n_samples = 0
        first = False
        # need to flatten dictionary to input to classifier
        for component_feature in self.feature_set:
            for test_group_data in self.data_set:
                for test_data in test_group_data:
                    if component_feature in test_group_data[test_data]:
                        for cpp_feature in self.feature_set[component_feature]:
                            if cpp_feature in test_group_data[test_data][component_feature]:
                                #  get feature data
                                data.extend(self.travese_cpp(self.feature_set[component_feature][cpp_feature], test_group_data[test_data][component_feature][cpp_feature]))
                            else:
                                # no data for cpp feature
                                data.extend(self.travese_cpp(self.feature_set[component_feature][cpp_feature]))
                        if first is False:
                            n_features = len(data)  # number of features for each data sample
                            first = True
                        n_samples += 1
        format_data = np.reshape(data, (n_samples, n_features)).T
        return format_data, n_features, n_samples

    def train(self):
        return
