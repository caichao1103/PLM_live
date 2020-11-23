# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/01/14
# FileName:     auto_build_pack
# Description:  Auto build Pack

import os
import project_globalvalue
import shutil
from time import sleep
from buildtools import common, log_tool, git_tool, unity_tool
from workspace import WorkSpace
from buildtools import globalvalue_tool as globalvalue_tool

BRANCH_NAME = os.environ.get("BRANCH_NAME")
if BRANCH_NAME:
    LOCAL_OP = False
    LANGUAGE = os.environ.get('LANGUAGE')
    VERSION_NUMBER = os.environ.get('VERSION_NUMBER')
    PACK_DIRS = os.environ.get('PACK_DIRS')
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    LANGUAGE = 'zh_CN'
    VERSION_NUMBER = ''
    PACK_DIRS = ''
    

# 参数判空处理
if VERSION_NUMBER is None:
    VERSION_NUMBER = ''


# UnityPath
UNITY_PATH = globalvalue_tool.get_value("windows_unity_path")
if common.is_macos():
    UNITY_PATH = globalvalue_tool.get_value("macos_uinty_path")

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


# 生成所有脚本路径的配置表
def CreateAllLuaFilePath():
    create_function = "KGame.KLuaFileFinder.CreateAllLuaFilePath"
    log_path = os.path.join(workspace.unity_project_path, 'create_allluapath_log.txt')
    unity_tool.build(create_function, UNITY_PATH, workspace.unity_project_path, log_path)


# 打包Pack
def BuildPack():
    # 先更新到最新
    if LOCAL_OP is False:
        UpdateProduct()

    # 生成所有脚本路径的配置表
    # 现在不需要生成，可以通过加载目录的方式
    #CreateAllLuaFilePath()

    sleep(1)

    # 获取所有需要Pack的目录
    pack_settings = workspace.get_pack_setting()
    if not pack_settings:
        exit(1)

    # FilePacker path
    if common.is_windows():
        filepackercpath = os.path.join(workspace.unity_project_path, 'FilePacker.exe')
    elif common.is_macos():
        filepackercpath = os.path.join(workspace.unity_project_path, 'FilePacker')
        # 获取执行权限
        os.chdir(workspace.unity_project_path)
        chmod = ['chmod', '755', 'FilePacker']
        common.run_command(chmod)

    if not os.path.isfile(filepackercpath):
        log_tool.show_error("Can't find the FilePacker.exe: {}".format(filepackercpath))
        exit(1)


    # 需要打包的目录
    pack_dirs = []
    if not PACK_DIRS or PACK_DIRS == '':
        for setting in pack_settings.values():
            pack_dirs.append(setting.pack_dir_name)
    else:
        dirs = PACK_DIRS.split(',')
        for dir_name in dirs:
            pack_dirs.append(dir_name.strip())

    # 删除需要打包的目录
    root_dir = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res')
    for pack_dir in pack_dirs:
        pack_forlder = os.path.join(root_dir, pack_dir)
        if os.path.isdir(pack_forlder):
            shutil.rmtree(pack_forlder)

    # 生成Pack文件
    pack_ini_file = os.path.join(workspace.unity_project_path, 'FilePacker.ini')
    for pack_dir in pack_dirs:
        # 修改pack配置文件
        if not pack_settings.has_key(pack_dir):
            log_tool.show_error('{} not in PackSetting'.format(pack_dir))
            exit(1)

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

        # 生成Pack目录
        dir_path = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}'.format(pack_dir))
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

        common.run_command(filepackercpath)

    # 打开一下Unity，自动生成一下pack的meta文件
    if LOCAL_OP is False:
        log_tool.show_info('Wait For Generator MetaFiles')
        build_function = 'KGame.KAutoBuilderPack.GenerMetaFiles'
        log_path = os.path.join(workspace.unity_project_path, 'generator_pack_metafiles_log.txt')
        unity_tool.build(build_function, UNITY_PATH, workspace.unity_project_path, log_path)
        log_tool.show_info('Generator MetaFiles Finished')


    # 提交Pack文件
    if LOCAL_OP is False:
        root_dir = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res')

        commit_file = []        
        for pack_dir in pack_dirs:
            pack_idx_path = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}/pack.idx'.format(pack_dir))
            pack_dat_path = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}/pack0.dat'.format(pack_dir))

            if os.path.isfile(pack_idx_path) and os.path.isfile(pack_dat_path):
                commit_file.append(pack_idx_path)
                commit_file.append(pack_dat_path)
            else:
                log_tool.show_error("Can't find {} and {}".format(pack_idx_path, pack_dat_path))
                exit(1)

        git_tool.git_add(workspace.product_path, root_dir)
        git_tool.git_commit(workspace.product_path, '[AutoBuild] pack.idx pack0.dat commit.')


if __name__ == '__main__':
    BuildPack()
