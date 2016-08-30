import re
import util
import logging

logger = logging.getLogger(__name__)

class TranscoderLogParser(object):
    """Parse Transcoder Log"""

    def __init__(self, debug_msg_template=None, log_file_path=None):
        self.log_file_path = log_file_path
        self.debug_msg_template = debug_msg_template

    def parse_debug_msg(self, cpp_name, debug_msg):
        rv = {}
        if self.debug_msg_template is not None and cpp_name in self.debug_msg_template:
            for debug_msg_template in self.debug_msg_template[cpp_name]:
                regex_match = debug_msg_template["debug_string_regex"]
                try:
                    rg = re.compile(regex_match)
                    m = rg.search(debug_msg)
                    if m:
                        rv["regex_match"] = regex_match
                        rv["variables"] = {}
                        for idx, variable_name in enumerate(debug_msg_template["debug_variables"]):
                            rv["variables"][variable_name] = m.group(idx)
                except Exception as e:
                    logger.error(str(e) + debug_msg + regex_match + debug_msg_template["debug_variables"])
        return rv

    def parse_line(self, txt, parse_debug_msg=False):
        rv = {}
        re1 = '.*?'  # Non-greedy match on filler
        re2 = '(L\\d)'  # Any Single Digit 1
        re3 = '.*?'  # Non-greedy match on filler
        re4 = '(\\[.*?\\])'  # Square Braces 1

        rg = re.compile(re1 + re2 + re3 + re4, re.IGNORECASE | re.DOTALL)
        m = rg.search(txt)
        if m:
            timestamp = util.get_timestamp(txt)
            level = int(m.group(1)[1])
            # remove start/ending square braces and split
            sbraces = re.split('[@|:]', m.group(2)[1:len(m.group(2)) - 1])
            cpp_name = sbraces[1]
            debug_msg = txt[m.end():]
            rv = {"timestamp": timestamp, "level": level, "function_name": sbraces[0], "cpp_name": cpp_name,
                  "line_number": int(sbraces[2]), "debug_msg": debug_msg}
            if parse_debug_msg:
                rv.update(self.parse_debug_msg(cpp_name, debug_msg))
        return rv

