"""
 Copyright (c) 2010, 2011, 2012 Popeye

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
import xbmc
import math
import re
import os
import shutil
from xml.dom.minidom import parse, parseString

class NfoLabels:
    def __init__(self, nfo_path = None):
        info_labels = {
            'size' : unicode(xbmc.getInfoLabel( "ListItem.Size" ), 'utf-8'),
            'tvshowtitle': unicode(xbmc.getInfoLabel( "ListItem.TvShowTitle" ), 'utf-8'),
            'title': unicode(xbmc.getInfoLabel( "ListItem.Title" ), 'utf-8'),
            'genre': unicode(xbmc.getInfoLabel( "ListItem.Genre" ), 'utf-8'),
            'plot': unicode(xbmc.getInfoLabel( "ListItem.Plot" ), 'utf-8'),
            'aired': unicode(xbmc.getInfoLabel( "ListItem.Premiered" ), 'utf-8'),
            'mpaa': unicode(xbmc.getInfoLabel( "ListItem.MPAA" ), 'utf-8'),
            'duration': unicode(xbmc.getInfoLabel( "ListItem.DUration" ), 'utf-8'),
            'studio': unicode(xbmc.getInfoLabel( "ListItem.Studio" ), 'utf-8'),
            'cast': unicode(xbmc.getInfoLabel( "ListItem.Cast" ), 'utf-8'),
            'writer': unicode(xbmc.getInfoLabel( "ListItem.Writer" ), 'utf-8'),
            'director': unicode(xbmc.getInfoLabel( "ListItem.Director" ), 'utf-8'),
            'season': int(xbmc.getInfoLabel( "ListItem.Season" ) or "-1"),
            'episode': int(xbmc.getInfoLabel( "ListItem.Episode" ) or "-1"),
            'year': int(xbmc.getInfoLabel( "ListItem.Year" ) or "-1"),
            }
        # Clear empty keys
        for key in info_labels.keys():
            if(info_labels[key] == -1):
                del info_labels[key]
            try:
                if (len(info_labels[key])<1):
                    del info_labels[key]
            except:
                pass
        try:
            info_labels['size'] = self._size_to_bytes(info_labels['size'])
        except:
           pass
        try:
            code = self._code_from_plot(info_labels['plot'])
            if code:
                info_labels['code'] = code
        except:
            pass
        try:
            info_labels['cast'] = info_labels['cast'].split('\n')
        except:
            pass
        if not 'title' in info_labels:
            if nfo_path:
                info_labels['title'] = os.path.basename(nfo_path)
            else:
                info_labels['title'] = 'Unknown'
        self.info_labels = info_labels
        self.fanart = unicode(xbmc.getInfoImage( "Listitem.Property(Fanart_Image)" ), 'utf-8')
        self.thumbnail = unicode(xbmc.getInfoImage( "ListItem.Thumb" ), 'utf-8')
        self.nfo_path = nfo_path

    def _size_to_bytes(self, size_str):
        conversion = {'K' : 1024,
                      'M' : 1048576,
                      'G' : 1073741824,}
        RE_GMK = ('(\w[GMK]?)B')
        RE_DIGIT = ('(\d*\.?\d*)')
        re_obj_gmk = re.compile(RE_GMK)
        re_obj_digit = re.compile(RE_DIGIT)
        gmk = re_obj_gmk.search(size_str)
        unit = 1
        if gmk:
            unit = conversion[gmk.groups()[0]]
        digit = re_obj_digit.search(size_str)
        if digit:
            size = int(math.floor((float(digit.groups()[0]) * unit)))
        else:
            size = 0
        return size

    def _code_from_plot(self, plot):
        RE_CODE = ('code:(t*\d*)')
        re_obj_code = re.compile(RE_CODE)
        code = re_obj_code.search(plot).groups()
        if code:
            code = code[0]
            return code
        else:
            return None
    
    def save(self):
        # TODO
        # Check if movie.nfo exists, if so, check the size
        # and replace if its smaler
        head_name = 'movie'
        if 'tvshowtitle' in self.info_labels:
            head_name = 'tvshow'
        filename = os.path.join(self.nfo_path, (head_name + '.nfo'))
        if not os.path.exists(filename):
            # TODO write using
            # http://www.postneo.com/projects/pyxml/
            f = open(filename, 'w')
            line = '<?xml version="1.0" encoding="UTF-8" ?>\n'
            f.write(line)
            line = "<" + head_name + ">\n"
            f.write(line)
            for key, value in self.info_labels.iteritems():
                if ('size' in key) or ('season' in key) or ('episode' in key) or ('year' in key):
                    value = str(value)
                if 'code' in key:
                    key = 'id'
                if 'cast' in key:
                    line = ''
                    for actor in value:
                        line = line + "<actor>\n<name>\n" + actor.encode('utf-8') + "\n</name>\n</actor>\n"
                else:
                    line = "    <" + key + ">" + value.encode('utf-8') + "</" + key + ">\n"
                f.write(line)
            line = "</" + head_name + ">\n"
            f.write(line)
            f.close()
        # Thumb and fanart
        thumbnail_dest = os.path.join(self.nfo_path, 'folder.jpg')
        cached_fanart = xbmc.getCacheThumbName(self.fanart).replace('.tbn', '')
        cached_fanart = "special://profile/Thumbnails/" + cached_fanart[0] + "/" +\
                        cached_fanart + ".jpg"
        try:
            shutil.copy(xbmc.translatePath(self.thumbnail), thumbnail_dest)
        except:
            xbmc.log("plugin.program.pneumatic failed to write: " +  thumbnail_dest)
        fanart_dest = os.path.join(self.nfo_path, 'fanart.jpg')
        try:
            shutil.copy(xbmc.translatePath(cached_fanart), fanart_dest)
        except:
            xbmc.log("plugin.program.pneumatic failed to write: " +  fanart_dest + " from: " + xbmc.translatePath(cached_fanart))

class ReadNfoLabels:
    def __init__(self, nfo_path):
        self.nfo_path = nfo_path
        filename_movie = os.path.join(self.nfo_path, ('movie.nfo'))
        filename_tvshow = os.path.join(self.nfo_path, ('tvshow.nfo'))
        if os.path.exists(filename_movie):
            filename = filename_movie
        elif os.path.exists(filename_tvshow):
            filename = filename_tvshow
        try:
            f = open(filename, 'r')
            out = parseString(f.read())
        except:
            xbmc.log("plugin.program.pneumatics could not open: " + self.nfo_path + "*.nfo")
            out = None
        if out:
            self.info_labels = self._get_info_labels(out)
        else:
            self.info_labels = {'title': os.path.basename(nfo_path)}
        self.thumbnail = os.path.join(self.nfo_path, 'folder.jpg')
        self.fanart = os.path.join(self.nfo_path, 'fanart.jpg')

    def _get_info_labels(self, doc):
        info_labels = dict()
        items = doc.getElementsByTagName("movie")
        if not items:
            items = doc.getElementsByTagName("tvshow")
        for item in items:
            info_labels['size'] = int(self._get_node_value(item, "size") or "-1")
            info_labels['tvshowtitle'] = (unicode(self._get_node_value(item, "tvshowtitle"), 'utf-8') or "")
            info_labels['title'] = unicode(self._get_node_value(item, "title"), 'utf-8')
            info_labels['genre'] = unicode(self._get_node_value(item, "genre"), 'utf-8')
            info_labels['plot'] = unicode(self._get_node_value(item, "plot"), 'utf-8')
            info_labels['aired'] = unicode(self._get_node_value(item, "aired"), 'utf-8')
            info_labels['mpaa'] = unicode(self._get_node_value(item, "mpaa"), 'utf-8')
            info_labels['duration'] = unicode(self._get_node_value(item, "duration"), 'utf-8')
            info_labels['studio'] = unicode(self._get_node_value(item, "studio"), 'utf-8')
            info_labels['cast'] = []
            for cast in item.getElementsByTagName("actor"):
                info_labels['cast'].append(unicode(self._get_node_value(cast, "name"), 'utf-8'))
            info_labels['writer'] = unicode(self._get_node_value(item, "writer"), 'utf-8')
            info_labels['director'] = unicode(self._get_node_value(item, "director"), 'utf-8')
            info_labels['season'] = int(self._get_node_value(item, "season") or "-1")
            info_labels['episode'] = int(self._get_node_value(item, "episode") or "-1")
            info_labels['episode'] = int(self._get_node_value(item, "episode") or "-1")
        # Clear empty keys
        for key in info_labels.keys():
            if(info_labels[key] == -1):
                del info_labels[key]
            try:
                if (len(info_labels[key])<1):
                    del info_labels[key]
            except:
                pass
        return info_labels

    def _get_node_value(self, parent, name, ns=""):
        if ns:
            try:
                return parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data.encode('utf-8')
            except:
                return ""
        else:
            try:
                return parent.getElementsByTagName(name)[0].childNodes[0].data.encode('utf-8')            
            except:
                return ""