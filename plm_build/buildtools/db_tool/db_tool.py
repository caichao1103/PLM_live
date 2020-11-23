# -*- coding: utf-8 -*-

import MySQLdb
import MySQLdb.cursors


# 获取数据库连接对象
def connect_to_db(db_host, db_port, db_user, db_pass, db_name):
    conn = MySQLdb.connect(host=db_host,
                           port=db_port,
                           user=db_user,
                           passwd=db_pass,
                           db=db_name,
                           cursorclass=MySQLdb.cursors.DictCursor,
                           charset='utf8',
                           use_unicode=True)

    return conn