#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Lissy Lau <lissy.lau@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#
# GerritKit
#
# Main module of GerritKit, a gerrit client.
#

__version__ = '0.1'
__author__ = 'Lissy Lau <lissy.lau@gmail.com>'

import os
import getpass
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
import csv
import codecs
import xml.dom.minidom as DOM
import Tkinter as tk
import ttk as ttk
import tkMessageBox
from FileDialog import *

from GerritServer import *
from GerritClient import *
from GerritQuery import *
from GerritUtil import *
from GerritDefaultConfig import *

reload(sys)
sys.setdefaultencoding('utf-8')

class GerritConfigurationException(Exception):
    pass


class App():

    def __init__(self, master, config_xml):

        self.master = master
        self.master.geometry(MAIN_GEOMETRY)
        self.config_xml = config_xml
        self.current_file_index = 0

        self.read_configuration_file()

        self.init_configuration()
        self.init_main_menu()
        self.init_layout()

        return


    def init_configuration(self):

        self.log_path = tk.StringVar()
        self.log_file = tk.StringVar()
        self.log_rotation = tk.IntVar()
        self.log_backup_count = tk.StringVar()
        self.log_max_size = tk.StringVar()

        logging_node = self.config_xml.getElementsByTagName('Logging')[0]
        self.log_path.set(logging_node.getAttribute('Path'))
        self.log_file.set(logging_node.getAttribute('FileName'))
        self.log_rotation.set(int(logging_node.getAttribute('Rotation')))
        self.log_backup_count.set(logging_node.getAttribute('BackupCount'))
        self.log_max_size.set(logging_node.getAttribute('MaxSize'))

        return

    def init_main_menu(self):

        menu_main = tk.Menu(self.master, borderwidth = 2, relief = tk.GROOVE)

        menu_query = tk.Menu(menu_main, borderwidth = 2,
                             relief = tk.GROOVE, tearoff = 0)
        menu_query.add_command(label = 'New Query', command = self.new_query)
        menu_query.add_command(label = 'Open Query...', command = self.open_query)
        menu_query.add_separator()
        menu_query.add_command(label = 'Exit',
                               command = self.master.destroy)
        menu_main.add_cascade(label = 'Query', menu = menu_query)

        menu_config = tk.Menu(menu_main, borderwidth = 2,
                              relief = tk.GROOVE, tearoff = 0)
        menu_config.add_command(label = 'Servers...',
                                command = self.configure_servers)
        menu_config.add_command(label = 'Preferrences...',
                                command = self.configure_preferences)
        menu_config.add_separator()
        menu_config.add_command(label = 'Import from...',
                                command = self.import_configuration_file)
        menu_config.add_command(label = 'Export to...',
                                command = self.export_configuration_file)
        menu_main.add_cascade(label = "Configuration", menu = menu_config)

        self.master.config(menu = menu_main)

        return


    def init_layout(self):

        self.tab_control = ttk.Notebook(self.master)
        self.add_query_tab()
        self.tab_control.pack(expand = 1, fill = tk.BOTH)
        self.tab_control.bind('<Double-Button-1>', self.delete_tab)

        return


    def add_query_tab(self, query_file = None):

        tab = tk.Frame(self.tab_control, borderwidth = 2, relief = tk.GROOVE)
        query_name = ''

        if query_file:
            logger.debug('Query file %s' % query_file)
        else:
            self.current_file_index = self.current_file_index + 1
            query_name = 'Untitled %d' % self.current_file_index;
            logger.debug('New query %s' % query_name)

        query_layout = QueryLayout(query_name, self.tab_control, tab,
                                   self.columns_config, self.labels_config,
                                   self.servers, query_file)

        self.tab_control.add(tab, text = query_layout.query.name)
        self.tab_control.select(tab)

        return


    def delete_tab(self, event):

        try:
            index = event.widget.index('@%d,%d' % (event.x, event.y))
            event.widget.forget(index)
        except:
            pass

        return


    def read_configuration_file(self):

        self.columns_config = []
        display_node = self.config_xml.getElementsByTagName('Display')
        nodes = display_node[0].getElementsByTagName('Column')
        for node in nodes:
            column = dict()
            column['Name'] = node.getAttribute('Name')
            column['Display'] = int(node.getAttribute('Display'))
            column['Width'] = int(node.getAttribute('Width'))
            self.columns_config.append(column)
            logger.debug('Add column: Name = %s, Display = %d, Width = %d' %
                         (column['Name'], column['Display'], column['Width'],))

        self.labels_config = []
        nodes = display_node[0].getElementsByTagName('Label')
        for node in nodes:
            label = dict()
            label['Name'] = node.getAttribute('Name')
            label['Display'] = int(node.getAttribute('Display'))
            label['Width'] = int(node.getAttribute('Width'))
            self.labels_config.append(label)
            logger.debug('Add label: Name = %s, Display = %d, Width = %d' %
                         (label['Name'], label['Display'], label['Width'],))

        self.servers = GerritServer(self, self.config_xml)

        return


    def import_configuration_file(self):

        fd = LoadFileDialog(self.master)
        input_file = fd.go()
        if input_file:
            try:
                self.config_xml = DOM.parse(input_file)
                self.read_configuration_file()
            except:
                logger.debug('Failed to parse configuration file %s' % input_file)

        return


    def export_configuration_file(self):

        fd = SaveFileDialog(self.master)
        output_file = fd.go()
        if output_file:
            save_configuration_file(self.config_xml, output_file)

        return


    def update_server_list(self):

        try:
            self.lb_server_list.select_clear(0, tk.END)
            self.lb_server_list.delete(0, tk.END)
            server_count = len(self.servers)
            for i in range(0, server_count):
                logger.debug('Index = %d, Name = %s' %
                             (i, self.servers[i]['Name'],))
                self.lb_server_list.insert(tk.END, self.servers[i]['Name'])
        except AttributeError:
            pass

        return


    def configure_servers(self):

        self.top_config_server = tk.Toplevel(self.master)
        self.top_config_server.title('Server Management')
        self.top_config_server.geometry(SERVER_LIST_GEOMETRY)

        frm_server_list = tk.Frame(self.top_config_server)
        scrollbar = tk.Scrollbar(frm_server_list, orient = tk.VERTICAL)
        self.lb_server_list = tk.Listbox(frm_server_list, selectmode = tk.SINGLE,
                                         height = 15, width = 50,
                                         yscrollcommand = scrollbar.set)
        scrollbar.config(command = self.lb_server_list.yview)
        scrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.lb_server_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = 1)
        self.update_server_list()
        frm_server_list.pack(anchor = tk.W, side = tk.TOP,
                             padx = 10, pady = 15)

        frm_buttons = tk.Frame(self.top_config_server)

        button_add = tk.Button(frm_buttons, text = 'Add', height = 1,
                               command = self.add_server_config)
        button_add.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_edit = tk.Button(frm_buttons, text = 'Edit', height = 1,
                                command = self.edit_server_config)
        button_edit.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_delete = tk.Button(frm_buttons, text = 'Delete', height = 1,
                                  command = self.delete_server_config)
        button_delete.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_cancel = tk.Button(frm_buttons, text = 'Cancel', height = 1,
                                  command = self.top_config_server.destroy)
        button_cancel.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        frm_buttons.pack(anchor = tk.W, side = tk.TOP, padx = 5)

        return


    def add_server_config(self):

        self.top_new_server = tk.Toplevel(self.top_config_server)
        self.top_new_server.title('New Server')
        new_server_profile = ServerProfile(self.top_new_server,
                                           self.servers,
                                           self.labels_config,
                                           is_new = True)

        return


    def edit_server_config(self):

        try:
            self.servers.index = self.lb_server_list.index(self.lb_server_list.curselection())
        except:
            return

        self.top_edit_server = tk.Toplevel(self.top_config_server)
        self.top_edit_server.title('Edit Server')
        server_profile = ServerProfile(self.top_edit_server, self.servers,
                                       self.labels_config)

        return


    def delete_server_config(self):

        try:
            self.servers.index = self.lb_server_list.index(self.lb_server_list.curselection())
            ret = tkMessageBox.askokcancel(title = 'Delete Server',
                                           message = ('Confirm to delete server "%s"?'
                                                      % self.servers[self.servers.index]['Name']),
                                           default = tkMessageBox.CANCEL,
                                           parent = self.top_config_server)
            if ret == False:
                return
        except:
            return

        self.servers.remove(self.servers.index)

        return


    def configure_preferences(self):

        self.top_config_preferences = tk.Toplevel(self.master)
        self.top_config_preferences.title('Preferences')
        self.top_config_preferences.geometry(PREFERENCES_GEOMETRY)

        frm_logging = tk.LabelFrame(self.top_config_preferences, text = 'Logging',
                                    borderwidth = 2, relief = tk.GROOVE,
                                    padx = 5, pady = 5)

        label_log_path = tk.Label(frm_logging, text = 'Path:')
        label_log_path.grid(row = 0, column = 0, sticky = tk.W,
                            padx = 5, pady = 2)
        entry_log_path = tk.Entry(frm_logging, show = None, width = 50,
                                  textvariable = self.log_path)
        entry_log_path.grid(row = 0, column = 1, columnspan = 4,
                            sticky = tk.W, padx = 5, pady = 2)

        label_log_file = tk.Label(frm_logging, text = 'File:')
        label_log_file.grid(row = 1, column = 0, sticky = tk.W,
                            padx = 5, pady = 2)
        entry_log_file = tk.Entry(frm_logging, show = None, width = 50,
                                  textvariable = self.log_file)
        entry_log_file.grid(row = 1, column = 1, columnspan = 4,
                            sticky = tk.W, padx = 5, pady = 2)

        chkbox_log_rotation = tk.Checkbutton(frm_logging, text = 'Rotation',
                                             variable = self.log_rotation,
                                             command = self.toggle_log_rotation)
        chkbox_log_rotation.grid(row = 2, column = 0, sticky = tk.W,
                                 padx = 5, pady = 2)

        self.label_log_backup_count = tk.Label(frm_logging, text = 'Backup Count:')
        self.label_log_backup_count.grid(row = 3, column = 1, sticky = tk.W,
                                         padx = 5, pady = 2)
        self.entry_log_backup_count = tk.Entry(frm_logging, show = None, width = 10,
                                               textvariable = self.log_backup_count)
        self.entry_log_backup_count.grid(row = 3, column = 2, sticky = tk.W,
                                         padx = 5, pady = 2)

        self.label_log_max_size = tk.Label(frm_logging, text = 'Max Size:')
        self.label_log_max_size.grid(row = 3, column = 3, sticky = tk.W,
                                     padx = 5, pady = 2)
        self.entry_log_max_size = tk.Entry(frm_logging, show = None, width = 10,
                                           textvariable = self.log_max_size)
        self.entry_log_max_size.grid(row = 3, column = 4, sticky = tk.W,
                                     padx = 5, pady = 2)

        self.toggle_log_rotation()

        frm_logging.pack(anchor = tk.W, side = tk.TOP, fill = tk.X,
                         padx = 10, pady = 5)

        frm_buttons = tk.Frame(self.top_config_preferences)

        button_save = tk.Button(frm_buttons, text = 'Save', height = 1,
                                command = self.save_preferences)
        button_save.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        button_cancel = tk.Button(frm_buttons, text = 'Cancel', height = 1,
                                  command = self.top_config_preferences.destroy)
        button_cancel.pack(anchor = tk.W, side = tk.LEFT, padx = 5)

        frm_buttons.pack(anchor = tk.W, side = tk.TOP, padx = 5, pady = 10)

        return


    def toggle_log_rotation(self):

        if self.log_rotation.get() == 1:
            self.label_log_backup_count.config(state = tk.NORMAL)
            self.entry_log_backup_count.config(state = tk.NORMAL)
            self.label_log_max_size.config(state = tk.NORMAL)
            self.entry_log_max_size.config(state = tk.NORMAL)
        else:
            self.label_log_backup_count.config(state = tk.DISABLED)
            self.entry_log_backup_count.config(state = tk.DISABLED)
            self.label_log_max_size.config(state = tk.DISABLED)
            self.entry_log_max_size.config(state = tk.DISABLED)
	
        return


    def save_preferences(self):

        logging_node = self.config_xml.getElementsByTagName('Logging')[0]
        logging_node.setAttribute('Path', self.log_path.get())
        logging_node.setAttribute('FileName', self.log_file.get())
        logging_node.setAttribute('Rotation', str(self.log_rotation.get()))
        logging_node.setAttribute('BackupCount', self.log_backup_count.get())
        logging_node.setAttribute('MaxSize', self.log_max_size.get())

        self.top_config_preferences.destroy()

        return


    def new_query(self):

        self.add_query_tab()

        return

    def open_query(self):

        fd = LoadFileDialog(self.master)
        query_file = fd.go(DEFAULT_QUERY_DIR)
        if query_file:
            self.add_query_tab(query_file)

        return


class ConsoleApp():

    def __init__(self, args):

        self._init_configuration(args)

        logger.info('Getting gerrits...')
        gerrits = self._run_query()

        if args.out_file:
            logger.info('Saving query result to %s' % args.out_file)
            self._save_result(args.out_file, gerrits)
        else:
            print gerrits

        return


    def _init_configuration(self, args):

        self.server = dict()
        self.query = []
        self.columns = []

        if args.server:
            self.server['URL'] = args.server
            self.server['Type'] = args.server_type
            if args.server_port:
                self.server['Port'] = args.server_port
            else:
                if self.server['Type'] == SRV_TYPE_SSH:
                    self.server['Port'] = DEFAULT_SSH_PORT
                if self.server['Type'] == SRV_TYPE_REST:
                    self.server['Port'] = DEFAULT_HTTPS_PORT
            if args.username:
                self.server['Username'] = args.username
                self.server['Password'] = ''
            if args.password:
                self.server['Password'] = args.password
        else:
            raise GerritConfigurationException('--server is not present')

        if args.query:
            self.query = args.query.split()
        else:
            if args.owner:
                self.query.append('owner:{%s}' % args.owner)
            if args.status:
                self.query.append('status:{%s}' % args.status)
            if args.project:
                self.query.append('project:{%s}' % args.project)
            if args.branch:
                self.query.append('branch:{%s}' % args.branch)

        if args.columns:
            self.columns = args.columns.split(',')
        else:
            for col in default_columns_config:
                self.columns.append(col['Name'])
            for label in default_labels_config:
                self.columns.append(label['Name'])

        return


    def _run_query(self):

        return GerritClient.query(self.server, self.query, self.columns)


    def _save_result(self, file_name, gerrits):

        with open(file_name, 'wb') as f:
            f.write(codecs.BOM_UTF8)
            writer = csv.writer(f)
            writer.writerow(self.columns)
            for gerrit in gerrits:
                values = []
                for col in self.columns:
                    if gerrit.has_key(col):
                        values.append(gerrit[col])
                    else:
                        values.append('')
                writer.writerow(values)

        return


def create_default_configuration_file():

    logger.debug('Generate configuration file')

    config_xml = DOM.Document()

    root_node = config_xml.createElement('Configuration')
    config_xml.appendChild(root_node)

    node = config_xml.createElement('Servers')
    root_node.appendChild(node)
    for server in default_servers_config:
        server_node = config_xml.createElement('Server')
        server_node.setAttribute('Name', server['Name'])
        server_node.setAttribute('URL', server['URL'])
        server_node.setAttribute('Port', server['Port'])
        server_node.setAttribute('Type', str(server['Type']))
        server_node.setAttribute('Version', server['Version'])
        node.appendChild(server_node)

    node = config_xml.createElement('Display')
    root_node.appendChild(node)

    sub_node = config_xml.createElement('Columns')
    node.appendChild(sub_node)
    for column in default_columns_config:
        column_node = config_xml.createElement('Column')
        column_node.setAttribute('Name', column['Name'])
        column_node.setAttribute('Display', str(column['Display']))
        column_node.setAttribute('Width', str(column['Width']))
        sub_node.appendChild(column_node)

    sub_node = config_xml.createElement('Labels')
    node.appendChild(sub_node)
    for label in default_labels_config:
        label_node = config_xml.createElement('Label')
        label_node.setAttribute('Name', label['Name'])
        label_node.setAttribute('Display', str(label['Display']))
        label_node.setAttribute('Width', str(label['Width']))
        sub_node.appendChild(label_node)

    node = config_xml.createElement('Preferences')
    root_node.appendChild(node)

    logging_node = config_xml.createElement('Logging')
    logging_node.setAttribute('Path', DEFAULT_LOG_DIR)
    logging_node.setAttribute('FileName', DEFAULT_LOG_FILE)
    logging_node.setAttribute('Rotation', '1')
    logging_node.setAttribute('MaxSize', str(DEFAULT_MAX_LOG_SIZE))
    logging_node.setAttribute('BackupCount', str(DEFAULT_LOG_BACKUP_COUNT))
    node.appendChild(logging_node)

    return config_xml


def get_logging_configuration(config_xml):

    logging_config = dict()

    node = config_xml.getElementsByTagName('Configuration')
    if len(node) > 0:
        root_node = node[0]
    else:
        root_node = config_xml.createElement('Configuration')

    node = root_node.getElementsByTagName('Preferences')
    if len(node) > 0:
        preferences_node = node[0]
    else:
        preferences_node = config_xml.createElement('Preferences')
        root_node.appendChild(preferences_node)
		
    node = preferences_node.getElementsByTagName('Logging')
    if len(node) > 0:
        logging_node = node[0]
        if not logging_node.hasAttribute('Path'):
            logging_node.setAttribute('Path', DEFAULT_LOG_DIR)
        if not logging_node.hasAttribute('FileName'):
            logging_node.setAttribute('FileName', DEFAULT_LOG_FILE)
        if not logging_node.hasAttribute('Rotation'):
            logging_node.setAttribute('Rotation', '1')
        if not logging_node.hasAttribute('MaxSize'):
            logging_node.setAttribute('MaxSize', str(DEFAULT_MAX_LOG_SIZE))
        if not logging_node.hasAttribute('BackupCount'):
            logging_node.setAttribute('BackupCount', str(DEFAULT_LOG_BACKUP_COUNT))
    else:
        logging_node = config_xml.createElement('Logging')
        logging_node.setAttribute('Path', DEFAULT_LOG_DIR)
        logging_node.setAttribute('FileName', DEFAULT_LOG_FILE)
        logging_node.setAttribute('Rotation', '1')
        logging_node.setAttribute('MaxSize', str(DEFAULT_MAX_LOG_SIZE))
        logging_node.setAttribute('BackupCount', str(DEFAULT_LOG_BACKUP_COUNT))
        preferences_node.appendChild(logging_node)

    logging_config['Path'] = logging_node.getAttribute('Path')
    logging_config['FileName'] = logging_node.getAttribute('FileName')
    logging_config['Rotation'] = int(logging_node.getAttribute('Rotation'))
    logging_config['MaxSize'] = int(logging_node.getAttribute('MaxSize'))
    logging_config['BackupCount'] = int(logging_node.getAttribute('BackupCount'))
		
    return logging_config


def save_configuration_file(config_xml, output_file):

    f = open(output_file, 'w+')
    dom_str = config_xml.toprettyxml(encoding = 'utf-8')
    dom_str = os.linesep.join([s for s in dom_str.splitlines() if s.strip()])
    f.write(dom_str)
    f.close()
    logger.debug('File %s is saved' % output_file)

    return


def main_gui(config_xml):

    logger.info("Session started in GUI mode")

    root = tk.Tk()
    root.title('GerritKit - Welcome %s' % getpass.getuser())
    app = App(root, config_xml)
    root.mainloop()

    save_configuration_file(app.config_xml, CONFIG_XML)

    return


def main_console(args):

    logger.info('Session started in console mode')

    try:
        app = ConsoleApp(args)
    except GerritConfigurationException as e:
        logger.error(e)
        logger.info('Run GerritKit --help for details')

    return


def main():

    try:
        os.mkdir(ROOT_DIR)
    except OSError:
        pass
    try:
        os.mkdir(CONFIG_DIR)
    except OSError:
        pass

    parser = argparse.ArgumentParser(description = 'GerritKit')
    parser.add_argument('--console', action = 'store_true', dest = 'console',
                        help = 'run in console mode')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ssh', const = SRV_TYPE_SSH, action = 'store_const',
                       dest = 'server_type', default = SRV_TYPE_SSH,
                       help = 'using SSH APIs (default)')
    group.add_argument('--rest', const = SRV_TYPE_REST, action = 'store_const',
                       dest = 'server_type', help = 'using REST APIs')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--debug', const = logging.DEBUG, action = 'store_const',
                       dest = 'loglevel', default = logging.INFO,
                       help = 'verbose debug output')
    group.add_argument('--quiet', const = logging.WARNING, action = 'store_const',
                       dest = 'loglevel', help = 'be quiet')
    parser.add_argument('--owner', metavar = '<USER>', dest = 'owner',
                        help = 'gerrit owned by <USER>')
    parser.add_argument('--status', metavar = '<STATUS>', dest = 'status',
                        help = '<STATUS> = open | reviewed | closed | merged | abandoned')
    parser.add_argument('--project', metavar = '<PROJECT>', dest = 'project',
                        help = 'gerrit in <PROJECT>')
    parser.add_argument('--branch', metavar = '<BRANCH>', dest = 'branch',
                        help = 'gerrit in <BRANCH>')
    parser.add_argument('--query', metavar = '<QUERY>', dest = 'query',
                        help = 'user-defined <QUERY>')
    parser.add_argument('--server', metavar = '<SERVER>', dest = 'server',
                        help = 'gerrit server')
    parser.add_argument('--server-port', metavar ='<PORT>',
                        dest = 'server_port', help = 'gerrit server port')
    parser.add_argument('--username', metavar = '<USERNAME>', dest = 'username',
                        help = 'login username')
    parser.add_argument('--password', metavar = '<PASSWORD>', dest = 'password',
                        help = 'login password')
    parser.add_argument('--columns', metavar = '<COL1,COL2,...>', dest = 'columns',
                        help = 'query columns')
    parser.add_argument('--output', metavar = '<FILE>', dest = 'out_file',
                        help = 'save to <FILE>')
    args = parser.parse_args()

    logger = logging.getLogger('GerritLogger')
    logger.setLevel(logging.DEBUG)

    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(args.loglevel)
    logger.addHandler(stdout_handler)

    try:
        config_xml = DOM.parse(CONFIG_XML)
        logger.debug('File %s is found' % CONFIG_XML)
    except IOError:
        logger.debug('File %s is not found, initialize configuration' % CONFIG_XML)
        config_xml = create_default_configuration_file()

    try:
        os.mkdir(DEFAULT_QUERY_DIR)
    except OSError:
        pass

    logging_config = get_logging_configuration(config_xml)
    try:
        os.mkdir(logging_config['Path'])
    except OSError:
        pass
    log_file_name = os.path.join(logging_config['Path'], logging_config['FileName'])
    fmt = '[%(asctime)s][%(className)s.%(funcName)s][%(levelname)s]: %(message)s'
    if logging_config['Rotation'] == 1:
        log_handler = RotatingFileHandler(log_file_name,
                                          maxBytes = logging_config['MaxSize'],
                                          backupCount = logging_config['BackupCount'])
        log_formatter = GerritRotatingLogFormatter(fmt)
    else:
        log_handler = logging.FileHandler(log_file_name)
        log_formatter = GerritLogFormatter(fmt)
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    logger.info('--- Session Start ---')

    if args.console:
        main_console(args)
    else:
        main_gui(config_xml)

    logger.info('--- Session End ---')

    return


if __name__ == '__main__':
    main()

