import os
import sys
import zipfile

m_namelist = []


class Filter(object):
    """Filter will filter log information"""

    def __init__(self, arg):
        super(Filter, self).__init__()
        self.arg = arg
        self.filename = arg["filename"]
        self.channel = int(arg["channel_number"])
        # print self.filename
        # print self.channel

    def filter_logs(self):
        if self.channel > 0 and self.filename != "":
            self.extractfile()
            self.filter_techdump()

    def extractfile(self):
        path_dir = os.path.join(os.path.dirname(__file__), "techdumps")
        filepath = os.path.join(path_dir, self.filename)
        with zipfile.ZipFile(filepath, "r") as z:
            '''
            with open(os.path.join(tDir, os.path.basename(icon[1])), 'wb') as f:
            f.write(z.read(icon[1]))
            '''
            # z.extractall(dest_folder)
            global m_namelist
            m_namelist = zipfile.ZipFile.namelist(z)

    def filter_techdump(self):
        print m_namelist
        return

if __name__ == "__main__":
    Filter(sys.argv[1:])
