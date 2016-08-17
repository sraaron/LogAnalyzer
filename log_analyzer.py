import sys
import zipfile
import argparse

import remote_proc

m_namelist = []


def extractfile(zip_filename, dest_folder):
    with zipfile.ZipFile(zip_filename, "r") as z:
        z.extractall(dest_folder)
        global m_namelist
        m_namelist = zipfile.ZipFile.namelist(z)


def filter_techdump(channel, dest_folder):
    print m_namelist
    print dest_folder
    return


def start_server(args):
    start(Worker, getMyIP(), args.port)


def main():
    description = '''
    Log Analyzer will analyzer logs to extract insights into log files.
    '''

    main_parser = argparse.ArgumentParser(description=description)
    sub_parsers = main_parser.add_subparsers(title='valid operations', metavar='command')

    parser = sub_parsers.add_parser('start', help='start log analyzer server')
    parser.add_argument('-i', '--ip', metavar='IP', help='Enter ip address to host server at')
    parser.add_argument('-p', '--port', metavar='PORT', help='Enter port to host server at')
    parser.set_defaults(func=start_server)

    args = main_parser.parse_args()

    '''
    if (opts.filename == ""):
        return
    extractfile(opts.filename, opts.destination)
    filter_techdump(opts.channel, opts.destination)    
    #filehandle = open(filename,'rb')    
    '''

    return args.func(args)


if __name__ == "__main__":
    main()
