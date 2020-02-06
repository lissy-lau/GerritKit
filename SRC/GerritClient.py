#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Lissy Lau <lissy.lau@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#
# GerritClient
#
# This module provides classes for gerrit client related operations
#

__version__ = '0.1'
__author__ = 'Lissy Lau <lissy.lau@gmail.com>'

import json
import os
import shutil
import stat
import errno
import ConfigParser
import sys
import time
import git
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests.cookies import RequestsCookieJar
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from paramiko import AutoAddPolicy, SSHClient, SSHConfig, ProxyCommand
import logging

from GerritDefaultConfig import *

reload(sys)
sys.setdefaultencoding('utf-8')
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logger = logging.getLogger('GerritLogger')

GERRIT_REST_HDR = ")]}'\n"
GERRIT_AUTH_PREFIX = 'a/'

MIN_GERRIT_VERSION = '2.7'

SRV_TYPE_UNKNOWN = 0
SRV_TYPE_SSH = 1
SRV_TYPE_REST = 2

DEFAULT_SSH_PORT = '29418'
DEFAULT_HTTPS_PORT = '443'

AUTH_TYPE_NONE = 0
AUTH_TYPE_HTTP_BASIC = 1
AUTH_TYPE_HTTP_DIGEST = 2
AUTH_TYPE_HTTP_COOKIE = 3

HTTP_CONTINUE = 100
HTTP_SWITCHING_PROTOCOLS = 101
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NON_AUTHORITATIVE_INFO = 203
HTTP_NO_CONTENT = 204
HTTP_RESET_CONTENT = 205
HTTP_PARTIAL_CONTENT = 206
HTTP_MULTIPLE_CHOICES = 300
HTTP_MOVED_PERMANENTLY = 301
HTTP_FOUND = 302
HTTP_SEE_OTHER = 303
HTTP_NOT_MODIFIED = 304
HTTP_USE_PROXY = 305
HTTP_TEMPORARY_REDIRECT = 307
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_NOT_ACCEPTABLE = 406
HTTP_PROXY_AUTHENTICATION_REQUIRED = 407
HTTP_REQUEST_TIMEOUT = 408
HTTP_CONFLICT = 409
HTTP_GONE = 410
HTTP_LENGTH_REQUIRED = 411
HTTP_PRECONDITION_FAILED = 412
HTTP_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_REQUEST_URI_TOO_LARGE = 414
HTTP_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_REQUESTED_RANGE_NOT_SATISFIABLE = 416
HTTP_EXPECTATION_FAILED = 417
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_NOT_IMPLEMENTED = 501
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504
HTTP_VERSION_NOT_SUPPORTED = 505


class GerritSSHClientException(Exception):
    pass


class GerritRESTClientException(Exception):
    pass


class GerritClientException(Exception):
    pass

def on_path_error(func, path, exc_info):
    exc_value = exc_info[1]
    if func in (os.rmdir, os.remove) and exc_value.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        func(path)
    else:
        raise

class GerritSSHClient():

    @classmethod
    def run_gerrit_cmd(cls, server, cmd):

        gerrit_cmd = 'gerrit ' + cmd

        return run_ssh_cmd(server, gerrit_cmd)


    @classmethod
    def get_server_port(cls, server):

        ret_code = 0
        res_str = ''
        port = -1

        if server.has_key('Proxy'):
            proxies = {'http': server['Proxy'], 'https': server['Proxy']}
        else:
            proxies = None

        cmd = 'https://%s/ssh_info' % server['URL']

        ret_code, res = http_get(cmd, proxies = proxies)
        if ret_code == HTTP_OK:
            ret_code = 0
        elif ret_code == HTTP_NOT_FOUND:
            logger.debug('Retry with HTTP')
            cmd = 'http://%s/ssh_info' % server['URL']
            ret_code, res = http_get(cmd, proxies = proxies)
            if ret_code == HTTP_OK:
                ret_code = 0
            else:
                return ret_code, 'Failed to get SSH info', port
        else:
            return ret_code, 'Failed to get SSH info', port

        ssh_info = res.split()
        if ssh_info[0] != server['URL']:
            return 255, 'Failed to get SSH info', port

        port = ssh_info[1]
        res_str = res_str + ('Gerrit Server: ssh://%s:%s\n' % (server['URL'], port,))

        return ret_code, res_str, port


    @classmethod
    def get_server_version(cls, server):

        ret_code = 0
        res_str = ''
        full_version = MIN_GERRIT_VERSION
        port = -1

        ret_code, res_str, port = cls.get_server_port(server)
        if ret_code != 0:
            return ret_code, res_str, full_version

        server['Port'] = port

        res = cls.run_gerrit_cmd(server, 'version')
        full_version = res[0].split()[2]
        res_str = res_str + 'Gerrit Version: %s\n' % full_version

        return ret_code, res_str, full_version


    @classmethod
    def get_server_labels_from_git(cls, server):

        labels = []
        ret_code = 0
        res_str = ''
        port = -1

        try:
            shutil.rmtree(TMP_DIR, ignore_errors = False, onerror = on_path_error)
        except OSError:
            pass

        if server['Type'] == SRV_TYPE_SSH:
            port = server['Port']
        else:
            ret_code, res_str, port = cls.get_server_port(server)
            if ret_code != 0:
                return ret_code, res_str, labels

        if server.has_key('Proxy'):
            cmd = 'git config --global http.proxy %s' % server['Proxy']
            git.Git().execute(cmd.split())
            all_project_path = 'https://%s/All-Projects' % server['URL']
        else:
            if server.has_key('Username'):
                all_project_path = 'ssh://%s@%s:%s/All-Projects' % (server['Username'], server['URL'], port,)
            else:
                all_project_path = 'ssh://%s:%s/All-Projects' % (server['URL'], port,)

        git.Repo.clone_from(all_project_path, TMP_DIR)

        if server.has_key('Proxy'):
            cmd = 'git config --global --unset http.proxy'
            git.Git().execute(cmd.split())

        config = ConfigParser.ConfigParser()
        project_config_file = os.path.join(TMP_DIR, 'project.config')
        try:
            config.read(project_config_file)
        except ConfigParser.ParsingError:
            pass
        sessions = config.sections()
        for session in sessions:
            names = session.split()
            if names[0] == 'label':
                label_name = names[1].strip('"')
                labels.append(label_name)
                res_str = res_str + 'Label: %s\n' % label_name

        try:
            shutil.rmtree(TMP_DIR, ignore_errors = False, onerror = on_path_error)
        except:
            pass

        return ret_code, res_str, labels


    @classmethod
    def get_server_labels(cls, server):

        return cls.get_server_labels_from_git(server)


    @classmethod
    def query(cls, server, query, columns):

        gerrits = []

        lines = cls.run_gerrit_cmd(server, 'query %s --current-patch-set --submit-records --format=JSON' % query)
        jsons = [json.loads(line) for line in lines if line]
        jsons.pop()

        for gerrit_json in jsons:
            gerrit = dict()
            cls._parse_gerrit(gerrit, gerrit_json, columns)
            gerrits.append(gerrit)

        logger.debug('DONE')

        return gerrits


    @classmethod
    def gerrit(cls, server, gerrit_id, columns):

        gerrit = dict()

        lines = cls.run_gerrit_cmd(server, 'query --current-patch-set --submit-records --format=JSON --commit-message --patch-sets --dependencies --files --crs --task--applicable %s' % gerrit_id)
        jsons = [json.loads(line) for line in lines if line]
        cls._parse_gerrit(gerrit, jsons[0], columns)

        logger.debug('DONE')

        return gerrit


    @classmethod
    def _parse_gerrit(cls, gerrit, jsons, columns):

        for col in columns:
            if col == 'ID':
                gerrit[col] = jsons["number"]
            elif col == 'Subject':
                gerrit[col] = jsons['subject']
            elif col == 'Owner':
                gerrit[col] = jsons['owner']['name']
            elif col == 'Author':
                gerrit[col] = jsons['currentPatchSet']['author']['name']
            elif col == 'Committer':
                gerrit[col] = jsons['currentPatchSet']['uploader']['name']
            elif col == 'Status':
                gerrit[col] = jsons['status']
            elif col == 'Project':
                gerrit[col] = jsons['project']
            elif col == 'Branch':
                gerrit[col] = jsons['branch']
            elif col == 'Created-On':
                timeArray = time.localtime(jsons['createdOn'])
                gerrit[col] = time.strftime('%Y-%m-%d %H:%M:%S', timeArray)
            elif col == 'Updated-On':
                timeArray = time.localtime(jsons['lastUpdated'])
                gerrit[col] = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
            elif col == 'Topic' and jsons.has_key('topic'):
                gerrit[col] = jsons['topic']
            elif col == 'Insertions':
                gerrit[col] = jsons['currentPatchSet']['sizeInsertions']
            elif col == 'Deletions':
                gerrit[col] = jsons['currentPatchSet']['sizeDeletions']
            else:
                labels = jsons['submitRecords'][0]['labels']
                for label in labels:
                    if label['label'] == col:
                        gerrit[col] = label['status']

        return


class GerritRESTClient():

    @classmethod
    def get_server_version(cls, server):

        ret_code = 0
        res_str = ''
        full_version = MIN_GERRIT_VERSION

        ret_code, full_version = cls.get(server, 'config/server/version')
        if ret_code == HTTP_OK:
            full_version = full_version.strip('"')
            res_str = 'Gerrit Version: %s\n' % full_version
        else:
            full_version = MIN_GERRIT_VERSION
            res_str = 'Configuration not found, set version to %s\n' % MIN_GERRIT_VERSION

        ret_code = 0

        return ret_code, res_str, full_version


    @classmethod
    def get_server_labels(cls, server):

        ret_code = 0
        res_str = ''
        labels = []

        ret_code, lines = cls.get(server, 'projects/All-Projects')
        if ret_code == HTTP_OK:
            jsons = json.loads(lines)
            if jsons.has_key('labels'):
                server_labels = jsons['labels']
                for label in server_labels:
                    labels.append(label)
                    res_str = res_str + 'Label: %s\n' % label
            ret_code = 0
        # Hack for gerrit-review.googlesource.com for which All-Projects is not present
        elif ret_code == HTTP_NOT_FOUND:
            ret_code, lines = cls.get(server, 'projects/gerrit')
            if ret_code == HTTP_OK:
                jsons = json.loads(lines)
                if jsons.has_key('labels'):
                    server_labels = jsons['labels']
                    for label in server_labels:
                        labels.append(label)
                        res_str = res_str + 'Label: %s\n' % label
                ret_code = 0

        return ret_code, res_str, labels


    @classmethod
    def query(cls, server, query, columns):

        gerrits = []
        params = 'q=%s&o=LABELS&o=DETAILED_ACCOUNTS&o=CURRENT_REVISION&o=CURRENT_COMMIT&o=CURRENT_FILES' % query

        logger.debug('Query: %s' % params)

        ret_code, lines = cls.get(server, 'changes/', params = params)
        if ret_code == HTTP_OK:
            jsons = json.loads(lines)
            for gerrit_json in jsons:
                gerrit = dict()
                cls._parse_gerrit(gerrit, gerrit_json, columns)
                gerrits.append(gerrit)

        logger.debug('DONE')

        return gerrits


    @classmethod
    def gerrit(cls, server, gerrit_id, columns):

        gerrit = dict()

        logger.debug('DONE')

        return gerrit


    @classmethod
    def _parse_gerrit(cls, gerrit, jsons, columns):

        current_patch_set_id = jsons['current_revision']
        current_patch_set = jsons['revisions'][current_patch_set_id]
        lines_inserted = 0
        lines_deleted = 0
        for filename in current_patch_set['files']:
            if current_patch_set['files'][filename].has_key('lines_inserted'):
                lines_inserted = lines_inserted + current_patch_set['files'][filename]['lines_inserted']
            if current_patch_set['files'][filename].has_key('lines_deleted'):
                lines_deleted = lines_deleted + current_patch_set['files'][filename]['lines_deleted']

        for col in columns:
            if col == 'ID':
                gerrit[col] = jsons["_number"]
            elif col == 'Subject':
                gerrit[col] = jsons['subject']
            elif col == 'Owner':
                gerrit[col] = jsons['owner']['name']
            elif col == 'Author':
                gerrit[col] = current_patch_set['commit']['author']['name']
            elif col == 'Committer':
                gerrit[col] = current_patch_set['commit']['committer']['name']
            elif col == 'Status':
                gerrit[col] = jsons['status']
            elif col == 'Project':
                gerrit[col] = jsons['project']
            elif col == 'Branch':
                gerrit[col] = jsons['branch']
            elif col == 'Created-On':
                gerrit[col] = jsons['created']
            elif col == 'Updated-On':
                gerrit[col] = jsons['updated']
            elif col == 'Topic' and jsons.has_key('topic'):
                gerrit[col] = jsons['topic']
            elif col == 'Insertions':
                gerrit[col] = lines_inserted
            elif col == 'Deletions':
                gerrit[col] = lines_deleted
            else:
                labels = jsons['labels']
                for label in labels:
                    if label == col:
                        for key in jsons['labels'][label]:
                            if key != 'value' and key != 'optional':
                                gerrit[col] = key

        return


    @classmethod
    def get(cls, server, endpoint, params = None):

        endpoint = endpoint.lstrip('/')
        logger.debug('REQUEST: endpoint = %s' % endpoint)

        if server.has_key('AuthType'):
            if server['AuthType'] == AUTH_TYPE_HTTP_BASIC:
                endpoint = GERRIT_AUTH_PREFIX + endpoint
                auth = HTTPBasicAuth(server['Username'], server['Password'])
                cookies = None
            elif server['AuthType'] == AUTH_TYPE_HTTP_DIGEST:
                endpoint = GERRIT_AUTH_PREFIX + endpoint
                auth = HTTPDigestAuth(server['Username'], server['Password'])
                cookies = None
            elif server['AuthType'] == AUTH_TYPE_HTTP_COOKIE:
                endpoint = GERRIT_AUTH_PREFIX + endpoint
                auth = None
                cookies = RequestsCookieJar()
                cookies.set(server['Username'], server['Password'],
                            domain = server['URL'], path = '/')
        else:
            auth = None
            cookies = None

        headers = {'Content-Type': 'application/json'}
        if server.has_key('Proxy'):
            proxies = {'http': server['Proxy'], 'https': server['Proxy']}
        else:
            proxies = None

        cmd = 'https://%s:%s/%s' % (server['URL'], server['Port'], endpoint,)

        return http_get(cmd, headers = headers, proxies = proxies,
                        auth = auth, cookies = cookies, params = params)


class GerritClient():

    @classmethod
    def get_server_version(cls, server):

        ret_code = 0
        res_str = ''
        full_version = ''

        if server['Type'] == SRV_TYPE_SSH:
            ret_code, res_str, full_version = GerritSSHClient.get_server_version(server)
        elif server['Type'] == SRV_TYPE_REST:
            ret_code, res_str, full_version = GerritRESTClient.get_server_version(server)
            if ret_code != 0:
                return ret_code, res_str
        else:
            return 255, 'Un-supported server type %d' % server['Type']

        logger.debug('Full Version: %s' % full_version)

        major_version = full_version.split('-')[0]
        versions = major_version.split('.')
        server['Version'] = versions[0] + '.' + versions[1]

        return ret_code, res_str


    @classmethod
    def get_server_labels(cls, server):

        ret_code = 0
        res_str = ''
        labels = []

        if server['Type'] == SRV_TYPE_SSH:
            ret_code, res_str, labels = GerritSSHClient.get_server_labels(server)
        elif server['Type'] == SRV_TYPE_REST:
            major_version = int(server['Version'].split('.')[0])
            minor_version = int(server['Version'].split('.')[1])
            if major_version == 2 and minor_version < 15:
                ret_code, res_str, labels = GerritSSHClient.get_server_labels_from_git(server)
            else:
                ret_code, res_str, labels = GerritRESTClient.get_server_labels(server)
        else:
            return 255, 'Un-supported server type %d' % server['Type']

        if len(labels) > 0:
            server['Labels'] = labels

        return ret_code, res_str


    @classmethod
    def query(cls, server, query, columns):

        gerrits = []

        if server['Type'] == SRV_TYPE_SSH:
            query_str = ' '.join(query)
            gerrits = GerritSSHClient.query(server, query_str, columns)
        elif server['Type'] == SRV_TYPE_REST:
            query_str = '+'.join(query)
            gerrits = GerritRESTClient.query(server, query_str, columns)
        else:
            logger.error('Un-supported server type %d' % server['Type'])

        return gerrits


    @classmethod
    def gerrit(cls, server, gerrit_id, columns):

        gerrit = dict()

        if server['Type'] == SRV_TYPE_SSH:
            gerrit = GerritSSHClient.gerrit(server, gerrit_id, columns)
        elif server['Type'] == SRV_TYPE_REST:
            gerrit = GerritRESTClient.gerrit(server, gerrit_id, columns)
        else:
            logger.error('Un-supported server type %d' % server['Type'])

        return gerrit


def run_ssh_cmd(server, cmd):

    logger.debug('CMD: %s' % cmd)

    if server.has_key('Username'):
        username = server['Username']
        password = server['Password']
    else:
        username = None
        password = None

    client = SSHClient()
    client.load_system_host_keys()
    client.connect(hostname = server['URL'], port = int(server['Port']),
                   username = username, password = password)
    stdin, stdout, stderr = client.exec_command(cmd)

    return stdout.read().splitlines()


def http_get(cmd, headers = None, proxies = None, auth = None, cookies = None, params = None):

    logger.debug('REQUEST: %s' % cmd)

    res = requests.get(cmd, headers = headers, proxies = proxies, auth = auth,
                       cookies = cookies, params = params, verify = False)

    logger.debug('RESPONSE: url = %s, status = %d' % (res.url, res.status_code,))

    ret_code = res.status_code
    res_str = (res.content.lstrip(GERRIT_REST_HDR)).strip()

    return ret_code, res_str

