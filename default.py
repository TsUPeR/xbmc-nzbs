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
from threading import Thread

import sabnzbd
import utils
import nfo

__settings__ = xbmcaddon.Addon(id='plugin.video.nzbs')
__language__ = __settings__.getLocalizedString

NS_MEDIA = "http://search.yahoo.com/mrss/"
NS_REPORT = "http://www.newzbin.com/DTD/2007/feeds/report/"
NS_NEWZNAB = "http://www.newznab.com/DTD/2010/feeds/attributes/"

NUMBER = [25,50,75,100][int(__settings__.getSetting("num"))]

SABNZBD = sabnzbd.Sabnzbd(__settings__.getSetting("sabnzbd_ip"),
        __settings__.getSetting("sabnzbd_port"),__settings__.getSetting("sabnzbd_key"),
        __settings__.getSetting("sabnzbd_user"), __settings__.getSetting("sabnzbd_pass"))
INCOMPLETE_FOLDER = __settings__.getSetting("sabnzbd_incomplete")
AUTO_PLAY = (__settings__.getSetting("auto_play").lower() == "true")

MODE_LIST = "list"
MODE_MOVIE_LIST = "movie_list"
MODE_DOWNLOAD = "download"
MODE_PLAY = "play"
MODE_AUTO_PLAY = "auto_play"
MODE_DELETE = "delete"
MODE_REPAIR = "repair"
MODE_INCOMPLETE = "incomplete"
MODE_INCOMPLETE_LIST = "incomplete_list"
MODE_JSONRPC = "jsonrpc"

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
                add_posts({'title':'Search...',}, key, MODE_NZBS_SEARCH)
            else:
                url = NZBS_URL + "&type=" + typeid
                key = "&type=" + typeid
                add_posts({'title':'Search...',}, key, MODE_NZBS_SEARCH)
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
                add_posts({'title' : name,}, key, MODE_NZBS)
            # TODO add settings toggle
            add_posts({'title':"My NZB\'s",}, '', MODE_NZBS_MY)
            add_posts({'title':"My Searches",}, '', MODE_NZBS_MYSEARCH)
    return

def list_feed_nzbs(feedUrl):
    doc, state = load_xml(feedUrl)
    if doc and not state:
        for item in doc.getElementsByTagName("item"):
            info_labels = dict()
            info_labels['title'] = get_node_value(item, "title")
            info_labels['plot'] = re.sub('<[^<]+?>', ' ', get_node_value(item, "description"))
            nzb = get_node_value(item, "nzb", NS_REPORT)
            thumbid = item.getElementsByTagNameNS(NS_REPORT, "imdbid")
            thumb = ""
            if thumbid:
                thumbid = get_node_value(item, "imdbid", NS_REPORT)
                thumb = "http://www.nzbs.org/imdb/" + thumbid + ".jpg"
            nzb = "&nzb=" + urllib.quote_plus(nzb) + "&nzbname=" + urllib.quote_plus(info_labels['title'])
            mode = MODE_LIST
            add_posts(info_labels, nzb, mode, thumb)
        xbmcplugin.setContent(HANDLE, 'movies')
    else:
        if state == "site":
            xbmc.executebuiltin('Notification("NZBS","Site down")')
        else:
            xbmc.executebuiltin('Notification("NZBS","Malformed result")')
    return

def add_posts(info_labels, url, mode, thumb='', fanart='', folder=True):
    listitem=xbmcgui.ListItem(info_labels['title'], iconImage="DefaultVideo.png", thumbnailImage=thumb)
    listitem.setInfo(type="Video", infoLabels=info_labels)
    listitem.setProperty("Fanart_Image", fanart)
    xurl = "%s?mode=%s" % (sys.argv[0],mode)
    xurl = xurl + url
    listitem.setPath(xurl)
    if mode == MODE_LIST:
        cm = []
        cm_mode = MODE_DOWNLOAD
        cm_label = "Download"
        if AUTO_PLAY:
            folder = False
        cm_url_download = sys.argv[0] + '?mode=' + cm_mode + url
        cm.append((cm_label , "XBMC.RunPlugin(%s)" % (cm_url_download)))
        listitem.addContextMenuItems(cm, replaceItems=False)
    if mode == MODE_INCOMPLETE_LIST:
        cm = []
        cm_url_delete = sys.argv[0] + '?' + "mode=delete&incomplete=True" + url
        cm.append(("Delete" , "XBMC.RunPlugin(%s)" % (cm_url_delete)))
        cm_url_delete_all = sys.argv[0] + '?' + "mode=delete&delete_all=True&incomplete=True" + url
        cm.append(("Delete all inactive" , "XBMC.RunPlugin(%s)" % (cm_url_delete_all)))
        listitem.addContextMenuItems(cm, replaceItems=False)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=xurl, listitem=listitem, isFolder=folder)
    
def is_nzb_home(params):
    get = params.get
    nzb = urllib.unquote_plus(get("nzb"))
    nzbname = urllib.unquote_plus(get("nzbname"))
    folder = INCOMPLETE_FOLDER + nzbname
    progressDialog = xbmcgui.DialogProgress()
    iscanceled = False
    if not os.path.exists(folder):
        addurl = SABNZBD.addurl(nzb, nzbname)
        # TODO
        # Start a meta_data_fetch thread and download covers, fanart and nfo
        # to the incomplete folder
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
                t = Thread(target=save_nfo, args=(folder,))
                t.start()
                return True
            else:
                return False
        else:
            xbmc.log(addurl)
            progressDialog.update(0, 'Request to SABnzbd failed!')
            time.sleep(2)
            progressDialog.close()
            return False
    else:
        switch = SABNZBD.switch(0,nzbname, '')
        if not "ok" in switch:
            xbmc.log(switch)
            progressDialog.create('NZBS', 'Failed to prioritize the nzb!')
            time.sleep(2)
            progressDialog.close()
        # TODO make sure there is also a NZB in the queue
        return True

def save_nfo(folder):
    nfo.NfoLabels(folder).save()
    return

def pre_play(nzbname, mode = None):
    iscanceled = False
    folder = INCOMPLETE_FOLDER + nzbname
    sab_nzo_id = SABNZBD.nzo_id(nzbname)
    file_list = utils.list_dir(folder)
    sab_file_list = []
    multi_arch_list = []
    if sab_nzo_id is None:
        sab_nzo_id_history = SABNZBD.nzo_id_history(nzbname)
    else:
        sab_file_list = SABNZBD.file_list(sab_nzo_id)
        file_list.extend(sab_file_list)
        sab_nzo_id_history = None
    file_list = utils.sorted_rar_file_list(file_list)
    multi_arch_list = utils.sorted_multi_arch_list(file_list)
    # Loop though all multi archives and add file to the 
    play_list = []
    for arch_rar, byte in multi_arch_list:
        if sab_nzo_id is not None:
            t = Thread(target=to_bottom, args=(sab_nzo_id, sab_file_list, file_list,))
            t.start()
            iscanceled = get_rar(folder, sab_nzo_id, arch_rar)
        if iscanceled:
            break
        else:
            if sab_nzo_id:
                set_streaming(sab_nzo_id)
            # TODO is this needed?
            time.sleep(1)
            # RAR ANALYSYS #
            in_rar_file_list = utils.rar_filenames(folder, arch_rar)
            movie_list = utils.sort_filename(in_rar_file_list)
            # Make sure we have a movie
            if not (len(movie_list) >= 1):
                xbmc.executebuiltin('Notification("NZBS","Not a movie!")')
                break
            # Who needs sample?
            movie_no_sample_list = utils.no_sample_list(movie_list)
            # If auto play is enabled we skip samples in the play_list
            if AUTO_PLAY and mode is not MODE_INCOMPLETE_LIST:
                for movie_file in movie_no_sample_list:
                    play_list.append(arch_rar)
                    play_list.append(movie_file)
            else:
                for movie_file in movie_list:
                    play_list.append(arch_rar)
                    play_list.append(movie_file)
            # If the movie is a .mkv we need the last rar
            if utils.is_movie_mkv(movie_list) and sab_nzo_id:
                # If we have a sample or other file, the second rar is also needed..
                if len(movie_no_sample_list) != len(in_rar_file_list):
                    second_rar = utils.find_rar(file_list, 0)
                    iscanceled = get_rar(folder, sab_nzo_id, second_rar)
                last_rar = utils.find_rar(file_list, -1)
                iscanceled =  get_rar(folder, sab_nzo_id, last_rar)
                if iscanceled: 
                    break 
    if iscanceled:
        return
    else:
        rar_file_list = [x[0] for x in file_list]
        if (len(rar_file_list) >= 1):
            if AUTO_PLAY and ( mode is None or mode is MODE_JSONRPC):
                video_params = dict()
                if not mode:
                    video_params['mode'] = MODE_AUTO_PLAY
                else:
                    video_params['mode'] = MODE_JSONRPC
                video_params['play_list'] = urllib.quote_plus(';'.join(play_list))
                video_params['file_list'] = urllib.quote_plus(';'.join(rar_file_list))
                video_params['folder'] = urllib.quote_plus(folder)
                return play_video(video_params)   
            else:
                return playlist_item(play_list, rar_file_list, folder, sab_nzo_id, sab_nzo_id_history)
        else:
            xbmc.executebuiltin('Notification("NZBS","No rar\'s in the NZB!!")')
            return

def set_streaming(sab_nzo_id):
    # Set the post process to 0 = skip will cause SABnzbd to fail the job. requires streaming_allowed = 1 in sabnzbd.ini (6.x)
    setstreaming = SABNZBD.setStreaming('', sab_nzo_id)
    if not "ok" in setstreaming:
        xbmc.log(setstreaming)
        xbmc.executebuiltin('Notification("NZBS","Post process request to SABnzbd failed!")')
        time.sleep(1)
    return

def playlist_item(play_list, rar_file_list, folder, sab_nzo_id, sab_nzo_id_history):
    new_play_list = play_list[:]
    for arch_rar, movie_file in zip(play_list[0::2], play_list[1::2]):
        info = nfo.ReadNfoLabels(folder)
        xurl = "%s?mode=%s" % (sys.argv[0],MODE_PLAY)
        url = (xurl + "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history)) +\
              "&play_list=" + urllib.quote_plus(';'.join(new_play_list)) + "&folder=" + urllib.quote_plus(folder) +\
              "&file_list=" + urllib.quote_plus(';'.join(rar_file_list))
        new_play_list.remove(arch_rar)
        new_play_list.remove(movie_file)
        item = xbmcgui.ListItem(movie_file, iconImage='DefaultVideo.png', thumbnailImage=info.thumbnail)
        item.setInfo(type="Video", infoLabels=info.info_labels)
        item.setProperty("Fanart_Image", info.fanart)
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
    
def get_rar(folder, sab_nzo_id, some_rar):
    if sab_nzo_id:
        sab_nzf_id = SABNZBD.nzf_id(sab_nzo_id, some_rar)
        if sab_nzf_id:
            SABNZBD.file_list_position(sab_nzo_id, [sab_nzf_id], 0)
        return wait_for_rar(folder, sab_nzo_id, some_rar)
    else:
        return False

def wait_for_rar(folder, sab_nzo_id, some_rar):
    isCanceled = False
    is_rar_found = False
    # If some_rar exist we skip dialogs
    for file, bytes in utils.sorted_rar_file_list(utils.list_dir(folder)):
        if file == some_rar:
            is_rar_found = True
            break
    if not is_rar_found:
        seconds = 0
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('NZBS', 'Request to SABnzbd succeeded, waiting for ', some_rar)
        while not is_rar_found:
            seconds += 1
            time.sleep(1)
            dirList = utils.sorted_rar_file_list(utils.list_dir(folder))
            for file, bytes in dirList:
                if file == some_rar:
                    path = os.path.join(folder,file)
                    # Wait until the file is written to disk before proceeding
                    size_now = int(bytes)
                    size_later = 0
                    while (size_now != size_later) or (size_now == 0) or (size_later == 0):
                        size_now = os.stat(path).st_size
                        if size_now != size_later:
                            time.sleep(0.5)
                            size_later = os.stat(path).st_size
                    is_rar_found = True
                    break
            label = str(seconds) + " seconds"
            # TODO
            # Shorten some_rar if to long for the dialog window
            progressDialog.update(0, 'Request to SABnzbd succeeded, waiting for', some_rar, label)
            if progressDialog.iscanceled():
                progressDialog.close()
                dialog = xbmcgui.Dialog()
                ret = dialog.select('What do you want to do?', ['Delete job', 'Just download'])
                if ret == 0:
                    pause = SABNZBD.pause('',sab_nzo_id)
                    time.sleep(3)
                    delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                    if not "ok" in delete_:
                        xbmc.log(delete_)
                        xbmc.executebuiltin('Notification("NZBS","Deleting failed")')
                    else:
                        xbmc.executebuiltin('Notification("NZBS","Deleting succeeded")')
                    iscanceled = True
                    return iscanceled 
                if ret == 1:
                    iscanceled = True
                    xbmc.executebuiltin('Notification("NZBS","Downloading")')
                    return iscanceled
        progressDialog.close()
    return isCanceled

def to_bottom(sab_nzo_id, sab_file_list, file_list):
    diff_list = list(set([x[0] for x in sab_file_list])-set([x[0] for x in file_list]))
    nzf_list = SABNZBD.nzf_id_list(sab_nzo_id, diff_list)
    SABNZBD.file_list_position(sab_nzo_id, nzf_list, 3)
    return

def list_movie(params):
    get = params.get
    mode = get("mode")
    file_list = urllib.unquote_plus(get("file_list")).split(";")
    play_list = urllib.unquote_plus(get("play_list")).split(";")
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    return playlist_item(play_list, file_list, folder, sab_nzo_id, sab_nzo_id_history)

def list_incomplete(params):
    get = params.get
    nzbname = get("nzbname")
    nzbname = urllib.unquote_plus(nzbname)
    folder = INCOMPLETE_FOLDER + nzbname
    pre_play(nzbname, MODE_INCOMPLETE_LIST)

def play_video(params):
    get = params.get
    mode = get("mode")
    file_list = get("file_list")
    file_list = urllib.unquote_plus(file_list).split(";")
    play_list = get("play_list")
    play_list = urllib.unquote_plus(play_list).split(";")
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    # We might have deleted the path
    if os.path.exists(folder):
        # we trick xbmc to play avi by creating empty rars if the download is only partial
        utils.write_fake(file_list, folder)
        # Prepare potential file stacking
        if (len(play_list) > 2):
            rar = []
            for arch_rar, movie_file in zip(play_list[0::2], play_list[1::2]):
                raruri = "rar://" + utils.rarpath_fixer(folder, arch_rar) + "/" + movie_file
                rar.append(raruri)
                raruri = 'stack://' + ' , '.join(rar)
        else:
            raruri = "rar://" + utils.rarpath_fixer(folder, play_list[0]) + "/" + play_list[1]
        info = nfo.NfoLabels()
        item = xbmcgui.ListItem(info.info_labels['title'], iconImage='DefaultVideo.png', thumbnailImage=info.thumbnail)
        item.setInfo(type="Video", infoLabels=info.info_labels)
        item.setPath(raruri)
        item.setProperty("IsPlayable", "true")
        xbmcplugin.setContent(HANDLE, 'movies')
        time.sleep(1)
        if mode == MODE_AUTO_PLAY:
            xbmc.Player( xbmc.PLAYER_CORE_DVDPLAYER ).play( raruri, item )
        else:
            xbmcplugin.setResolvedUrl(handle=HANDLE, succeeded=True, listitem=item)
        wait = 0
        time.sleep(3)
        while (wait <= 10):
            time.sleep(1)
            wait+= 1
            if xbmc.Player().isPlayingVideo():
                break
        # if the item is in the queue we remove the temp files
        utils.remove_fake(file_list, folder)
    else:
        # TODO Notification
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('NZBS', 'File deleted')
        time.sleep(1)
        progressDialog.close()
        time.sleep(1)
        xbmc.executebuiltin("Action(ParentDir)")
    return


def delete(params):
    get = params.get
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    sab_nzo_id_history_list = get("nzoidhistory_list")
    if sab_nzo_id_history_list:
        sab_nzo_id_history_list = urllib.unquote_plus(sab_nzo_id_history_list).split(";")
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    incomplete = get("incomplete")
    delete_all = get("delete_all")
    if delete_all:
        xbmc.executebuiltin('Notification("NZBS","Deleting all incomplete")')
    else:
        xbmc.executebuiltin('Notification("NZBS","Deleting '+ folder +'")')
    if sab_nzo_id or sab_nzo_id_history:
        delete_ = "ok"
        if sab_nzo_id:
            if not "None" in sab_nzo_id and not delete_all:
                pause = SABNZBD.pause('',sab_nzo_id)
                time.sleep(3)
                if "ok" in pause:
                    delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                else:
                    delete_ = "failed"
        if  sab_nzo_id_history:
            if not "None" in sab_nzo_id_history and not delete_all:
                delete_ = SABNZBD.delete_history('',sab_nzo_id_history)
        if delete_all and sab_nzo_id_history_list:
            for sab_nzo_id_history_item in sab_nzo_id_history_list:
                delete_state = SABNZBD.delete_history('',sab_nzo_id_history_item)
                if delete_state is not delete_:
                    delete_state = "failed"
            delete_ = delete_state
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
    active_nzbname_list = []
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
            m_row.append(folder)
            m_row.append(sab_nzo_id)
            active_nzbname_list.append(m_row)
            m_row = []
    nzbname_list = SABNZBD.nzo_id_history_list(m_nzbname_list)
    nzoid_history_list = [x[1] for x in nzbname_list if x[1] is not None]
    for row in active_nzbname_list:
        url = "&nzoid=" + str(row[1]) + "&nzbname=" + urllib.quote_plus(row[0]) +\
              "&nzoidhistory_list=" + urllib.quote_plus(';'.join(nzoid_history_list)) +\
              "&folder=" + urllib.quote_plus(row[0])
        info = nfo.ReadNfoLabels(os.path.join(INCOMPLETE_FOLDER, row[0]))
        info.info_labels['title'] = "Active - " + info.info_labels['title']
        add_posts(info.info_labels, url, MODE_INCOMPLETE_LIST, info.thumbnail, info.fanart)
    for row in nzbname_list:
        if row[1]:
            url = "&nzoidhistory=" + str(row[1]) + "&nzbname=" + urllib.quote_plus(row[0]) +\
                  "&nzoidhistory_list=" + urllib.quote_plus(';'.join(nzoid_history_list)) +\
                  "&folder=" + urllib.quote_plus(row[0])
            info = nfo.ReadNfoLabels(os.path.join(INCOMPLETE_FOLDER, row[0]))
            add_posts(info.info_labels, url, MODE_INCOMPLETE_LIST, info.thumbnail, info.fanart)
    xbmcplugin.setContent(HANDLE, 'movies')
    return

def get_node_value(parent, name, ns=""):
    if ns:
        return parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data.encode('utf-8')
    else:
        return parent.getElementsByTagName(name)[0].childNodes[0].data.encode('utf-8')

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
        out = parseString(utils.descape(xml).replace('&', '&amp;').decode('utf-8').encode('iso-8859-1'))
    except:
        xbmc.log("plugin.video.nzbs: malformed xml from url: " + url)
        return None, "xml"
    return out, None

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
    HANDLE = int(sys.argv[1])
    if not (__settings__.getSetting("firstrun") and __settings__.getSetting("sabnzbd_ip") and
        __settings__.getSetting("sabnzbd_port") and __settings__.getSetting("sabnzbd_key") and 
        __settings__.getSetting("sabnzbd_incomplete")):
        __settings__.openSettings()
        __settings__.setSetting("firstrun", '1')
    if (not sys.argv[2]):
        if __settings__.getSetting("nzbs_enable").lower() == "true":
            nzbs(None)
        add_posts({'title':'Incomplete'}, '', MODE_INCOMPLETE)
    else:
        params = utils.get_parameters(sys.argv[2])
        get = params.get
        if get("mode")== MODE_LIST:
            if is_nzb_home(params):
                nzbname = urllib.unquote_plus(get("nzbname"))
                pre_play(nzbname)
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
        if get("mode")== MODE_JSONRPC:
            if is_nzb_home(params):
                nzbname = urllib.unquote_plus(get("nzbname"))
                pre_play(nzbname, MODE_JSONRPC)

xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=True)


