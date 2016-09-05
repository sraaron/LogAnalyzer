import os
import sys
import util
import json
import logging
import numpy as np
from sklearn import svm, metrics
from sklearn.externals import joblib
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.preprocessing import Imputer

logger = logging.getLogger(__name__)
missing_value = 'NaN'

class MLEngine(object):
    """Train ML Engine"""
    def __init__(self, debug_msg_set, feature_set, data_set, ground_truth=None, start_path=None, end_path=None):
        # TO DO need to have out of core learning if data set is very large
        # http://scikit-learn.org/stable/modules/scaling_strategies.html
        logger.info("Initialize ML Engine")
        self.cur_path = os.path.dirname(__file__)
        self.trained_model_path = os.path.join(self.cur_path, "outputs", "trained_models", "model.pkl")
        if start_path is not None and end_path is not None:
            output_name = os.path.basename(start_path) + "_" + os.path.basename(end_path) + ".json"
            self.prediction_path = os.path.join(self.cur_path, "outputs", "test", output_name)
        self.debug_msg_set = debug_msg_set
        self.feature_set = feature_set
        self.data_set = data_set
        self.ground_truth = ground_truth
        self.target = []
        self.data, self.n_features, self.n_samples = self.format_data()
        # Create a classifier: a support vector classifier
        # use linear classifier as we have large dimensionality
        self.classifier = svm.SVC(gamma='auto', kernel='linear', probability=False)
        self.predicted = []

    def train(self):
        self.target = self.format_target()
        # train the classifier
        clf = self.classifier.fit(self.data, self.target)
        # evaluate training error
        # clf.score(self.data, self.target)
        joblib.dump(clf, self.trained_model_path, compress=9)
        print "TRAINED!"

    def predict(self):
        clf = joblib.load(self.trained_model_path)
        self.predicted = clf.predict(self.data)
        prediction = {}
        report, c_matrix = None
        for group_idx, test_group_data in enumerate(self.data_set):
            for idx, test_name in enumerate(test_group_data):
                actual = "NaN"
                if self.ground_truth is not None:
                    actual = self.ground_truth[group_idx][test_name]
                prediction["test_name"] = {"prediction": self.predicted[idx], "actual": actual}
        if self.ground_truth is not None:
            self.target = self.format_target()
            prediction["report"] = classification_report(self.target, self.predicted)
            prediction["confusion_matrix"] = confusion_matrix(self.target, self.predicted)
        with open(self.prediction_path, "w") as f:
            json.dump(f, prediction)
        return prediction

    def add_data(self, dbg_msg_template, feature_template, log_msgs):
        rv_data = []
        for log_line in log_msgs:
            try:
                # add feature variables
                rv_data.append(log_line["log_line_number"])
                rv_data.append(util.str_timedelta_to_float(log_line["timedelta"]))
                # sparse data, should be unique and shouldn't affect locality
                if "" != log_line["hash"]:
                    rv_data.append(long(log_line["hash"], 16) % (2 ^ 63))
                    # TO DO: need to perform dimensionality reduction (PCA?)
                    for idx, feature in enumerate(feature_template):
                        if idx > 2:
                            hash_variable = feature.split('_', 1)
                            if hash_variable[0] == log_line["hash"]:  # if hashes match
                                rv_data.append(util.variable_eval(log_line["debug_variables"][hash_variable[1]]))
                            else:
                                if len(rv_data) > len(feature_template):
                                    rv_data.append(rv_data[len(rv_data) - len(feature_template)])  # use previous value, use as state
                                else:
                                    rv_data.append(missing_value)
            except Exception as e:
                logger.exception(log_line)
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
        n_features = sys.maxsize
        n_samples = 0
        # need to flatten dictionary to input to classifier
        for component, component_feature in self.debug_msg_set.iteritems():
            for test_group_data in self.data_set:
                for test_name, test_data in test_group_data.iteritems():
                    if component in test_data and component in self.feature_set:
                        #  get feature data
                        data.append(self.add_data(component_feature, self.feature_set[component], test_data[component]))
                        if len(data[len(data)-1]) < n_features:
                            n_features = len(data[len(data)-1])  # number of features for each data sample
                        n_samples += 1
        format_data = None
        for data_item in data:
            if format_data is None:
                format_data = np.array(data_item[:n_features])[np.newaxis]
            else:
                format_data = np.hstack((format_data, np.array(data_item[:n_features])[np.newaxis]))
        format_data = format_data.reshape(n_samples, n_features)

        # Create our imputer to replace missing values with the mean e.g.
        imp = Imputer(missing_values='NaN', strategy='mean', axis=0)
        imp = imp.fit(format_data)

        # Impute our data, then train
        rv_format_data = imp.transform(format_data)

        return rv_format_data, n_features, n_samples
