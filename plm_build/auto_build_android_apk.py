# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/01/15
# FileName:     auto_build_android_apk
# Description:  Auto build Android Apk

import os
import time
import shutil
import fileinput
import hashlib
import zipfile
import project_globalvalue
from buildtools import unity_tool, log_tool, common, git_tool
from workspace import WorkSpace
from buildtools import globalvalue_tool as globalvalue_tool


BRANCH_NAME = os.environ.get("BRANCH_NAME")
if BRANCH_NAME:
    LOCAL_OP = False
    LANGUAGE = os.environ.get('LANGUAGE')
    VERSION_NUMBER = os.environ.get('VERSION_NUMBER')
    VERSION_TYPE = os.environ.get('VERSION_TYPE')
    IS_PRODUCT = os.environ.get('IS_PRODUCT') == 'true'
    MAJOR_NUMBER = os.environ.get('MAJOR_NUMBER')
    MINOR_NUMBER = os.environ.get('MINOR_NUMBER')
    PATCH_NUMBER = os.environ.get('PATCH_NUMBER')
    BUILD_NUMBER = os.environ.get('BUILD_NUMBER')
    IS_OBB_VERSION = os.environ.get('IS_OBB_VERSION') == 'true'
    NEED_DOWNLOAD_OBB = os.environ.get('NEED_DOWNLOAD_OBB') == 'true'
    APP_SHOW_NAME = os.environ.get('APP_SHOW_NAME')
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    LANGUAGE = 'zh_CN'
    VERSION_NUMBER = ''
    VERSION_TYPE = 'Alpha'
    IS_PRODUCT = False
    MAJOR_NUMBER = '0'
    MINOR_NUMBER = '1'
    PATCH_NUMBER = '0'
    BUILD_NUMBER = '0'
    IS_OBB_VERSION = False
    NEED_DOWNLOAD_OBB = False
    APP_SHOW_NAME = '牌乐门'

# ProjectName
PROJECT_NAME = globalvalue_tool.get_value("project_name")

# BundleId
BUNDLE_ID = globalvalue_tool.get_value("bundle_id_android")

# ProductName
PRODUCT_NAME = globalvalue_tool.get_value("product_name")

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

# ApkDir，所有版本Apk存放的目录
APK_DIR = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/AndroidApk')
APK_DIR = os.path.join(APK_DIR, PROJECT_NAME)
if not os.path.isdir(APK_DIR):
    os.makedirs(APK_DIR)

# Product Update
def UpdateProduct():
    if VERSION_NUMBER != '':
        workspace.up_product(VERSION_NUMBER)
    else:
        workspace.up_product()


# 清除Build残留信息
def ClearBuildInfo():
    unity_package_manager_path = os.path.join(workspace.unity_project_path, 'UnityPackageManager')
    if os.path.isdir(unity_package_manager_path):
        shutil.rmtree(unity_package_manager_path, ignore_errors=True)
        log_tool.show_info('[INFO]:  delete' + unity_package_manager_path)


# 删除不需要打包到客户端的资源
def ClearResNoNeedBuild():
    update_package_settings = workspace.get_update_package_setting()
    if not update_package_settings:
        exit(1)

    pack_dir_info = {}
    bundle_dir_info = {}
    bundle_file_info = {}
    for setting in update_package_settings.values():
        need_buildin = setting.need_buildin

        if len(setting.pack_dirs) > 0:
            for pack_dir in setting.pack_dirs:
                if pack_dir_info.has_key(pack_dir):
                    pack_dir_info[pack_dir] = need_buildin or pack_dir_info[pack_dir]
                else:
                    pack_dir_info[pack_dir] = need_buildin

        if len(setting.bundle_dirs) > 0:
            for bundle_dir in setting.bundle_dirs:
                if bundle_dir_info.has_key(bundle_dir):
                    info = bundle_dir_info[bundle_dir]
                    info['need_buildin'] = info['need_buildin'] or need_buildin
                else:
                    info = {
                        'need_buildin' : need_buildin, 
                        'full_delete' : True,
                        'no_delete_file' : []}
                    bundle_dir_info[bundle_dir] = info

        if len(setting.bundle_files) > 0:
            for bundle_file in setting.bundle_files:
                if bundle_file_info.has_key(bundle_file):
                    bundle_file_info[bundle_file] = need_buildin or bundle_file_info[bundle_file]
                else:
                    bundle_file_info[bundle_file] = need_buildin

    # 判断Bundle目录删除情况
    for bundle_dir_name in bundle_dir_info.keys():
        dir_info = bundle_dir_info[bundle_dir_name]
        if dir_info['need_buildin']:
            continue

        for bundle_file_name in bundle_file_info.keys():
            if not bundle_dir_name in bundle_file_name:
                continue

            need_buildin = bundle_file_info[bundle_file_name]
            if need_buildin:
                dir_info['full_delete'] = False
                bundle_file_path = os.path.join(workspace.unity_project_path, 'Bundles/Android/{}'.format(bundle_file_name))
                bundle_file_path = bundle_file_path.replace('\\', '/')
                dir_info['no_delete_file'].append(bundle_file_path)


    # 删除不需要打包的Pack
    for pack_dir_name in pack_dir_info.keys():
        if pack_dir_info[pack_dir_name]:
            continue

        pack_dir = os.path.join(workspace.unity_project_path, 'Assets/StreamingAssets/Res/{}'.format(pack_dir_name))
        shutil.rmtree(pack_dir)

    # 删除不需要打包的Bundle
    for bundle_dir_name in bundle_dir_info.keys():
        dir_info = bundle_dir_info[bundle_dir_name]
        if dir_info['need_buildin']:
            continue

        bundle_dir = os.path.join(workspace.unity_project_path, 'Bundles/Android/{}'.format(bundle_dir_name))
        if dir_info['full_delete']:
            shutil.rmtree(bundle_dir)
        else:
            for root, dirs, files in os.walk(bundle_dir):
                for name in files:
                    file_path = os.path.join(root, name).replace('\\', '/')
                    if not os.path.exists(file_path):
                        continue

                    no_need_delete = False
                    for bundle_file_path in dir_info['no_delete_file']:
                        if bundle_file_path == file_path:
                            no_need_delete = True
                            break
                    if not no_need_delete:
                        os.remove(file_path)

                for name in dirs:
                    dir_path = os.path.join(root, name).replace('\\', '/')
                    if not os.path.exists(file_path):
                        continue

                    no_need_delete = False
                    for bundle_file_path in dir_info['no_delete_file']:
                        if dir_path in bundle_file_path:
                            no_need_delete = True
                            break
                    if not no_need_delete:
                        shutil.rmtree(dir_path, ignore_errors=True)

        for bundle_file_name in bundle_file_info.keys():
            if bundle_file_info[bundle_file_name]:
                continue

            bundle_file_path = os.path.join(workspace.unity_project_path, 'Bundles/Android/{}'.format(bundle_file_name))
            if os.path.exists(bundle_file_path):
                os.remove(bundle_file_path)


# 获取Apk的正确路径
def GetApkDir():
    apk_dir = os.path.join(APK_DIR, '{}/{}.{}.{}.{}/{}'.format(BRANCH_NAME, MAJOR_NUMBER, MINOR_NUMBER, PATCH_NUMBER, BUILD_NUMBER, VERSION_TYPE))
    if not os.path.isdir(apk_dir):
        os.makedirs(apk_dir)

    return apk_dir


# 导出Android工程
def ExportAndroidPrj():
    build_function = 'KGame.KAutoBuilderProject.BuildAndroid{}'.format(VERSION_TYPE)

    # 构造unity命令行参数
    build_params = []
    build_params.append('-majorNumber={}'.format(MAJOR_NUMBER))
    build_params.append('-minorNumber={}'.format(MINOR_NUMBER))
    build_params.append('-patchNumber={}'.format(PATCH_NUMBER))
    build_params.append('-buildNumber={}'.format(BUILD_NUMBER))
    build_params.append('-branchName={}'.format(BRANCH_NAME))
    build_params.append('-language={}'.format(LANGUAGE))
    build_params.append('-isObbVersion={}'.format(IS_OBB_VERSION))
    build_params.append('-needDownloadObb={}'.format(NEED_DOWNLOAD_OBB))
    build_params.append('-isProduct={}'.format(IS_PRODUCT))
    
    log_path = os.path.join(workspace.unity_project_path, "unity_build_android_apk_log.txt")
    unity_tool.build_with_params(build_function,
                                 UNITY_PATH,
                                 workspace.unity_project_path,
                                 log_path,
                                 build_params)


# Android工程编译前处理
def PreHandleAndroidPrj():
    # 回滚列表，以下文件需要回滚
    build_gradle_path = os.path.join(
        workspace.unity_project_path, 
        'AndroidPrj/Version_{}/{}/build.gradle'.format(LANGUAGE, PRODUCT_NAME))
    
    string_xml_path = os.path.join(
        workspace.unity_project_path, 
        'AndroidPrj/Version_{}/{}/src/main/res/values/strings.xml'.format(LANGUAGE, PRODUCT_NAME))

    android_manifest = os.path.join(
        workspace.unity_project_path,
        'AndroidPrj/Version_{}/{}/src/main/AndroidManifest.xml'.format(LANGUAGE, PRODUCT_NAME))

    revert_list = [build_gradle_path, string_xml_path, android_manifest]
    for revert_file in revert_list:
        git_tool.git_revert(workspace.unity_project_path, revert_list)

    # 修改string.xml，修改app_name
    common.replace_text(
        string_xml_path, 
        '<string name="app_name">{}</string>'.format(PRODUCT_NAME),
        '<string name="app_name">{}</string>'.format(APP_SHOW_NAME))

    # 修改AndroidManifest.xml
    version_name = "{}.{}.{}".format(MAJOR_NUMBER, MINOR_NUMBER, BUILD_NUMBER)
    common.replace_text(android_manifest, 'android:versionName="0.0.0"', 'android:versionName="%s"' % version_name)
    common.replace_text(android_manifest, 'android:versionCode="1"', 'android:versionCode="%s"' % BUILD_NUMBER)

    # Obb相关修改
    if IS_OBB_VERSION is True:
        #Obb文件改名
        obb_src_path = os.path.join(
            workspace.unity_project_path, 
            'AndroidPrj/Version_{}/{}/{}.main.obb'.format(LANGUAGE, PRODUCT_NAME, PRODUCT_NAME))
        obb_dst_path = os.path.join(
            workspace.unity_project_path, 
            'AndroidPrj/Version_{}/{}/main.{}.{}.obb'.format(LANGUAGE, PRODUCT_NAME, BUILD_NUMBER, BUNDLE_ID))
        os.rename(obb_src_path, obb_dst_path)

        # 修改AppConfig
        appconfig_path = os.path.join(
            workspace.unity_project_path, 
            'AndroidPrj/Version_{}/{}/src/main/assets/AppConfigs.txt'.format(LANGUAGE, PRODUCT_NAME))
        common.replace_text(appconfig_path, 'IsObbVersion = 0', 'IsObbVersion = 1')
        common.replace_text(appconfig_path, 'ObbFileName = ', 'ObbFileName = main.{}.{}.obb'.format(BUILD_NUMBER, BUNDLE_ID))
        if NEED_DOWNLOAD_OBB is True:
            common.replace_text(appconfig_path, 'IsNeedDownloadObb = 0', 'IsNeedDownloadObb = 1')

        # 获取Obb文件内的MD5只，修改AndroidManifest.xml
        obb_zipfile = zipfile.ZipFile(obb_dst_path)
        for file_path in obb_zipfile.namelist():
            file_path = file_path.encode('utf-8')
            if file_path.startswith('assets/') and len(file_path.split('/')) == 2:
                if len(file_path.split('/')[-1]) > 20 and '.' not in file_path.split('/')[-1]:
                    obb_md5 = os.path.basename(file_path)
                    # 替换 AndroidManifest.xml MD5 值
                    common.replace_text(android_manifest, '10015bb9-866e-406b-bc8d-feff9e1f6045', obb_md5)

        # 拷贝到Apk目录去
        apk_dir = GetApkDir()
        shutil.copy(obb_dst_path, apk_dir)

        # 如果需要cdn下载Obb，需要再生成一个md5文件
        if NEED_DOWNLOAD_OBB is True:
            md5_file_path = '%s.md5' % obb_dst_path
            log_tool.show_info('Calculate the MD5 value and write it to file: {}'.format(md5_file_path))

            md5_obj = hashlib.md5()
            with open(obb_dst_path, 'rb') as tmp_f:
                md5_obj.update(tmp_f.read())
            md5 = md5_obj.hexdigest()

            md5_file = open(md5_file_path, 'w')
            md5_file.write(md5)
            md5_file.flush()

            # 拷贝到Apk目录去
            shutil.copy(md5_file_path, apk_dir)


# 编译Android工程，生成Apk
def BuildAndroidPrj():
    gradle_dir = os.path.join(
        workspace.unity_project_path, 
        'AndroidPrj/Version_{}/{}'.format(LANGUAGE, PRODUCT_NAME))
    os.chdir(gradle_dir)

    # 删除Build目录
    build_dir = os.path.join(gradle_dir, 'build')
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    if VERSION_TYPE == 'Alpha':
        compile_parm = 'assembleDebug'
        dir_name = 'debug'
    elif VERSION_TYPE == 'Preview' or VERSION_TYPE == 'Release':
        compile_parm = 'assembleRelease'
        dir_name = 'release'
    else:
        compile_parm = None
        exit(1)

    if common.is_windows():
        cmd = ['gradlew', compile_parm]
        os.system(' '.join(cmd))
    else:
        chmod = ['chmod', '755', 'gradlew']
        common.run_command(chmod)

        cmd = ['./gradlew', compile_parm]
        common.run_command(cmd)

    apk_src_path = os.path.join(
        build_dir,
        'outputs/apk/{}/{}-{}.apk'.format(dir_name, PRODUCT_NAME, dir_name))

    # 检测Apk是否Build成功
    if not os.path.isfile(apk_src_path):
        log_tool.show_error("Build Android Apk Failed! Can't Find the file: {}".format(apk_src_path))
        exit(1)

    # Apk改名
    build_date = time.strftime("%Y.%m.%d.%H.%M.%S", time.localtime())
    apk_dst_path = os.path.join(
        build_dir,
        'outputs/apk/{}/{}_{}_{}.{}.{}.{}_{}_{}.apk'.format(
            dir_name, PRODUCT_NAME, BRANCH_NAME, MAJOR_NUMBER, MINOR_NUMBER, PATCH_NUMBER, BUILD_NUMBER, VERSION_TYPE, build_date))
    os.rename(apk_src_path, apk_dst_path)

    # 拷贝到Apk目录去
    apk_dir = GetApkDir()
    shutil.copy(apk_dst_path, apk_dir)


# 编译Apk
def BuildApk():
    if LOCAL_OP is False:
        UpdateProduct()

    #  清除上次构建残留
    ClearBuildInfo()

    # 删除不需要打包的资源
    ClearResNoNeedBuild()

    # 导出Android工程
    ExportAndroidPrj()

    # # 分析日志行，确保unity是否构建成功
    # time.sleep(1)
    # log_path = os.path.join(workspace.unity_project_path, "unity_build_android_apk_log.txt")
    # if os.path.isfile(log_path):
    #     for line in fileinput.input(log_path, 1024):
    #         if "is an incorrect path for a scene file" in line:
    #             log_tool.show_error(u'[ERROR]: 场景文件路径不正确，请检查EditorBuildSettings')
    #             fileinput.close()
    #             exit(1)
    #         if "Compilation failed:" in line:
    #             log_tool.show_error('Build Android Apk Failed!')
    #             fileinput.close()
    #             exit(1)
    #         if "OBB Builder Failed!" in line:
    #             log_tool.show_error('OBB Builder Failed!')
    #             fileinput.close()
    #             exit(1)

    # Android工程编译前处理
    PreHandleAndroidPrj()

    # 编译Android工程，生成Apk
    BuildAndroidPrj()

    log_tool.show_info('Build Android Apk is done!')


if __name__ == '__main__':
    BuildApk()
