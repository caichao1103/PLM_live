# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2020/04/03
# FileName:     auto_build_ios_ipa
# Description:  Auto build IOS Ipa

import os
import time
import shutil
import fileinput
import plistlib
import zipfile
import project_globalvalue

from buildtools import unity_tool, log_tool, common, git_tool
from workspace import WorkSpace
from pbxproj import XcodeProject
from pbxproj.pbxextensions import ProjectFiles
from ruamel import yaml
from buildtools import globalvalue_tool as globalvalue_tool

BRANCH_NAME = os.environ.get("BRANCH_NAME")
if BRANCH_NAME:
    LOCAL_OP = False
    LANGUAGE = os.environ.get('LANGUAGE')
    # VERSION_NUMBER = os.environ.get('VERSION_NUMBER')
    VERSION_TYPE = os.environ.get('VERSION_TYPE')
    IS_PRODUCT = os.environ.get('IS_PRODUCT') == 'true'
    MAJOR_NUMBER = os.environ.get('MAJOR_NUMBER')
    MINOR_NUMBER = os.environ.get('MINOR_NUMBER')
    PATCH_NUMBER = os.environ.get('PATCH_NUMBER')
    BUILD_NUMBER = os.environ.get('BUILD_NUMBER')
    ONLY_EXPORT = os.environ.get('ONLY_EXPORT') == 'true'
    SIGN_TYPE = os.environ.get('SIGN_TYPE')
    PROFILE_TYPE = os.environ.get('PROFILE_TYPE')
    APP_SHOW_NAME = os.environ.get('APP_SHOW_NAME')
    IS_OBB_VERSION = False
    NEED_DOWNLOAD_OBB = False
else:
    LOCAL_OP = True
    BRANCH_NAME = 'master'
    LANGUAGE = 'zh_CN'
    # VERSION_NUMBER = ''
    VERSION_TYPE = 'Alpha'
    IS_PRODUCT = False
    MAJOR_NUMBER = '0'
    MINOR_NUMBER = '1'
    PATCH_NUMBER = '0'
    BUILD_NUMBER = '0'
    ONLY_EXPORT = False
    SIGN_TYPE = 'Inhouse'
    PROFILE_TYPE = 'Distribution'
    APP_SHOW_NAME = '合家欢测试V2'
    IS_OBB_VERSION = False
    NEED_DOWNLOAD_OBB = False

# ProjectName
PROJECT_NAME = globalvalue_tool.get_value("project_name")

# ProductName
PRODUCT_NAME = globalvalue_tool.get_value("product_name")

# 定义签名相关全局变量, 具体赋值在_PreHandleIosPrj_Sign中，不同项目记得做修改
# TeamId
developmentTeam = ''
# 签名类型
code_sign_identity = ''
# 描述文件名
provisioning_profile_specifier = ''
# 包名
bundle_id = ''

# 参数判空处理
# if VERSION_NUMBER is None:
#     VERSION_NUMBER = ''

# unicode编码处理
APP_SHOW_NAME = APP_SHOW_NAME.decode('utf-8')


# UnityPath
UNITY_PATH = globalvalue_tool.get_value("macos_uinty_path")

# current path
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

# InitWorkSpace
workdirbase = os.path.dirname(os.path.dirname(CURRENT_PATH))
if not os.path.isdir(workdirbase):
    os.makedirs(workdirbase)
workspace = WorkSpace(workdirbase, BRANCH_NAME)

# Ios工程目录
IOS_PRJ_DIR = os.path.join(workspace.unity_project_path, 'IosPrj/Version_{}'.format(LANGUAGE))
# Ios工程文件路径
IOS_PRJ_PATH = os.path.join(IOS_PRJ_DIR, 'Unity-iPhone.xcodeproj/project.pbxproj')
# XCodeBuild路径
XCODE_BUILD_PATH = '/usr/bin/xcodebuild'

# IpaDir，所有版本Ipa存放的目录
IPA_DIR = os.path.join(os.path.dirname(os.path.dirname(workspace.product_path)), 'FtpShare/IosIpa')
IPA_DIR = os.path.join(IPA_DIR, PROJECT_NAME)
if not os.path.isdir(IPA_DIR):
    os.makedirs(IPA_DIR)

# 获取Ipa的正确路径
def GetIpaDir():
    ipa_dir = os.path.join(IPA_DIR, '{}/{}.{}.{}.{}/{}/{}/{}'.format(
        BRANCH_NAME, MAJOR_NUMBER, MINOR_NUMBER, PATCH_NUMBER, BUILD_NUMBER, VERSION_TYPE, SIGN_TYPE, PROFILE_TYPE))
    if not os.path.isdir(ipa_dir):
        os.makedirs(ipa_dir)

    return ipa_dir

# Product Update
# def UpdateProduct():
#     if VERSION_NUMBER != '':
#         workspace.up_product(VERSION_NUMBER)
#     else:
#         workspace.up_product()


# 清除Build残留信息
def ClearBuildInfo():
    unity_package_manager_path = os.path.join(workspace.unity_project_path, 'UnityPackageManager')
    if os.path.isdir(unity_package_manager_path):
        shutil.rmtree(unity_package_manager_path, ignore_errors=True)
        log_tool.show_info('[INFO]:  delete' + unity_package_manager_path)

    # 清除ios工程目录
    if os.path.isdir(IOS_PRJ_DIR):
        shutil.rmtree(IOS_PRJ_DIR, ignore_errors=True)
        log_tool.show_info('[INFO]:  delete' + IOS_PRJ_DIR)


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
                bundle_file_path = os.path.join(workspace.unity_project_path, 'Bundles/iOS/{}'.format(bundle_file_name))
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

        bundle_dir = os.path.join(workspace.unity_project_path, 'Bundles/iOS/{}'.format(bundle_dir_name))
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

            bundle_file_path = os.path.join(workspace.unity_project_path, 'Bundles/iOS/{}'.format(bundle_file_name))
            if os.path.exists(bundle_file_path):
                os.remove(bundle_file_path)


# 获取Ipa的正确路径
def GetIpaDir():
    ipa_dir = os.path.join(IPA_DIR, '{}/{}.{}.{}.{}/{}/{}/{}'.format(
        BRANCH_NAME, MAJOR_NUMBER, MINOR_NUMBER, PATCH_NUMBER, BUILD_NUMBER, VERSION_TYPE, SIGN_TYPE, PROFILE_TYPE))
    if not os.path.isdir(ipa_dir):
        os.makedirs(ipa_dir)

    return ipa_dir


# 导出Ios工程
def ExportIosPrj():
    build_function = 'KGame.KAutoBuilderProject.BuildiOS{}'.format(VERSION_TYPE)

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
    
    log_path = os.path.join(workspace.unity_project_path, "unity_build_ios_ipa_log.txt")
    unity_tool.build_with_params(build_function,
                                 UNITY_PATH,
                                 workspace.unity_project_path,
                                 log_path,
                                 build_params)

    if (not os.path.isfile(IOS_PRJ_PATH)):
        log_tool.show_error("Can't find the XCode project file {}!".format(IOS_PRJ_PATH))
        log_tool.show_error("ExportIosPrj Failed!")
        exit(1)


# Ios工程编译前处理
def PreHandleIosPrj():
    # 工程文件预修改
    xcode_project = XcodeProject().load(IOS_PRJ_PATH)
    _PreHandleIosPrj_Base(xcode_project)
    _PreHandleIosPrj_Sign(xcode_project)
    _PreHandle_ProductBundleIdentifier(xcode_project)
    xcode_project.save()
    log_tool.show_info('XcodeProject PreHandle Done!')

    # plist文件修改
    _PreHandle_plist()
    log_tool.show_info('plist.info PreHandle Done!')

    log_tool.show_info('PreHandleIosPrj Done!')


# iOS工程公用处理
def _PreHandleIosPrj_Base(xcode_project):
    xcode_project.remove_flags('ENABLE_BITCODE', ['YES', 'NO'])
    xcode_project.add_flags('ENABLE_BITCODE', 'NO')

    xcode_project.set_flags('GCC_OPTIMIZATION_LEVEL', '0')
    xcode_project.set_flags('COPY_PHASE_STRIP', 'YES', target_name='Unity_iPhone')
    xcode_project.set_flags('DEBUG_INFORMATION_FORMAT', 'dwarf-with-dsym', target_name='Unity-iPhone')

# iOS工程手动签名
def _PreHandleIosPrj_Sign(xcode_project):
    global developmentTeam
    global code_sign_identity
    global provisioning_profile_specifier
    global bundle_id

    if SIGN_TYPE == 'Inhouse':
        if PROFILE_TYPE == 'Development':
            # 暂时没有development类型的pp
            log_tool.show_error('Have not Inhouse Development Provioning Profile')
            exit(1)
        elif PROFILE_TYPE == 'Distribution':
            developmentTeam = globalvalue_tool.get_value("development_team_inhouse")
            code_sign_identity = globalvalue_tool.get_value("code_sign_identity_inhouse_distribution")
            provisioning_profile_specifier = globalvalue_tool.get_value("provisioning_profile_specifier_inhouse_distribuion")
            bundle_id = globalvalue_tool.get_value("bundle_id_ios_inhouse")

    elif SIGN_TYPE == 'AppStore':
        if PROFILE_TYPE == 'Development':
            # 暂时没有development类型的pp
            log_tool.show_error('Have not AppStore Development Provioning Profile')
            exit(1)
        elif PROFILE_TYPE == 'Distribution':
            developmentTeam = globalvalue_tool.get_value("development_team_appstore")
            code_sign_identity = globalvalue_tool.get_value("code_sign_identity_appstore_distribution")
            provisioning_profile_specifier = globalvalue_tool.get_value("provisioning_profile_specifier_appstore_distribuion")
            bundle_id = globalvalue_tool.get_value("bundle_id_ios_appstore")

    else:
        log_tool.show_error("Invalid SignType {}".format(SIGN_TYPE))
        exit(1)

    # 设置手动签名
    xcode_project.set_flags('CODE_SIGN_STYLE', 'Manual')
    for st in xcode_project.get_build_phases_by_name('PBXProject'):
        for t in xcode_project.get_build_phases_by_name('PBXNativeTarget'):
            log_tool.show_info("Handling target[{}], Set 'ProvisioningStyle = Manual'".format(t.name))
            st.set_provisioning_style('Manual', t)
            st.attributes.TargetAttributes[u'1D6058900D05DD3D006BFB54'].parse({'DevelopmentTeam': developmentTeam})
            st.attributes.TargetAttributes[u'1D6058900D05DD3D006BFB54'].SystemCapabilities.parse(
                {'com.apple.Push': {'enabled': '1'}})
            st.attributes.TargetAttributes[u'1D6058900D05DD3D006BFB54'].SystemCapabilities.parse(
                {'com.apple.Keychain': {'enabled': '0'}})

    xcode_project.set_flags('DEVELOPMENT_TEAM', developmentTeam, target_name='Unity-iPhone')
    xcode_project.set_flags('CODE_SIGN_IDENTITY', code_sign_identity)
    xcode_project.set_flags('CODE_SIGN_IDENTITY[sdk=iphoneos*]', code_sign_identity)
    xcode_project.set_flags('PROVISIONING_PROFILE_SPECIFIER', provisioning_profile_specifier, target_name='Unity-iPhone')


# 修改包名
def _PreHandle_ProductBundleIdentifier(xcode_project):
    index = bundle_id.rfind('.')
    bundle_id_prefix = bundle_id[0:index]
    product_name = bundle_id[(index + 1):]
    xcode_project.set_flags('PRODUCT_BUNDLE_IDENTIFIER', '{}.{}'.format(bundle_id_prefix, '${PRODUCT_NAME:rfc1034identifier}'))
    xcode_project.set_flags('PRODUCT_NAME', product_name)


# plist.info文件修改
def _PreHandle_plist():
    info_plist_path = os.path.join(IOS_PRJ_DIR, 'Info.plist')
    if (not os.path.isfile(info_plist_path)):
        log_tool.show_error("{} Can't Find!".format(info_plist_path))
        exit(1)

    plist_file = plistlib.readPlist(info_plist_path)

    # 配置AppId
    plist_file['CFBundleIdentifier'] = bundle_id
    # 配置版号
    plist_file['CFBundleShortVersionString'] = '{}.{}.{}'.format(MAJOR_NUMBER, MINOR_NUMBER, PATCH_NUMBER)
    plist_file['CFBundleVersion'] = BUILD_NUMBER
    # 配置显示名
    plist_file['CFBundleDisplayName'] = APP_SHOW_NAME

    # 配置描述文件
    if (SIGN_TYPE == 'Inhouse'):
        plist_file['method'] = 'enterprise'
    else:     
        if (PROFILE_TYPE == 'Development'):
            plist_file['method'] = 'development'
        else:
            plist_file['method'] = 'app-store'
    plist_file['provisioningProfiles'] = {bundle_id: provisioning_profile_specifier}

    # 此参数用来控制是否可以放至debug.ini
    if VERSION_TYPE.lower() != 'release':
        plist_file['UIFileSharingEnabled'] = True
    else:
        if 'UIFileSharingEnabled' in plist_file:
            del plist_file['UIFileSharingEnabled']

    plistlib.writePlist(plist_file, info_plist_path)


# 编译Ios工程，生成Ipa
def BuildIosPrj():
    scheme = 'Unity-iPhone'
    info_plist_path = 'Info.plist'
    package_name = 'Unity-iPhone.ipa'
    if (VERSION_TYPE == 'Alpha'):
        configuration = 'Debug'
    else:
        configuration = 'Release'

    # 切换到工程目录
    os.chdir(IOS_PRJ_DIR)

    # Archive
    archive_cmd = [
        XCODE_BUILD_PATH,
        '-archivePath', 'Unity-iPhone',
        '-project', 'Unity-iPhone.xcodeproj',
        '-configuration', configuration,
        '-scheme', scheme,
        'archive',
        '-verbose',
        'CODE_SIGN_IDENTITY={}'.format(code_sign_identity),
        'PROVISIONING_PROFILE_SPECIFIER={}'.format(provisioning_profile_specifier),
        '-sdk', 'iphoneos'
    ]
    common.run_command(archive_cmd)

    # Export
    export_cmd = [
        XCODE_BUILD_PATH,
        '-exportArchive',
        '-archivePath', 'Unity-iPhone.xcarchive',
        '-exportPath', 'Unity-iPhone-resigned-dist',
        '-exportOptionsPlist', info_plist_path
    ]
    common.run_command(export_cmd)

    # Copy ipa
    build_date = time.strftime("%Y.%m.%d.%H.%M.%S", time.localtime())
    ipa_dir = GetIpaDir()
    source_ipa_path = os.path.join(IOS_PRJ_DIR, os.path.join('Unity-iPhone-resigned-dist', package_name))
    target_ipa_path = os.path.join(ipa_dir, '{}_{}_{}.{}.{}.{}_{}_{}.ipa'.format(
        PRODUCT_NAME, BRANCH_NAME, MAJOR_NUMBER, MINOR_NUMBER, PATCH_NUMBER, BUILD_NUMBER, VERSION_TYPE, build_date))
    shutil.copyfile(source_ipa_path, target_ipa_path)

    log_tool.show_info('Build Ios Ipa is done!')


# 编译Ipa
def BuildIpa():
    if not common.is_macos():
        log_tool.show_error('Only mac can build ios ipa')
        exit(1)

    # if LOCAL_OP is False:
    #     UpdateProduct()

    #  清除上次构建残留
    ClearBuildInfo()

    # 删除不需要打包的资源
    ClearResNoNeedBuild()

    # 导出Ios工程
    ExportIosPrj()

    # # 分析日志行，确保unity是否构建成功
    # time.sleep(1)
    # log_path = os.path.join(workspace.unity_project_path, "unity_build_ios_ipa_log.txt")
    # if os.path.isfile(log_path):
    #     for line in fileinput.input(log_path, 1024):
    #         if "is an incorrect path for a scene file" in line:
    #             log_tool.show_error(u'[ERROR]: 场景文件路径不正确，请检查EditorBuildSettings')
    #             fileinput.close()
    #             exit(1)
    #         if "Compilation failed:" in line:
    #             log_tool.show_error('Build iOS Ipa Failed!')
    #             fileinput.close()
    #             exit(1)

    # Ios工程编译前处理
    PreHandleIosPrj()

    if ONLY_EXPORT is True:
        log_tool.show_info('Only Export XcodeProject, Excape BuildIosPrj!')
        exit(0)

    # 编译Ios工程，生成ipa
    BuildIosPrj()


if __name__ == '__main__':
    BuildIpa()
