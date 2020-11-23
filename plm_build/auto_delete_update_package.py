# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2020/04/20
# FileName:     auto_delete_update_package
# Description:  自动删除指定版本后的所有热更版本

import os
import Queue
import shutil
import project_globalvalue
from buildtools import common, log_tool
from workspace import WorkSpace
from buildtools import globalvalue_tool as globalvalue_tool

BRANCH_NAME = os.environ.get('BRANCH_NAME')
if BRANCH_NAME:
    LOCAL_OP = False
    MAIN_VERSION = os.environ.get('MAIN_VERSION')
    PLATFORM = os.environ.get('PLATFORM')
    DELETE_VERSION_NUMBER = int(os.environ.get('DELETE_VERSION_NUMBER'))
    PACK_DIR = os.environ.get('PACK_DIR')
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    MAIN_VERSION = '0.1.0.0'
    PLATFORM = 'Android'
    DELETE_VERSION_NUMBER = -1
    PACK_DIR = 'Base'

# ProjectName
PROJECT_NAME = globalvalue_tool.get_value("project_name")

# PackageNamePrefix
PACKAGE_NAME_PREFIX = globalvalue_tool.get_value("package_name_prefix")

# current path
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

# InitWorkSpace
workdirbase = os.path.dirname(os.path.dirname(CURRENT_PATH))
if not os.path.isdir(workdirbase):
    os.makedirs(workdirbase)
workspace = WorkSpace(workdirbase, BRANCH_NAME)


# 获取热更包目录
def _GetHotPackageDir():
    hot_package_dir = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/HotPackage')
    branch_name = BRANCH_NAME if '/' not in BRANCH_NAME else BRANCH_NAME.replace('/', '_')
    hot_package_dir = os.path.join(hot_package_dir, '{}/{}/{}/{}'.format(PROJECT_NAME, branch_name, MAIN_VERSION, PLATFORM))

    return hot_package_dir


# 获取最新的更新版本号
def _GetLastVersionNumber(resource_version_path):
    strVersion = ''
    with open(resource_version_path, 'rb+') as f:
        strVersion = f.read()
    return int(strVersion)


# 设置最新的更新版本号
def _SetLastVersionNumber(resource_version_path, version_number):
    with open(resource_version_path, 'wb+') as wf:
        wf.write(str(version_number).zfill(0))

    log_tool.show_info('SetLastVersionNumber {} Done!'.format(version_number))


# 删除指定目录更新包
def DeleteUpdatePackage(pack_dir):
    hot_package_dir = _GetHotPackageDir()
    hot_package_dir = os.path.join(hot_package_dir, pack_dir)
    if not os.path.isdir(hot_package_dir):
        log_tool.show_info('HotPackageDir {} not Exist!'.format(hot_package_dir))
        return

    # 获取最新版本号
    resource_version_path = os.path.join(hot_package_dir, '{}.{}.resource_version.txt'.format(PACKAGE_NAME_PREFIX, MAIN_VERSION))
    last_version_number = _GetLastVersionNumber(resource_version_path)
    if last_version_number == 0:
        log_tool.show_info('last_version_number = {}, no update_version to delete!'.format(last_version_number))
        return

    global DELETE_VERSION_NUMBER
    if DELETE_VERSION_NUMBER == -1:
        DELETE_VERSION_NUMBER = last_version_number
    if DELETE_VERSION_NUMBER > last_version_number:
        log_tool.show_error('DELETE_VERSION_NUMBER {} > last_version_number {}', DELETE_VERSION_NUMBER, last_version_number)
        return
    
    delete_package_list = Queue.Queue()

    delete_version_number = last_version_number
    while delete_version_number >= DELETE_VERSION_NUMBER:
        for i in range(0, delete_version_number):
            zipfile_name = '{}.{}.{}-{}.zip'.format(PACKAGE_NAME_PREFIX, MAIN_VERSION, i, delete_version_number)
            zipfile_path = os.path.join(hot_package_dir, zipfile_name)
            zipfile_md5_path = '{}.md5'.format(zipfile_path)
            zipfile_info_path = '{}.info'.format(zipfile_path)

            if os.path.isfile(zipfile_path):
                delete_package_list.put(zipfile_path)
            if os.path.isfile(zipfile_md5_path):
                delete_package_list.put(zipfile_md5_path)
            if os.path.isfile(zipfile_info_path):
                delete_package_list.put(zipfile_info_path)

        version_zipfile_manifest_path = os.path.join(hot_package_dir, '{}.{}.{}.zip.manifest'.format(PACKAGE_NAME_PREFIX, MAIN_VERSION, delete_version_number))
        version_zipfile_info_path = os.path.join(hot_package_dir, '{}.{}.{}.zip.info'.format(PACKAGE_NAME_PREFIX, MAIN_VERSION, delete_version_number))
        if os.path.isfile(version_zipfile_manifest_path):
            delete_package_list.put(version_zipfile_manifest_path)
        if os.path.isfile(version_zipfile_info_path):
            delete_package_list.put(version_zipfile_info_path)

        delete_version_number = delete_version_number - 1

    # 删除热更版本文件
    while not delete_package_list.empty():
        source_file_path = delete_package_list.get()
        os.remove(source_file_path)

    # 更新热更版本号
    _SetLastVersionNumber(resource_version_path, DELETE_VERSION_NUMBER - 1)

    log_tool.show_info('auto_delete_update_package Done!')

# 删除指定Pack
def DeletePackage():
    if not PACK_DIR or PACK_DIR == '':
        log_tool.show_error("PACK_DIR is none!")
        return

    DeleteUpdatePackage(PACK_DIR)

if __name__ == '__main__':
    DeletePackage()
