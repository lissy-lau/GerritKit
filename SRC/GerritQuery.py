#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Lissy Lau <lissy.lau@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#
# GerritQuery
#
# This module provides classes for gerrit query related operations
#

__version__ = '0.1'
__author__ = 'Lissy Lau <lissy.lau@gmail.com>'

import os
import sys
import copy
import csv
import codecs
import logging
import xml.dom.minidom as DOM
import Tkinter as tk
import ttk as ttk
from FileDialog import *

from GerritDefaultConfig import *
from GerritServer import *
from GerritClient import *

reload(sys)
sys.setdefaultencoding('utf-8')
logger = logging.getLogger('GerritLogger')

FILE_TYPE_UNKNOWN = 0
FILE_TYPE_CSV = 1
FILE_TYPE_XML = 2

class GerritQueryException(Exception):
    pass


class GerritQuery():

    def __init__(self, name, servers, query_file = None):

        self.name = name
        self.servers = servers
        self.server = None
        self.server_name = None
        self.columns_config = None
        self.query = None

        if query_file:
            try:
                self.query_xml = DOM.parse(query_file)
                self.read_configuraion_file()
            except IOError:
                raise GerritQueryException('File not found')
        else:
            self.init_default_configuraion()

        return


    def init_default_configuraion(self):

        self.query_xml = DOM.Document()
        root_node = self.query_xml.createElement('Query')
        self.query_xml.appendChild(root_node)
        root_node.setAttribute('Name', self.name)

        return


    def read_configuraion_file(self):

        query = dict()
        columns = []
        root_node = self.query_xml.getElementsByTagName('Query')[0]
        nodes = root_node.getElementsByTagName('Filter')
        for filter in nodes:
            name = filter.getAttribute('Name')
            value = filter.getAttribute('Value')
            query[name] = value
        nodes = root_node.getElementsByTagName('Column')
        for column in nodes:
            col = dict()
            col['Name'] = column.getAttribute('Name')
            col['Display'] = int(column.getAttribute('Display'))
            col['Width'] = int(column.getAttribute('Width'))
            columns.append(col)
        self.configure(name = root_node.getAttribute('Name'),
                       server_name = root_node.getAttribute('Server'),
                       query = query,
                       columns_config = columns,
                       update_xml = False)

        return

    def configure(self, name = None, server_name = None, query = None,
                  columns_config = None, update_xml = True):

        root_node = self.query_xml.getElementsByTagName('Query')[0]

        if name:
            self.name = name
            if update_xml:
                root_node.setAttribute('Name', self.name)
        if server_name:
            index = self.servers.find(server_name)
            if index < 0:
                raise GerritQueryException('Server %s is not found' % server_name)
            self.server = self.servers[index]
            if update_xml:
                root_node.setAttribute('Server', server_name)
        if query:
            self.query = query
            if update_xml:
                filter_node = root_node.getElementsByTagName('Filters')
                if len(filter_node) > 0:
                    root_node.removeChild(filter_node[0])
                filter_node = self.query_xml.createElement('Filters')
                root_node.appendChild(filter_node)
                for key in self.query.keys():
                    filter = self.query_xml.createElement('Filter')
                    filter.setAttribute('Name', key)
                    filter.setAttribute('Value', self.query[key])
                    filter_node.appendChild(filter)
        if columns_config:
            self.columns_config = columns_config
            if update_xml:
                column_node = root_node.getElementsByTagName('Columns')
                if len(column_node) > 0:
                    root_node.removeChild(column_node[0])
                column_node = self.query_xml.createElement('Columns')
                root_node.appendChild(column_node)
                for col in self.columns_config:
                    column = self.query_xml.createElement('Column')
                    column.setAttribute('Name', col['Name'])
                    column.setAttribute('Display', str(col['Display']))
                    column.setAttribute('Width', str(col['Width']))
                    column_node.appendChild(column)

        return


    def get_columns(self):

        columns = []

        for col in self.columns_config:
            columns.append(col['Name'])

        return columns


    def run(self):

        if not self.server:
            raise GerritQueryException('Server is not configured')
        if not self.query:
            raise GerritQueryException('Query filters are not configured')
        if not self.columns_config:
            raise GerritQueryException('Query fields are not configured')

        query = []
        for key in self.query.keys():
            if key == 'user-defined':
                query = self.query[key].split(' ')
            elif key == 'starred':
                query.append('is:starred')
            elif key == 'watched':
                query.append('is:watched')
            elif key == 'draft':
                query.append('is:draft')
            elif key == 'mergeable':
                query.append('is:mergeable')
            else:
                filter = key + ':{' + self.query[key] + '}'
                query.append(filter)
			
        return GerritClient.query(self.server, query,
                                  columns = self.get_columns())


    def gerrit(self, gerrit_id):

        if not self.server:
            raise GerritQueryException('Server is not configured')
        if not self.columns_config:
            raise GerritQueryException('Query fields are not configured')

        return GerritClient.gerrit(self.server, gerrit_id,
                                   columns = self.get_columns())


    def save(self, file_name):

        f = open(file_name, 'w+')
        dom_str = self.query_xml.toprettyxml(encoding = 'utf-8')
        dom_str = os.linesep.join([s for s in dom_str.splitlines() if s.strip()])
        f.write(dom_str)
        f.close()
        logger.debug('File %s is saved' % file_name)

        return


class QueryProfile():

    def __init__(self, parent, top, query, servers, fix_columns_config):

        self.parent = parent
        self.top = top
        self.top.geometry(QUERY_PROFILE_GEOMETRY)
        self.top.title('Query - %s' % query.name)
        self.query = query
        self.servers = servers
        self.fix_columns_config = fix_columns_config

        self.init_configuration()
        self.init_layout()

        return


    def init_configuration(self):

        self.query_name = tk.StringVar()
        self.server_name = tk.StringVar()
        self.local_columns_config = []
        self.local_columns_chkbox = []
        self.local_columns_entry = []

        self.query_name.set(self.query.name)
        if self.query.server:
            self.server = self.query.server
        else:
            self.server = self.servers[0]

        self.server_name.set(self.server['Name'])

        if self.query.columns_config:
            for col in self.query.columns_config:
                local_col = dict()
                local_col['Name'] = tk.StringVar()
                local_col['Name'].set(col['Name'])
                local_col['Display'] = tk.IntVar()
                local_col['Display'].set(col['Display'])
                local_col['Width'] = tk.IntVar()
                local_col['Width'].set(col['Width'])
                self.local_columns_config.append(local_col)
        else:
            self.update_server_column_config()

        self.filter_type = tk.IntVar()
        self.filter_type.set(0)

        self.local_labels_value = []
        self.local_labels_chkbox = []
        self.local_labels_entry = []

        self.select_owner = tk.IntVar()
        self.select_owner.set(0)
        self.query_owner = tk.StringVar()
        self.select_author = tk.IntVar()
        self.select_author.set(0)
        self.query_author = tk.StringVar()
        self.select_committer = tk.IntVar()
        self.select_committer.set(0)
        self.query_committer = tk.StringVar()
        self.select_reviewer = tk.IntVar()
        self.select_reviewer.set(0)
        self.query_reviewer = tk.StringVar()
        self.select_status = tk.IntVar()
        self.select_status.set(0)
        self.query_status = tk.StringVar()
        self.select_project = tk.IntVar()
        self.select_project.set(0)
        self.query_project = tk.StringVar()
        self.select_branch = tk.IntVar()
        self.select_branch.set(0)
        self.query_branch = tk.StringVar()
        self.select_age = tk.IntVar()
        self.select_age.set(0)
        self.query_age = tk.StringVar()
        self.select_before = tk.IntVar()
        self.select_before.set(0)
        self.query_before = tk.StringVar()
        self.select_after = tk.IntVar()
        self.select_after.set(0)
        self.query_after = tk.StringVar()
        self.select_change = tk.IntVar()
        self.select_change.set(0)
        self.query_change = tk.StringVar()
        self.select_commit = tk.IntVar()
        self.select_commit.set(0)
        self.query_commit = tk.StringVar()
        self.select_message = tk.IntVar()
        self.select_message.set(0)
        self.query_message = tk.StringVar()
        self.select_comment = tk.IntVar()
        self.select_comment.set(0)
        self.query_comment = tk.StringVar()
        self.select_file = tk.IntVar()
        self.select_file.set(0)
        self.query_file = tk.StringVar()
        self.select_limit = tk.IntVar()
        self.select_limit.set(0)
        self.query_limit = tk.StringVar()
        self.select_starred = tk.IntVar()
        self.select_starred.set(0)
        self.select_watched = tk.IntVar()
        self.select_watched.set(0)
        self.select_draft = tk.IntVar()
        self.select_draft.set(0)
        self.select_mergeable = tk.IntVar()
        self.select_mergeable.set(0)
        self.user_query = tk.StringVar()

        if self.query.query:
            if self.query.query.has_key('user-defined'):
                self.filter_type.set(1)
                self.user_query.set(self.query.query['user-defined'])
            else:
                if self.query.query.has_key('owner'):
                    self.select_owner.set(1)
                    self.query_owner.set(self.query.query['owner'])
                if self.query.query.has_key('author'):
                    self.select_author.set(1)
                    self.query_author.set(self.query.query['author'])
                if self.query.query.has_key('committer'):
                    self.select_committer.set(1)
                    self.query_committer.set(self.query.query['committer'])
                if self.query.query.has_key('reviewer'):
                    self.select_reviewer.set(1)
                    self.query_reviewer.set(self.query.query['reviewer'])
                if self.query.query.has_key('status'):
                    self.select_status.set(1)
                    self.query_status.set(self.query.query['status'])
                if self.query.query.has_key('project'):
                    self.select_project.set(1)
                    self.query_project.set(self.query.query['project'])
                if self.query.query.has_key('branch'):
                    self.select_branch.set(1)
                    self.query_branch.set(self.query.query['branch'])
                if self.query.query.has_key('age'):
                    self.select_age.set(1)
                    self.query_age.set(self.query.query['age'])
                if self.query.query.has_key('before'):
                    self.select_before.set(1)
                    self.query_before.set(self.query.query['before'])
                if self.query.query.has_key('after'):
                    self.select_after.set(1)
                    self.query_after.set(self.query.query['after'])
                if self.query.query.has_key('change'):
                    self.select_change.set(1)
                    self.query_change.set(self.query.query['change'])
                if self.query.query.has_key('commit'):
                    self.select_commit.set(1)
                    self.query_commit.set(self.query.query['commit'])
                if self.query.query.has_key('message'):
                    self.select_message.set(1)
                    self.query_message.set(self.query.query['message'])
                if self.query.query.has_key('comment'):
                    self.select_comment.set(1)
                    self.query_comment.set(self.query.query['comment'])
                if self.query.query.has_key('file'):
                    self.select_file.set(1)
                    self.query_file.set(self.query.query['file'])
                if self.query.query.has_key('limit'):
                    self.select_limit.set(1)
                    self.query_limit.set(self.query.query['limit'])
                if self.query.query.has_key('starred'):
                    self.select_starred.set(1)
                if self.query.query.has_key('watched'):
                    self.select_watched.set(1)
                if self.query.query.has_key('draft'):
                    self.select_draft.set(1)
                if self.query.query.has_key('mergeable'):
                    self.select_mergeable.set(1)
		
        return


    def update_server_column_config(self):

        self.local_columns_config = []

        for col in self.fix_columns_config:
            local_col = dict()
            local_col['Name'] = tk.StringVar()
            local_col['Name'].set(col['Name'])
            local_col['Display'] = tk.IntVar()
            local_col['Display'].set(col['Display'])
            local_col['Width'] = tk.IntVar()
            local_col['Width'].set(col['Width'])
            self.local_columns_config.append(local_col)
            logger.debug('Add column %s' % local_col['Name'].get())

        if self.server.has_key('Labels'):
            labels = self.server['Labels']
            for label in labels:
                local_col = dict()
                local_col['Name'] = tk.StringVar()
                local_col['Name'].set(label)
                local_col['Display'] = tk.IntVar()
                local_col['Display'].set(1)
                local_col['Width'] = tk.IntVar()
                local_col['Width'].set(100)
                self.local_columns_config.append(local_col)
                logger.debug('Add column %s' % local_col['Name'].get())

        return


    def init_layout(self):

        frm_basic = tk.LabelFrame(self.top, text = 'Basic Setting',
                                  borderwidth = 2, relief = tk.GROOVE,
                                  padx = 5, pady = 5)

        label_query_name = tk.Label(frm_basic, text = 'Name:')
        label_query_name.grid(row = 0, column = 0, sticky = tk.W,
                              padx = 5, pady = 2)
        entry_query_name = tk.Entry(frm_basic, show = None, width = 20,
                                    textvariable = self.query_name)
        entry_query_name.grid(row = 0, column = 1, sticky = tk.W,
                              padx = 5, pady = 2)

        label_server_name = tk.Label(frm_basic, text = 'Server:')
        label_server_name.grid(row = 0, column = 2, sticky = tk.W,
                               padx = 5, pady = 2)
        self.combo_server_name = ttk.Combobox(frm_basic, width = 15,
                                              postcommand = self.init_server_list,
                                              textvariable = self.server_name)
        self.combo_server_name.bind("<<ComboboxSelected>>", self.update_server)
        self.combo_server_name.grid(row = 0, column = 3, sticky = tk.W,
                                    pady = 2)

        frm_basic.pack(anchor = tk.W, side = tk.TOP, fill = tk.X,
                       padx = 10, pady = 5)

        self.frm_column = tk.LabelFrame(self.top, text = 'Query Fields Setting',
                                        borderwidth = 2, relief = tk.GROOVE,
                                        padx = 5, pady = 5)

        self.update_columns_display()

        self.frm_column.pack(anchor = tk.W, side = tk.TOP, fill = tk.BOTH,
                             padx = 10, pady = 5)

        frm_query = tk.LabelFrame(self.top, text = 'Query Filters Setting',
                                  borderwidth = 2, relief = tk.GROOVE,
                                  padx = 5, pady = 5)

        # pre-defined
        radio_pre_defined = tk.Radiobutton(frm_query,
                                           text = 'Pre-defined',
                                           variable = self.filter_type,
                                           value = 0,
                                           command = self.update_filter_display)
        radio_pre_defined.grid(row = 0, column = 0, columnspan = 3,
                               sticky = tk.W, padx = 5, pady = 2)

        # owner
        self.chkbox_owner = tk.Checkbutton(frm_query, text = 'Owner:',
                                           variable = self.select_owner,
                                           command = self.update_filter_display)
        self.chkbox_owner.grid(row = 1, column = 1, sticky = tk.W,
                               padx = 5, pady = 2)
        self.entry_owner = tk.Entry(frm_query, show = None, width = 15,
                                    textvariable = self.query_owner)
        self.entry_owner.grid(row = 1, column = 2, sticky = tk.W,
                              padx = 5, pady = 2)

        # author(>=2.12)
        self.chkbox_author = tk.Checkbutton(frm_query, text = 'Author:',
                                            variable = self.select_author,
                                            command = self.update_filter_display)
        self.chkbox_author.grid(row = 1, column = 3, sticky = tk.W,
                                padx = 5, pady = 2)
        self.entry_author = tk.Entry(frm_query, show = None, width = 15,
                                     textvariable = self.query_author)
        self.entry_author.grid(row = 1, column = 4, sticky = tk.W,
                               padx = 5, pady = 2)

        # committer(>=2.12)
        self.chkbox_committer = tk.Checkbutton(frm_query, text = 'Committer:',
                                               variable = self.select_committer,
                                               command = self.update_filter_display)
        self.chkbox_committer.grid(row = 1, column = 5, sticky = tk.W,
                                   padx = 5, pady = 2)
        self.entry_committer = tk.Entry(frm_query, show = None, width = 15,
                                        textvariable = self.query_committer)
        self.entry_committer.grid(row = 1, column = 6, sticky = tk.W,
                                  padx = 5, pady = 2)

        # reviewer
        self.chkbox_reviewer = tk.Checkbutton(frm_query, text = 'Reviewer:',
                                              variable = self.select_reviewer,
                                              command = self.update_filter_display)
        self.chkbox_reviewer.grid(row = 2, column = 1, sticky = tk.W,
                                  padx = 5, pady = 2)
        self.entry_reviewer = tk.Entry(frm_query, show = None, width = 15,
                                       textvariable = self.query_reviewer)
        self.entry_reviewer.grid(row = 2, column = 2, sticky = tk.W,
                                 padx = 5, pady = 2)

        # status:open status:closed status:merged status:abandoned
        # status:reviewed status:submitted
        self.chkbox_status = tk.Checkbutton(frm_query, text = 'Status:',
                                            variable = self.select_status,
                                            command = self.update_filter_display)
        self.chkbox_status.grid(row = 2, column = 3, sticky = tk.W,
                                padx = 5, pady = 2)
        self.combo_status = ttk.Combobox(frm_query, width = 15,
                                         textvariable = self.query_status)
        self.combo_status['values'] = ('open', 'closed', 'merged', 'abandoned',
                                       'reviewed', 'submitted')
        self.combo_status.grid(row = 2, column = 4, sticky = tk.W,
                               padx = 5, pady = 2)

        # project
        self.chkbox_project = tk.Checkbutton(frm_query, text = 'Project:',
                                             variable = self.select_project,
                                             command = self.update_filter_display)
        self.chkbox_project.grid(row = 3, column = 1, sticky = tk.W,
                                 padx = 5, pady = 2)
        self.entry_project = tk.Entry(frm_query, show = None, width = 15,
                                      textvariable = self.query_project)
        self.entry_project.grid(row = 3, column = 2, sticky = tk.W,
                                padx = 5, pady = 2)

        # branch
        self.chkbox_branch = tk.Checkbutton(frm_query, text = 'Branch:',
                                            variable = self.select_branch,
                                            command = self.update_filter_display)
        self.chkbox_branch.grid(row = 3, column = 3, sticky = tk.W,
                                padx = 5, pady = 2)
        self.entry_branch = tk.Entry(frm_query, show = None, width = 15,
                                     textvariable = self.query_branch)
        self.entry_branch.grid(row = 3, column = 4, sticky = tk.W,
                               padx = 5, pady = 2)

        # limit
        self.chkbox_limit = tk.Checkbutton(frm_query, text = 'Limit:',
                                           variable = self.select_limit,
                                           command = self.update_filter_display)
        self.chkbox_limit.grid(row = 3, column = 5, sticky = tk.W,
                               padx = 5, pady = 2)
        self.entry_limit = tk.Entry(frm_query, show = None, width = 15,
                                    textvariable = self.query_limit)
        self.entry_limit.grid(row = 3, column = 6, columnspan = 6,
                              sticky = tk.W, padx = 5, pady = 2)

        # age
        self.chkbox_age = tk.Checkbutton(frm_query, text = 'Age:',
                                         variable = self.select_age,
                                         command = self.update_filter_display)
        self.chkbox_age.grid(row = 4, column = 1, sticky = tk.W,
                             padx = 5, pady = 2)
        self.entry_age = tk.Entry(frm_query, show = None, width = 15,
                                  textvariable = self.query_age)
        self.entry_age.grid(row = 4, column = 2, sticky = tk.W,
                            padx = 5, pady = 2)

        # before(>=2.9)
        self.chkbox_before = tk.Checkbutton(frm_query, text = 'Before:',
                                            variable = self.select_before,
                                            command = self.update_filter_display)
        self.chkbox_before.grid(row = 4, column = 3, sticky = tk.W,
                                padx = 5, pady = 2)
        self.entry_before = tk.Entry(frm_query, show = None, width = 15,
                                     textvariable = self.query_before)
        self.entry_before.grid(row = 4, column = 4, sticky = tk.W,
                               padx = 5, pady = 2)

        # after(>=2.9)
        self.chkbox_after = tk.Checkbutton(frm_query, text = 'After:',
                                           variable = self.select_after,
                                           command = self.update_filter_display)
        self.chkbox_after.grid(row = 4, column = 5, sticky = tk.W,
                               padx = 5, pady = 2)
        self.entry_after = tk.Entry(frm_query, show = None, width = 15,
                                    textvariable = self.query_after)
        self.entry_after.grid(row = 4, column = 6, sticky = tk.W,
                              padx = 5, pady = 2)

        # change
        self.chkbox_change = tk.Checkbutton(frm_query, text = 'Change:',
                                            variable = self.select_change,
                                            command = self.update_filter_display)
        self.chkbox_change.grid(row = 5, column = 1, sticky = tk.W,
                                padx = 5, pady = 2)
        self.entry_change = tk.Entry(frm_query, show = None, width = 70,
                                     textvariable = self.query_change)
        self.entry_change.grid(row = 5, column = 2, columnspan = 6,
                               sticky = tk.W, padx = 5, pady = 2)

        # commit
        self.chkbox_commit = tk.Checkbutton(frm_query, text = 'Commit:',
                                            variable = self.select_commit,
                                            command = self.update_filter_display)
        self.chkbox_commit.grid(row = 6, column = 1, sticky = tk.W,
                                padx = 5, pady = 2)
        self.entry_commit = tk.Entry(frm_query, show = None, width = 70,
                                     textvariable = self.query_commit)
        self.entry_commit.grid(row = 6, column = 2, columnspan = 6,
                               sticky = tk.W, padx = 5, pady = 2)

        # message
        self.chkbox_message = tk.Checkbutton(frm_query, text = 'Message:',
                                             variable = self.select_message,
                                             command = self.update_filter_display)
        self.chkbox_message.grid(row = 7, column = 1, sticky = tk.W,
                                 padx = 5, pady = 2)
        self.entry_message = tk.Entry(frm_query, show = None, width = 70,
                                      textvariable = self.query_message)
        self.entry_message.grid(row = 7, column = 2, columnspan = 6,
                                sticky = tk.W, padx = 5, pady = 2)

        # comment(>=2.8)
        self.chkbox_comment = tk.Checkbutton(frm_query, text = 'Comment:',
                                             variable = self.select_comment,
                                             command = self.update_filter_display)
        self.chkbox_comment.grid(row = 8, column = 1, sticky = tk.W,
                                 padx = 5, pady = 2)
        self.entry_comment = tk.Entry(frm_query, show = None, width = 70,
                                      textvariable = self.query_comment)
        self.entry_comment.grid(row = 8, column = 2, columnspan = 6,
                                sticky = tk.W, padx = 5, pady = 2)

        # file
        self.chkbox_file = tk.Checkbutton(frm_query, text = 'File:',
                                          variable = self.select_file,
                                          command = self.update_filter_display)
        self.chkbox_file.grid(row = 9, column = 1, sticky = tk.W,
                              padx = 5, pady = 2)
        self.entry_file = tk.Entry(frm_query, show = None, width = 70,
                                   textvariable = self.query_file)
        self.entry_file.grid(row = 9, column = 2, columnspan = 6,
                             sticky = tk.W, padx = 5, pady = 2)

        # is:starred is:watched is:draft is:mergeable(>=2.9)
        self.chkbox_starred = tk.Checkbutton(frm_query, text = 'Starred',
                                             variable = self.select_starred)
        self.chkbox_starred.grid(row = 10, column = 1, sticky = tk.W,
                                 padx = 5, pady = 2)
        self.chkbox_watched = tk.Checkbutton(frm_query, text = 'Watched',
                                             variable = self.select_watched)
        self.chkbox_watched.grid(row = 10, column = 2, sticky = tk.W,
                                 padx = 5, pady = 2)
        self.chkbox_draft = tk.Checkbutton(frm_query, text = 'Draft',
                                           variable = self.select_draft)
        self.chkbox_draft.grid(row = 10, column = 3, sticky = tk.W,
                               padx = 5, pady = 2)
        self.chkbox_mergeable = tk.Checkbutton(frm_query, text = 'Mergeable',
                                               variable = self.select_mergeable)
        self.chkbox_mergeable.grid(row = 10, column = 4, sticky = tk.W,
                                   padx = 5, pady = 2)

        # label
        self.frm_labels = tk.Frame(frm_query)

        self.frm_labels.grid(row = 11, column = 1, columnspan = 7,
                             sticky = tk.W)

        # user-defined
        radio_user_defined = tk.Radiobutton(frm_query,
                                            text = 'User-defined',
                                            variable = self.filter_type,
                                            value = 1,
                                            command = self.update_filter_display)
        radio_user_defined.grid(row = 12, column = 0, columnspan = 3,
                                sticky = tk.W, padx = 5, pady = 2)

        self.entry_user_query = tk.Entry(frm_query, show = None, width = 70,
                                         textvariable = self.user_query)
        self.entry_user_query.grid(row = 13, column = 2, columnspan = 6,
                                   sticky = tk.W, padx = 5, pady = 2)

        frm_query.pack(anchor = tk.W, side = tk.TOP, fill = tk.X,
                       padx = 10, pady = 5)

        frm_buttons = tk.Frame(self.top)

        button_save = tk.Button(frm_buttons, text = 'Save', height = 1,
                                command = self.save_query_configuration)
        button_save.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_cancel = tk.Button(frm_buttons, text = 'Cancel', height = 1,
                                  command = self.top.destroy)
        button_cancel.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        frm_buttons.pack(anchor = tk.W, side = tk.TOP, padx = 5, pady = 10)

        self.update_filter_display()

        return


    def update_columns_display(self):

        while self.local_columns_chkbox:
            chkbox = self.local_columns_chkbox.pop()
            chkbox.pack_forget()
            chkbox.destroy()
        while self.local_columns_entry:
            entry = self.local_columns_entry.pop()
            entry.pack_forget()
            entry.destroy()

        self.top.update()

        column_count = len(self.local_columns_config)
        for i in range(0, column_count):
            chkbox = tk.Checkbutton(self.frm_column,
                                    text = self.local_columns_config[i]['Name'].get(),
                                    variable = self.local_columns_config[i]['Display'],
                                    command = self.toggle_display)
            chkbox.grid(row = i / 4, column = (i % 4) * 2, sticky = tk.W,
                        padx = 5, pady = 2)
            self.local_columns_chkbox.append(chkbox)
            entry = tk.Entry(self.frm_column, show = None, width = 5,
                             textvariable = self.local_columns_config[i]['Width'])
            if self.local_columns_config[i]['Display'].get() == 1:
                entry.config(state = tk.NORMAL)
            else:
                entry.config(state = tk.DISABLED)
            entry.grid(row = i / 4, column = (i % 4) * 2 + 1, sticky = tk.W,
                       padx = 5, pady = 2)
            self.local_columns_entry.append(entry)

        self.top.update()

        return


    def init_server_list(self):

        server_list = []

        server_count = len(self.servers)
        for i in range(0, server_count):
            server_list.append(self.servers[i]['Name'])

        self.combo_server_name['values'] = (tuple(server_list))

        return


    def update_filter_display(self):

        major_version = int(self.server['Version'].split('.')[0])
        minor_version = int(self.server['Version'].split('.')[1])

        if self.filter_type.get() == 0:
            self.chkbox_owner.config(state = tk.NORMAL)
            if self.select_owner.get() == 1:
                self.entry_owner.config(state = tk.NORMAL)
            else:
                self.entry_owner.config(state = tk.DISABLED)
            self.chkbox_reviewer.config(state = tk.NORMAL)
            if self.select_reviewer.get() == 1:
                self.entry_reviewer.config(state = tk.NORMAL)
            else:
                self.entry_reviewer.config(state = tk.DISABLED)
            self.chkbox_status.config(state = tk.NORMAL)
            if self.select_status.get() == 1:
                self.combo_status.config(state = tk.NORMAL)
            else:
                self.combo_status.config(state = tk.DISABLED)
            self.chkbox_project.config(state = tk.NORMAL)
            if self.select_project.get() == 1:
                self.entry_project.config(state = tk.NORMAL)
            else:
                self.entry_project.config(state = tk.DISABLED)
            self.chkbox_branch.config(state = tk.NORMAL)
            if self.select_branch.get() == 1:
                self.entry_branch.config(state = tk.NORMAL)
            else:
                self.entry_branch.config(state = tk.DISABLED)
            self.chkbox_age.config(state = tk.NORMAL)
            if self.select_age.get() == 1:
                self.entry_age.config(state = tk.NORMAL)
            else:
                self.entry_age.config(state = tk.DISABLED)
            self.chkbox_change.config(state = tk.NORMAL)
            if self.select_change.get() == 1:
                self.entry_change.config(state = tk.NORMAL)
            else:
                self.entry_change.config(state = tk.DISABLED)
            self.chkbox_commit.config(state = tk.NORMAL)
            if self.select_commit.get() == 1:
                self.entry_commit.config(state = tk.NORMAL)
            else:
                self.entry_commit.config(state = tk.DISABLED)
            self.chkbox_message.config(state = tk.NORMAL)
            if self.select_message.get() == 1:
                self.entry_message.config(state = tk.NORMAL)
            else:
                self.entry_message.config(state = tk.DISABLED)
            self.chkbox_file.config(state = tk.NORMAL)
            if self.select_file.get() == 1:
                self.entry_file.config(state = tk.NORMAL)
            else:
                self.entry_file.config(state = tk.DISABLED)
            self.chkbox_limit.config(state = tk.NORMAL)
            if self.select_limit.get() == 1:
                self.entry_limit.config(state = tk.NORMAL)
            else:
                self.entry_limit.config(state = tk.DISABLED)
            self.chkbox_starred.config(state = tk.NORMAL)
            self.chkbox_watched.config(state = tk.NORMAL)
            self.chkbox_draft.config(state = tk.NORMAL)
            self.entry_user_query.config(state = tk.DISABLED)
            # (>=2.8) comment
            if major_version == 2 and minor_version < 8:
                self.chkbox_comment.config(state = tk.DISABLED)
                self.entry_comment.config(state = tk.DISABLED)
            else:
                self.chkbox_comment.config(state = tk.NORMAL)
                if self.select_comment.get() == 1:
                    self.entry_comment.config(state = tk.NORMAL)
                else:
                    self.entry_comment.config(state = tk.DISABLED)
            # (>=2.9) before after is:mergeable
            if major_version == 2 and minor_version < 9:
                self.chkbox_before.config(state = tk.DISABLED)
                self.entry_before.config(state = tk.DISABLED)
                self.chkbox_after.config(state = tk.DISABLED)
                self.entry_after.config(state = tk.DISABLED)
                self.chkbox_mergeable.config(state = tk.DISABLED)
            else:
                self.chkbox_before.config(state = tk.NORMAL)
                if self.select_before.get() == 1:
                    self.entry_before.config(state = tk.NORMAL)
                else:
                    self.entry_before.config(state = tk.DISABLED)
                self.chkbox_after.config(state = tk.NORMAL)
                if self.select_after.get() == 1:
                    self.entry_after.config(state = tk.NORMAL)
                else:
                    self.entry_after.config(state = tk.DISABLED)
                self.chkbox_mergeable.config(state = tk.NORMAL)
            # (>=2.12) author committer
            if major_version == 2 and minor_version < 12:
                self.chkbox_author.config(state = tk.DISABLED)
                self.entry_author.config(state = tk.DISABLED)
                self.chkbox_committer.config(state = tk.DISABLED)
                self.entry_committer.config(state = tk.DISABLED)
            else:
                self.chkbox_author.config(state = tk.NORMAL)
                if self.select_author.get() == 1:
                    self.entry_author.config(state = tk.NORMAL)
                else:
                    self.entry_author.config(state = tk.DISABLED)
                self.chkbox_committer.config(state = tk.NORMAL)
                if self.select_committer.get() == 1:
                    self.entry_committer.config(state = tk.NORMAL)
                else:
                    self.entry_committer.config(state = tk.DISABLED)
        else:
            self.chkbox_owner.config(state = tk.DISABLED)
            self.entry_owner.config(state = tk.DISABLED)
            self.chkbox_author.config(state = tk.DISABLED)
            self.entry_author.config(state = tk.DISABLED)
            self.chkbox_committer.config(state = tk.DISABLED)
            self.entry_committer.config(state = tk.DISABLED)
            self.chkbox_reviewer.config(state = tk.DISABLED)
            self.entry_reviewer.config(state = tk.DISABLED)
            self.chkbox_status.config(state = tk.DISABLED)
            self.combo_status.config(state = tk.DISABLED)
            self.chkbox_project.config(state = tk.DISABLED)
            self.entry_project.config(state = tk.DISABLED)
            self.chkbox_branch.config(state = tk.DISABLED)
            self.entry_branch.config(state = tk.DISABLED)
            self.chkbox_age.config(state = tk.DISABLED)
            self.entry_age.config(state = tk.DISABLED)
            self.chkbox_before.config(state = tk.DISABLED)
            self.entry_before.config(state = tk.DISABLED)
            self.chkbox_after.config(state = tk.DISABLED)
            self.entry_after.config(state = tk.DISABLED)
            self.chkbox_change.config(state = tk.DISABLED)
            self.entry_change.config(state = tk.DISABLED)
            self.chkbox_commit.config(state = tk.DISABLED)
            self.entry_commit.config(state = tk.DISABLED)
            self.chkbox_message.config(state = tk.DISABLED)
            self.entry_message.config(state = tk.DISABLED)
            self.chkbox_comment.config(state = tk.DISABLED)
            self.entry_comment.config(state = tk.DISABLED)
            self.chkbox_file.config(state = tk.DISABLED)
            self.entry_file.config(state = tk.DISABLED)
            self.chkbox_limit.config(state = tk.DISABLED)
            self.entry_limit.config(state = tk.DISABLED)
            self.chkbox_starred.config(state = tk.DISABLED)
            self.chkbox_watched.config(state = tk.DISABLED)
            self.chkbox_draft.config(state = tk.DISABLED)
            self.chkbox_mergeable.config(state = tk.DISABLED)
            self.entry_user_query.config(state = tk.NORMAL)

        return


    def update_server(self, event):

        logger.debug('Server is changed to %s' % self.server_name.get())

        index = self.servers.find(self.server_name.get())
        self.server = self.servers[index]
        self.update_server_column_config()
        self.update_columns_display()
        self.update_filter_display()

        return


    def toggle_display(self):

        column_count = len(self.local_columns_config)
        for i in range(0, column_count):
            if self.local_columns_config[i]['Display'].get() == 1:
                self.local_columns_entry[i].config(state = tk.NORMAL)
            else:
                self.local_columns_entry[i].config(state = tk.DISABLED)

        return


    def save_query_configuration(self):

        columns_config = []

        for local_col in self.local_columns_config:
            col = dict()
            col['Name'] = local_col['Name'].get()
            col['Display'] = local_col['Display'].get()
            col['Width'] = local_col['Width'].get()
            columns_config.append(col)

        query = dict()

        if self.filter_type.get() == 0:
            if self.select_owner.get() == 1:
                query['owner'] = self.query_owner.get()
            if self.select_author.get() == 1:
                query['author'] = self.query_author.get()
            if self.select_committer.get() == 1:
                query['committer'] = self.query_committer.get()
            if self.select_reviewer.get() == 1:
                query['reviewer'] = self.query_reviewer.get()
            if self.select_status.get() == 1:
                query['status'] = self.query_status.get()
            if self.select_branch.get() == 1:
                query['branch'] = self.query_branch.get()
            if self.select_age.get() == 1:
                query['age'] = self.query_age.get()
            if self.select_before.get() == 1:
                query['before'] = self.query_before.get()
            if self.select_after.get() == 1:
                query['after'] = self.query_after.get()
            if self.select_change.get() == 1:
                query['change'] = self.query_change.get()
            if self.select_commit.get() == 1:
                query['commit'] = self.query_commit.get()
            if self.select_message.get() == 1:
                query['message'] = self.query_message.get()
            if self.select_comment.get() == 1:
                query['comment'] = self.query_comment.get()
            if self.select_file.get() == 1:
                query['file'] = self.query_file.get()
            if self.select_starred.get() == 1:
                query['starred'] = '1'
            if self.select_watched.get() == 1:
                query['watched'] = '1'
            if self.select_draft.get() == 1:
                query['draft'] = '1'
            if self.select_mergeable.get() == 1:
                query['mergeable'] = '1'
            if self.select_limit.get() == 1:
                query['limit'] = self.query_limit.get()
        else:
            query['user-defined'] = self.user_query.get() 

        self.query.configure(name = self.query_name.get(),
                             server_name = self.server_name.get(),
                             query = query,
                             columns_config = columns_config)

        self.parent.update_query_name(self.query.name)
        self.parent.update_columns(columns_config)
        self.top.destroy()

        return


class QueryLayout():

    def __init__(self, name, tab_control, tab, columns_config,
                 labels_config, servers, query_file = None):

        self.query = GerritQuery(name, servers, query_file)
        if self.query.columns_config:
            self.columns_config = self.query.columns_config
        else:
            self.columns_config = []
            for col in columns_config:
                self.columns_config.append(col)
            for label in labels_config:
                self.columns_config.append(label)
            self.query.configure(columns_config = self.columns_config)
        self.fix_columns_config = columns_config
        self.tab_control = tab_control
        self.tab = tab
        self.servers = servers

        self.init_default_variables()
        self.init_layout()

        return


    def init_default_variables(self):

        self.status_msg = tk.StringVar()
        self.status_msg.set('')

        return


    def init_layout(self):

        style = ttk.Style()
        style.configure("Query.Treeview", rowheight = 20)

        frm_buttons = tk.Frame(self.tab)

        button_run = tk.Button(frm_buttons, text = 'Run Query',
                               height = 1, command = self.run_query)
        button_run.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_configure = tk.Button(frm_buttons, text = 'Configure',
                                     height = 1, command = self.configure_query)
        button_configure.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_save = tk.Button(frm_buttons, text = 'Save', height = 1,
                                command = self.save_query)
        button_save.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_export = tk.Button(frm_buttons, text = 'Export', height = 1,
                                  command = self.export_query_result)
        button_export.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        frm_buttons.pack(anchor = tk.W, side = tk.TOP, padx = 5, pady = 5)

        frm_result = tk.Frame(self.tab)

        self.gerrit_list = ttk.Treeview(frm_result, show = "headings",
                                        style = "Query.Treeview")
        self.update_columns()
        self.gerrit_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = 1)

        frm_result.pack(anchor = tk.W, side = tk.TOP, fill = tk.BOTH, expand = 1)

        frm_status = tk.Frame(self.tab)

        label_status = tk.Label(frm_status, justify = tk.LEFT,
                                textvariable = self.status_msg)
        label_status.pack(anchor = tk.W, side = tk.TOP, padx = 5, pady = 5)

        self.progress = ttk.Progressbar(frm_status, length = 640,
                                        mode = "determinate", orient = tk.HORIZONTAL)
        self.progress.pack(anchor = tk.W, side = tk.TOP, fill = tk.X, expand = 1)

        frm_status.pack(anchor = tk.W, side = tk.TOP, fill = tk.X)

        return


    def get_columns(self):

        columns = []

        for col in self.columns_config:
            columns.append(col['Name'])

        return columns


    def get_display_columns(self):

        display_columns = []

        for col in self.columns_config:
            if col['Display'] == 1:
                display_columns.append(col['Name'])

        return display_columns


    def update_query_name(self, query_name):

        self.tab_control.tab(self.tab, text = query_name)
        self.tab.update()

        return


    def update_columns(self, columns_config = None):

        if columns_config:
            self.columns_config = columns_config

        columns = self.get_columns()
        display_columns = self.get_display_columns()
        self.gerrit_list.config(columns = columns,
                                displaycolumns = display_columns)
        for col in self.columns_config:
            self.gerrit_list.column(col['Name'], width = col['Width'],
                                    anchor = 'w', stretch = True) 
            self.gerrit_list.heading(col['Name'], text = col['Name'],
                                     anchor = 'w')
            logger.debug('Add column: Name = %s, Width = %d' %
                         (col['Name'], col['Width'],))
        self.tab.update()

        return


    def run_query(self):

        rows = self.gerrit_list.get_children()
        for item in rows:
            self.gerrit_list.delete(item)
        self.reset_progress()

        try:
            self.status('Query is running, please wait ...')
            gerrits = self.query.run()
        except GerritQueryException as e:
            self.status(e)
            return
        gerrit_count = len(gerrits)
        self.init_progress(gerrit_count)
        self.status('Gerrit [0/%d]' % gerrit_count)

        for i in range(0, gerrit_count):
            line = []
            self.status('Gerrit [%d/%d]: Processing Gerrit %s' %
                        (i + 1, gerrit_count, gerrits[i]['ID']))
            for col in self.query.get_columns():
                if gerrits[i].has_key(col):
                    line.append(gerrits[i][col])
                else:
                    line.append('')
            self.gerrit_list.insert('', tk.END, values = line)
            self.progress_step(i + 1)
            self.tab.update()

        self.status('Query done, total %d gerrits' % gerrit_count)

        return


    def init_progress(self, gerrits):

        self.progress['maximum'] = gerrits
        self.progress['value'] = 0

        return


    def progress_step(self, gerrits):

        self.progress['value'] = gerrits

        return


    def reset_progress(self):

        self.progress['value'] = 0

        return


    def status(self, message):

        logger.debug(message)

        self.status_msg.set(message)
        self.tab.update()

        return


    def configure_query(self):

        self.top_query = tk.Toplevel(self.tab)
        query_name = self.tab_control.tab(self.tab_control.select(), 'text')
        query_profile = QueryProfile(parent = self, top = self.top_query,
                                     query = self.query, servers = self.servers,
                                     fix_columns_config = self.fix_columns_config)

        return


    def save_query(self):

        fd = SaveFileDialog(self.tab)
        file_name = fd.go(DEFAULT_QUERY_DIR)
        if file_name:
            self.query.save(file_name)
            self.status('Query is saved in %s' % file_name)

        return


    def export_query_result(self):

        fd = SaveFileDialog(self.tab)
        file_name = fd.go()
        if file_name:
            with open(file_name, 'w') as f:
                f.write(codecs.BOM_UTF8)
                writer = csv.writer(f)
                writer.writerow(self.get_columns())
                rows = self.gerrit_list.get_children()
                row_count = len(rows)
                self.init_progress(row_count)
                self.status('Exporting to %s' % file_name)
                for i in range(0, row_count):
                    values = self.gerrit_list.item(rows[i], 'values')
                    writer.writerow(values)
                    self.progress_step(i + 1)
                    self.tab.update()
            self.status('Write done, total %d rows are saved in %s' %
                        (row_count, file_name,))

        return

