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
from rar import RarFile
from sabnzbd import sabnzbd

__settings__ = xbmcaddon.Addon(id='plugin.video.nzbs')
__language__ = __settings__.getLocalizedString

RE_PART = '.part\d\d.rar'

NS_MEDIA = "http://search.yahoo.com/mrss/"
NS_REPORT = "http://www.newzbin.com/DTD/2007/feeds/report/"

STREAMING = [1,0][int(__settings__.getSetting("mode"))]

SABNZBD = sabnzbd(__settings__.getSetting("sabnzbd_ip"),
        __settings__.getSetting("sabnzbd_port"),__settings__.getSetting("sabnzbd_key"))
INCOMPLETE_FOLDER = __settings__.getSetting("sabnzbd_incomplete")

MODE_LIST = "list"
MODE_DOWNLOAD = "download"
MODE_PLAY = "play"
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
            "&h=" + __settings__.getSetting("nzbs_key") + "&")

TABLE = [['Movies', 1, 2],
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
            if nzbs:
                print nzbs
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
                addPosts('Search...', key, MODE_NZBS_SEARCH, '', '')
            else:
                url = NZBS_URL + "&type=" + typeid
                key = "&type=" + typeid
                addPosts('Search...', key, MODE_NZBS_SEARCH, '', '')
            listFeed(url)
        else:
            # if not (catid and typeid):
            # Build Main menu
            for name, type, catid in TABLE:
                if ("XXX" in name) and (__settings__.getSetting("nzbs_hide_xxx").lower() == "true"):
                 break
                if type:
                    key = "&type=" + str(catid)
                else:
                    key = "&catid=" + str(catid)
                addPosts(name, key, MODE_NZBS, '', '')
            # TODO add settings toggle
            addPosts("My NZB\'s", '', MODE_NZBS_MY, '', '')
            addPosts("My Searches", '', MODE_NZBS_MYSEARCH, '', '')
    return

def listFeed(feedUrl):
    doc = load_xml(feedUrl)
    for item in doc.getElementsByTagName("item"):
        title = get_node_value(item, "title")
        description = get_node_value(item, "description")
        nzb = get_node_value(item, "nzb", NS_REPORT)
        thumbid = item.getElementsByTagNameNS(NS_REPORT, "imdbid")
        thumb = ""
        if thumbid:
            thumbid = get_node_value(item, "imdbid", NS_REPORT)
            thumb = "http://www.nzbs.org/imdb/" + thumbid + ".jpg"
        nzb = "&nzb=" + urllib.quote_plus(nzb) + "&nzbname=" + urllib.quote_plus(title)
        if STREAMING:
            mode = MODE_LIST
        else:
            mode = MODE_DOWNLOAD
        addPosts(title, nzb, mode, description, thumb)
    return
            
  
def addPosts(title, url, mode, description='', thumb='', folder=True):
    listitem=xbmcgui.ListItem(title, iconImage="DefaultFolder.png", thumbnailImage=thumb)
    listitem.setInfo(type="Video", infoLabels={ "Title": title, "Plot" : description })
    xurl = "%s?mode=%s" % (sys.argv[0],mode)
    xurl = xurl + url
    listitem.setPath(xurl)
    if mode == MODE_LIST or mode == MODE_DOWNLOAD:
        cm = []
        if STREAMING :
            cm_mode = MODE_DOWNLOAD
            cm_label = "Download"
        else:
            cm_mode = MODE_LIST
            cm_label = "Stream"
        cm_url_download = sys.argv[0] + '?mode=' + cm_mode + url
        cm.append((cm_label , "XBMC.RunPlugin(%s)" % (cm_url_download)))
        listitem.addContextMenuItems(cm, replaceItems=False)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=xurl, listitem=listitem, isFolder=folder)
 
# FROM plugin.video.youtube.beta  -- converts the request url passed on by xbmc to our plugin into a dict  
def getParameters(parameterString):
    commands = {}
    splitCommands = parameterString[parameterString.find('?')+1:].split('&')
    
    for command in splitCommands: 
        if (len(command) > 0):
            splitCommand = command.split('=')
            name = splitCommand[0]
            value = splitCommand[1]
            commands[name] = value
    
    return commands
    
def listVideo(params):
    get = params.get
    nzb = urllib.unquote_plus(get("nzb"))
    nzbname = urllib.unquote_plus(get("nzbname"))
    folder = INCOMPLETE_FOLDER + nzbname
    if not os.path.exists(folder):
        addurl = SABNZBD.addurl(nzb, nzbname)
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('NZBS', 'Sending request to SABnzbd')
        if "ok" in addurl:
            progressDialog.update(0, 'Request to SABnzbd succeeded', 'waiting for nzb download')
            seconds = 0
            while not SABNZBD.nzo_id(nzbname):
                time.sleep(1)
                seconds += 1
                label = str(seconds) + " seconds"
                progressDialog.update(0, 'Request to SABnzbd succeeded', 'waiting for nzb download', label)
            setstreaming = SABNZBD.setStreaming(nzbname, '')
            if not "ok" in setstreaming:
                xbmc.log(setstreaming)
                progressDialog.update(0, 'Stream request to SABnzbd failed!')
            time.sleep(2)
            progressDialog.close()
            listFile(nzbname)
        else:
            xbmc.log(addurl)
            progressDialog.update(0, 'Request to SABnzbd failed!')
            time.sleep(2)
            progressDialog.close()
    else:
        # TODO make sure there is also a NZB in the queue
        listFile(nzbname)

def listFile(nzbname):
    folder = INCOMPLETE_FOLDER + nzbname
    print folder
    progressDialog = xbmcgui.DialogProgress()
    progressDialog.create('NZBS', 'Request to SABnzbd succeeded', 'Waiting for first rar')
    seconds = 0
    while not os.path.exists(folder):
        time.sleep(1)
        seconds += 1
        print "waiting for incomplete...."
        label = str(seconds) + " seconds"
        progressDialog.update(0, 'Request to SABnzbd succeeded', 'Waiting for first rar', 'Waiting for download to start', label)
        if progressDialog.iscanceled():
            break
    size = -1
    rar = False
    seconds = 0
    while not rar:
        for file in os.listdir(folder):
            partrar = re.findall(RE_PART, file)
            if (file.endswith(".rar") and not partrar) or file.endswith("part01.rar"):
                filepath = os.path.join(folder, file)
                if size == os.path.getsize(filepath):
                    #
                    rar = True
                    # progressDialog.close()
                    break
                size = os.path.getsize(filepath)
        label = str(seconds) + " seconds"
        progressDialog.update(0, 'Request to SABnzbd succeeded', 'Waiting for first rar', label)
        if progressDialog.iscanceled():
            break
        seconds += 2
        time.sleep(2)
        
    movieFile = RarFile(filepath).namelist()
    print movieFile
    rarpath = filepath
    filepath = filepath.replace(".","%2e")
    filepath = filepath.replace("-","%2d")
    filepath = filepath.replace(":","%3a")
    filepath = filepath.replace("\\","%5c")
    filepath = filepath.replace("/","%2f")
    # TODO more replace 
    progressDialog.update(0, 'First rar downloaded', 'pausing SABnzbd')
    sab_nzo_id = SABNZBD.nzo_id(nzbname)
    sab_nzo_id_history = ''
    if sab_nzo_id:
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
    else:
        sab_nzo_id_history = SABNZBD.nzo_id_history(nzbname)
    progressDialog.close()
    xurl = "%s?mode=%s" % (sys.argv[0],MODE_PLAY)
    item = xbmcgui.ListItem(movieFile[0], iconImage='', thumbnailImage='')
    item.setInfo(type="Video", infoLabels={ "Title": movieFile[0]})
    url = (xurl + "&filepath=" + filepath + "&file=" + urllib.quote_plus(file) + "&folder=" + urllib.quote_plus(folder) + 
                "&filename=" + urllib.quote_plus(movieFile[0]) + "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history))
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
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isfolder)

def list_incomplete(params):
    get = params.get
    nzbname = get("nzbname")
    nzbname = urllib.unquote_plus(nzbname)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    folder = INCOMPLETE_FOLDER + nzbname
    # DEBUG
    print folder
    if sab_nzo_id:
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('NZBS', 'Waiting for first rar')
    rar = False
    size = -1
    while not rar:
        seconds = 0
        for file in os.listdir(folder):
            partrar = re.findall(RE_PART, file)
            if (file.endswith(".rar") and not partrar) or file.endswith("part01.rar"):
                filepath = os.path.join(folder, file)
                if size == os.path.getsize(filepath):
                    rar = True
                    break
                size = os.path.getsize(filepath)
        label = str(seconds) + " seconds"
        if sab_nzo_id:
            progressDialog.update(0, 'Waiting for first rar', label)
            if progressDialog.iscanceled():
                break
        seconds += 2
        time.sleep(2)
        
    movieFile = RarFile(filepath).namelist()
    # DEBUG
    print movieFile
    rarpath = filepath
    filepath = filepath.replace(".","%2e")
    filepath = filepath.replace("-","%2d")
    filepath = filepath.replace(":","%3a")
    filepath = filepath.replace("\\","%5c")
    filepath = filepath.replace("/","%2f")
    # TODO more replace 
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

    xurl = "%s?mode=%s" % (sys.argv[0],MODE_PLAY)
    item = xbmcgui.ListItem(movieFile[0], iconImage='', thumbnailImage='')
    item.setInfo(type="Video", infoLabels={ "Title": movieFile[0]})
    url = (xurl + "&filepath=" + filepath + "&file=" + urllib.quote_plus(file) + "&folder=" + urllib.quote_plus(folder) + 
                "&filename=" + urllib.quote_plus(movieFile[0]) + "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history))
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
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isfolder)

def playVideo(params):
    get = params.get
    filepath = get("filepath")
    file = get("file")
    file = urllib.unquote_plus(file)
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    # DEBUG
    print "PlayVideo filepath " + filepath + " file " + file + " folder " + folder
    movieFile = get("filename")
    # We might have deleted the path
    if os.path.exists(folder):
        # we trick xbmc to play avi by creating empty rars if the download is only partial
        # if (("avi" in movieFile) or ("mkv" in movieFile)) and sab_nzo_id:
        if sab_nzo_id:
            end = ""
            if ".part01.rar" in file:
                basename = file.replace(".part01.rar", ".part")
                end = ".rar"
            else:
                basename = file.replace(".rar", ".r")
            for i in range(10):
                for y in range(10):
                    filebasename = basename + str(i) + str(y) + end
                    filename = os.path.join(folder, filebasename) 
                    if not os.path.exists(filename):
                        # make 0 byte file
                        open(filename,'w').close()
                        print filename
        # lets play the movie
        raruri = "rar://" + filepath + "/" + movieFile
        item = xbmcgui.ListItem(movieFile, iconImage='', thumbnailImage='')
        item.setInfo(type="Video", infoLabels={ "Title": movieFile})
        item.setPath(raruri)
        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=item)
        time.sleep(5)
        # if the item is in the queue we remove the temp files
        # if (("avi" in movieFile) or ("mkv" in movieFile)) and sab_nzo_id:
        if sab_nzo_id:
            for i in range(10):
                for y in range(10):
                    filebasename = basename + str(i) + str(y) + end
                    filename = os.path.join(folder, filebasename)
                    if os.path.exists(filename):
                        if os.stat(filename).st_size == 0:
                            os.remove(filename)
            resume = SABNZBD.resume('', sab_nzo_id)
            if not "ok" in resume:
                xbmc.log(resume)  
    else:
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
    folder = get("folder")
    folder = urllib.unquote_plus(folder)
    progressDialog = xbmcgui.DialogProgress()
    progressDialog.create('NZBS', 'Deleting')
    if sab_nzo_id:
        pause = SABNZBD.pause('',sab_nzo_id)
        time.sleep(3)
        if "ok" in pause:
            delete_ = SABNZBD.delete_queue('',sab_nzo_id)
            if "ok" in delete_:
                progressDialog.update(100, 'Deletion', 'Succeeded')
            else:
                xbmc.log(delete_)
                progressDialog.update(0, 'Deletion failed!')
        else:
            progressDialog.update(0, 'Deletion failed!')
    elif sab_nzo_id_history:
        delete_ = SABNZBD.delete_history('',sab_nzo_id_history)
        if "ok" in delete_:
            progressDialog.update(100, 'Deletion', 'Succeeded')
        else:
            xbmc.log(delete_)
            progressDialog.update(0, 'Deletion failed!')
    else:
        progressDialog.update(0, 'Deletion failed!')
    time.sleep(2)
    progressDialog.close()
    time.sleep(1)
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
    for folder in os.listdir(INCOMPLETE_FOLDER):
        sab_nzo_id = SABNZBD.nzo_id(folder)
        sab_nzo_id_history = SABNZBD.nzo_id_history(folder)
        url = "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history) + "&nzbname=" + urllib.quote_plus(folder)
        addPosts(folder, url, MODE_INCOMPLETE_LIST)
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
        xbmc.log("unable to load url: " + url)

    xml = response.read()
    response.close()
    return parseString(xml)

def search(dialog_name):
    searchString = unikeyboard('', '' )
    if searchString == "":
        xbmcgui.Dialog().ok('Missing text', 'Second line' )
    elif searchString:
        # latestSearch = __settings__.setSetting( "latestSearch", searchString )
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
        return None

if (__name__ == "__main__" ):
    if not (__settings__.getSetting("firstrun") and __settings__.getSetting("sabnzbd_ip") and
        __settings__.getSetting("sabnzbd_port") and __settings__.getSetting("sabnzbd_key") and 
        __settings__.getSetting("sabnzbd_incomplete")):
        __settings__.openSettings()
        __settings__.setSetting("firstrun", '1')
    if (not sys.argv[2]):
        nzbs(None)
        addPosts('Incomplete', '', MODE_INCOMPLETE)
    else:
        params = getParameters(sys.argv[2])
        get = params.get
        if get("mode")== MODE_LIST:
            listVideo(params)
        if get("mode")== MODE_PLAY:
            playVideo(params)
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