import os
import util
import json
import logging
import pandas as pd
import scipy.spatial.distance
from operator import itemgetter
from collections import Counter
from sklearn import preprocessing
from sklearn.externals import joblib
from sklearn.metrics import confusion_matrix
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report
from sklearn.feature_selection import SelectFromModel
from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression


logger = logging.getLogger(__name__)
missing_value = 0  # 'NaN'  # sys.maxint  #
max_features = 25

class MLEngine(object):
    """Train ML Engine"""
    def __init__(self, acp_version, msg_template_set, feature_set, data_set, ground_truth=None, start_path=None, end_path=None):
        # TO DO need to have out of core learning if data set is very large
        # http://scikit-learn.org/stable/modules/scaling_strategies.html
        logger.info("Initialize ML Engine")
        self.cur_path = os.path.dirname(__file__)
        self.scaler_path = os.path.join(self.cur_path, "outputs", "trained_models", "scaler.pkl")
        self.feature_selection_path = os.path.join(self.cur_path, "outputs", "trained_models", "feature.pkl")
        self.trained_model_path = os.path.join(self.cur_path, "outputs", "trained_models", "model.pkl")
        self.trained_model_info_path = os.path.join(self.cur_path, "outputs", "trained_models", "model_info.json")
        if start_path is not None and end_path is not None:
            output_name = os.path.basename(start_path) + "_" + os.path.basename(end_path) + ".json"
            self.prediction_path = os.path.join(self.cur_path, "outputs", "test", output_name)
        self.msg_template_set = msg_template_set
        self.feature_set = feature_set
        self.data_set = data_set
        self.ground_truth = ground_truth
        self.test_sample_len = {}
        self.target = []
        self.data = None
        self.n_features = None
        self.n_samples = None
        self.classifier = SVC(gamma=2, C=1, shrinking=False, verbose=2)
        self.min_threshold = 0

        # RandomForestClassifier(n_estimators=25)
        # svm.SVC(gamma=2, C=1, shrinking=False, verbose=2)
        """
        C=1.0, cache_size=200, class_weight=None, coef0=0.0,
        decision_function_shape=None, degree=3, gamma='auto', kernel='rbf',
        max_iter=-1, probability=False, random_state=None, shrinking=True,
        tol=0.001, verbose=True
        """
        self.predicted = []
        branch = util.version_to_branch_mapping(acp_version[:acp_version.rfind('.')])
        self.features_path = os.path.join(self.cur_path, "templates", branch + "_RmpSpTranscodePack_features.json")
        self.features_selected_info_path = os.path.join(self.cur_path, "templates", branch +
                                                        "_RmpSpTranscodePack_selected_features_info.json")
        self.features_selected_path = os.path.join(self.cur_path, "templates",
                                                        branch + "_RmpSpTranscodePack_selected_features.json")


    def test(self):
        self.data, self.n_features, self.n_samples = self.format_data(mode="test")
        # X_normalized = preprocessing.scale(self.data)
        # preprocessing.sale(self.data)# preprocessing.normalize(self.data, norm='l2')
        X_normalized = preprocessing.normalize(self.data, norm='l1')
        # split dataset into train and test
        X_train, X_test, y_train, y_test = train_test_split(
            X_normalized, self.target, test_size=0.5, random_state=0)
        # Set the parameters by cross-validation
        linear_svc_parameters = {'C': [0.1, 0.3, 0.5, 0.7, 1], 'class_weight': 'balanced'}
        svc_parameters = [{'kernel': ['rbf'], 'gamma': [1e-3, 1e-4],
                             'C': [0.1, 0.5, 1, 10, 100, 1000]},
                            {'kernel': ['linear'], 'C': [0.1, 0.5, 1, 10, 100, 1000]}]

        knn_parameters = [{"n_neighbors": [2, 5, 10, 15, 20], "algorithm": ['auto', 'ball_tree', 'kd_tree', 'brute'], "p": [1, 2],
                           "weights": ['uniform', 'distance']}]

        ensemble_parameters = [{"n_estimators": [10, 20, 50, 100], "criterion": ["gini", "entropy"],
                                "max_features": [1, 5, 10, 10, 20, 25],
                                "max_depth": [None, 1, 5, 10], "bootstrap": [True, False], "oob_score": [True, False],
                                "class_weight": [None, "balanced_subsample", "balanced"],
                                "min_samples_split": [1, 2, 5], "random_state": [0, 1, 2, None]}]
        cl_list = [SVC]
        cl_list = [LinearSVC]
        cl_list = [DecisionTreeClassifier, RandomForestClassifier, ExtraTreesClassifier]

        # resampling unbalanced data
        # Apply SMOTE SVM
        sm = SMOTE(kind='svm')
        X_resampled, y_resampled = sm.fit_sample(X_train, y_train)

        for cl in cl_list:
            print("# Tuning hyper-parameters for %s" % 'default')
            print(cl)
            if cl == DecisionTreeClassifier:
                ensemble_parameters = [{"criterion": ["gini", "entropy"],
                                        "max_features": [1, 5, 10, 10, 20, 25],
                                        "max_depth": [None, 1, 5, 10],
                                        "class_weight": [None, "balanced"],
                                        "min_samples_split": [1, 2, 5], "random_state": [0, 1, 2, None]}]
            # clf = GridSearchCV(SVC(C=1, cache_size=7000), tuned_parameters, cv=5, n_jobs=1, scoring='%s_macro' % score)
            # clf = GridSearchCV(LinearSVC(), param_grid={'C': [0.1, 0.3, 0.5, 0.7, 1]})
            # clf = GridSearchCV(SVC(), param_grid=svc_parameters)
            # clf = GridSearchCV(KNeighborsClassifier(), param_grid=knn_parameters, scoring='accuracy')
            clf = GridSearchCV(cl(), param_grid=ensemble_parameters, scoring='f1')
            clf.fit(X_resampled, y_resampled)

            print("Best parameters set found on development set:")
            print()
            print(clf.best_params_)
            print()
            print("confusion matrix for best estimator:")
            y_pred = clf.best_estimator_.predict(X_normalized)
            print confusion_matrix(self.target, y_pred)
            print("Grid scores on development set:")
            print()
            means = clf.cv_results_['mean_test_score']
            stds = clf.cv_results_['std_test_score']
            for mean, std, params in zip(means, stds, clf.cv_results_['params']):
                print("%0.3f (+/-%0.03f) for %r"
                      % (mean, std * 2, params))
            print()

            print("Detailed classification report:")
            print()
            print("The model is trained on the full development set.")
            print("The scores are computed on the full evaluation set.")
            print()
            y_true, y_pred = y_test, clf.predict(X_test)
            print(classification_report(y_true, y_pred))
            print()


    def train(self):
        self.data, self.n_features, self.n_samples = self.format_data(mode="train")
        with open(self.features_path, "r") as f:
            features_names = json.load(f)

        # feature selection
        # fit an Extra Trees model to the data
        sel = ExtraTreesClassifier(verbose=2)  # RandomForestClassifier(n_estimators=30, verbose=2)
        sel.fit(self.data, self.target)
        if os.path.isfile(self.feature_selection_path):
            os.remove(self.feature_selection_path)
        joblib.dump(sel, self.feature_selection_path, compress=9)

        features_selected = {}
        # display the relative importance of each attribute
        for idx, importance in enumerate(sel.feature_importances_):
            print importance
            features_selected[features_names[idx]] = importance
        features_selected = dict(Counter(features_selected).most_common(max_features))
        self.min_threshold = min(features_selected.iteritems(), key=itemgetter(1))[1]
        with open(self.features_selected_info_path, "w") as f:
            json.dump(features_selected, f, indent=2)
        with open(self.features_selected_path, "w") as f:
            json.dump(features_selected.keys(), f, indent=2)
        selection_model = SelectFromModel(sel, prefit=True, threshold=self.min_threshold)
        X_new = selection_model.transform(self.data)

        scaler = preprocessing.StandardScaler().fit(X_new)
        if os.path.isfile(self.scaler_path):
            os.remove(self.scaler_path)
        joblib.dump(scaler, self.scaler_path, compress=9)
        X_scaled = scaler.transform(X_new)

        """
        # create a base classifier used to evaluate a subset of attributes
        model = LogisticRegression()
        # create the RFE model and select 3 attributes
        rfe = RFE(model, 3)
        rfe = rfe.fit(X_scaled, self.target)
        # summarize the selection of the attributes
        X_data = rfe.transform(X_scaled)
        support = rfe.support_
        features = features_selected.keys()
        features_rfe = []
        for idx, support_feature in enumerate(support):
            if support_feature:
                features_rfe.append(features[idx])
        with open(self.features_selected_path, "w") as f:
            json.dump(features_rfe, f, indent=2)
        # print(rfe.support_)
        # print(rfe.ranking_)

        scaler = preprocessing.StandardScaler().fit(X_data)
        if os.path.isfile(self.scaler_path):
            os.remove(self.scaler_path)
        joblib.dump(scaler, self.scaler_path, compress=9)
        X_scaled = scaler.transform(X_data)
        """

        # resampling unbalanced data
        # Apply SMOTE SVM
        sm = SMOTE(kind='svm')
        X_resampled, y_resampled = sm.fit_sample(X_scaled, self.target)

        clf = self.classifier.fit(X_resampled, y_resampled)
        self.n_samples, self.n_features = X_scaled.shape

        # evaluate training error
        # clf.score(self.data, self.target)

        if os.path.isfile(self.trained_model_path):
            os.remove(self.trained_model_path)
        joblib.dump(clf, self.trained_model_path, compress=9)
        model_info = {"n_samples": self.n_samples, "n_features": self.n_features}
        with open(self.trained_model_info_path, "w") as f:
            json.dump(model_info, f, indent=2)
        print "TRAINED!"

    def predict(self):
        self.data, self.n_features, self.n_samples = self.format_data(mode="predict")
        # feature selection
        """
        lsvc = LinearSVC(C=0.01, penalty="l1", dual=False).fit(self.data, self.target)
        model = SelectFromModel(lsvc, prefit=True)
        X_new = model.transform(self.data)
        """
        scaler = joblib.load(self.scaler_path)
        X_scaled = scaler.transform(self.data)
        # sel = joblib.load(self.feature_selection_path)
        # selection_model = SelectFromModel(sel, prefit=True, threshold=self.min_threshold)
        # X_new = selection_model.transform(X_scaled)
        clf = joblib.load(self.trained_model_path)
        self.predicted = clf.predict(X_scaled)

        prediction = {}
        if self.ground_truth is not None:
            prediction["report"] = classification_report(self.target, self.predicted)
            prediction["confusion_matrix"] = confusion_matrix(self.target, self.predicted).tolist()
        result_idx = 0
        for test_group_data in self.data_set:
            for test_name in test_group_data:
                actual = "NaN"
                if self.target is not None:
                    actual = self.target[result_idx]
                prediction[test_name] = {"prediction": self.predicted[result_idx], "actual": actual}
                result_idx += self.test_sample_len[test_name]
        """"
        raw_result = []
        for idx, predict in enumerate(self.predicted):
            actual = "NaN"
            if self.target is not None:
                actual = self.target[idx]
            raw_result.append([predict, actual])
        prediction["raw_result"] = raw_result
        """
        with open(self.prediction_path, "w") as f:
            json.dump(prediction, f, indent=2)
        return prediction

    def add_data(self, dbg_msg_template, feature_template, log_msgs):
        rv_data = []
        for log_line in log_msgs:
            try:
                rv_features = []
                debug_msg_match = False
                """
                if log_line["debug_variables"] != {}:
                    for idx, variable_name in enumerate(log_line["debug_variables"]):
                        debug_msg_id = float(str(log_line["msg_id"]) + "." + str(idx))
                        rv_features.append(debug_msg_id)  # debug_variable_id
                        # debug_variable_value
                        rv_features.append(util.variable_eval(log_line["debug_variables"][variable_name]))
                        for feature in feature_template:
                            if feature != "debug_variable_id" and feature != "debug_variable_value":
                                rv_features.append(log_line[feature])
                        rv_data.append(rv_features)
                        rv_features = []
                else:
                    rv_features.append(float(str(log_line["msg_id"]) + ".0"))  # debug_variable_id
                    rv_features.append(0.0)  # debug_variable_value
                    for feature in feature_template:
                        if feature != "debug_variable_id" and feature != "debug_variable_value":
                            rv_features.append(log_line[feature])
                    rv_data.append(rv_features)
                    rv_features = []
                """
                for idx, feature in enumerate(feature_template):
                        if '-' in feature:
                            hash_variable = feature.split('-', 1)
                            if hash_variable[0] == log_line["hash"]:  # if hashes match
                                debug_msg_match = True
                                rv_features.append(util.variable_eval(log_line["debug_variables"][hash_variable[1]]))
                            else:
                                rv_features.append(missing_value)
                                """
                                if len(rv_data) > 0:
                                    # use previous value, use as state
                                    rv_features.append(rv_data[len(rv_data) - 1][idx])
                                else:
                                    rv_features.append(missing_value)
                                """
                        else:
                            if feature in log_line and "" != log_line[feature]:
                                rv_features.append(log_line[feature])
                            else:
                                rv_features.append(missing_value)
                if debug_msg_match:
                    rv_data.append(rv_features)
            except Exception as e:
                logger.exception(log_line)
        return rv_data

    def format_data(self, mode="train"):
        data = []
        # need to flatten dictionary to input to classifier
        for component, component_feature in self.msg_template_set.iteritems():
            for test_group_idx, test_group_data in enumerate(self.data_set):
                for test_name, test_data in test_group_data.iteritems():
                    if component in test_data and component in self.feature_set:
                        #  get feature data
                        pre_len = len(data)
                        data.extend(self.add_data(component_feature, self.feature_set[component], test_data[component]))
                        post_len = len(data)
                        added_len = post_len - pre_len
                        self.test_sample_len[test_name] = added_len
                        # get target
                        if self.ground_truth is not None:
                            if "Dolby - Metadata" in self.ground_truth[test_group_idx][test_name]:
                                if self.ground_truth[test_group_idx][test_name]["Dolby - Metadata"] == "fail":
                                    self.target.extend([1] * added_len)
                                else:
                                    self.target.extend([0] * added_len)
        n_samples = len(data)
        n_features = len(data[0])
        print n_samples
        print n_features

        if mode == "predict":
            with open(self.trained_model_info_path, "r") as f:
                model_n_features = json.load(f)["n_features"]
                '''
                if model_n_features > n_features:
                    raise Exception("Model consists of %d features, test sample consists of %d features. "
                                    "Model needs to have more features than test sample")
                '''
                n_features = model_n_features

        format_data = pd.lib.to_object_array(data).astype(float)
        '''
        # Create our imputer to replace missing values with most_frequent value
        imp = Imputer(missing_values='NaN', strategy='most_frequent', axis=0)
        imp = imp.fit(format_data)

        # Impute our data, then train
        rv_format_data = imp.transform(format_data)
        '''
        rv_format_data = format_data
        return rv_format_data, n_features, n_samples
