import re
import util
import logging

logger = logging.getLogger(__name__)

class TranscoderLogParser(object):
    """Parse Transcoder Log"""

    def __init__(self, debug_msg_template=None):
        self.debug_msg_template = debug_msg_template
        self.first_timestamp = None

    def parse_debug_msg(self, cpp_name, debug_msg):
        rv = {}
        debug_msg = debug_msg.rstrip("\n").rstrip("\\n")
        if self.debug_msg_template is not None and cpp_name in self.debug_msg_template:
            for debug_msg_template in self.debug_msg_template[cpp_name]:
                regex_match = debug_msg_template["debug_string_regex"]
                try:
                    rg = re.compile(regex_match, re.DOTALL)
                    m = rg.search(debug_msg)
                    if m:
                        # rv["regex_match"] = regex_match
                        # rv["variables"] = {}
                        for idx, variable_name in enumerate(debug_msg_template["debug_variables"]):
                            # rv["variables"][variable_name] = m.group(idx)
                            rv[variable_name] = util.tryeval(m.group(idx+1))
                except Exception as e:
                    logger.exception(debug_msg + regex_match)
        return rv

    def parse_file(self, log_file_path, parse_debug_msg=False):
        rv = {}
        re1 = '.*?'  # Non-greedy match on filler
        re2 = '(L\\d)'  # Any Single Digit 1
        re3 = '.*?'  # Non-greedy match on filler
        re4 = '(\\[.*?\\])'  # Square Braces 1
        rg = re.compile(re1 + re2 + re3 + re4, re.IGNORECASE | re.DOTALL)
        with open(log_file_path, "r") as f:
            # read each line in log file
            for txt in f:
                m = rg.search(txt)
                if m:
                    timedelta = util.get_timestamp(txt)
                    if self.first_timestamp is None:
                        self.first_timestamp = timedelta
                    timedelta -= self.first_timestamp
                    timedelta = str(timedelta)
                    level = int(m.group(1)[1])
                    # remove start/ending square braces and split
                    sbraces = re.split('[@|:]', m.group(2)[1:len(m.group(2)) - 1])
                    cpp_name = sbraces[1]
                    if ".cpp" not in cpp_name:
                        logger.error(cpp_name + txt)
                        continue
                    debug_msg = txt[m.end():].rstrip("\n")
                    try:
                        if cpp_name not in rv:
                            rv[cpp_name] = []
                        rv[cpp_name].append({timedelta: {"level": level, "function_name": sbraces[0],
                                                         "line_number": int(sbraces[2]), "debug_msg": debug_msg}})
                        if parse_debug_msg:
                            rv[cpp_name][len(rv[cpp_name]) - 1][timedelta]["variables"] = \
                                self.parse_debug_msg(cpp_name, debug_msg)
                    except Exception as e:
                        logger.exception(cpp_name + txt)
        return rv
