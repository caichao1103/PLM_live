# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/12/30
# FileName:     auto_build_update_package
# Description:  Auto build update package

import os
import shutil
import json
import project_globalvalue
from buildtools import common, log_tool
from workspace import WorkSpace
from shutil import *
from buildtools import globalvalue_tool as globalvalue_tool


BRANCH_NAME = os.environ.get('BRANCH_NAME')
if BRANCH_NAME:
    LOCAL_OP = False
    LANGUAGE = os.environ.get('LANGUAGE')
    MAIN_VERSION = os.environ.get('MAIN_VERSION')
    PLATFORM = os.environ.get('PLATFORM')
    IS_REBOOT = os.environ.get('IS_REBOOT').capitalize()
    IS_BACKGROUND_UPDATE = os.environ.get('IS_BACKGROUND_UPDATE').capitalize()
    VERSION_NUMBER = os.environ.get('VERSION_NUMBER')
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    LANGUAGE = 'LANG_ZH_CN'
    MAIN_VERSION = '0.1.0.0'
    PLATFORM = 'Android'
    IS_REBOOT = 'False'
    IS_BACKGROUND_UPDATE = 'False'
    VERSION_NUMBER = ''


# PackageNamePrefix
PACKAGE_NAME_PREFIX = globalvalue_tool.get_value("package_name_prefix")

# ProjectName
PROJECT_NAME = globalvalue_tool.get_value("project_name")

# 参数判空处理
if VERSION_NUMBER is None:
    VERSION_NUMBER = ''

# current path
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

# InitWorkSpace
workdirbase = os.path.dirname(os.path.dirname(CURRENT_PATH))
if not os.path.isdir(workdirbase):
    os.makedirs(workdirbase)
workspace = WorkSpace(workdirbase, BRANCH_NAME)

# Product Update
def UpdateProduct():
    if VERSION_NUMBER != '':
        workspace.up_product(VERSION_NUMBER)
    else:
        workspace.up_product()


# 是否需要打基础包
def NeedBasePack(update_dir):
    hot_package_dir = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/HotPackage')
    hot_package_dir = os.path.join(hot_package_dir, PROJECT_NAME)
    branch_name = BRANCH_NAME if '/' not in BRANCH_NAME else BRANCH_NAME.replace('/', '_')
    package_dir_base = os.path.join(hot_package_dir, branch_name)
    package_path = os.path.join(package_dir_base, MAIN_VERSION)
    package_dir = os.path.join(package_path, '{}/{}'.format(PLATFORM, update_dir))
    package_name = PACKAGE_NAME_PREFIX + "." + MAIN_VERSION
    version_file = '{}/{}.resource_version.txt'.format(package_dir, package_name)

    return not os.path.isfile(version_file)


def Pack(package_setting, is_packbase):
    # FilePacker path
    if common.is_windows():
        filepackerpath = os.path.join(workspace.unity_project_path, 'FilePacker.exe')
    else:
        filepackerpath = os.path.join(workspace.unity_project_path, 'FilePacker')
        # 获取执行权限
        os.chdir(workspace.unity_project_path)
        chmod = ['chmod', '755', 'FilePacker']
        common.run_command(chmod)

    UPDATER_PACK_PATH = os.path.join(CURRENT_PATH, 'updater_pack.py')
    UPDATER_CMD = ['python',
                   UPDATER_PACK_PATH,
                   BRANCH_NAME,
                   VERSION_NUMBER,
                   MAIN_VERSION,
                   PLATFORM,
                   workspace.unity_project_path,
                   PROJECT_NAME,
                   package_setting.package_dir_name,
                   '{}'.format(is_packbase),
                   IS_REBOOT,
                   IS_BACKGROUND_UPDATE]

    # 生成Patch包
    for pack_dir in package_setting.pack_dirs:
        pack_idx_path = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}/pack.idx'.format(pack_dir))
        pack_dat_path = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}/pack0.dat'.format(pack_dir))

        if not os.path.isfile(pack_idx_path) or not os.path.isfile(pack_dat_path):
            log_tool.show_error("Can't find {} and {}".format(pack_idx_path, pack_dat_path))
            exit(1)

        if not is_packbase:
            pack_settings = workspace.get_pack_setting()
            if not pack_settings:
                log_tool.show_error("GetPackSetting Failed")
                exit(1)

            if not pack_settings.has_key(pack_dir):
                log_tool.show_error('{} not in PackSetting'.format(pack_dir))
                exit(1)

            patch_srcfile_path = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}/pack.patch'.format(pack_dir))
            patch_path = os.path.join(workspace.unity_project_path, 'Patch/{}'.format(pack_dir))
            patch_idx_path = os.path.join(patch_path, 'pack.idx')
            patch_dstfile_path = os.path.join(patch_path, 'pack.patch')

            if os.path.isdir(patch_path):
                shutil.rmtree(patch_path)
            os.makedirs(patch_path)

            # 修改pack配置文件
            pack_ini_file = os.path.join(workspace.unity_project_path, 'FilePacker.ini')
            pack_setting = pack_settings[pack_dir]
            # outdir
            config_content = '[FilePacker]\n'
            config_content = '{}DstPath=Assets/StreamingAssets/Res/{}\n'.format(config_content, pack_dir)
            # folders
            folder_index = 1
            for folder in pack_setting.folders:
                config_content = '{}Folder{}={}\n'.format(config_content, folder_index, folder)
                folder_index = folder_index + 1
            # files
            file_index = 1
            for file in pack_setting.files:
                config_content = '{}File{}={}\n'.format(config_content, file_index, file)
                file_index = file_index + 1
            file = open(pack_ini_file, 'w')
            file.write(config_content)
            file.close()

            log_tool.show_info('Run FilePacker --patch')
            common.run_command([filepackerpath, '--patch'])
            log_tool.show_info('Run FilePacker --patch is done!')

            if os.path.isfile(pack_idx_path) and os.path.isfile(patch_srcfile_path):
                log_tool.show_info('Copy {} --> {}'.format(pack_idx_path, patch_idx_path))
                shutil.copyfile(pack_idx_path, patch_idx_path)
                log_tool.show_info('Copy {} --> {}'.format(patch_srcfile_path, patch_dstfile_path))
                shutil.copyfile(patch_srcfile_path, patch_dstfile_path)
            else:
                log_tool.show_info("Can't find {}! No Change!".format(patch_srcfile_path))

    # 生成热更包
    log_tool.show_info("========== Run updater_pack.py ==========")
    common.run_command(UPDATER_CMD)


# 生成版本信息文件
def CreateVersionInfo(update_package_setting):
    hot_package_dir = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/HotPackage')
    hot_package_dir = os.path.join(hot_package_dir, PROJECT_NAME)
    branch_name = BRANCH_NAME if '/' not in BRANCH_NAME else BRANCH_NAME.replace('/', '_')
    package_dir_base = os.path.join(hot_package_dir, branch_name)
    package_path = os.path.join(package_dir_base, MAIN_VERSION)
    package_dir = os.path.join(package_path, PLATFORM)
    package_name = PACKAGE_NAME_PREFIX + "." + MAIN_VERSION
    version_file = os.path.join(package_dir, 'version_info.txt')

    if not os.path.isdir(package_dir):
        os.makedirs(package_dir)

    # mainVersion
    version_info = {}
    version_info['mainVersion'] = MAIN_VERSION
    
    # updateVersion
    update_version_info = {}
    for setting in update_package_setting.values():
        resource_version = '{}/{}/{}.resource_version.txt'.format(package_dir, setting.package_dir_name, package_name)
        strVersion = ''
        with open(resource_version, 'rb+') as f:
            strVersion = f.read()
        update_version_info[setting.package_dir_name] = int(strVersion)
    version_info['updateVersion'] = update_version_info

    # write file
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    if LOCAL_OP is False:
        UpdateProduct()

    update_package_setting = workspace.get_update_package_setting()
    if not update_package_setting:
        log_tool.show_error('Get UpdatePackageSetting Failed!')
        exit(1)

    # 生成全部更新包
    for setting in update_package_setting.values():
        is_packbase = NeedBasePack(setting.package_dir_name)
        Pack(setting, is_packbase)

    # 生成版本信息文件
    CreateVersionInfo(update_package_setting)
