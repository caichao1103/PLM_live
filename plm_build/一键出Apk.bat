@echo off

echo ��Android��

echo ��ʼ����AssetBundle
python auto_build_asset_bundle.py
echo ����AssetBundle���

echo ��ʼ����ű������ñ�
python auto_build_pack.py
echo ����ű������ñ����

echo ��ʼ����Apk
python auto_build_android_apk.py
echo ����Apk���

pause
