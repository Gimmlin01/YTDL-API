#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging,os,pexpect,subprocess
from threading import Thread
import youtube_dl,MySqlHandler
#logging.basicConfig(filename='example.log',level=logging.DEBUG)
logging.basicConfig(level=logging.DEBUG,format='%(levelname)s:%(message)s',)
#logging.debug('This message should go to the log file')
#logging.info('So should this')
#logging.warning('And this, too')


class Downloader():
    def __init__(self, url=None, conv=None):
        self.url=url
        self.conv=conv
        self.filename=None
        self.status=0
        self.duration=0
        self.keepFile=False
        self.dl_id=-1
        self.sql = MySqlHandler.MySqlHandler()
        if url:
            self.dl_id=self.sql.createRow(url)
            os.mkdir(str(self.dl_id))
            self.info("Song Created")
        else:
            e=TypeError("Song has no url")
            self.warn("Song Not Created",e)
            raise e

    def start(self):
        self.worker=DownloaderWorker(self)
        self.worker.start()
        return self.dl_id

    def setFilename(self,name=None):
        if name and os.path.isfile(name):
            self.filename = name
            if self.sql.updateRow("filename",name):
                self.debug("Filename set to {}".format(name))
                return True
        else:
            self.warn("Could not set Filename")
        return False

    def setStatus(self,status):
        self.status=status
        self.sql.updateRow("status",status)
        self.debug("Status set to {}".format(status))



    def convert(self):
        self.debug("Converting to {}".format(self.conv))
        try:
            if (self.conv=="mp3"):
                filename=self.convertToMp3()
            else:
                filename=self.convertToNothing()
            if not self.keepFile and not self.filename==filename:
                os.remove(self.filename)
            if self.setFilename(filename):
                self.setStatus(100)
            else:
                self.setStatus(-1)
        except Exception as e:
            self.setStatus(-1)

    def parseTime(self,time):
        d=time.split(":")
        t=int(d[0])*3600+int(d[1])*60+float(d[2])
        return t

    def convertToNothing(self):
        self.setStatus(100)
        return self.filename

    def convertToMp3(self):
        newfilename = self.filename
        if (os.path.splitext(self.filename)[1]!=".mp3"):
            newfilename = os.path.splitext(self.filename)[0]+".mp3"
            self.info("Starting Converting to Mp3")
            cmd="ffmpeg -y -i '{}' -vn -ar 44100 -ac 2 -ab 192k -f mp3 '{}'".format(self.filename.replace( "'", r"'\''" ),newfilename.replace( "'", r"'\''" ))
            self.debug("Invoking Command: {}".format(cmd))
            thread = pexpect.spawn(cmd)
            cpl = thread.compile_pattern_list([
                pexpect.EOF,
                ".*Duration:.*",
                ".*time=.*"
                '(.+)'
            ])

            while True:
                i = thread.expect_list(cpl, timeout=None)
                if i == 0: # EOF
                    self.debug("Converting sub process exited")
                    break
                elif i == 1:
                    output = thread.match.group(0).decode("utf-8")
                    d=output.find("Duration: ")
                    self.duration=self.parseTime(output[d+10:output.find(",",d)])
                    self.debug("Output: {} parsedTime: {}".format(output,self.duration))
                    thread.close
                elif i == 2:
                    output = thread.match.group(0).decode("utf-8")
                    d=output.find("time=")
                    time=output[d+5:output.find(" ",d)]
                    self.setStatus(min(round(self.parseTime(time)/self.duration*80+20,2),99.99))
                    thread.close
                elif i == 3:
                    unknown_line = thread.match.group(0)
                    self.warn("Unknown Line: {}".format(unknown_line))
        basename=os.path.basename(newfilename)[:-4]
        infolist=basename.split(" - ")
        if not len(infolist)>1:
            infolist=basename.split(" – ")
        self.debug("writing tags")
        if len(infolist) >1:
            artist=infolist[0]
            track=infolist[1]
            subprocess.call(["id3v2","-a",artist,"-t",track,newfilename])
        else:
            track=infolist[0]
            subprocess.call(["id3v2","-t",track,newfilename])
        self.debug("done")
        return newfilename

    def delete(self):
        os.rmdir(str(self.dl_id))
        self.sql.deleteRow(self.dl_id)
        self.info("succssesfully deleted")

    def warn(self,text,e=None):
        logging.warning("[{}] {}:\n{}".format(self.dl_id,e,text))

    def debug(self,text,e=None):
        logging.debug("[{}] {} ".format(self.dl_id,text))

    def info(self,text):
        logging.info("[{}] {}".format(self.dl_id,text))



class MyLogger(object):
    def __init__(self,dl_id):
        self.dl_id=dl_id

    def debug(self, msg):
        logging.debug("[{}] {}".format(self.dl_id,msg))

    def warning(self, msg):
        logging.warning("[{}] {}".format(self.dl_id,msg))

    def error(self, msg):
        logging.error("[{}] {}".format(self.dl_id,msg))


class DownloaderWorker(Thread):
    def __init__(self,song=None):
        super(DownloaderWorker,self).__init__()
        self.wd=os.getcwd()
        self.song=song
        self.logger=MyLogger(self.song.dl_id)
        self.opts ={
            "outtmpl": "{}/{}/%(title)s.%(ext)s".format(self.wd,self.song.dl_id),
            'format': 'bestaudio/best',
            'postprocessors': [],
            'verbose':True,
            'logger': self.logger,
            'progress_hooks': [self.hook]
        }

    def run(self):
        logging.info("[{}] Starting Thread for {}".format(self.song.dl_id,self.song.url))
        self.song.setStatus(0)
        try:
            with youtube_dl.YoutubeDL(self.opts) as ydl:
                ydl.download([self.song.url])
        except Exception as e:
            logging.warn("[{}] Download Failed:\n{}".format(self.song.dl_id,e))
            self.song.delete()
        logging.info("[{}] Finished Thread".format(self.song.dl_id,self.song.url))

    def hook(self,d):
        if d['status'] == 'finished':
            self.song.setStatus(20)
            logging.info("[{}] Finished Download".format(self.song.dl_id))
            filename=d["filename"]
            if filename:
                self.song.setFilename(filename)
            t = Thread(target=self.startConv, args=(self,))
            t.start()
        if d["status"] == "downloading":
            status=d["_percent_str"][:-1]
            self.song.setStatus(float(status)*0.2)

    def startConv(self,t):
        t.join()
        self.song.convert()

class Song():
    def __init__(self,dl_id=None,url=None,filename=None,status=None,json=None):
        if dl_id:
            self.dl_id=dl_id
        if url:
            self.url=url
        if filename:
            self.filename=filename
        if not status==None:
            self.status=status
        if json:
            self.__dict__=json

    def toJson(self):
        return self.__dict__
