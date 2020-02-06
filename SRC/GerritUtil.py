#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, Lissy Lau <lissy.lau@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#
# GerritUtil
#
# Utilities for GerritKit
#

__version__ = '0.1'
__author__ = 'Lissy Lau <lissy.lau@gmail.com>'

import sys
import logging
import inspect

reload(sys)
sys.setdefaultencoding('utf-8')

class GerritLogFormatter(logging.Formatter):

    def format(self, record):

        stack = inspect.stack()

        try:
            className = stack[9][0].f_locals['self'].__class__.__name__
        except KeyError:
            className = 'Global'
        record.className = className

        return super(GerritLogFormatter, self).format(record)


class GerritRotatingLogFormatter(logging.Formatter):

    def format(self, record):

        stack = inspect.stack()

        try:
            className = stack[10][0].f_locals['self'].__class__.__name__
        except KeyError:
            className = 'Global'
        record.className = className

        return super(GerritRotatingLogFormatter, self).format(record)

