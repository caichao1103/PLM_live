# -*- coding: utf-8 -*-
# Author:       xiewenzhe<xiewenzhe@kingsoft.com>
# Date:         2020/6/4
# FileName:     tabfile_tool.py
# Description:  Tool for tabfile

import os
from buildtools import log_tool

class TabFile:
	def __init__(self, read_file_path):
		self.read_file_path = read_file_path


	# 读取文件
	def init(self):
		try:
			file_handle = open(self.read_file_path, 'r')
			file_content = file_handle.readlines()

			self.file_head = file_content[0].rstrip('\r').rstrip('\n').split('\t')
			self.row_count = len(file_content) - 1
			self.col_count = len(self.file_head)

			self.data = []
			for row_content in file_content:
				content = row_content.rstrip('\r').rstrip('\n').split('\t')
				self.data.append(content)

			file_handle.close()
			return True
		except Exception as e:
			log_tool.show_error('Read file: {} failed! Error: {}'.format(self.read_file_path, e))
			return False


	def get_row_count(self):
		return self.row_count


	def get_head(self):
		return self.file_head


	def get_value(self, row, colName):
		if (row <= 0 or row > self.row_count):
			return None

		col = self.file_head.index(colName)
		if (col < 0):
			return None

		return self.data[row][col]


	def set_value(self, row, colName, value):
		if (row < 0 or row > self.row_count):
			return

		col = self.file_head.index(colName)
		if (col < 0):
			return

		self.data[row][col] = value


	def save(self, save_file_path):
		file = open(save_file_path, 'w')
		if not file:
			return

		content = ''
		for line in self.data:
			content = '{}{}'.format(content, '\t'.join(line) + '\n')

		file.write(content)
		file.close()
