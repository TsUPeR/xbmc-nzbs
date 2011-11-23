"""
 Copyright (c) 2010 Popeye

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use,
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import re
import urllib
import urllib2
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from xml.dom.minidom import parse, parseString
from rarfile import RarFile
from sabnzbd import sabnzbd
from threading import Thread

__settings__ = xbmcaddon.Addon(id='plugin.video.nzbs')
__language__ = __settings__.getLocalizedString

RE_PART = '.part\d{2,3}.rar$'
RE_R = '.r\d{2,3}$'
RE_CD = '(dvd|cd|bluray)1'
RE_A = 'a\.(rar|part01.rar)$'
RE_MOVIE = '\.avi$|\.mkv'
RE_MKV = '\.mkv$'
RAR_HEADER = "Rar!\x1a\x07\x00"
RAR_MIN_SIZE = 10485760

NS_MEDIA = "http://search.yahoo.com/mrss/"
NS_REPORT = "http://www.newzbin.com/DTD/2007/feeds/report/"
NS_NEWZNAB = "http://www.newznab.com/DTD/2010/feeds/attributes/"

NUMBER = [25,50,75,100][int(__settings__.getSetting("num"))]

SABNZBD = sabnzbd(__settings__.getSetting("sabnzbd_ip"),
        __settings__.getSetting("sabnzbd_port"),__settings__.getSetting("sabnzbd_key"))
INCOMPLETE_FOLDER = __settings__.getSetting("sabnzbd_incomplete")

MODE_LIST = "list"
MODE_MOVIE_LIST = "movie_list"
MODE_DOWNLOAD = "download"
MODE_PLAY = "play"
MODE_AUTO_PLAY = "auto_play"
MODE_DELETE = "delete"
MODE_REPAIR = "repair"
MODE_INCOMPLETE = "incomplete"
MODE_INCOMPLETE_LIST = "incomplete_list"

# ---NZBS---
MODE_NZBS = "nzbs"
MODE_NZBS_SEARCH = "nzbs&nzbs=search"
MODE_NZBS_MY = "nzbs&nzbs=mynzbs"
MODE_NZBS_MYSEARCH = "nzbs&nzbs=mysearch"

NZBS_URL = ("http://www.nzbs.org/rss.php?dl=1&i=" + __settings__.getSetting("nzbs_id") + 
            "&h=" + __settings__.getSetting("nzbs_key") + "&num=" + str(NUMBER) + "&")

TABLE_NZBS = [['Movies', 1, 2],
        [' - DVD', 0, 9],
        [' - WMW-HD', 0, 12],
        [' - XviD', 0, 2],
        [' - x264', 0, 4],
        ['TV', 1, 1],
        [' - DVD', 0, 11],
        [' - H264', 0, 22],
        [' - other', 0, 27],
        [' - XviD', 0, 1],
        [' - x264', 0, 14],
        ['Foreign', 1, 7],
        [' - Movies', 0, 30],
        [' - TV', 0, 24],
        ['XXX', 1, 4],
        [' - Clip', 0, 21],
        [' - DVD', 0, 13],
        [' - Pack', 0, 25],
        [' - XviD', 0, 3],
        [' - x264', 0, 23]]

def nzbs(params):
    if not(__settings__.getSetting("nzbs_id") and __settings__.getSetting("nzbs_key")):
        __settings__.openSettings()
    else:
        if params:
            get = params.get
            catid = get("catid")
            typeid = get("type")
            nzbs = get("nzbs")
            url = None
            if nzbs:
                if nzbs == "mynzbs":
                    url = NZBS_URL + "&action=mynzbs"
                if nzbs == "mysearch":
                    url = NZBS_URL + "&action=mysearches"
                if nzbs == "search":
                    search_term = search('Nzbs')
                    if search_term and catid:
                        url = NZBS_URL + "&q=" + search_term + "&catid=" + catid
                    if search_term and typeid:
                        url = NZBS_URL + "&q=" + search_term + "&type=" + typeid
            elif catid:
                url = NZBS_URL + "&catid=" + catid
                key = "&catid=" + catid
                add_posts('Search...', key, MODE_NZBS_SEARCH, '', '')
            else:
                url = NZBS_URL + "&type=" + typeid
                key = "&type=" + typeid
                add_posts('Search...', key, MODE_NZBS_SEARCH, '', '')
            if url:
                list_feed_nzbs(url)
        else:
            # Build Main menu
            for name, type, catid in TABLE_NZBS:
                if ("XXX" in name) and (__settings__.getSetting("nzbs_hide_xxx").lower() == "true"):
                 break
                if type:
                    key = "&type=" + str(catid)
                else:
                    key = "&catid=" + str(catid)
                add_posts(name, key, MODE_NZBS, '', '')
            # TODO add settings toggle
            add_posts("My NZB\'s", '', MODE_NZBS_MY, '', '')
            add_posts("My Searches", '', MODE_NZBS_MYSEARCH, '', '')
    return

def list_feed_nzbs(feedUrl):
    doc, state = load_xml(feedUrl)
    if doc and not state:
        for item in doc.getElementsByTagName("item"):
            title = get_node_value(item, "title")
            description = re.sub('<[^<]+?>', ' ', get_node_value(item, "description"))
            nzb = get_node_value(item, "nzb", NS_REPORT)
            thumbid = item.getElementsByTagNameNS(NS_REPORT, "imdbid")
            thumb = ""
            if thumbid:
                thumbid = get_node_value(item, "imdbid", NS_REPORT)
                thumb = "http://www.nzbs.org/imdb/" + thumbid + ".jpg"
            nzb = "&nzb=" + urllib.quote_plus(nzb) + "&nzbname=" + urllib.quote_plus(title)
            mode = MODE_LIST
            add_posts(title, nzb, mode, description, thumb)
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    else:
        if state == "site":
            xbmc.executebuiltin('Notification("NZBS","Site down")')
        else:
            xbmc.executebuiltin('Notification("NZBS","Malformed result")')
    return

def add_posts(title, url, mode, description='', thumb='', folder=True):
    listitem=xbmcgui.ListItem(title, iconImage="DefaultFolder.png", thumbnailImage=thumb)
    listitem.setInfo(type="Video", infoLabels={ "Title": title, "Plot" : description })
    xurl = "%s?mode=%s" % (sys.argv[0],mode)
    xurl = xurl + url
    listitem.setPath(xurl)
    if mode == MODE_LIST:
        cm = []
        cm_mode = MODE_DOWNLOAD
        cm_label = "Download"
        if (__settings__.getSetting("auto_play").lower() == "true"):
            folder = False
        cm_url_download = sys.argv[0] + '?mode=' + cm_mode + url
        cm.append((cm_label , "XBMC.RunPlugin(%s)" % (cm_url_download)))
        listitem.addContextMenuItems(cm, replaceItems=False)
    if mode == MODE_INCOMPLETE_LIST:
        cm = []
        cm_url_delete = sys.argv[0] + '?' + "mode=delete&incomplete=True" + url + "&folder=" + urllib.quote_plus(title)
        cm.append(("Delete" , "XBMC.RunPlugin(%s)" % (cm_url_delete)))
        listitem.addContextMenuItems(cm, replaceItems=False)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=xurl, listitem=listitem, isFolder=folder)
 
# FROM plugin.video.youtube.beta  -- converts the request url passed on by xbmc to our plugin into a dict  
def get_parameters(parameterString):
    commands = {}
    splitCommands = parameterString[parameterString.find('?')+1:].split('&')
    for command in splitCommands: 
        if (len(command) > 0):
            splitCommand = command.split('=')
            name = splitCommand[0]
            value = splitCommand[1]
            commands[name] = value  
    return commands
    
def get_nzb(params):
    get = params.get
    nzb = urllib.unquote_plus(get("nzb"))
    nzbname = urllib.unquote_plus(get("nzbname"))
    folder = INCOMPLETE_FOLDER + nzbname
    progressDialog = xbmcgui.DialogProgress()
    iscanceled = False
    if not os.path.exists(folder):
        addurl = SABNZBD.addurl(nzb, nzbname)
        progressDialog.create('NZBS', 'Sending request to SABnzbd')
        if "ok" in addurl:
            progressDialog.update(0, 'Request to SABnzbd succeeded', 'waiting for nzb download')
            seconds = 0
            while not SABNZBD.nzo_id(nzbname):
                label = str(seconds) + " seconds"
                progressDialog.update(0, 'Request to SABnzbd succeeded', 'waiting for nzb download', label)
                if progressDialog.iscanceled():
                    #SABnzbd uses nzb url as name until it has downloaded the nzb file
                    #Trying to delete both the queue and history
                    pause = SABNZBD.pause(nzb,'')
                    time.sleep(3)
                    delete_msg = SABNZBD.delete_queue(nzb,'')
                    if not "ok" in delete_msg:
                        xbmc.log(delete_msg)
                        delete_msg = SABNZBD.delete_history(nzb,'')
                        if not "ok" in delete_msg:
                            xbmc.log(delete_msg)
                    iscanceled = True
                    break
                time.sleep(1)
                seconds += 1
            if not iscanceled:
                switch = SABNZBD.switch(0,nzbname, '')
                if not "ok" in switch:
                    xbmc.log(switch)
                    progressDialog.update(0, 'Failed to prioritize the nzb!')
                    time.sleep(2)
                progressDialog.close()
                get_rar(nzbname)
            else:
                return
        else:
            xbmc.log(addurl)
            progressDialog.update(0, 'Request to SABnzbd failed!')
            time.sleep(2)
            progressDialog.close()
            return
    else:
        switch = SABNZBD.switch(0,nzbname, '')
        if not "ok" in switch:
            xbmc.log(switch)
            progressDialog.create('NZBS', 'Failed to prioritize the nzb!')
            time.sleep(2)
            progressDialog.close()
        # TODO make sure there is also a NZB in the queue
        get_rar(nzbname)

def get_rar(nzbname, first_rar = None, last_rar = None):
    iscanceled = False
    folder = INCOMPLETE_FOLDER + nzbname
    sab_nzo_id = SABNZBD.nzo_id(nzbname)
    file_list = []
    cd_file_list = []
    if not sab_nzo_id:
        sab_nzo_id_history = SABNZBD.nzo_id_history(nzbname)
    else:
        file_list = sorted_rar_file_list(SABNZBD.file_list(sab_nzo_id))
        cd_file_list = sorted_cd_file_list(file_list)
        sab_nzo_id_history = None
    progressDialog = xbmcgui.DialogProgress()
    progressDialog.create('NZBS', 'Request to SABnzbd succeeded', 'Waiting for download to start')
    if not os.path.exists(folder):
        seconds = 0
        while not os.path.exists(folder):
            label = str(seconds) + " seconds"
            progressDialog.update(0, 'Request to SABnzbd succeeded', 'Waiting for download to start', label)
            if progressDialog.iscanceled():
                dialog = xbmcgui.Dialog()
                ret = dialog.select('What do you want to do?', ['Delete job', 'Just download'])
                if ret == 0:
                    if sab_nzo_id:
                        pause = SABNZBD.pause('',sab_nzo_id)
                        time.sleep(3)
                        delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                    else:
                        delete_ = SABNZBD.delete_history('',sab_nzo_id_history)
                    if not "ok" in delete_:
                        xbmc.log(delete_)
                    iscanceled = True
                    break
                if ret == 1:
                    iscanceled = True
                    break
            time.sleep(1)
            seconds += 1
    if not iscanceled:
        file, iscanceled = wait_for_rar(progressDialog, folder, sab_nzo_id, sab_nzo_id_history, 'Request to SABnzbd succeeded', last_rar)
        if not iscanceled:
            progressDialog.update(0, 'First rar downloaded', 'pausing SABnzbd')
            if sab_nzo_id:
                pause = SABNZBD.pause('',sab_nzo_id)
                if "ok" in pause:
                    progressDialog.update(0, 'First rar downloaded', 'SABnzbd paused')
                else:
                    xbmc.log(pause)
                    progressDialog.update(0, 'Request to SABnzbd failed!')
                    time.sleep(2)
                # Set the post process to 0 = skip will cause SABnzbd to fail the job. requires streaming_allowed = 1 in sabnzbd.ini (6.x)
                postprocess = SABNZBD.postProcess(0, '', sab_nzo_id)
                if not "ok" in postprocess:
                    xbmc.log(postprocess)
                    progressDialog.update(0, 'Post process request to SABnzbd failed!')
                    time.sleep(1)
            progressDialog.close()
            time.sleep(1)
            if not last_rar:
                movie_list = movie_filenames(folder, file)
            else:
                movie_list = ['']
            auto_play = __settings__.getSetting("auto_play").lower() 
            if ( auto_play == "true") and (len(movie_list) == 1) and (len(cd_file_list) == 1):
                video_params = dict()
                video_params['nzoidhistory'] = str(sab_nzo_id_history)
                video_params['mode'] = MODE_AUTO_PLAY
                if not last_rar:
                    video_params['file'] = urllib.quote_plus(file)
                else:
                    video_params['file'] = urllib.quote_plus(first_rar)
                video_params['movie'] = urllib.quote_plus(movie_list[0])
                video_params['file_list'] = urllib.quote_plus(';'.join(file_list))
                video_params['folder'] = urllib.quote_plus(folder)
                video_params['nzoid'] = str(sab_nzo_id)
                video_params['last_rar'] = str(last_rar)
                return play_video(video_params)
            elif (auto_play == "true"):
                xurl = "%s?mode=%s" % (sys.argv[0],MODE_MOVIE_LIST)
                url = (xurl + "&movie_list=" + urllib.quote_plus(';'.join(movie_list)) + "&file_list=" +
                      urllib.quote_plus(';'.join(file_list)) + "&folder=" + urllib.quote_plus(folder) + 
                      "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history)) + "&last_rar=" + str(last_rar)
                if not last_rar:
                    url = url + "&file=" + urllib.quote_plus(file) 
                else:
                    url = url + "&file=" + urllib.quote_plus(first_rar) 
                xbmc.executebuiltin("Container.Update("+url+")")
            else:
                return playlist_item(file, file_list, movie_list, folder, sab_nzo_id, sab_nzo_id_history)
        else:
            return
    else:
        return

def sorted_rar_file_list(rar_file_list):
    file_list = []
    for file in rar_file_list:
        partrar = re.findall(RE_PART, file)
        rrar = re.findall(RE_R, file)
        if (file.endswith(".rar") and not partrar) or partrar or rrar:
            file_list.append(file)
    if len(file_list) > 1:
        file_list.sort()
    return file_list

def sorted_cd_file_list(rar_file_list):
    file_list = []
    for file in rar_file_list:
        partrar = re.findall(RE_PART, file)
        if (file.endswith(".rar") and not partrar) or file.endswith("part01.rar"):
            file_list.append(file)
    if len(file_list) > 1:
        file_list.sort()
    return file_list

def playlist_item(file, file_list, movie_list, folder, sab_nzo_id, sab_nzo_id_history):
    for movie in movie_list:
        xurl = "%s?mode=%s" % (sys.argv[0],MODE_PLAY)
        url = (xurl + "&file=" + urllib.quote_plus(file) + "&movie=" + urllib.quote_plus(movie) + "&file_list=" + urllib.quote_plus(';'.join(file_list)) + "&folder=" + urllib.quote_plus(folder) + 
                "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history))
        item = xbmcgui.ListItem(movie, iconImage='', thumbnailImage='')
        item.setInfo(type="Video", infoLabels={ "Title": movie})
        item.setPath(url)
        isfolder = False
        item.setProperty("IsPlayable", "true")
        cm = []
        if sab_nzo_id_history:
            cm_url_repair = sys.argv[0] + '?' + "mode=repair" + "&nzoidhistory=" + str(sab_nzo_id_history) + "&folder=" + urllib.quote_plus(folder)
            cm.append(("Repair" , "XBMC.RunPlugin(%s)" % (cm_url_repair)))
        cm_url_delete = sys.argv[0] + '?' + "mode=delete" + "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history) + "&folder=" + urllib.quote_plus(folder)
        cm.append(("Delete" , "XBMC.RunPlugin(%s)" % (cm_url_delete)))
        item.addContextMenuItems(cm, replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isfolder)
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    return 

def wait_for_rar(progressDialog, folder, sab_nzo_id, sab_nzo_id_history, dialog_string = None, last_rar = None):
    isCanceled = False
    rar = False
    size = -1
    seconds = 0
    while not rar:
        dirList = sorted_rar_file_list(os.listdir(folder))
        if last_rar:
            for file in dirList:
                if file == last_rar:
                    filepath = os.path.join(folder, file)
                    sizeLater = os.path.getsize(filepath)
                    if size == sizeLater:
                        rar = True
                        break
                    else:
                        size = sizeLater
                        break
        else:
            for file in dirList:
                partrar = re.findall(RE_PART, file)
                if (file.endswith(".rar") and not partrar) or file.endswith("part01.rar"):
                    filepath = os.path.join(folder, file)
                    sizeLater = os.path.getsize(filepath)
                    if size == sizeLater and size > RAR_MIN_SIZE:
                        rar = True
                        break
                    else:
                        size = sizeLater
                        break
        label = str(seconds) + " seconds"
        if sab_nzo_id:
            if dialog_string:
                if last_rar:
                    progressDialog.update(0, dialog_string, 'Waiting for last rar', label)
                else:
                    progressDialog.update(0, dialog_string, 'Waiting for first rar', label)
            else:
                progressDialog.update(0, 'Waiting for first rar', label)
            if progressDialog.iscanceled():
                dialog = xbmcgui.Dialog()
                ret = dialog.select('What do you want to do?', ['Delete job', 'Just download'])
                if ret == 0:
                    if sab_nzo_id:
                        pause = SABNZBD.pause('',sab_nzo_id)
                        time.sleep(3)
                        delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                    else:
                        delete_ = SABNZBD.delete_history('',sab_nzo_id_history)
                    if not "ok" in delete_:
                        xbmc.log(delete_)
                    iscanceled = True
                    break
                if ret == 1:
                    iscanceled = True
                    break
        seconds += 1
        time.sleep(1)
    return file, isCanceled

def list_movie(params):
    get = params.get
    mode = get("mode")
    file = urllib.unquote_plus(get("file"))
    file_list = urllib.unquote_plus(get("file_list")).split(";")
    movie_list = urllib.unquote_plus(get("movie_list")).split(";")
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    return playlist_item(file, file_list, movie_list, folder, sab_nzo_id, sab_nzo_id_history)

def list_incomplete(params):
    get = params.get
    nzbname = get("nzbname")
    nzbname = urllib.unquote_plus(nzbname)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    folder = INCOMPLETE_FOLDER + nzbname
    progressDialog = xbmcgui.DialogProgress()
    if sab_nzo_id:
        progressDialog.create('NZBS', 'Waiting for first rar')
    file, iscanceled = wait_for_rar(progressDialog, folder, sab_nzo_id, sab_nzo_id_history)
    if not iscanceled:
        if sab_nzo_id:
            progressDialog.update(0, 'First rar downloaded', 'pausing SABnzbd')
            pause = SABNZBD.pause('',sab_nzo_id)
            if "ok" in pause:
                progressDialog.update(0, 'First rar downloaded', 'SABnzbd paused')
            else:
                xbmc.log(pause)
                progressDialog.update(0, 'Request to SABnzbd failed!')
                time.sleep(2)
            # Set the post process to 0 = skip will cause SABnzbd to fail the job. requires streaming_allowed = 1 in sabnzbd.ini (6.x)
            setstreaming = SABNZBD.setStreaming('', sab_nzo_id)
            if not "ok" in setstreaming:
                xbmc.log(setstreaming)
                progressDialog.update(0, 'Stream request to SABnzbd failed!')
                time.sleep(2)
            progressDialog.close()
        file_list = SABNZBD.file_list(sab_nzo_id)
        movie_list = movie_filenames(folder, file)
        return playlist_item(file, file_list, movie_list, folder, sab_nzo_id, sab_nzo_id_history)
    else:
        return

def play_video(params):
    get = params.get
    mode = get("mode")
    file = get("file")
    file = urllib.unquote_plus(file)
    file_list = get("file_list")
    file_list = urllib.unquote_plus(file_list).split(";")
    movie = get("movie")
    movie = urllib.unquote_plus(movie)
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    last_rar = get("last_rar")
    if last_rar:
        if "None" in last_rar:
            last_rar = False
        else:
            last_rar = True
    # We might have deleted the path
    if os.path.exists(folder):
        # we trick xbmc to play avi by creating empty rars if the download is only partial
        write_fake(sab_nzo_id, file_list, folder)
        # lets play the movie
        if not movie:
            movie = movie_filenames(folder, file)[0]
        raruri = "rar://" + rarpath_fixer(folder, file) + "/" + movie
        item = xbmcgui.ListItem(movie, iconImage='', thumbnailImage='')
        item.setInfo(type="Video", infoLabels={ "Title": movie})
        item.setPath(raruri)
        item.setProperty("IsPlayable", "true")
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        if mode == MODE_AUTO_PLAY:
            if re.search(RE_MKV, movie, re.IGNORECASE) and not last_rar:
                remove_fake(sab_nzo_id, file_list, folder)
                t = Thread(target=get_last_rar, args=(folder, sab_nzo_id, file_list, file))
                t.start()
                return
            else:
                xbmc.Player( xbmc.PLAYER_CORE_DVDPLAYER ).play( raruri, item )
        else:
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)
        wait = 0
        time.sleep(3)
        while (wait <= 10):
            time.sleep(1)
            wait+= 1
            if xbmc.Player().isPlayingVideo():
                break
        # if the item is in the queue we remove the temp files
        remove_fake(sab_nzo_id, file_list, folder)
        add_to_playlist(file, file_list, folder)
    else:
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('NZBS', 'File deleted')
        time.sleep(1)
        progressDialog.close()
        time.sleep(1)
        xbmc.executebuiltin("Action(ParentDir)")
    return

def write_fake(sab_nzo_id, file_list, folder):
    if not "None" in sab_nzo_id:
                for filebasename in file_list:
                    filename = os.path.join(folder, filebasename)
                    if not os.path.exists(filename):
                            # make 7 byte file with a rar header
                            fd = open(filename,'wb')
                            fd.write(RAR_HEADER)
                            fd.close()
    return

def remove_fake(sab_nzo_id, file_list, folder):
    if not "None" in sab_nzo_id:
        for filebasename in file_list:
            filename = os.path.join(folder, filebasename)
            filename_one = os.path.join(folder, (filebasename + ".1"))
            if os.path.exists(filename):
                if os.stat(filename).st_size == 7:
                    os.remove(filename)
                    if os.path.exists(filename_one):
                        os.rename(filename_one, filename)
        resume = SABNZBD.resume('', sab_nzo_id)
        if not "ok" in resume:
            xbmc.log(resume)
    return

def get_last_rar(folder, sab_nzo_id, file_list, first_rar):
    nzbname = os.path.basename(folder)
    last_rar = find_last_rar(file_list, folder)
    sab_nzf_id = SABNZBD.nzf_id(sab_nzo_id, last_rar)
    if sab_nzf_id:
        SABNZBD.file_list_position(sab_nzo_id, [sab_nzf_id], 0)
    get_rar(nzbname, first_rar, last_rar)
    return

def find_last_rar(file_list, folder):
    file_list.extend(os.listdir(folder))
    rar_list = []
    for file in file_list:
        partrar = re.findall(RE_PART, file)
        rrar = re.findall(RE_R, file)
        if partrar or rrar:
            rar_list.append(file)
    if len(rar_list) > 1:
        rar_list.sort()
    return rar_list[-1]

def add_to_playlist(file, file_list, folder):
    fileStr = str(file)
    RE_CD_obj = re.compile(RE_CD, re.IGNORECASE)
    RE_A_obj = re.compile(RE_A, re.IGNORECASE)
    cd_file = RE_CD_obj.sub(r"\g<1>2", fileStr)
    a_file = RE_A_obj.sub(r"b.\g<1>", fileStr)
    if not cd_file == a_file:
        if len(file_list) == 1:
            file_list = sorted_rar_file_list(os.listdir(folder))
        for hit in file_list:
            if hit == a_file:
                file2str = a_file
            if hit == cd_file:
                file2str = cd_file
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        item = xbmcgui.ListItem(file2str, iconImage='', thumbnailImage='')
        item.setInfo(type="Video", infoLabels={ "Title": file2str})
        item.setProperty("IsPlayable", "true")
        position = playlist.getposition() + 1
        url = sys.argv[0] + '?' + "mode=play" + "&file=" + urllib.quote_plus(file2str) + "&movie=" + "&file_list=" + urllib.quote_plus(';'.join(file_list)) + "&folder=" + urllib.quote_plus(folder) + "&nzoid=Blank" + "&nzoidhistory=Blank"
        playlist.add(url, item, position)
    return

def movie_filenames(folder, file):
    filepath = os.path.join(folder, file)
    movieFileList = sort_filename(RarFile(filepath).namelist())
    return movieFileList

def sort_filename(filenameList):
    outList = filenameList[:]
    if len(filenameList) == 1:
        return outList
    else:
        for i in range(len(filenameList)):
            match = re.search(RE_MOVIE, filenameList[i], re.IGNORECASE)
            if not match:
                outList.remove(filenameList[i])
        if len(outList) == 0:
            outList.append(filenameList[0])
        return outList

def delete(params):
    get = params.get
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    incomplete = get("incomplete")
    xbmc.executebuiltin('Notification("NZBS","Deleting '+ folder +'")')
    if sab_nzo_id or sab_nzo_id_history:
        if sab_nzo_id:
            if not "None" in sab_nzo_id:
                pause = SABNZBD.pause('',sab_nzo_id)
                time.sleep(3)
                if "ok" in pause:
                    delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                    if "ok" in delete_:
                        xbmc.executebuiltin('Notification("NZBS","Deleting succeeded")')
                    else:
                        xbmc.log(delete_)
                        xbmc.executebuiltin('Notification("NZBS","Deleting failed")')
                else:
                    xbmc.executebuiltin('Notification("NZBS","Deleting failed")')
        if  sab_nzo_id_history:
            if not "None" in sab_nzo_id_history:
                delete_ = SABNZBD.delete_history('',sab_nzo_id_history)
                if "ok" in delete_:
                    xbmc.executebuiltin('Notification("NZBS","Deleting succeeded")')
                else:
                    xbmc.log(delete_)
                    xbmc.executebuiltin('Notification("NZBS","Deleting failed")')
    else:
        xbmc.executebuiltin('Notification("NZBS","Deleting failed")')
    time.sleep(2)
    if incomplete:
        xbmc.executebuiltin("Container.Refresh")
    else:
        xbmc.executebuiltin("Action(ParentDir)")
    return

def download(params):
    get = params.get
    nzb = urllib.unquote_plus(get("nzb"))
    nzbname = urllib.unquote_plus(get("nzbname"))
    addurl = SABNZBD.addurl(nzb, nzbname)
    progressDialog = xbmcgui.DialogProgress()
    progressDialog.create('NZBS', 'Sending request to SABnzbd')
    if "ok" in addurl:
        progressDialog.update(100, 'Request to SABnzbd succeeded')
        time.sleep(2)
    else:
        xbmc.log(addurl)
        progressDialog.update(0, 'Request to SABnzbd failed!')
        time.sleep(2)
    progressDialog.close()
    return

def repair(params):
    get = params.get
    sab_nzo_id_history = get("nzoidhistory")
    repair_ = SABNZBD.repair('',sab_nzo_id_history)
    progressDialog = xbmcgui.DialogProgress()
    progressDialog.create('NZBS', 'Sending request to SABnzbd')
    if "ok" in repair_:
        progressDialog.update(100, 'Repair', 'Succeeded')
    else:
        xbmc.log(repair_)
        progressDialog.update(0, 'Repair failed!')
    time.sleep(2)
    progressDialog.close()
    time.sleep(1)
    xbmc.executebuiltin("Action(ParentDir)")
    return

def incomplete():
    m_nzbname_list = []
    m_row = []
    for folder in os.listdir(INCOMPLETE_FOLDER):
        sab_nzo_id = SABNZBD.nzo_id(folder)
        if not sab_nzo_id:
            m_row.append(folder)
            m_row.append(None)
            m_nzbname_list.append(m_row)
            m_row = []
        else:
            url = "&nzoid=" + str(sab_nzo_id) + "&nzbname=" + urllib.quote_plus(folder)
            add_posts(folder, url, MODE_INCOMPLETE_LIST)
    nzbname_list = SABNZBD.nzo_id_history_list(m_nzbname_list)
    for row in nzbname_list:
        if row[1]:
            url = "&nzoidhistory=" + str(row[1]) + "&nzbname=" + urllib.quote_plus(row[0])
            add_posts(row[0], url, MODE_INCOMPLETE_LIST)
    return

def get_node_value(parent, name, ns=""):
    if ns:
        return parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data
    else:
        return parent.getElementsByTagName(name)[0].childNodes[0].data

def load_xml(url):
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
    except:
        xbmc.log("plugin.video.nzbs: unable to load url: " + url)
        return None, "site"
    xml = response.read()
    response.close()
    try:
        out = parseString(xml)
    except:
        xbmc.log("plugin.video.nzbs: malformed xml from url: " + url)
        return None, "xml"
    return out, None

def rarpath_fixer(folder, file):
    filepath = os.path.join(folder, file)
    filepath = filepath.replace(".","%2e")
    filepath = filepath.replace("-","%2d")
    filepath = filepath.replace(":","%3a")
    filepath = filepath.replace("\\","%5c")
    filepath = filepath.replace("/","%2f")
    return filepath

def search(dialog_name):
    searchString = unikeyboard(__settings__.getSetting( "latestSearch" ), 'Search NZBS')
    if searchString == "":
        xbmcgui.Dialog().ok('NZBS','Missing text')
    elif searchString:
        latestSearch = __settings__.setSetting( "latestSearch", searchString )
        dialogProgress = xbmcgui.DialogProgress()
        dialogProgress.create(dialog_name, 'Searching for: ' , searchString)
        #The XBMC onscreen keyboard outputs utf-8 and this need to be encoded to unicode
    encodedSearchString = urllib.quote_plus(searchString.decode("utf_8").encode("raw_unicode_escape"))
    return encodedSearchString

#From old undertexter.se plugin    
def unikeyboard(default, message):
    keyboard = xbmc.Keyboard(default, message)
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        return keyboard.getText()
    else:
        return ""

if (__name__ == "__main__" ):
    if not (__settings__.getSetting("firstrun") and __settings__.getSetting("sabnzbd_ip") and
        __settings__.getSetting("sabnzbd_port") and __settings__.getSetting("sabnzbd_key") and 
        __settings__.getSetting("sabnzbd_incomplete")):
        __settings__.openSettings()
        __settings__.setSetting("firstrun", '1')
    if (not sys.argv[2]):
        if __settings__.getSetting("nzbs_enable").lower() == "true":
            nzbs(None)
        add_posts('Incomplete', '', MODE_INCOMPLETE)
    else:
        params = get_parameters(sys.argv[2])
        get = params.get
        if get("mode")== MODE_LIST:
            get_nzb(params)
        if get("mode")== MODE_MOVIE_LIST:
            list_movie(params)
        if get("mode")== MODE_PLAY or get("mode")== MODE_AUTO_PLAY:
            play_video(params)
        if get("mode")== MODE_DELETE:
            delete(params)
        if get("mode")== MODE_DOWNLOAD:
            download(params)
        if get("mode")== MODE_REPAIR:
            repair(params)
        if get("mode")== MODE_NZBS:
            nzbs(params)
        if get("mode")== MODE_INCOMPLETE:
            incomplete()
        if get("mode")== MODE_INCOMPLETE_LIST:
            list_incomplete(params)

xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, cacheToDisc=True)
