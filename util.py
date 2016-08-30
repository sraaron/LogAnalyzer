import re
import string
from datetime import datetime, timedelta


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
