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

import re
import os
import htmlentitydefs
import urllib
import xbmc

import rarfile

RE_PART = '.part\d{2,3}.rar$'
RE_PART01 = '.part0{1,2}1.rar$'
RE_R = '.r\d{2,3}$'
RE_MOVIE = '\.avi$|\.mkv$|\.iso$|\.img$'
RE_SAMPLE = 'sample'
RE_MKV = '\.mkv$'
RE_HTML = '&(\w+?);'

RAR_HEADER = "Rar!\x1a\x07\x00"
RAR_MIN_SIZE = 10485760

def write_fake(file_list, folder):
    for filebasename in file_list:
        filename = os.path.join(folder, filebasename)
        if not os.path.exists(filename):
            # make 7 byte file with a rar header
            fd = open(filename,'wb')
            fd.write(RAR_HEADER)
            fd.close()
    return

def remove_fake(file_list, folder):
    for filebasename in file_list:
        filename = os.path.join(folder, filebasename)
        filename_one = os.path.join(folder, (filebasename + ".1"))
        if os.path.exists(filename):
            if os.stat(filename).st_size == 7:
                os.remove(filename)
                if os.path.exists(filename_one):
                    os.rename(filename_one, filename)
    return

def sorted_rar_file_list(rar_file_list):
    file_list = []
    if len(rar_file_list) > 0:
        for file, bytes in rar_file_list:
            partrar = re.findall(RE_PART, file)
            rrar = re.findall(RE_R, file)
            if ((file.endswith(".rar") and not partrar) or partrar or rrar):
                file_list.append([file, bytes])
        if len(file_list) > 1:
            file_list.sort()
    return file_list

def sorted_multi_arch_list(rar_file_list):
    file_list = []
    for file, bytes in rar_file_list:
        partrar = re.findall(RE_PART, file)
        part01rar = re.findall(RE_PART01, file)
        # No small sub archives
        if ((file.endswith(".rar") and not partrar) or part01rar) and bytes > RAR_MIN_SIZE:
            file_list.append([file, bytes])
    if len(file_list) > 1:
        file_list.sort()
    return file_list

def list_dir(folder):
    file_list = []
    for filename in os.listdir(folder):
        row = []
        row.append(filename)
        bytes = os.path.getsize(os.path.join(folder,filename))
        row.append(bytes)
        file_list.append(row)
    return file_list

def find_rar(file_list, index):
    rar_list = []
    for file, bytes in file_list:
        partrar = re.findall(RE_PART, file)
        rrar = re.findall(RE_R, file)
        if partrar or rrar:
            rar_list.append(file)
    if len(rar_list) > 1:
        rar_list.sort()
    return rar_list[index]

def rar_filenames(folder, file):
    filepath = os.path.join(folder, file)
    rf = rarfile.RarFile(filepath)
    movie_file_list = rf.namelist()
    for f in rf.infolist():
        if f.compress_type != 48:
            xbmc.executebuiltin('Notification("NZBS","Compressed rar!!!")')
    return movie_file_list

def is_movie_mkv(movie_list):
    mkv = False
    for movie in movie_list:
        if re.search(RE_MKV, movie, re.IGNORECASE):
            mkv = True
    return mkv

def no_sample_list(movie_list):
    outList = movie_list[:]
    for i in range(len(movie_list)):
        match = re.search(RE_SAMPLE, movie_list[i], re.IGNORECASE)
        if match:
            outList.remove(movie_list[i])
    if len(outList) == 0:
        # We return sample if it's the only file left 
        outList.append(movie_list[0])
    return outList
  
def rarpath_fixer(folder, file):
    filepath = os.path.join(folder, file)
    filepath = urllib.quote(filepath)
    filepath = filepath.replace(".","%2e")
    filepath = filepath.replace("-","%2d")
    filepath = filepath.replace(":","%3a")
    filepath = filepath.replace("\\","%5c")
    filepath = filepath.replace("/","%2f")
    return filepath
    
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

def sort_filename(filename_list):
    outList = filename_list[:]
    if len(filename_list) == 1:
        return outList
    else:
        for i in range(len(filename_list)):
            match = re.search(RE_MOVIE, filename_list[i], re.IGNORECASE)
            if not match:
                outList.remove(filename_list[i])
        if len(outList) == 0:
            outList.append(filename_list[0])
        return outList

def descape_entity(m, defs=htmlentitydefs.entitydefs):
    # callback: translate one entity to its ISO Latin value
    try:
        return defs[m.group(1)]
    except KeyError:
        return m.group(0) # use as is

def descape(string):
    pattern = re.compile(RE_HTML)
    return pattern.sub(descape_entity, string)
