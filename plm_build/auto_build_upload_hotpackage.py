# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2020/04/17
# FileName:     auto_build_upload_hotpackage
# Description:  Auto build upload hotpackage

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
    UPDATE_VERSION_NUMBER = int(os.environ.get('UPDATE_VERSION_NUMBER'))
    PACK_DIR = os.environ.get('PACK_DIR')
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    MAIN_VERSION = '0.1.0.0'
    PLATFORM = 'Android'
    UPDATE_VERSION_NUMBER = -1
    PACK_DIR = 'Base'

# ProjectName
PROJECT_NAME = globalvalue_tool.get_value("project_name")

# PackageNamePrefix
PACKAGE_NAME_PREFIX = globalvalue_tool.get_value("package_name_prefix")

# 热更包支持的最大版本间隔
MAX_VERSION_SPAN = globalvalue_tool.get_value("max_package_version_span")

# current path
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

# InitWorkSpace
workdirbase = os.path.dirname(os.path.dirname(CURRENT_PATH))
if not os.path.isdir(workdirbase):
    os.makedirs(workdirbase)
workspace = WorkSpace(workdirbase, BRANCH_NAME)


# 获取生成需要上传的热更包目录
def _GetUploadDir():
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/UploadPackage')
    upload_dir = os.path.join(upload_dir, '{}/{}/{}/{}'.format(PROJECT_NAME, BRANCH_NAME, MAIN_VERSION, PLATFORM))

    return upload_dir

# 获取热更包目录
def _GetHotPackageDir():
    hot_package_dir = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/HotPackage')
    branch_name = BRANCH_NAME if '/' not in BRANCH_NAME else BRANCH_NAME.replace('/', '_')
    hot_package_dir = os.path.join(hot_package_dir, '{}/{}/{}/{}'.format(PROJECT_NAME, branch_name, MAIN_VERSION, PLATFORM))

    return hot_package_dir

# 获取临时拷贝目录
def _GetTempDir():
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'TempHotPackage')
    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)

    return temp_dir

# 获取最新的更新版本号
def _GetLastVersionNumber(resource_version_path):
    strVersion = ''
    with open(resource_version_path, 'rb+') as f:
        strVersion = f.read()
    return int(strVersion)


# 生成指定目录的上传更新包
def ProduceUploadPackage(pack_dir):
    temp_dir = _GetTempDir()
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)

    hot_package_dir = _GetHotPackageDir()
    hot_package_dir = os.path.join(hot_package_dir, pack_dir)
    if not os.path.isdir(hot_package_dir):
        log_tool.show_error('HotPackageDir {} not Exist!'.format(hot_package_dir))
        return
    
    upload_package_list = Queue.Queue()

    # 拷贝resource_version
    resource_version_path = os.path.join(hot_package_dir, '{}.{}.resource_version.txt'.format(PACKAGE_NAME_PREFIX, MAIN_VERSION))
    upload_package_list.put(resource_version_path)

    global UPDATE_VERSION_NUMBER
    if UPDATE_VERSION_NUMBER == -1:
        UPDATE_VERSION_NUMBER = _GetLastVersionNumber(resource_version_path)

    for i in range(0, UPDATE_VERSION_NUMBER):
        if i == 0 or UPDATE_VERSION_NUMBER - i <= MAX_VERSION_SPAN:
            zipfile_name = '{}.{}.{}-{}.zip'.format(PACKAGE_NAME_PREFIX, MAIN_VERSION, i, UPDATE_VERSION_NUMBER)
            zipfile_path = os.path.join(hot_package_dir, zipfile_name)
            zipfile_md5_path = '{}.md5'.format(zipfile_path)
            zipfile_info_path = '{}.info'.format(zipfile_path)

            upload_package_list.put(zipfile_path)
            upload_package_list.put(zipfile_md5_path)
            upload_package_list.put(zipfile_info_path)

    temp_dir = _GetTempDir()
    branch_name = BRANCH_NAME if '/' not in BRANCH_NAME else BRANCH_NAME.replace('/', '_')
    copy_dir = os.path.join(temp_dir, '{}/{}/{}/{}'.format(branch_name, MAIN_VERSION, PLATFORM, pack_dir))
    if not os.path.isdir(copy_dir):
        os.makedirs(copy_dir)

    while not upload_package_list.empty():
        source_file_path = upload_package_list.get()
        target_file_path = os.path.join(copy_dir, os.path.basename(source_file_path))
        if os.path.isfile(source_file_path):
            log_tool.show_info('=================== Copy {} to {} ======================'.format(source_file_path, target_file_path))
            shutil.copyfile(source_file_path, target_file_path)
        else:
            log_tool.show_error("Can't find the file {}".format(source_file_path))
            return

    # zip file
    os.chdir(temp_dir)
    upload_package_zipfile = '{}.{}.{}-{}.zip'.format(PACKAGE_NAME_PREFIX, PLATFORM, MAIN_VERSION, UPDATE_VERSION_NUMBER)
    zip_cmd = ['zip', '-r', upload_package_zipfile, branch_name]
    common.run_command(zip_cmd)

    # 拷贝到热更包目录
    upload_dir = _GetUploadDir()
    upload_dir = os.path.join(upload_dir, pack_dir)
    if not os.path.isdir(upload_dir):
        os.makedirs(upload_dir)
        
    target_file_path = os.path.join(upload_dir, os.path.basename(upload_package_zipfile))
    shutil.copyfile(upload_package_zipfile, target_file_path)

    # 删除临时目录
    shutil.rmtree(temp_dir)

    log_tool.show_info('auto_build_upload_hotpackage Done!')


# 生成上传更新包
def ProducePackage():
    if not PACK_DIR or PACK_DIR == '':
        log_tool.show_error("PACK_DIR is none!")
        return

    ProduceUploadPackage(PACK_DIR)

if __name__ == '__main__':
    ProducePackage()
