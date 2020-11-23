# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2019/04/19
# FileName:     project_globalvalue.py
# Description:  项目一些全局变量定义,不同的项目，记得修改这里的定义

from buildtools import globalvalue_tool

# 项目名称，用来区分不同的产品
globalvalue_tool.set_value("project_name", "PaiLeMen")
# 产品git路径
globalvalue_tool.set_value("product_url", "git@xsjgitlab.rdev.kingsoft.net:plmnh_client/plm_client.git")
# 产品名（与Unity PlayerSetting中定义保持一致）
globalvalue_tool.set_value("product_name", "Mahjong")

# Android包名
globalvalue_tool.set_value("bundle_id_android", "cn.com.xishanju.qyqtest")

'''
iOS签名相关(Inhouse)
'''
globalvalue_tool.set_value("development_team_inhouse", "9Y82UF4YM8")
globalvalue_tool.set_value("bundle_id_ios_inhouse", "cn.com.xishanju.qyq")
globalvalue_tool.set_value("code_sign_identity_inhouse_distribution", "iPhone Distribution")
globalvalue_tool.set_value("provisioning_profile_specifier_inhouse_distribuion", "XC iOS: cn.com.xishanju.qyq")
'''
iOS签名相关(AppStore)
'''
globalvalue_tool.set_value("development_team_appstore", "Q2Y22K3LHS")
globalvalue_tool.set_value("bundle_id_ios_appstore", "com.xishanju.qyq")
globalvalue_tool.set_value("code_sign_identity_appstore_distribution", "Apple Distribution")
globalvalue_tool.set_value("provisioning_profile_specifier_appstore_distribuion", "qyq for Distribution")

# 热更包名前缀
globalvalue_tool.set_value("package_name_prefix", "plm.res")
# 热更包的配置文件后缀名
globalvalue_tool.set_value("package_manifest_file_suffix", ".manifest")
# Manifest文件的文件头
globalvalue_tool.set_value("package_manifest_headers", ['File', 'MD5', 'Size', 'MTime', 'MFormatTime'])
# 热更包支持的最大版本间隔（与热更代码定义保持一致）
globalvalue_tool.set_value("max_package_version_span", 5)


# window构建机下的Unity路径
globalvalue_tool.set_value("windows_unity_path", "D:/Program Files/Unity2018.4.14f1/Editor/Unity.exe")
# MacOS构建机下的Unity路径
globalvalue_tool.set_value("macos_uinty_path", "/Applications/Unity2018.4.14f1/Unity.app/Contents/MacOS/Unity")
