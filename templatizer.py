import os
import re
import json
import subprocess
# traverse code repo
# extract log message statements
# convert log message statements into template
# (extract variables names, variable type, variable values, file and line number)


class Templatizer(object):
    """Create log message template based on code repo"""

    def __init__(self, filter_settings):
        self.filter_settings = filter_settings
        self.cur_path = os.path.dirname(__file__)
        self.templates_path = os.path.join(self.cur_path, "templates")
        self.component_branch_version_file_path = os.path.join(self.cur_path, "settings",
                                                               "component_branch_version.json")
        self.component_branch_version = {}
        self.component_template = {}
        with open(self.component_branch_version_file_path, "r") as f:
            self.component_branch_version = json.load(f)

    def is_svn_dir(self, svn_path):
        rv = False
        if svn_path[len(svn_path)-1] == "/":
            rv = True
        return rv

    def is_cpp(self, svn_path):
        rv = False
        file_name, extension = os.path.splitext(svn_path)
        if ".cpp" == extension:
            rv = True
        return rv

    def debug_msg_arg_parser(self, debug_msg_arg):
        try:
            first_quote_pos = debug_msg_arg.find("\"")
            last_quote_pos = debug_msg_arg.rfind("\"")
            debug_string = debug_msg_arg[first_quote_pos+1:last_quote_pos].strip()
            debug_area = debug_msg_arg[:first_quote_pos-1].split(",")[0].strip()
            debug_level = debug_msg_arg[:first_quote_pos-1].split(",")[1].strip()
            debug_variables = []
            if len(debug_msg_arg) > last_quote_pos+2:
                debug_variables = [s.strip() for s in debug_msg_arg[last_quote_pos+2:].split(",")]
        except Exception as e:
            print e
            print debug_msg_arg
        return [debug_area, debug_level, debug_string, debug_variables]

    def extract_transcode_pack_template(self, svn_path, component_template_path):
        if "RmpSpTranscodePack" not in self.component_template:
            self.component_template["RmpSpTranscodePack"] = {}
        cpp_file_name = os.path.basename(svn_path)
        cpp_cat = [s.strip() for s in subprocess.check_output(['svn', 'cat', svn_path]).splitlines()]
        re1 = '.*?'  # Non-greedy match on filler
        re2 = '(\\(.*\\))'  # Round Braces 1
        rg = re.compile(re1 + re2, re.IGNORECASE | re.DOTALL)
        debug_msg_count = 0
        search_line = ""
        debug_msg_templates = []
        for line in cpp_cat:
            if line == "" or line.startswith(r"//") or line.startswith("#"):
                continue
            if "DEBUG_MSG" in line or "DEBUG_MSG" in search_line:
                search_line += line
                if search_line.endswith(";"):
                    m = rg.search(search_line)
                    if m:
                        debug_msg_args = self.debug_msg_arg_parser(m.group(1)[1:len(m.group(1))-1])
                        debug_msg_templates.append({"debug_area": debug_msg_args[0], "debug_level": debug_msg_args[1],
                                                    "debug_string": debug_msg_args[2], "debug_variables":
                                                        debug_msg_args[3]})
                        debug_msg_count += 1
                    search_line = ""
        if debug_msg_count > 0:
            self.component_template["RmpSpTranscodePack"][cpp_file_name] = debug_msg_templates

    def crawler(self, svn_path, component_template_path, component):
        svn_list = [s.strip() for s in subprocess.check_output(['svn', 'list', svn_path]).splitlines()]
        for sub_path in svn_list:
            path = svn_path + sub_path
            if self.is_svn_dir(path):
                self.crawler(path, component_template_path, component)
            elif self.is_cpp(path):
                if component == "RmpSpTranscodePack":
                    self.extract_transcode_pack_template(path, component_template_path)

    def gen_template(self):
        version, build_number = self.get_swversion()
        branch = self.version_to_branch_mapping(version)
        for component, path in self.component_branch_version[branch].iteritems():
            component_template_path = os.path.join(self.templates_path, branch + "_" + component + ".json")
            # if not os.path.exists(component_template_path):
            self.crawler(path, component_template_path, component)
            with open(component_template_path, "w") as f:
                json.dump(self.component_template[component], f, indent=2)

    def version_to_branch_mapping(self, version):
        branch = ""
        version = version.lower()
        if "eng" in version:
            branch = "trunk"
        else:
            version_split = version.split(".")
            version_split[len(version_split)-2] = "x"
            for idx, val in enumerate(version_split):
                if idx == len(version_split)-1:
                    branch += val
                else:
                    branch += val + "."
        return branch

    def get_swversion(self):
        rv = None
        for key in self.filter_settings:
            if key == "swversion":
                with open(self.filter_settings[key]["path"], "r") as f:
                    txt = f.read()

                    re1 = '.*?'  # Non-greedy match on filler
                    re2 = '(ACP)'  # Word 1
                    re3 = '.*?'  # Non-greedy match on filler
                    re4 = '(version)'  # Word 2
                    re5 = '(=)'  # Any Single Character 1
                    re6 = '((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))' \
                          '(?![\\d])'
                    re7 = '.*?'  # Non-greedy match on filler
                    re8 = '(buildnum)'  # Word 3
                    re9 = '(=)'  # Any Single Character 2
                    re10 = '(\\d+)'  # build number

                    rg = re.compile(re1 + re2 + re3 + re4 + re5 + re6 + re7 + re8 + re9 + re10, re.IGNORECASE | re.DOTALL)
                    m = rg.search(txt)
                    if m:
                        word1 = m.group(1)
                        word2 = m.group(2)
                        c1 = m.group(3)
                        version_number = m.group(4)
                        word3 = m.group(5)
                        c2 = m.group(6)
                        build_number = m.group(7)
                        rv = version_number, build_number
                break
        return rv
