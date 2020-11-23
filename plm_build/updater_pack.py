# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/12/31
# FileName:     updater_pack.py
# Description:  

import os
import sys
import project_globalvalue
from buildtools import common
from buildtools import globalvalue_tool as globalvalue_tool
from workspace import WorkSpace

CURRENT_PATH = os.path.abspath(__file__)
RESOURCES_PACKER_PATH = os.path.join(os.path.dirname(CURRENT_PATH), 'resources_packer.py')
PACKAGE_NAME_PREFIX = globalvalue_tool.get_value("package_name_prefix")


def pack(svn_branch, svn_version, main_version, platform, project_path, project_name, package_setting, is_packbase, is_restart=False, is_bacekground_update=True):
    """生成更新包"""
    # 不指定版本,默认将置为0
    if (svn_version == ''):
        svn_version = '0'

    svn_name = svn_branch if '/' not in svn_branch else svn_branch.replace('/', '_')
    hot_package_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(project_path))), 'FtpShare/HotPackage')
    hot_package_dir = os.path.join(hot_package_dir, project_name)
    package_dir_base = os.path.join(hot_package_dir, svn_name)
    package_path = os.path.join(package_dir_base, main_version)
    package_dir = os.path.join(package_path, '{}/{}'.format(platform, package_setting.package_dir_name))
    package_name = PACKAGE_NAME_PREFIX + "." + main_version

    if not os.path.isdir(package_dir):
        os.makedirs(package_dir)

    package_paths = []

    # 包含的pack或者patch
    for pack_dir in package_setting.pack_dirs:
        if is_packbase:
            # 第一次打包，需要打包packdata
            patch_path = os.path.join(project_path, 'Assets/StreamingAssets/Res/{}'.format(pack_dir))
        else:
            patch_path = os.path.join(project_path, 'Patch/{}'.format(pack_dir))
        package_paths.append(patch_path)

    # 包含的Bundle
    bundle_base_path = os.path.join(project_path, 'Bundles')
    if platform== "iOS":
        bundle_base_path = os.path.join(bundle_base_path, 'iOS')
    elif platform == "Android":
        bundle_base_path = os.path.join(bundle_base_path, 'Android')
    elif platform == "Windows":
        bundle_base_path = os.path.join(bundle_base_path, 'Windows')
    else:
        bundle_base_path = os.path.join(bundle_base_path, 'MacOS')

    for bundle_dir in package_setting.bundle_dirs:
        bundle_path = os.path.join(bundle_base_path, bundle_dir.lower())
        package_paths.append(bundle_path)

    for bundle_file in package_setting.bundle_files:
        bundle_path = os.path.join(bundle_base_path, bundle_file.lower())
        package_paths.append(bundle_path)

    if package_setting.include_bundle_manifest:
        if platform== "iOS":
            bundle_path = os.path.join(bundle_base_path, 'iOS')
            package_paths.append(bundle_path)

            bundle_path = os.path.join(bundle_base_path, 'iOS.manifest')
            package_paths.append(bundle_path)
        elif platform == "Android":
            bundle_path = os.path.join(bundle_base_path, 'Android')
            package_paths.append(bundle_path)

            bundle_path = os.path.join(bundle_base_path, 'Android.manifest')
            package_paths.append(bundle_path)
        elif platform == "Windows":
            bundle_path = os.path.join(bundle_base_path, 'Windows')
            package_paths.append(bundle_path)

            bundle_path = os.path.join(bundle_base_path, 'Windows.manifest')
            package_paths.append(bundle_path)
        else:
            bundle_path = os.path.join(bundle_base_path, 'MacOS')
            package_paths.append(bundle_path)

            bundle_path = os.path.join(bundle_base_path, 'MacOS.manifest')
            package_paths.append(bundle_path)


    # 执行原始包检查
    _updater_package_action(package_paths, project_path, package_dir, package_name, main_version, False, False, 'check')
    # 生成新包
    _updater_package_action(package_paths, project_path, package_dir, package_name, main_version, is_restart, is_bacekground_update, 'pack')


def _updater_package_action(paths, project_path, package_dir, package_name, main_version,
                            is_need_restart, is_need_back_update,
                            action=['check', 'pack']):
    # 需要打包目录
    """生成新包"""
    command = ['python', RESOURCES_PACKER_PATH, '-paths']
    if isinstance(paths, list):
        for path in paths:
            command.append(path)
    else:
        command.append(paths)

    command = command + [
        '-project-path', project_path,
        '-package-name', package_name,
        '-artifact-dir', package_dir,
        '-main-version', main_version,
        '-action', action,
        '-ignores-ext', '.meta', '.svn', '.git',]

    need_restart = "-need-restart"
    need_back = "-need-back"

    # 是否需要重启
    if is_need_restart == "True":
        command.append(need_restart)

    if is_need_back_update == "True":
        command.append(need_back)

    print "run command = {}".format(command)
    common.run_command(command)

if __name__ == '__main__':
    if len(sys.argv) != 11:
        print "[ERROR]: Parameter error! Parameter count: %d" % len(sys.argv)
        exit(1)
    get_svn_branch = sys.argv[1]
    get_svn_version = sys.argv[2]
    get_main_version = sys.argv[3]
    get_platform = sys.argv[4]
    get_project_path = sys.argv[5]
    get_project_name = sys.argv[6]
    get_package_dir_name = sys.argv[7]
    get_is_packbase = (sys.argv[8] == 'True')
    get_is_restart = sys.argv[9]
    get_is_background = sys.argv[10]

    print "[updater_pack] Params - SVN_BRANCH: {} SVN_VERSION: {} MAIN_VERSION: {} PLATFORM: {} PROJECT_PATH: {} PROJECT_NAME: {} PACKAGE_DIR_NAME: {} IS_PACKBASE: {} IS_RESTART: {} IS_BACKGRUND: {} ".format(
        get_svn_branch, get_svn_version, get_main_version, get_platform, get_project_path, get_project_name, get_package_dir_name, get_is_packbase, get_is_restart,
        get_is_background)

    # current path
    CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

    # InitWorkSpace
    workdirbase = os.path.dirname(os.path.dirname(CURRENT_PATH))
    if not os.path.isdir(workdirbase):
        os.makedirs(workdirbase)
    workspace = WorkSpace(workdirbase, get_svn_branch)

    update_package_setting = workspace.get_update_package_setting()
    if not update_package_setting or not update_package_setting.has_key(get_package_dir_name):
        print('package_dir_name:{} not in package_setting')
        exit(1)

    package_setting = update_package_setting[get_package_dir_name]
    pack(get_svn_branch, get_svn_version, get_main_version, get_platform, get_project_path, get_project_name, package_setting, 
        get_is_packbase, is_restart=get_is_restart, is_bacekground_update=get_is_background)
