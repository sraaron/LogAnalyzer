import os
import re
import sys
import time
import json
import shutil
import urllib
import signal
import socket
import httplib
import logging
import mimetypes
import threading
import posixpath
import subprocess
from os import curdir, sep
from log_filter import Filter
from templatizer import Templatizer
from feature_extractor import FeatureExtractor
from txt_result_importer import TxtResultImporter
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)
PORT_NUMBER = 54321


def getMyIP():
    try:
        # windows
        res = subprocess.check_output('ipconfig')
        res = res.splitlines()
        for line in res:
            if 'IPv4 Address' in line:
                return line.split(': ')[1]
    except:
        # linux
        try:
            res = subprocess.check_output('ifconfig')
            res = res.splitlines()
            for line in res:
                addr = None
                if 'inet addr:' in line:
                    addr = re.search(r'inet addr:([\d.]+)\s', line).groups()[0]
                elif 'inet ' in line:
                    addr = re.search(r'inet\s([\d.]+)\s', line).groups()[0]
                if addr and addr != '127.0.0.1':
                    return addr
        except:
            pass


def file_pipe(src, dst, size=None, mess=None):
    try:
        if size == 0:
            if mess:
                print 'empty file'
            return 0
        elif size != None:
            chunk_size = 1024 * 1024  # 1MB
            remaining = size
            while True:
                if remaining < chunk_size:
                    chunk_size = remaining
                chunk = src.read(chunk_size)
                dst.write(chunk)
                remaining -= chunk_size
                if remaining <= 0:
                    break
                if mess:
                    print '\r%d%%' % (float(size - remaining) / size * 100),
            if mess:
                print '\r',
        else:
            chunk_size = 1
            size = 0
            while True:
                chunk = src.read(chunk_size)
                if not len(chunk):
                    break
                size += len(chunk)
                dst.write(chunk)
                if '\n' in chunk:
                    if hasattr(dst, 'flush'):
                        dst.flush()
                if mess:
                    print '.',
    except Exception as e:
        if not threading.current_thread().daemon:
            raise e
        else:
            logger.debug(e)
    finally:
        try:
            src.close()
        except:
            pass
        try:
            dst.close()
        except:
            pass
    return size


def analyze(command):
    params = json.loads(command)
    preprocessing(params)


def train(command):
    params = json.loads(command)
    training_label = params['training_label']
    feature_set, ml_input_data_set = preprocessing(params)
    training(training_label, feature_set, ml_input_data_set)


def train_with_txt(command):
    params = json.loads(command)
    # filter_logs = Filter(params, filter_type="txt_results")
    txt_result_importer = TxtResultImporter(params)
    txt_result_importer.extract_results()
    print command
    return


def training(training_label, feature_set, ml_input_data_set):

    return


def preprocessing(params):
    # filter the logs
    filter_logs = Filter(params)
    filter_settings = filter_logs.get_filter_settings()
    filter_logs.filter_logs()
    # if template file not available, generate template
    # filter settings needed to get svn branch path for particular version
    # currently accesses svn server directly, TO DO: have local back up copy in case svn server is down?
    templatizer = Templatizer(filter_settings=filter_settings)
    component_template = templatizer.gen_template()
    # extract features from log, using template
    extractor = FeatureExtractor(component_template=component_template, techdump_filename=params['filename'],
                                  filter_settings=filter_settings)
    return component_template, extractor.extract_features()


# This class handles any incoming request from
# the browser
class myHandler(BaseHTTPRequestHandler):
    # Handler for the GET requests
    def do_GET(self):
        if self.path == "/":
            self.path = "log_analyzer.html"

        try:
            # Check the file extension required and
            # set the right mime type

            sendReply = False
            if self.path.endswith(".html"):
                mimetype = 'text/html'
                sendReply = True
            if self.path.endswith(".jpg"):
                mimetype = 'image/jpg'
                sendReply = True
            if self.path.endswith(".gif"):
                mimetype = 'image/gif'
                sendReply = True
            if self.path.endswith(".png"):
                mimetype = 'image/png'
                sendReply = True
            if self.path.endswith(".js"):
                mimetype = 'application/javascript'
                sendReply = True
            if self.path.endswith(".css"):
                mimetype = 'text/css'
                sendReply = True

            if sendReply == True:
                # Open the static file requested and send it
                f = open(curdir + sep + self.path)
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
            return


        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)


class simpleHttpServerHander(SimpleHTTPRequestHandler):
    SimpleHTTPRequestHandler.extensions_map.update({
        '.log': 'text/plain',
        '.json': 'text/plain',
    })

    def do_POST(self):
        try:
            user = self.get_user()
            path = self.path
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)
            if path.startswith('/'):
                path = path[1:]
            result = self.perform_operation(user, path, body)
            if result:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                if hasattr(result, 'read'):  # is a file like object
                    file_pipe(result, self.wfile)
                else:
                    self.wfile.write(result)
            else:
                self.send_response(404)
        except socket.error as e:
            logger.debug('Error during processing POST: %s', str(e))
            self.wfile._wbuf = []
            self.wfile._wbuf_len = 0

    def do_GET(self):
        try:
            if self.path == "/":
                self.path = "log_analyzer.html"
            path = self.translate_path(self.path)
            path = self.translate_download_path(path)
            if path and os.path.exists(path):
                if os.path.isfile(path):
                    self.send_response(200)
                    size = os.path.getsize(path)
                    self.send_header('Content-Length', size)
                    self.send_header('Content-type', self.guess_type(path))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    file_pipe(open(path, 'rb'), self.wfile, size)
                    return
                elif os.path.isdir(path):
                    file_pipe(self.list_directory(path), self.wfile)
                    return
            self.send_response(404)
        except socket.error as e:
            logger.debug('Error during processing GET: %s', str(e))
            self.wfile._wbuf = []
            self.wfile._wbuf_len = 0

    def do_PUT(self):
        try:
            length = int(self.headers['Content-Length'])
            path = self.translate_path(self.path)
            path = self.translate_upload_path(path)
            if path and (not os.path.exists(path) or not os.path.isdir(path)):
                file_pipe(self.rfile, open(path, 'wb'), length)
                if os.path.getsize(path) == length:
                    self.upload_completed(path, length)
                    self.send_response(200)
                else:
                    os.remove(path)
                    logger.info('upload aborted')
                    self.send_response(405)
            else:
                self.send_response(405)
        except socket.error as e:
            logger.debug('Error during processing PUT: %s', str(e))
            self.wfile._wbuf = []
            self.wfile._wbuf_len = 0

    # to be overrided by subclass
    def translate_upload_path(self, path):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), path)
        return path

    # to be overrided by subclass
    def translate_download_path(self, path):
        return path

    # to be overrided by subclass
    def upload_completed(self, path, length):
        logger.info('upload completed %s (%d bytes)' % (path, length))

    # to be overrided by subclass
    def get_user(self):
        return self.client_address[0]  # ip address

    # to be overrided by subclass
    def perform_operation(self, user, oper, command):
        logger.info('[%s] %s: %s' % (user, oper, command))
        print '[%s] %s: %s' % (user, oper, command)
        if oper == "analyze":
            analyze(command)
        elif oper == "train":
            train(command)
        elif oper == "train_with_txt":
            train_with_txt(command)
        return 'okay'

    # override SimpleHTTPRequestHandler
    def translate_path(self, path):
        # abandon query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = ''  # this line is different!
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path


try:
    # Create a web server and define the handler to manage the
    # incoming request
    ip_addr = getMyIP()
    print ip_addr
    server = HTTPServer((ip_addr, PORT_NUMBER), simpleHttpServerHander)
    print 'Started httpserver on IP %s port %d' % (ip_addr, PORT_NUMBER)

    # Wait forever for incoming htto requests
    server.serve_forever()

except KeyboardInterrupt:
    print '^C received, shutting down the web server'
    server.socket.close()
