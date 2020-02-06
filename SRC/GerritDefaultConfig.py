#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Lissy Lau <lissy.lau@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#
# GerritDefaultConfig
#
# This module defines default configuration of GerritKit
#

__version__ = '0.1'
__author__ = 'Lissy Lau <lissy.lau@gmail.com>'

import os
import sys

env_dict = os.environ
if sys.platform == 'win32':
    ROOT_DIR = os.path.join(env_dict['USERPROFILE'], '.GerritKit')
    TMP_DIR = os.path.join(env_dict['TMP'], 'GerritKit')
    MAIN_GEOMETRY = '800x600'
    SERVER_LIST_GEOMETRY = '350x350'
    PREFERENCES_GEOMETRY = '500x250'
    SERVER_PROFILE_GEOMETRY = '700x500'
    QUERY_PROFILE_GEOMETRY = '800x750'
else:
    ROOT_DIR = os.path.join(env_dict['HOME'], '.GerritKit')
    TMP_DIR = '/tmp/GerritKit'
    MAIN_GEOMETRY = '800x600'
    SERVER_LIST_GEOMETRY = '350x300'
    PREFERENCES_GEOMETRY = '500x250'
    SERVER_PROFILE_GEOMETRY = '700x500'
    QUERY_PROFILE_GEOMETRY = '800x700'

CONFIG_DIR = os.path.join(ROOT_DIR, 'config')
CONFIG_XML = os.path.join(CONFIG_DIR, 'config.xml')

DEFAULT_QUERY_DIR = os.path.join(ROOT_DIR, 'query')

DEFAULT_LOG_DIR = os.path.join(ROOT_DIR, 'log')
DEFAULT_LOG_FILE = 'gerrit.log'
DEFAULT_MAX_LOG_SIZE = 2 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 3

default_servers_config = [
    {'Name':'Gerrit (SSH)',     'URL':'gerrit-review.googlesource.com',   'Port':'29418', 'Type':'1', 'Version':'3.1'},
    {'Name':'Gerrit (REST)',    'URL':'gerrit-review.googlesource.com',   'Port':'443',   'Type':'2', 'Version':'3.1'}
]

default_columns_config = [
    {'Name':'ID',         'Display':1, 'Width':50},
    {'Name':'Subject',    'Display':1, 'Width':100},
    {'Name':'Owner',      'Display':1, 'Width':50},
    {'Name':'Author',     'Display':0, 'Width':50},
    {'Name':'Committer',  'Display':0, 'Width':50},
    {'Name':'Status',     'Display':1, 'Width':50},
    {'Name':'Project',    'Display':1, 'Width':100},
    {'Name':'Branch',     'Display':1, 'Width':100},
    {'Name':'Created-On', 'Display':0, 'Width':100},
    {'Name':'Updated-On', 'Display':1, 'Width':100},
    {'Name':'Topic',      'Display':0, 'Width':100},
    {'Name':'Insertions', 'Display':0, 'Width':50},
    {'Name':'Deletions',  'Display':0, 'Width':50}
]

default_labels_config = [
    {'Name':'Verified',    'Display':1, 'Width':100},
    {'Name':'Code-Review', 'Display':1, 'Width':100}
]

