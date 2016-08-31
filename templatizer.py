import os
import re
import util
import json
import logging
import subprocess

logger = logging.getLogger(__name__)

# traverse code repo
# extract log message statements
# convert log message statements into template
# (extract variables names, variable type, variable values, file and line number)


class Templatizer(object):
    """Create log message template based on code repo"""

    def __init__(self, filter_settings):
        logger.info("Initialize Templatizer")
        self.filter_settings = filter_settings
        self.cur_path = os.path.dirname(__file__)
        self.templates_path = os.path.join(self.cur_path, "templates")
        self.component_branch_version_file_path = os.path.join(self.cur_path, "settings",
                                                               "component_branch_version.json")
        self.component_branch_version = {}
        self.component_template = {}
        self.int_types = []
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

    def debug_level_to_val(self, debug_level):
        debug_level_enum = {"L_EMERG": 0, "L_ALERT": 0, "L_CRITICAL": 2, "L_ERROR": 3, "L_WARN": 4, "L_NOTICE": 6,
                            "L_INFO": 8, "DEFAULT_LOG_LEVEL": 8, "L_DEBUG": 10, "L_MAX_LEVEL": 12,
                            "D_ALWAYS_PRINT": 0, "D_STAT_ERROR": 1, "D_STAT_NORMAL": 2, "D_ERROR": 3,
                            "D_WARN": 4, "D_INFO": 8, "D_MAX_LEVEL": 12}
        rv = 0
        try:
            if "+" in debug_level:
                debug_level_split = debug_level.split("+")
                rv = debug_level_enum[debug_level_split[0].strip()] + int(debug_level_split[1].strip())
            elif debug_level in debug_level_enum:
                rv = debug_level_enum[debug_level]
            else:
                # TO DO: need to handle direct integer values, integer variable values, c++ conditional expressions
                rv = 0
        except Exception as e:
            logger.exception(debug_level)
        return str(rv)

    def int_types_to_ctypes(self, debug_string):
        for k, v in self.int_types:
            if k in debug_string:
                debug_string = re.sub('\"\s*' + k + '\s*\"', v, debug_string)  # match zero or more space occurrences
        return debug_string

    def debug_string_to_regex(self, debug_string):
        valid = False
        # Format Specification Syntax: https://msdn.microsoft.com/en-us/library/56e442dc.aspx
        # Format Specification: http://www.cplusplus.com/reference/cstdio/printf/
        debug_string = debug_string.rstrip("\n").rstrip("\\n")
        # hexadecmial floating point skipped (TO DO)
        int_match = '([-+]?\\d+)'
        unsigned_int_match = '(\\d+)'
        octal_match = '([0-7]{1,3})'
        lower_case_hex_match = '([0-9a-f]+)'
        upper_case_hex_match = '([0-9A-F]+)'
        floating_point = '([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'
        exponent_form = '(%s[+-]?%s)' % (floating_point, int_match)
        shortest_form = '(%s)|(%s)' % (exponent_form, floating_point)
        char_match = '(.)'
        string_match = '(.*)'
        cpp_specifier_match_dict = {'d': int_match, 'i': int_match, 'u': unsigned_int_match, 'x': lower_case_hex_match,
                   'X': upper_case_hex_match, 'f': floating_point, 'F': floating_point, 'e': exponent_form,
                   'E': exponent_form, 'g': shortest_form, 'G': shortest_form, 'c': char_match, 's': string_match,
                   'p': string_match, '%': char_match, 'o': octal_match}
        flags = '[-+\s#0]'
        width = '(\\d+|[*])'
        precision = '([.]\\d+|[*])'
        length = '(hh|h|l|ll|j|z|t|L|I32|I64|I|w)'
        specifier = '[diuoxXfFeEgGaAcspn%]'
        cpp_specifier_format = '(%s(%s)?(%s)?(%s)?(%s)?(%s))' % ('%', flags, width, precision, length, specifier)
        rg = re.compile(cpp_specifier_format)
        # escape regex meta-characters in existing debug message
        debug_list = re.split(cpp_specifier_format, debug_string)
        if len(debug_list) > 0:
            if len(debug_list) < 12 and debug_list[0] == "":  # check if only single
                return "", valid
            debug_string = ""
            for idx in range(0, len(debug_list), 10):
                debug_string += util.escape(debug_list[idx])
                if len(debug_list) > 1 and idx + 1 < len(debug_list):
                    debug_string += debug_list[idx + 1]
            # print debug_string
            for i in set(rg.finditer(debug_string)):
                specifier_format = '(%s(%s)?(%s)?(%s)?(%s)?(%s))' % ('%', flags, width, precision, length, i.group(9))
                debug_string = re.sub(specifier_format, cpp_specifier_match_dict[i.group(9)], debug_string)
            # print debug_string
        return debug_string, True

    def populate_int_types(self, base_path):
        re1 = '(#)'  # Any Single Character 1
        re2 = '(define)'  # Word 1
        re3 = '(\\s+)'  # White Space 1
        re4 = '((?:[a-z][a-z]*[0-9]+[a-z0-9]*))'  # Alphanum 1
        re5 = '(\\s+)'  # White Space 2
        re6 = '(".*?")'  # Double Quote String 1
        rg = re.compile(re1 + re2 + re3 + re4 + re5 + re6, re.IGNORECASE | re.DOTALL)
        svn_path = base_path + "baselib/win32/inttypes.h"
        int_types_cat = [s.strip() for s in subprocess.check_output(['svn', 'cat', svn_path]).splitlines()]
        for line in int_types_cat:
            m = rg.search(line)
            if m:
                int_type = m.group(4)
                c_type = m.group(6).replace('"', '').strip()
                self.int_types.append((int_type, c_type))

    def debug_msg_arg_parser(self, debug_msg_arg):
        debug_string = ""
        debug_area = ""
        debug_level_string = ""
        debug_level_value = ""
        debug_string_regex = ""
        debug_variables = []
        try:
            debug_msg_arg = self.int_types_to_ctypes(debug_msg_arg)
            data = re.compile(r'''((?:[^,"']|"[^"]*"|'[^']*')+)''').split(debug_msg_arg)[1::2]
            debug_area, debug_level_string, debug_string,  = data[0].strip(), data[1].strip(), data[2].\
                strip().replace('"', '')
            debug_variables = [x.strip() for x in data[3:]]
            debug_level_value = self.debug_level_to_val(debug_level_string)
            debug_string_regex, valid = self.debug_string_to_regex(debug_string)
            if valid is False:
                return None
        except Exception as e:
            logger.exception(debug_msg_arg)
        return {"debug_area": debug_area, "debug_level_string": debug_level_string,
                "debug_level_value": debug_level_value, "debug_string": debug_string,
                "debug_variables": debug_variables, "debug_string_regex": debug_string_regex}

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
            if re.search(r'\bDEBUG_MSG\b', line) or re.search(r'\bDEBUG_MSG\b', search_line):
                search_line += line
                if search_line.endswith(";"):
                    m = rg.search(search_line)
                    if m:
                        template = self.debug_msg_arg_parser(m.group(1)[1:len(m.group(1))-1])
                        if template is not None:
                            debug_msg_templates.append(template)
                            debug_msg_count += 1
                    search_line = ""
        if debug_msg_count > 0:
            self.component_template["RmpSpTranscodePack"][cpp_file_name] = debug_msg_templates

    def crawler(self, svn_path, component_template_path, component):
        svn_list = [s.strip() for s in subprocess.check_output(['svn', 'list', svn_path]).splitlines()]
        if component == "RmpSpTranscodePack" and len(self.int_types) == 0:
            self.populate_int_types(svn_path)
        for sub_path in svn_list:
            path = svn_path + sub_path
            if self.is_svn_dir(path):
                self.crawler(path, component_template_path, component)
            elif self.is_cpp(path):
                if component == "RmpSpTranscodePack":
                    self.extract_transcode_pack_template(path, component_template_path)
                else:
                    self.component_template[component] = {}

    def gen_template(self):
        version, build_number = self.get_swversion()
        branch = self.version_to_branch_mapping(version)
        for component, path in self.component_branch_version[branch].iteritems():
            component_template_path = os.path.join(self.templates_path, branch + "_" + component + ".json")
            if not os.path.exists(component_template_path):
                self.crawler(path, component_template_path, component)
                with open(component_template_path, "w") as f:
                    json.dump(self.component_template[component], f, indent=2)
            else:
                with open(component_template_path, "r") as f:
                    self.component_template[component] = json.load(f)
        return self.component_template

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
                        version_number = m.group(4)
                        build_number = m.group(7)
                        rv = version_number, build_number
                break
        return rv
