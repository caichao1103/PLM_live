# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/12/31
# FileName:     workspace.py
# Description:  workspace class

import os
import project_globalvalue
from buildtools import git_tool, common, log_tool
from buildtools import globalvalue_tool as globalvalue_tool

import sys
sys.path.append('buildtools/tabfile_tool')
from tabfile_tool import TabFile


class PackSetting:
    def __init__(self, pack_dir_name):
        self.pack_dir_name = pack_dir_name
        self.folders = []
        self.files = []

class UpdatePackageSetting:
    def __init__(self, package_dir_name):
        self.package_dir_name = package_dir_name
        self.pack_dirs = []
        self.bundle_dirs = []
        self.bundle_files = []
        self.include_bundle_manifest = False
        self.need_buildin = False


class WorkSpace:
    def __init__(self, workspace, branch_name='master'):
        # 工程目录相关
        self.workspace = workspace
        self.branch_name = branch_name
        # svn info
        self.product_url = globalvalue_tool.get_value('product_url')

        # 本地库路径
        self.product_path = common.full_path(self.workspace)

        # Unity 工程
        self.unity_project_path = os.path.join(self.product_path, 'Game')

        # Unity插件目录
        self.unity_plugins_path = os.path.join(self.unity_project_path, 'Assets/Plugins')

        # PackSetting
        self.pack_setting = None

        # UpdatePackageSetting
        self.update_package_setting = None


    def up_product(self, version_code = None):
        """
        只更新products库
        :return:
        """
        if version_code:
            log_tool.show_info('Update Products To Version:Newest, Working Dir: {}'.format(self.product_path))
        else:
            log_tool.show_info('Update Products To Version:{}, Working Dir: {}'.format(version_code, self.product_path))

        if not os.path.isdir(self.product_path):
            log_tool.show_info('Checkout new products...')
            git_tool.git_clone(self.product_url, self.product_path)

        git_tool.git_cleanup(self.product_path)
        git_tool.git_switch(self.product_path, self.branch_name)
        git_tool.git_up(self.product_path, version_code)


    def get_pack_setting(self):
        if not self.pack_setting:
            try:
                setting_path = os.path.join(self.unity_project_path, 'Setting/Base/Update/PackSetting.txt')
                tabfile = TabFile(setting_path)
                if not tabfile.init():
                    log_tool.show_error('Load PackSetting.txt Failed')
                    return None

                self.pack_setting = {}
                row_count = tabfile.get_row_count()
                for row in range(1, row_count + 1):
                    pack_dir_name = tabfile.get_value(row, 'PackDirName').replace('\\', '/')
                    folder_path = tabfile.get_value(row, 'Folder').replace('\\', '/')
                    file_path = tabfile.get_value(row, 'File').replace('\\', '/')

                    if self.pack_setting.has_key(pack_dir_name):
                        pack_setting = self.pack_setting[pack_dir_name]
                    else:
                        pack_setting = PackSetting(pack_dir_name)
                        self.pack_setting[pack_dir_name] = pack_setting

                    if folder_path != '':
                        pack_setting.folders.append(folder_path)
                    if file_path != '':
                        pack_setting.files.append(file_path)

            except Exception as e:
                log_tool.show_error('GetPackSetting Failed! Error: {}'.format(e))
                self.pack_setting = None


        return self.pack_setting


    def get_update_package_setting(self):
        if not self.update_package_setting:
            try:
                setting_path = os.path.join(self.unity_project_path, 'Setting/Base/Update/UpdatePackageSetting.txt')
                tabfile = TabFile(setting_path)
                if not tabfile.init():
                    log_tool.show_error('Load UpatePackageSetting.txt Failed')
                    return None

                self.update_package_setting = {}
                row_count = tabfile.get_row_count()
                for row in range(1, row_count + 1):
                    package_dir_name = tabfile.get_value(row, 'PackageDirName').replace('\\', '/')
                    pack_dir_name = tabfile.get_value(row, 'PackDirName').replace('\\', '/')
                    bundle_dir_name = tabfile.get_value(row, 'BundleDirName').replace('\\', '/')
                    bundle_file_name = tabfile.get_value(row, 'BundleFileName').replace('\\', '/')
                    include_bundle_manifest = tabfile.get_value(row, 'IncludeBundleManifest') == '1'
                    need_buildin = tabfile.get_value(row, 'NeedBuildIn') == '1'

                    if self.update_package_setting.has_key(package_dir_name):
                        update_package_setting = self.update_package_setting[package_dir_name]
                    else:
                        update_package_setting = UpdatePackageSetting(package_dir_name)
                        self.update_package_setting[package_dir_name] = update_package_setting

                    if pack_dir_name != '':
                        update_package_setting.pack_dirs.append(pack_dir_name)

                    if bundle_dir_name != '':
                        update_package_setting.bundle_dirs.append(bundle_dir_name)

                    if bundle_file_name != '':
                        update_package_setting.bundle_files.append(bundle_file_name)

                    update_package_setting.include_bundle_manifest = update_package_setting.include_bundle_manifest or include_bundle_manifest
                    update_package_setting.need_buildin = update_package_setting.need_buildin or need_buildin

            except Exception as e:
                log_tool.show_error('GetUpdatePackageSetting Failed! Error: {}'.format(e))
                self.update_package_setting = None

        return self.update_package_setting

    @staticmethod
    def set_file_permission(file_path):
        """
        设置文件权限
        :param file_path:
        :return:
        """
        cmd = ['chmod', '755', file_path]
        common.run_command(cmd)

