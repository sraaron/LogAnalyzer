import os
import re
import sys
import ast
import json
import errno
import string
from datetime import datetime, timedelta

_alphanum = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

_timeunitdeltas = [3600, 60, 1]

_min_line_count = sys.maxsize


def get_min_line_count():
    return _min_line_count


def update_min_line_count(val):
    global _min_line_count
    if val < _min_line_count:
        _min_line_count = val


def timedelta_to_float(timedelta_timedelta):
    return timedelta_timedelta.total_seconds()


def str_timedelta_to_float(str_timedelta):
    float_timedelta = datetime.strptime(str_timedelta, "%H:%M:%S.%f")
    float_timedelta = timedelta(seconds=float_timedelta.second, microseconds=float_timedelta.microsecond,
                                minutes=float_timedelta.minute, hours=float_timedelta.hour)
    return float_timedelta.total_seconds()


def variable_eval(val):
    # if string return exists
    if isinstance(val, basestring):
        return 1
    # else return value
    else:
        return val


def tryeval(val):
    try:
        val = ast.literal_eval(val)
    except:
        pass
    return val


def load_json(path):
    with open(path, "r") as f:
        rv = json.load(f)
    return rv


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def get_timestamp_regex(get_utc=False):
    re1 = '((?:2|1)\\d{3}(?:-|\\/)(?:(?:0[1-9])|(?:1[0-2]))(?:-|\\/)(?:(?:0[1-9])|(?:[1-2][0-9])|(?:3[0-1]))' \
          '(?:T|\\s)(?:(?:[0-1][0-9])|(?:2[0-3])):(?:[0-5][0-9]):(?:[0-5][0-9]))'  # Time Stamp 1
    re2 = '(.|,)'  # Any Single Character 1
    re3 = '(\\d)'  # Any Single Digit 1
    re4 = '(\\d)'  # Any Single Digit 2
    re5 = '(\\d)'  # Any Single Digit 3

    if get_utc:
        # UTC time offset handling
        re6 = '(\\+)'  # Any Single Character 2
        re7 = '((?:(?:[0-1][0-9])|(?:[2][0-3])|(?:[0-9])):(?:[0-5][0-9])(?::[0-5][0-9])?)'  # HourMinuteSec 1
        rg = re.compile(re1 + re2 + re3 + re4 + re5 + re6 + re7, re.IGNORECASE | re.DOTALL)  # utc rg
    else:
        rg = re.compile(re1 + re2 + re3 + re4 + re5, re.IGNORECASE | re.DOTALL)
    return rg


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")

def timestamp_to_string(timestamp, utc=None):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")


def get_timestamp(txt, get_utc=False):
    timestamp = ""
    rg = get_timestamp_regex(get_utc)
    m = rg.search(txt)

    if m:
        timestamp1 = m.group(1)
        d1 = m.group(3)
        d2 = m.group(4)
        d3 = m.group(5)
        timestamp = string.replace(timestamp1, "T", " ") + "." + d1 + d2 + d3
        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")

        # UTC time offset handling
        if get_utc:
            sign = m.group(6)
            time1 = m.group(7)
            utc_offset = timedelta(hours=int(time1[0:2]), minutes=int(time1[3:5]))
            if sign == "+":
                timestamp += utc_offset
            elif sign == "-":
                timestamp -= utc_offset
    return timestamp


def escape(pattern):
    """Escape all non-alphanumeric characters in pattern."""
    s = list(pattern)
    alphanum = _alphanum
    for i, c in enumerate(pattern):
        if c == " ":
            continue
        if c not in alphanum:
            if c == "\000":  # skip escape for "_"
                s[i] = "\\000"
            else:
                s[i] = "\\" + c
    return pattern[:0].join(s)
