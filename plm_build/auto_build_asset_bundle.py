# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/01/14
# FileName:     auto_build_asset_bundle
# Description:  Auto build AssetBundle

import os
import fileinput
import shutil
import string
import project_globalvalue
from buildtools import common, git_tool, log_tool, unity_tool
from buildtools import globalvalue_tool as globalvalue_tool
from workspace import WorkSpace


BRANCH_NAME = os.environ.get("BRANCH_NAME")
if BRANCH_NAME:
    LOCAL_OP = False
    LANGUAGE = os.environ.get('LANGUAGE')
    PLATFORM = os.environ.get('PLATFORM')
    IS_REBUILD = False if os.environ.get('IS_REBUILD') == 'false' else True
    VERSION_NUMBER = os.environ.get('VERSION_NUMBER')
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    LANGUAGE = 'zh_CN'
    PLATFORM = 'Android'
    IS_REBUILD = True
    VERSION_NUMBER = ''

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

# UnityPath
UNITY_PATH = globalvalue_tool.get_value("windows_unity_path")
if common.is_macos():
    UNITY_PATH = globalvalue_tool.get_value("macos_uinty_path")


# Product Update
def UpdateProduct():
    if VERSION_NUMBER != '':
        workspace.up_product(VERSION_NUMBER)
    else:
        workspace.up_product()


# 打包AB
def BuildAssetBundle():
    # 先更新到最新
    if LOCAL_OP is False:
        UpdateProduct()

    log_tool.show_info('[REBUILD] --> {}'.format(IS_REBUILD))
    ab_path = os.path.join(workspace.unity_project_path, 'Bundles')
    platform_bundle_path = os.path.join(ab_path, PLATFORM)

    if IS_REBUILD is True:
        # 如果是Rebuild，需要删除库里的Bundles目录
        log_tool.show_info('[AutoBuild] Rebuild AssetBundle, Delete Bundle Direcotory for {}'.format(PLATFORM))
        if os.path.isdir(platform_bundle_path):
            if LOCAL_OP is False:
                git_tool.git_delete(workspace.product_path, platform_bundle_path)
                git_tool.git_commit(workspace.product_path, '[AutoBuild] Rebuild AssetBundle, Delete Bundle Direcotory for {}'.format(PLATFORM))
            else:
                shutil.rmtree(platform_bundle_path)

        build_function = 'KGame.KAutoBuilderAB.ReBuildAssetBundles{}'.format(PLATFORM)
    else:
        build_function = 'KGame.KAutoBuilderAB.BuildAssetBundles{}'.format(PLATFORM)

    log_path = os.path.join(workspace.unity_project_path, "build_ab_log.txt")
    unity_tool.build(build_function, UNITY_PATH, workspace.unity_project_path, log_path)

    # 判断平台manifest文件是否存在，是则构建成功，否则失败
    if PLATFORM == 'Android':
        android_manifest_file = os.path.join(workspace.unity_project_path, 'Bundles/Android/Android.manifest')
        if not os.path.exists(android_manifest_file):
            log_tool.show_error("Build failed! Can't find the file of {}, Platform: {}".format(android_manifest_file, PLATFORM))
            exit(1)
    elif PLATFORM == 'iOS':
        ios_manifest_file = os.path.join(workspace.unity_project_path, 'Bundles/iOS/iOS.manifest')
        if not os.path.exists(ios_manifest_file):
            log_tool.show_error("Build failed! Can't find the file of {}, Platform: {}".format(ios_manifest_file, PLATFORM))
            exit(1)
    else:
        pass

    if not os.path.isdir(platform_bundle_path):
        log_tool.show_error("Can't find the path of {}".format(platform_bundle_path))
        exit(1)

    # 提交AB相关修改文件
    if LOCAL_OP is False:
        ab_setting_path = os.path.join(workspace.unity_project_path, 'Setting/Base/FileAbInfoSetting_{}.txt'.format(PLATFORM))
        git_tool.git_add(workspace.product_path, ab_setting_path)
        git_tool.git_add(workspace.product_path, platform_bundle_path)
        git_tool.git_commit(workspace.product_path, '[AutoBuild]: Asset Bundles Rebuild: {} Commit.'.format(IS_REBUILD))


if __name__ == '__main__':
    BuildAssetBundle()

