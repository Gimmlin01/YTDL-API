#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
from sqlalchemy import create_engine


class MySqlHandler():
    def __init__(self,mysql_login,dl_id=-1):
        self.db_connect = create_engine('mysql+pymysql://'+mysql_login+'@localhost/ytdl?charset=utf8mb4', encoding='utf8')
        self.dl_id=dl_id

    def updateRow(self,col,value,dl_id=0):
        if dl_id==0:
            dl_id=self.dl_id
        self.debug("Trying to Update {} to {}".format(col,value))
        try:
            conn = self.db_connect.connect()
            query = conn.execute("UPDATE downloads SET "+col+" = %s WHERE ID = %s",(value,dl_id))
            conn.close()
            self.debug("Done")
            return True
        except Exception as e:
            self.warn("updateRow {} to {} failed".format(col,value),e)
            return False

    def createRow(self,url):
        self.debug("Trying to create a new row for {}".format(url))
        try:
            conn = self.db_connect.connect()
            query = conn.execute("INSERT into downloads values(null,null,'{0}',0,null)".format(url))
            conn.close()
            self.debug("Done")
            self.dl_id=query.lastrowid
            return self.dl_id
        except Exception as e:
            self.warn("newRow for {} failed".format(col,value),e)
            return false

    def deleteRow(self,dl_id):
        self.debug("Trying to delete [{}]".format(dl_id))
        try:
            conn = self.db_connect.connect()
            query = conn.execute("DELETE from downloads WHERE ID = {}".format(dl_id))
            conn.close()
            self.debug("Done")
            return True
        except Exception as e:
            self.warn("deleteRow for [{}] failed".format(dl_id),e)
            return False

    def selectRow(self,dl_id="",offset=0,limit=-1):
        if limit < 0:
            limit=18446744073709551615
        self.debug("Trying to Select [{}]".format(dl_id))
        try:
            query_string=""
            if dl_id == "":
                query_string = "SELECT id,url,filename,status from downloads where status>=100 ORDER BY time DESC Limit {} Offset {}".format(limit,offset)
            else:
                query_string = "SELECT id,url,filename,status from downloads where id ={} Limit {} Offset {}".format(dl_id,limit,offset)
            self.debug(query_string)
            conn = self.db_connect.connect()
            query=conn.execute(query_string)
            conn.close()
            self.debug("Done")
            return [i for i in query.cursor.fetchall()]
        except Exception as e:
            self.warn("selectRow for [{}] failed".format(dl_id),e)
            return False

    def warn(self,text,e=None):
        logging.warning("[{}] {}:\n{}".format(self.dl_id,e,text))

    def debug(self,text,e=None):
        logging.debug("[{}] {} ".format(self.dl_id,text))

    def info(self,text):
        logging.info("[{}] {}".format(self.dl_id,text))
