# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2020/04/19
# FileName:     resources_packer
# Description:  用于指定目录的差异zip包命令行工具，无项目逻辑依赖，可各个项目使用
#               注意点：跨版本，文件回滚； 相邻版本，文件删除

import argparse
import os
import sys
import zipfile
import csv
import StringIO
import hashlib
import datetime
import shutil
import errno
import json
import project_globalvalue
from buildtools import globalvalue_tool as globalvalue_tool


MANIFEST_FILE_NAME = globalvalue_tool.get_value("package_manifest_file_suffix")
MANIFEST_HEADERS = globalvalue_tool.get_value("package_manifest_headers")
MAX_PACKAGE_VERSION_SPAN = globalvalue_tool.get_value("max_package_version_span")


def init_args(args):
    """
    初始化args，放入参数
    """
    args.version_file = '%s/%s.resource_version.txt' % (args.artifact_dir, args.package_name)

    if not os.path.isfile(args.version_file):
        # 不存在则创建默认Versionfile版本号0
        _mkdir_p(args.artifact_dir)

        with open(args.version_file, 'wb+') as wf:
            wf.write('0'.zfill(0))
        print "Create Version file: %s" % args.version_file

    # 获取当前更新版本号
    args.resVersion = _get_current_resource_version(args.version_file)
    args.newResVersion = args.resVersion + 1

    print("Current Resource Version: %d" % args.resVersion)
    print("Action: %s" % args.action)
    if args.ignores_ext:
        print('Ignores Ext: `%s`' % ','.join(args.ignores_ext))
    if args.blacklist:
        print('Blacklist: `%s`' % ','.join(args.blacklist))


    args.project_path = _get_clean_path(args.project_path) + '/'
    print("Project Path : %s" % args.project_path)

    args.get_main_package_name = lambda: '%s.%d.zip' % (args.package_name, 0)
    args.get_main_package_path = lambda: '%s/%s' % (args.artifact_dir, args.get_main_package_name())


def do_check(args):
    # 直接生成完整包
    if not os.path.isfile(args.get_main_package_path()):  # 不存在，重新创建版本完整包
        create_package(args, args.get_main_package_path(), args.paths, 0)
    else:  # check and exist
        # 存在的，不允许重新创建
        print('[WARN]no need main package `%s`' % args.get_main_package_path())


def do_pack(args):
    """
    执行pack操作
    """
    is_need_restart = args.need_restart and True
    is_need_backup = args.need_back and True

    print("package info: need_restart = {}, need_back = {}".format(is_need_restart, is_need_backup))
    bResult = create_package_diff(args, is_need_restart, is_need_backup)
    if bResult:

        # 差异包生成完，生成对应版本的完整包
        newFullPackageName = '%s.%d.zip' % (args.package_name, args.newResVersion)
        newFullPackagePath = '%s/%s' % (args.artifact_dir, newFullPackageName)
        bResult = create_package(args, newFullPackagePath, args.paths, args.newResVersion, None, False,
                                              is_need_restart, is_need_backup, True)
        if bResult:
            need_restart = is_need_restart
            need_back = is_need_backup

            # 生成指定版本的info信息，方便后续查找
            _create_package_info_file('%s.info' % newFullPackagePath, need_restart, need_back)

            # 修改版本号，并写入
            with open(args.version_file, 'wb+') as wf:
                wf.write(str(args.newResVersion).zfill(0))
            print('')
            print('New Resource Version --> %s' % args.newResVersion)


# 创建对应版本的资源包
def create_package(args, packagePath, paths, packageVersion, compareFilesMap=None, force_create=False,
                   isNeedRestart=False, isNeedBack=True, isOnlyCreateManifest=False):
    """
    创建资源包
    后面参数为空则是全量包了
    force_create 默认如果没有任何文件差异，会自动删除掉文件，适用于跨版本差异包，文件回滚状态时，如3-7版本，虽然没有变化，但要强制创建
    compareFilesMap 为上一版的文件列表
    """

    manifestPath = None
    if isOnlyCreateManifest:
        manifestPath = packagePath + MANIFEST_FILE_NAME
    else:
        print('@@ => Create Package ... %s' % packagePath)

    writedFilesMap = {}  # 写入过的文件统计 / zipPath -> fullPath
    touchFilesMap = {}  # 检查过但没有实际写入的文件统计 / zipPath -> fullPath
    deleted_files_map = {}  # 差异比较后，被删除的文件的列表

    if os.path.isfile(packagePath):
        print '[WARN]Delete and repack ... %s' % packagePath
        os.remove(packagePath)

    if isOnlyCreateManifest:
        manifestStream = file(manifestPath, "w")
    else:
        manifestStream = StringIO.StringIO()
    manifestCsv = csv.DictWriter(manifestStream, delimiter='\t', fieldnames=MANIFEST_HEADERS)
    manifestCsv.writeheader()

    with zipfile.ZipFile(packagePath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            abspath = _get_clean_path(os.path.abspath(path))
            related_path = abspath.replace(args.project_path, '')

            # 如果是第一次Pack，Pack包的路径要特殊处理一下
            if related_path.find('Assets/StreamingAssets/') >= 0:
                related_path = related_path.replace('Assets/StreamingAssets/', '')

            if os.path.isfile(abspath):
                _write_package_file(zf, abspath, related_path, args.ignores_ext, args.blacklist,
                                    compareFilesMap, isOnlyCreateManifest, writedFilesMap, touchFilesMap, manifestCsv)

            elif os.path.isdir(abspath):
                topDirPath = abspath[0:abspath.find(related_path)]     # 上级目录路径，替换掉这个字符串，就是最终目录相对路径了
                print 'Top Dir: ' + topDirPath

                for dirFullPath, subdirList, fileList in os.walk(abspath):
                    cleanDirFullPath = _get_clean_path(dirFullPath)
                    dirZipPath = cleanDirFullPath.replace(topDirPath, '')

                    for filePath in fileList:
                        fileFullPath = _get_clean_path('%s/%s' % (cleanDirFullPath, filePath))
                        filename, file_extension = os.path.splitext(fileFullPath)

                        # 文件相对zip的路径
                        fileZipPath = _get_clean_path('%s/%s' % (dirZipPath, filePath))
                        fileZipPath = fileZipPath.lstrip('/')  # 去掉开始的/

                        _write_package_file(zf, fileFullPath, fileZipPath, args.ignores_ext, args.blacklist,
                                            compareFilesMap, isOnlyCreateManifest, writedFilesMap, touchFilesMap, manifestCsv)

            else:
                print('[WARN] {} is not directory and is not a file'.format(abspath))
                continue
        
        if not isOnlyCreateManifest:
            zf.writestr(MANIFEST_FILE_NAME, manifestStream.getvalue())

        if packageVersion == 0:
            manifestPath = packagePath + MANIFEST_FILE_NAME
            manifestFile = os.open(manifestPath, os.O_CREAT | os.O_WRONLY)
            os.write(manifestFile, manifestStream.getvalue())

        """
        # 判断有无文件删除
        if compareFilesMap:
            for filepath in compareFilesMap.keys():
                if not filepath in touchFilesMap.keys():
                    print("[Deleted]Found a deleted file `%s`" % (filepath))
                    deleted_files_map[filepath] = compareFilesMap[filepath]

            # 写入被删除的文件的列表
            if len(deleted_files_map) > 0:
                deletedStream= StringIO.StringIO()
                for k in deleted_files_map.keys():
                    deletedStream.write('%s\n'%k)
                zf.writestr('.deleted', deletedStream.getvalue())
        """

    # print manifestStream.getvalue()
    print("Total Writed Files Count: %d" % len(writedFilesMap))
    has_changed = len(writedFilesMap) > 0 or len(deleted_files_map) > 0

    # 验证文件
    if not isOnlyCreateManifest:
        _verify_package(packagePath, writedFilesMap, deleted_files_map)

    manifestStream.close()

    if isOnlyCreateManifest:
        print("[Create Manifest File Only]")
        os.remove(packagePath)    
        return True

    # 如果没任何操作就直接退出，不写入版本，并且删除临时创建的zip
    if packageVersion != 0 and not has_changed and not force_create:
        # 没写入任何文件，删掉生成的zip直接退出吧
        print("[WARN]No Files Changed, no need to Zip Resource : %s " % packagePath)
        os.remove(packagePath)
        # 删除md5文件
        os.remove('%s.md5' % packagePath)
        if manifestPath:
            os.remove(manifestPath)
        return False

    # 客户端创建package info文件
    _create_package_info_file('%s.info' % packagePath, isNeedRestart, isNeedBack)
    return True


# 创建指定版本的差异包
def create_package_diff(args, isNeedRestart=False, isNeedBack=True, autoClean=True):
    """
    创建指定新版本的新差异资源包

    autoClean 是否创建完毕后，清理旧的差异包
    """

    # 寻找上一版zip包, 总结跟现在的不同
    bResult = True  # 标记是否有任意失败
    force_create_diff = False
    history_package_info = _get_history_package_info(args.artifact_dir, args.package_name, args.resVersion)
    
    i = args.newResVersion
    while True:
        i = i - 1
        if i < 0:
            break
        if args.newResVersion - i > MAX_PACKAGE_VERSION_SPAN and i != 0:
            continue

        _manifestName = '%s.%d.zip' % (args.package_name, i) + MANIFEST_FILE_NAME  # 用来对比差异的zip包
        _manifestPath = '%s/%s' % (args.artifact_dir, _manifestName)

        print ''
        print '====>'
        print 'ANANALYSE ==============> %s' % _manifestName

        compareFilesMap = {}  # 文件历史记录在这

        if i != 0 and not os.path.isfile(_manifestPath):
            print("[ERROR]Cannot find manifest: %s" % _manifestName)
            sys.exit(1)

        # 读取上一版的manifeset

        rManifestStream = file(_manifestPath, "r")
        rManifestReader = csv.DictReader(rManifestStream, delimiter='\t', fieldnames=MANIFEST_HEADERS)

        for row in rManifestReader:
            # 忽略第一行header
            if rManifestReader.line_num == 1:
                continue

            compareFilesMap[row['File']] = row  # 读取到所有记录

        # 写入新版
        newPackageName = '%s.%d-%d.zip' % (args.package_name, i, args.newResVersion)
        newPackagePath = '%s/%s' % (args.artifact_dir, newPackageName)
        print 'NEW PACK ==============> %s' % newPackageName

        need_restart, need_back = _get_package_info(history_package_info, i, args.newResVersion, isNeedRestart,
                                                    isNeedBack)
        print "create package info: need_restart = {}, need_back = {}".format(need_restart, need_back)
        if create_package(args, newPackagePath, args.paths, args.newResVersion, compareFilesMap, force_create_diff,
                          need_restart, need_back):
            # 当最后一个差异包生成成功后，要确保其它差异包强制生成！
            if (i + 1) == args.newResVersion:  #
                force_create_diff = True
            pass
        else:
            # 任意一个没有构建成功直接退出吧
            bResult = False
            break

    return bResult


# 校验文件，将差异文件写入更新包
def _write_package_file(zip_file, full_file_path, zip_file_path, ignores_ext, blacklist, 
                        compareFilesMap, isOnlyCreateManifest, writedFilesMap, touchFilesMap, manifestCsv):
    # 扩展名判断
    hasIgnoreExt = False
    if ignores_ext != None:
        for ext in ignores_ext:
            if full_file_path.endswith(ext):
                hasIgnoreExt = True  # 忽略该扩展名的
                break
    if hasIgnoreExt:
        return

    # 是否激活黑名单模式
    in_blacklist = False  # 默认true
    if blacklist:  # 黑名单存在则要判断
        for black_item in blacklist:
            if black_item in full_file_path:
                in_blacklist = True
                break
    if in_blacklist:
        # 黑名单直接忽略
        # if compareFilesMap:
        # manifestCsv.writerow(compareFilesMap[zip_file_path])
        return

    fileMD5 = _get_file_md5(full_file_path)
    # 进行比较! 如果一样，不写入文件，但写入信息, 以下是写入文件
    if ( \
            compareFilesMap == None or \
            (zip_file_path not in compareFilesMap) or \
            (zip_file_path in compareFilesMap and compareFilesMap[zip_file_path]['MD5'] != fileMD5) \
        ):

        print('%s --> %s' % (full_file_path, zip_file_path))
        if not isOnlyCreateManifest:
            zip_file.write(full_file_path, zip_file_path)

        writedFilesMap[zip_file_path] = full_file_path
        print 'write .... %s' % zip_file_path

    # 所有文件都写入这里，无例外
    touchFilesMap[zip_file_path] = full_file_path

    # 使用整数时间戳
    os.stat_float_times(False)
    file_mtime = os.path.getmtime(full_file_path)

    manifestCsv.writerow({
        'File': zip_file_path,
        'MD5': fileMD5,
        'Size': os.path.getsize(full_file_path),
        'MTime': file_mtime,
        'MFormatTime': datetime.datetime.fromtimestamp(os.path.getmtime(full_file_path))
    })


# 校验文件内容是否跟manifest一致，一致则生成md5文件
def _verify_package(packagePath, writedFilesMap, deleted_files_map):
    """
    校验文件内容是否跟manifest一致，一致则生成md5文件
    """
    assert (os.path.isfile(packagePath))
    with zipfile.ZipFile(packagePath, 'r', zipfile.ZIP_DEFLATED) as rz:
        print 'Verify zip package correct ... %s' % packagePath
        rManifestStream = rz.open(MANIFEST_FILE_NAME)
        rManifestReader = csv.DictReader(rManifestStream, delimiter='\t', fieldnames=MANIFEST_HEADERS)

        for row in rManifestReader:
            # 忽略第一行header
            if rManifestReader.line_num == 1:
                continue

            zipFilePath = row['File']
            if not zipFilePath in writedFilesMap:  # 上一次没有写入，忽略校验
                continue

            md5Str = row['MD5']
            stream = rz.open(zipFilePath)
            assert (stream)
            zipFileMd5 = _get_stream_md5(stream)
            fullFile = writedFilesMap[zipFilePath]
            assert (zipFileMd5 == md5Str)
            assert (zipFileMd5 == _get_file_md5(fullFile))

        for deleted in deleted_files_map:
            try:
                rz.open(deleted)
            except:
                continue  # 不存在就对了，存在反而不对
            assert (False)

        # 验证成功，生成md5文件
        with open('%s.md5' % packagePath, 'wb+') as md5f:
            md5f.write(_get_file_md5(packagePath))
    return True


def _create_package_info_file(package_info_file, is_need_restart=False, is_need_back_update=True):
    """生成更新包信息"""
    # 生成文件
    info = {"is_need_restart": is_need_restart,
            "is_need_back_update": is_need_back_update}

    with open(package_info_file, 'w') as f:
        json.dump(info, f, indent=4, ensure_ascii=False)


def _get_history_package_info(package_dir, package_name, cur_version):
    '''
    读取0-cur_version的info数据
    '''
    # 只有原始包的话，没有info数据
    if cur_version == 0:
        return None

    history_package_info = {}
    for i in range(0, cur_version):
        info_file_path = '{}/{}.{}.zip.info'.format(package_dir, package_name, i)
        if not os.path.isfile(info_file_path):
            print '[ERROR] _get_history_package_info failed!, Cannot find info_file: {}'.format(info_file_path)
            exit(1)

        with open(info_file_path, 'r') as f:
            info_content = f.read()
            info_dict = json.loads(info_content)
            history_package_info[i] = info_dict

    return history_package_info


def _get_package_info(history_package_info, from_update_version, to_update_version, 
                      is_need_restart=False, is_need_back_update=True):
    '''
    根据历史更新包的info信息，计算的info信息
    '''
    if not history_package_info:
        return is_need_restart, is_need_back_update

    for k, v in history_package_info.items():
        update_version = k
        if update_version > from_update_version and update_version < to_update_version:
            is_need_restart = is_need_restart or v['is_need_restart'] == "True"
            if v['is_need_back_update'] == "False":
                is_need_back_update = False

    return is_need_restart, is_need_back_update


def _get_clean_path(dirtyPath):
    """
    获取干净路径，主要替换windows的\\
    """
    return dirtyPath.replace('\\', '/')


def _get_stream_md5(stream):
    """
    获取流的MD5
    """
    return hashlib.md5(stream.read()).hexdigest().upper()


def _get_file_md5(filePath):
    """
    获取文件的MD5
    """
    return _get_stream_md5(open(filePath, 'rb'))


def _mkdir_p(path):
    """
    same as command `mkdir -p`
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def _get_current_resource_version(versionFilePath):
    """
    获取当前Resource Version返回 int
    """
    strVersion = ''
    with open(versionFilePath, 'rb+') as f:
        strVersion = f.read()
    return int(strVersion)


def main():
    parser = argparse.ArgumentParser(description=u'资源包、差异包生成工具， 传入指定的文件目录、输出名字，生成zip')
    parser.add_argument('-paths', required=True, nargs='+', help=u'路径，目录或文件，将作为zip的根路径')
    parser.add_argument('-project-path', required=True, help=u'工程根目录')
    parser.add_argument('-package-name', required=True, help=u'包名字前缀')
    parser.add_argument('-artifact-dir', required=True, help=u'最终成品目录？将搜索这些目录，找出过往的日志')
    parser.add_argument('-main-version', required=True, help=u'更新包主版本')
    parser.add_argument('-action', choices=['check', 'pack'], required=True, help=u'check只确保初始包存在，pack则生成差异包(递进版本)')
    parser.add_argument('-ignores-ext', nargs='*', help=u'彻底忽略的扩展名，如: .meta .gitignore')
    parser.add_argument('-blacklist', nargs='*', help=u'类似ignores-ext, 激活黑名单模式,路径包含这些字符串才会被忽略')
    parser.add_argument('-need-restart', action='store_true', help=u'更新包是否需要重启')
    parser.add_argument('-need-back', action='store_true', help=u'更新包是否需要后台更新')

    args = parser.parse_args()
    init_args(args)

    if args.action == 'check':
        do_check(args)
    elif args.action == 'pack':
        do_pack(args)
    else:
        print '[ERROR] Wrong pack action {}'.format(args.action)


if __name__ == '__main__':
    main()
