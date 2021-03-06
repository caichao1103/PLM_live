# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/12/30
# FileName:     unity_tool.py
# Description:  Tool for Unity

import os
import thread
from buildtools import common, log_tool


def build(method, unity_path, project_path, log_path):
    """
    call unity to build a project
    :param method:
    :param unity_path:
    :param project_path:
    :param log_path:
    :return:
    """
    build_cmd = [unity_path,
                 '-batchmode',
                 '-projectPath', project_path,
                 '-nographics',
                 '-executeMethod', method,
                 '-logFile', log_path,
                 '-quit']
    log_tool.show_info('Start Unity...')

    if os.path.exists(log_path):
        os .remove(log_path)
        log_tool.show_info('Delete the old logfile!')

    thread.start_new_thread(common.start_thread_to_tail, (log_path,))

    log_tool.show_info('Run Unity Command: {}'.format(' '.join(build_cmd)))
    result_file = 'result.txt'

    common.run_command_write_result_to_file(build_cmd, result_file, is_print=True, cwd=project_path)
    log_tool.show_info('Run Command is done!')


def build_with_params(method,
                      unity_path,
                      project_path,
                      log_path,
                      build_params):
    """
    call unity to build with params
    :param method:
    :param unity_path:
    :param project_path:
    :param log_path:
    :param build_params
    :return:
    """
    build_cmd = [unity_path,
                 '-batchmode',
                 '-projectPath', project_path,
                 '-nographics',
                 '-executeMethod', method,
                 '-logFile', log_path,
                 '-quit']

    if build_params:
        build_cmd = build_cmd + build_params

    log_tool.show_info('Start Unity...')

    if os.path.exists(log_path):
        os .remove(log_path)
        log_tool.show_info('Delete the old logfile!')

    thread.start_new_thread(common.start_thread_to_tail, (log_path,))

    log_tool.show_info('[INFO]: Run Unity Command: {}'.format(' '.join(build_cmd)))
    result_file = 'result.txt'

    common.run_command_write_result_to_file(build_cmd, result_file, is_print=True, cwd=project_path)
    log_tool.show_info('Run Command is done!')
