@echo off

echo 出Android包

echo 开始编译AssetBundle
python auto_build_asset_bundle.py
echo 编译AssetBundle完毕

echo 开始打包脚本与配置表
python auto_build_pack.py
echo 打包脚本与配置表完毕

echo 开始编译Apk
python auto_build_android_apk.py
echo 编译Apk完毕

pause
