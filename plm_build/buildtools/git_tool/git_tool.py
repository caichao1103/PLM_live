# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/1/3
# FileName:     git_tool.py
# Description:  Tool for git

import os
import sys
import shutil
import platform
from subprocess import check_output
from buildtools import common, log_tool


def git_clone(git_url, local_path):
    """
    git clone
    :param git_url:
    :param local_path:
    :return:
    """
    cmd = ['git', 'clone', git_url, local_path]
    common.run_command(cmd)


def git_cleanup(local_path):
    """
    git cleanup
    :param local_path:
    :return:
    """
    os.chdir(local_path)

    cmd = ['git', 'add', '.']
    common.run_command(cmd)
    cmd = ['git', 'stash', 'save', 'remove']
    common.run_command(cmd)
    cmd = ['git', 'stash', 'clear']
    common.run_command(cmd)


def git_switch(local_path, branch_name):
    """
    git switch
    :param local_path:
    :param branch_name:
    :return:
    """
    os.chdir(local_path)
    cmd = ['git', 'checkout', branch_name]
    common.run_command(cmd)


def git_up(local_path, version_number=None):
    """
    git up
    :param local_path:
    :param version_number:
    :return:
    """ 
    os.chdir(local_path)
    if version_number:
        cmd = ['git', 'reset', '--hard', version_number]
        common.run_command(cmd)
    else:
        cmd = ['git', 'pull']
        common.run_command(cmd)


def git_add(local_path, add_list):
    """
    git add
    :param local_path:
    :param add_list:
    :return:
    """ 
    os.chdir(local_path)
    if type(add_list) == str:
        addlist = [add_list]
    else:
        addlist = add_list

    cmd = ['git', 'add'] + addlist
    common.run_command(cmd)


def git_delete(local_path, remove_list):
    """
    git delete
    :param local_path:
    :param remove_list:
    :return:
    """
    os.chdir(local_path)
    if type(remove_list) == str:
        removelist = [remove_list]
    else:
        removelist = remove_list

    cmd = ['git', 'rm', '-r'] + removelist
    common.run_command(cmd)


def git_revert(local_path, revert_list):
    """
    git revert
    :param local_path:
    :param revert_list:
    :return:
    """
    os.chdir(local_path)
    if type(revert_list) == str:
        revertlist = [revert_list]
    else:
        revertlist = revert_list

    cmd = ['git', 'reset', 'HEAD'] + revertlist
    common.run_command(cmd)
    cmd = ['git', 'checkout'] + revertlist
    common.run_command(cmd)


def git_commit(local_path, message):
    """
    git commit
    :param local_path:
    :param message:
    :return:
    """ 
    os.chdir(local_path)

    # 先Commit
    cmd = ['git', 'commit', '--allow-empty', '-m', message]
    common.run_command(cmd)

    # 再Push
    cmd = ['git', 'push']
    common.run_command(cmd)
