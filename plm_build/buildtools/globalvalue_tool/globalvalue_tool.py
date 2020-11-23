# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/04/19
# FileName:     globalvalue_tool.py
# Description:  Tool for globalvalue

from buildtools import log_tool

# 全局变量放在这里
globalvalue = {}

def set_value(value_name, value):
    globalvalue[value_name] = value


def get_value(value_name):
    try:
        return globalvalue[value_name]
    except Exception as e:
        log_tool.show_error('GlobalValue {} not Exist!'.format(value_name))
        return None
