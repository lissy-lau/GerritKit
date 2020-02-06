#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Lissy Lau <lissy.lau@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#
# GerritServer
#
# This module provides classes for gerrit server related operations
#

__version__ = '0.1'
__author__ = 'Lissy Lau <lissy.lau@gmail.com>'

import getpass
import sys
import logging
import copy
import xml.dom.minidom as DOM
import Tkinter as tk
import ttk as ttk
import tkMessageBox

from GerritClient import *

reload(sys)
sys.setdefaultencoding('utf-8')
logger = logging.getLogger('GerritLogger')

DEFAULT_USER = getpass.getuser()
DEFAULT_PASSWORD = ''

E_OK = 0
E_INVAL = 1
E_NOT_FOUND = 2
E_ALREADY_EXIST = 3


class GerritServerException(Exception):
    pass


class GerritServer():

    def __init__(self, parent, config_xml):

        self.parent = parent
        self.config_xml = config_xml
        self.data = []
        self.count = 0
        self.index = 0

        self.read_configuration_file()

        return


    def __len__(self):

        return self.count


    def __getitem__(self, index):

        self.index = index
        return self.data[index]


    def read_configuration_file(self):

        nodes = self.config_xml.getElementsByTagName('Server')
        for node in nodes:
            server = dict()
            self.index = self.count
            server['Name'] = node.getAttribute('Name')
            server['URL'] = node.getAttribute('URL')
            server['Port'] = node.getAttribute('Port')
            server['Type'] = int(node.getAttribute('Type'))
            server['Version'] = node.getAttribute('Version')
            if node.hasAttribute('Proxy'):
                server['Proxy'] = node.getAttribute('Proxy')
            login_node = node.getElementsByTagName('Login')
            if len(login_node) > 0:
                server['AuthType'] = int(login_node[0].getAttribute('AuthType'))
                server['Username'] = login_node[0].getAttribute('Username')
                server['Password'] = login_node[0].getAttribute('Password')
            label_node = node.getElementsByTagName('Label')
            if len(label_node) > 0:
                server['Labels'] = []
                for label in label_node:
                    server['Labels'].append(label.getAttribute('Name'))
            self.count = self.count + 1
            self.data.append(server)
            logger.debug('Load server: Index = %d, Name = %s, URL = %s, Port = %s, Type = %d, Version = %s' %
                         (self.index,
                          server['Name'],
                          server['URL'],
                          server['Port'],
                          server['Type'],
                          server['Version'],))

        return


    def add(self, server):

        index = self.find(server['Name'])
        if index >= 0:
            logger.error('Server %s already exist' % server['Name'])
            return E_ALREADY_EXIST

        new_server = copy.deepcopy(server)
        self.index = self.count
        self.data.append(new_server)
        self.count = self.count + 1
        logger.debug('Add server: Index = %d, Name = %s, URL = %s, Port = %s, Type = %d, version = %s' %
                     (self.index,
                      new_server['Name'],
                      new_server['URL'],
                      new_server['Port'],
                      new_server['Type'],
                      new_server['Version'],))

        root_node = self.config_xml.getElementsByTagName('Servers')
        node = self.config_xml.createElement('Server')
        node.setAttribute('Name', new_server['Name'])
        node.setAttribute('URL', new_server['URL'])
        node.setAttribute('Port', new_server['Port'])
        node.setAttribute('Type', str(new_server['Type']))
        node.setAttribute('Version', new_server['Version'])
        if new_server.has_key('Proxy'):
            node.setAttribute('Proxy', new_server['Proxy'])
        if new_server.has_key('Username'):
            login_node = self.config_xml.createElement('Login')
            login_node.setAttribute('AuthType', str(new_server['AuthType']))
            login_node.setAttribute('Username', new_server['Username'])
            login_node.setAttribute('Password', new_server['Password'])
            node.appendChild(login_node)
        if new_server.has_key('Labels'):
            labels_node = self.config_xml.createElement('Labels')
            node.appendChild(labels_node)
            for label in new_server['Labels']:
                label_node = self.config_xml.createElement('Label')
                label_node.setAttribute('Name', label)
                labels_node.appendChild(label_node)
        root_node[0].appendChild(node)

        self.parent.update_server_list()

        return E_OK


    def update(self, index, server):

        idx = self.find(server['Name'])
        if idx >= 0 and idx != index:
            logger.error('Server %s already exist' % server['Name'])
            return E_ALREADY_EXIST

        logger.debug('Before update: Index = %d, Name = %s, URL = %s, Port = %s, Type = %d, version = %s' %
                     (index,
                      self.data[index]['Name'],
                      self.data[index]['URL'],
                      self.data[index]['Port'],
                      self.data[index]['Type'],
                      self.data[index]['Version'],))

        self.index = index
        update_server = copy.deepcopy(server)
        self.data[self.index] = update_server

        nodes = self.config_xml.getElementsByTagName('Server')
        nodes[self.index].setAttribute('Name', update_server['Name'])
        nodes[self.index].setAttribute('URL', update_server['URL'])
        nodes[self.index].setAttribute('Port', update_server['Port'])
        nodes[self.index].setAttribute('Type', str(update_server['Type']))
        nodes[self.index].setAttribute('Version', update_server['Version'])
        if update_server.has_key('Proxy'):
            nodes[self.index].setAttribute('Proxy', update_server['Proxy'])
        else:
            if nodes[self.index].hasAttribute('Proxy'):
                nodes[self.index].removeAttribute('Proxy')
        login_node = nodes[self.index].getElementsByTagName('Login')
        if len(login_node) > 0:
            if update_server.has_key('Username'):
                login_node[0].setAttribute('AuthType', str(update_server['AuthType']))
                login_node[0].setAttribute('Username', update_server['Username'])
                login_node[0].setAttribute('Password', update_server['Password'])
            else:
                nodes[self.index].removeChild(login_node[0])
        else:
            if update_server.has_key('Username'):
                login_node = self.config_xml.createElement('Login')
                login_node.setAttribute('AuthType', str(update_server['AuthType']))
                login_node.setAttribute('Username', update_server['Username'])
                login_node.setAttribute('Password', update_server['Password'])
                nodes[self.index].appendChild(login_node)
        labels_node = nodes[self.index].getElementsByTagName('Labels')
        if len(labels_node) > 0:
            if update_server.has_key('Labels'):
                old_label_nodes = labels_node[0].getElementsByTagName('Label')
                for old_label in old_label_nodes:
                    labels_node[0].removeChild(old_label)
                for label in update_server['Labels']:
                    label_node = self.config_xml.createElement('Label')
                    label_node.setAttribute('Name', label)
                    labels_node[0].appendChild(label_node)
            else:
                nodes[self.index].removeChild(lables_node[0])
        else:
            if update_server.has_key('Labels'):
                labels_node = self.config_xml.createElement('Labels')
                nodes[self.index].appendChild(labels_node)
                for label in update_server['Labels']:
                    label_node = self.config_xml.createElement('Label')
                    label_node.setAttribute('Name', label)
                    labels_node.appendChild(label_node)

        logger.debug('After update: Index = %d, Name = %s, URL = %s, Port = %s, Type = %d, version = %s' %
                     (self.index,
                      self.data[self.index]['Name'],
                      self.data[self.index]['URL'],
                      self.data[self.index]['Port'],
                      self.data[self.index]['Type'],
                      self.data[self.index]['Version'],))

        self.parent.update_server_list()

        return E_OK


    def remove(self, index):

        logger.debug('Remove server: Index = %d, Name = %s, URL = %s, Port = %s, Type = %d, version = %s' %
                     (index,
                      self.data[index]['Name'],
                      self.data[index]['URL'],
                      self.data[index]['Port'],
                      self.data[index]['Type'],
                      self.data[index]['Version'],))

        root_node = self.config_xml.getElementsByTagName('Servers')
        nodes = self.config_xml.getElementsByTagName('Server')
        root_node[0].removeChild(nodes[index])
        self.index = 0

        del self.data[index]
        self.count = self.count - 1

        self.parent.update_server_list()

        return


    def find(self, name):

        index = -1

        for i in range(0, self.count):
            if self.data[i]['Name'] == name:
                logger.debug('Server %s found' % name)
                index = i

        return index


class ServerProfile():

    def __init__(self, top, servers, labels_config, is_new = False):

        self.top = top
        self.top.geometry(SERVER_PROFILE_GEOMETRY)
        self.servers = servers
        self.is_new = is_new
        self.labels_config = copy.deepcopy(labels_config)

        self.init_default_variables()

        if not self.is_new:
            self.server_name.set(self.servers[self.servers.index]['Name'])
            self.server_url.set(self.servers[self.servers.index]['URL'])
            self.server_port.set(self.servers[self.servers.index]['Port'])
            self.server_type.set(self.servers[self.servers.index]['Type'])
            self.server_version.set(self.servers[self.servers.index]['Version'])
            if self.servers[self.servers.index].has_key('Proxy'):
                self.server_use_proxy.set(1)
                self.server_proxy.set(self.servers[self.servers.index]['Proxy'])
            if self.servers[self.servers.index].has_key('Labels'):
                self.labels_config = copy.deepcopy(self.servers[self.servers.index]['Labels'])
            else:
                self.labels_config = []
            if self.servers[self.servers.index].has_key('Username'):
                self.server_require_login.set(1)
                auth_type = self.servers[self.servers.index]['AuthType']
                if auth_type == AUTH_TYPE_HTTP_BASIC:
                    self.server_auth_type.set('HTTP Basic')
                elif auth_type == AUTH_TYPE_HTTP_DIGEST:
                    self.server_auth_type.set('HTTP Digest')
                elif auth_type == AUTH_TYPE_HTTP_COOKIE:
                    self.server_auth_type.set('HTTP Cookie')
                else:
                    self.server_auth_type.set('None')
                self.server_username.set(self.servers[self.servers.index]['Username'])
                self.server_password.set(self.servers[self.servers.index]['Password'])
            logger.debug('Loaded server configuration: Index = %d, Name = %s, URL = %s, Port = %s, Type = %d, Version = %s' % 
                         (self.servers.index, 
                          self.server_name.get(),
                          self.server_url.get(),
                          self.server_port.get(),
                          self.server_type.get(),
                          self.server_version.get(),))

        self.server_labels.set(tuple(self.labels_config))

        self.init_layout()

        return


    def init_layout(self):

        frm_server_profile = tk.LabelFrame(self.top, text = 'Server Profile',
                                           borderwidth = 2, relief = tk.GROOVE,
                                           padx = 5, pady = 5)

        # server information

        label_server_name = tk.Label(frm_server_profile, text = 'Name*:')
        label_server_name.grid(row = 0, column = 0, sticky = tk.W,
                               padx = 5, pady = 2)
        entry_server_name = tk.Entry(frm_server_profile, show = None, width = 20,
                                     textvariable = self.server_name)
        entry_server_name.grid(row = 0, column = 1, sticky = tk.W,
                               padx = 5, pady = 2)

        radio_ssh = tk.Radiobutton(frm_server_profile, text = 'SSH',
                                   variable = self.server_type,
                                   value = SRV_TYPE_SSH,
                                   command = self.set_server_type)
        radio_ssh.grid(row = 0, column = 2, sticky = tk.W, pady = 2)
        radio_rest = tk.Radiobutton(frm_server_profile, text = 'REST',
                                    variable = self.server_type,
                                    value = SRV_TYPE_REST,
                                    command = self.set_server_type)
        radio_rest.grid(row = 0, column = 3, sticky = tk.W, pady = 2)

        label_server_url = tk.Label(frm_server_profile, text = 'URL*:')
        label_server_url.grid(row = 1, column = 0, sticky = tk.W,
                              padx = 5, pady = 2)
        entry_server_url = tk.Entry(frm_server_profile, show = None, width = 40,
                                    textvariable = self.server_url)
        entry_server_url.grid(row = 1, column = 1, columnspan = 3,
                              sticky = tk.W, padx = 5, pady = 2)

        label_server_port = tk.Label(frm_server_profile, text = 'Port:')
        label_server_port.grid(row = 2, column = 0, sticky = tk.W,
                               padx = 5, pady = 2)
        entry_server_port = tk.Entry(frm_server_profile, show = None, width = 20,
                                     textvariable = self.server_port)
        entry_server_port.grid(row = 2, column = 1, sticky = tk.W,
                               padx = 5, pady = 2)

        label_server_version = tk.Label(frm_server_profile, text = 'Version:')
        label_server_version.grid(row = 2, column = 2, sticky = tk.W,
                                  padx = 5, pady = 2)
        combo_server_version = ttk.Combobox(frm_server_profile, width = 7,
                                            textvariable = self.server_version)
        combo_server_version['values'] = ('', '2.7', '2.8', '2.9', '2.10', '2.11',
                                          '2.12', '2.13', '2.14', '2.15', '2.16',
                                          '3.0', '3.1')
        combo_server_version.grid(row = 2, column = 3, sticky = tk.W,
                                  pady = 2)

        # user login

        if self.server_require_login.get() == 1:
            login_state = tk.NORMAL
        else:
            login_state = tk.DISABLED

        label_auth = tk.Label(frm_server_profile, text = 'Authentication:')
        label_auth.grid(row = 3, column = 0, sticky = tk.W,
                        padx = 5, pady = 2)
        self.combo_auth = ttk.Combobox(frm_server_profile, width = 18,
                                       textvariable = self.server_auth_type,
                                       state = login_state)
        self.combo_auth['values'] = ('None', 'HTTP Basic', 'HTTP Digest',
                                     'HTTP Cookie')
        self.combo_auth.grid(row = 3, column = 1, sticky = tk.W,
                             padx = 5, pady = 2)

        chkbox_login = tk.Checkbutton(frm_server_profile, text = 'Require Login',
                                      variable = self.server_require_login,
                                      command = self.toggle_login)
        chkbox_login.grid(row = 3, column = 2, columnspan = 2,
                          sticky = tk.W, pady = 2)

        show_password = tk.IntVar()
        show_password.set(0)
        chkbox_show_password = tk.Checkbutton(frm_server_profile,
                                              text = 'Show Password',
                                              variable = self.show_password,
                                              command = self.toggle_show_password)
        chkbox_show_password.grid(row = 5, column = 2, columnspan = 2,
                                  sticky = tk.W, pady = 2)

        label_username = tk.Label(frm_server_profile, text = 'Username:')
        label_username.grid(row = 4, column = 0, sticky = tk.W,
                            padx = 5, pady = 2)
        self.entry_username = tk.Entry(frm_server_profile, show = None, width = 20,
                                       textvariable = self.server_username,
                                       state = login_state)
        self.entry_username.grid(row = 4, column = 1, sticky = tk.W,
                                 padx = 5, pady = 2)

        label_password = tk.Label(frm_server_profile, text = 'Password:')
        label_password.grid(row = 5, column = 0, sticky = tk.W,
                            padx = 5, pady = 2)
        self.entry_password = tk.Entry(frm_server_profile, show = '*', width = 20,
                                       textvariable = self.server_password,
                                       state = login_state)
        self.entry_password.grid(row = 5, column = 1, sticky = tk.W,
                                 padx = 5, pady = 2)

        # proxy settings

        chkbox_proxy = tk.Checkbutton(frm_server_profile, text = 'Proxy',
                                      variable = self.server_use_proxy,
                                      command = self.toggle_proxy)
        chkbox_proxy.grid(row = 6, column = 0, sticky = tk.W, pady = 2)

        if self.server_use_proxy.get() == 1:
            proxy_state = tk.NORMAL
        else:
            proxy_state = tk.DISABLED

        self.entry_server_proxy = tk.Entry(frm_server_profile, show = None, width = 40,
                                           textvariable = self.server_proxy,
                                           state = proxy_state)
        self.entry_server_proxy.grid(row = 6, column = 1, columnspan = 3,
                                     sticky = tk.W, padx = 5, pady = 2)

        # server labels

        frm_label_list = tk.Frame(frm_server_profile)
        scrollbar = tk.Scrollbar(frm_label_list, orient = tk.VERTICAL)
        self.lb_server_label = tk.Listbox(frm_label_list, selectmode = tk.SINGLE,
                                          height = 10, width = 25,
                                          listvariable = self.server_labels,
                                          yscrollcommand = scrollbar.set)
        scrollbar.config(command = self.lb_server_label.yview)
        scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.lb_server_label.pack(side = tk.LEFT, fill = tk.BOTH, expand = 1)

        frm_label_list.grid(row = 0, column = 4, rowspan = 7, sticky = tk.NW,
                            padx = 5, pady = 2)

        frm_server_profile.pack(anchor = tk.W, side = tk.TOP, fill = tk.X,
                                padx = 10, pady = 10)

        frm_buttons = tk.Frame(self.top)

        button_test = tk.Button(frm_buttons, text = 'Test Server',
                                height = 1, command = self.test_server_config)
        button_test.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_save = tk.Button(frm_buttons, text = 'Save', height = 1,
                                 command = self.save_server_config)
        button_save.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_cancel = tk.Button(frm_buttons, text = 'Cancel', height = 1,
                                  command = self.top.destroy)
        button_cancel.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        frm_buttons.pack(anchor = tk.W, side = tk.TOP, padx = 5)

        frm_test_server_result = tk.LabelFrame(self.top, text = 'Test Result',
                                                    borderwidth = 2, relief = tk.GROOVE,
                                                    height = 200, padx = 5, pady = 5)

        msg_test_result_str = tk.Message(frm_test_server_result, width = 600,
                                         textvariable = self.test_result_str)
        msg_test_result_str.pack(anchor = tk.W, side = tk.TOP, padx = 5)

        frm_test_server_result.pack(anchor = tk.W, side = tk.TOP,
                                    fill = tk.BOTH, expand = 1,
                                    padx = 10, pady = 10)

        frm_status = tk.Frame(self.top, padx = 5, pady = 5)

        label_status = tk.Label(frm_status, justify = tk.LEFT,
                                textvariable = self.status_msg)
        label_status.pack(anchor = tk.W, side = tk.TOP, padx = 5, pady = 5)

        frm_status.pack(anchor = tk.W, side = tk.TOP, fill = tk.X)

        return


    def init_default_variables(self):

        self.server_name = tk.StringVar()
        self.server_name.set('New Server');
        self.server_type = tk.IntVar()
        self.server_type.set(SRV_TYPE_UNKNOWN)
        self.server_version = tk.StringVar()
        self.server_version.set('');
        self.server_url = tk.StringVar()
        self.server_url.set('');
        self.server_port = tk.StringVar()
        self.server_port.set('')
        self.server_require_login = tk.IntVar()
        self.server_require_login.set(0)
        self.server_auth_type = tk.StringVar()
        self.server_auth_type.set('');
        self.server_username = tk.StringVar()
        self.server_username.set(DEFAULT_USER)
        self.server_password = tk.StringVar()
        self.server_password.set('')
        self.server_labels = tk.StringVar()
        self.server_labels.set('')
        self.show_password = tk.IntVar()
        self.show_password.set(0)
        self.server_use_proxy = tk.IntVar()
        self.server_use_proxy.set(0)
        self.server_proxy = tk.StringVar()
        self.server_proxy.set('');

        self.test_result_str = tk.StringVar()
        self.test_result_str.set('')
        self.status_msg = tk.StringVar()
        self.status_msg.set('')

        return


    def set_server_type(self):

        if self.server_type.get() == SRV_TYPE_SSH:
            self.server_port.set(DEFAULT_SSH_PORT)
        if self.server_type.get() == SRV_TYPE_REST:
            self.server_port.set(DEFAULT_HTTPS_PORT)

        return


    def toggle_login(self):

        if self.server_require_login.get() == 1:
            logger.debug('Enable login')
            self.combo_auth.config(state = tk.NORMAL)
            self.entry_username.config(state = tk.NORMAL)
            self.entry_password.config(state = tk.NORMAL)
        else:
            logger.debug('Disable login')
            self.combo_auth.config(state = tk.DISABLED)
            self.entry_username.config(state = tk.DISABLED)
            self.entry_password.config(state = tk.DISABLED)

        return


    def toggle_show_password(self):

        if self.show_password.get() == 1:
            logger.debug('Show password')
            self.entry_password.config(show = '')
        else:
            logger.debug('Hide password')
            self.entry_password.config(show = '*')

        return


    def toggle_proxy(self):

        if self.server_use_proxy.get() == 1:
            logger.debug('Enable proxy')
            self.entry_server_proxy.config(state = tk.NORMAL)
        else:
            logger.debug('Disable proxy')
            self.entry_server_proxy.config(state = tk.DISABLED)

        return


    def test_server_config(self):

        server = dict()

        if self.server_auth_type.get() == 'HTTP Basic':
            auth_type = AUTH_TYPE_HTTP_BASIC
        elif self.server_auth_type.get() == 'HTTP Digest':
            auth_type = AUTH_TYPE_HTTP_DIGEST
        elif self.server_auth_type.get() == 'HTTP Cookie':
            auth_type = AUTH_TYPE_HTTP_COOKIE
        else:
            auth_type = AUTH_TYPE_NONE

        server['URL'] = self.server_url.get()
        server['Port'] = self.server_port.get()
        server['Type'] = self.server_type.get()
        server['Version'] = self.server_version.get()
        if self.server_require_login.get() == 1:
            server['AuthType'] = auth_type
            server['Username'] = self.server_username.get()
            server['Password'] = self.server_password.get()
        if self.server_use_proxy.get() == 1:
            server['Proxy'] = self.server_proxy.get()

        if server['Version'] == '':
            self.status_msg.set('Getting server version ...')
            self.top.update()
            ret_code, res_str = GerritClient.get_server_version(server)
            self.test_result_str.set(res_str)
            if ret_code != 0:
                self.status_msg.set('Test Result: Aborted with error %d' % ret_code)
                return
            # Update configuration when suceeded
            self.server_url.set(server['URL'])
            self.server_port.set(server['Port'])
            self.server_version.set(server['Version'])

        self.status_msg.set('Getting server labels ...')
        self.top.update()
        ret_code, res_str = GerritClient.get_server_labels(server)
        self.test_result_str.set(self.test_result_str.get() + res_str)
        if ret_code != 0:
            self.status_msg.set('Test Result: Aborted with error %d' % ret_code)
            return
        # Update configuration when suceeded
        if server.has_key('Labels'):
            self.server_labels.set(tuple(server['Labels']))

        self.status_msg.set('Test Result: Completed successfully')
        self.top.update()

        return


    def save_server_config(self):

        logger.debug('Save server configuration')

        server = dict()
        ret = E_OK

        if self.server_auth_type.get() == 'HTTP Basic':
            auth_type = AUTH_TYPE_HTTP_BASIC
        elif self.server_auth_type.get() == 'HTTP Digest':
            auth_type = AUTH_TYPE_HTTP_DIGEST
        elif self.server_auth_type.get() == 'HTTP Cookie':
            auth_type = AUTH_TYPE_HTTP_COOKIE
        else:
            auth_type = AUTH_TYPE_NONE

        server['Name'] = self.server_name.get()
        server['URL'] = self.server_url.get()
        server['Port'] = self.server_port.get()
        server['Type'] = self.server_type.get()
        server['Version'] = self.server_version.get()
        if self.server_require_login.get() == 1:
            server['AuthType'] = auth_type
            server['Username'] = self.server_username.get()
            server['Password'] = self.server_password.get()
        if self.server_use_proxy.get() == 1:
            server['Proxy'] = self.server_proxy.get()

        labels = self.lb_server_label.get(0, tk.END)
        if len(labels) > 0:
            server['Labels'] = labels

        if self.is_new:
            ret = self.servers.add(server)
        else:
            ret = self.servers.update(self.servers.index, server)

        if ret == E_OK:
            self.top.destroy()
        elif ret == E_ALREADY_EXIST:
            tkMessageBox.showerror(title = 'ERROR',
                                   message = ('Server name "%s" already in use!'
                                              % self.server_name.get()),
                                   parent = self.top)

        return

