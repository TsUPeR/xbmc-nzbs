import urllib
import urllib2
from xml.dom.minidom import parse, parseString

class sabnzbd(object):
    def __init__ (self, ip, port, apikey):
        self.ip = ip
        self.port = port
        self.apikey = apikey
        self.baseurl = "http://" + self.ip + ":" + self.port + "/api?apikey=" + apikey
    
    
    def addurl(self, nzb, nzbname):
        # TODO
        url = self.baseurl + "&mode=addurl&name=" + urllib.quote_plus(nzb) + "&nzbname=" + urllib.quote_plus(nzbname)
        responseMessage = self._sabResponse(url)
        return responseMessage

    def pause(self, nzbname='', id=''):
        url = self.baseurl + "&mode=pause"
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=queue&name=pause&value=" + str(sab_nzo_id)
        if id:
            url = self.baseurl + "&mode=queue&name=pause&value=" + str(id)
        responseMessage = self._sabResponse(url)
        return responseMessage

    def resume(self, nzbname='', id=''):
        url = self.baseurl + "&mode=pause"
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=queue&name=resume&value=" + str(sab_nzo_id)
        if id:
            url = self.baseurl + "&mode=queue&name=resume&value=" + str(id)
        responseMessage = self._sabResponse(url)
        return responseMessage

    def delete_queue(self, nzbname='', id=''):
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=queue&name=delete&del_files=1value=" + str(sab_nzo_id)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=queue&name=delete&del_files=1&value=" + str(id)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for delete queue provided"
        return responseMessage

    def delete_history(self, nzbname='', id=''):
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=history&name=delete&del_files=1&value=" + str(sab_nzo_id)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=history&name=delete&del_files=1&value=" + str(id)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for delete history provided"
        return responseMessage 

    def postProcess(self, value=0, nzbname='',id=''):
        if not value in range(0,3):
            value = 0
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=change_opts&value=" + str(sab_nzo_id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=change_opts&value=" + str(id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for post process provided"
        return responseMessage


    def switch(self, value=0, nzbname='',id=''):
        if not value in range(0,100):
            value = 0
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=switch&value=" + str(sab_nzo_id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=switch&value=" + str(id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for job switch provided"
        if "0" in responseMessage:
            responseMessage = "ok"
        return responseMessage


    def repair(self, nzbname='',id=''):
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=retry&value=" + str(sab_nzo_id)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=retry&value=" + str(id)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for repair provided"
        return responseMessage 
        
    def setStreaming(self, nzbname='',id=''):
        # DEBUG
        print nzbname + " " + id
        if (not id) and nzbname:
            id = self.nzo_id(nzbname)
            # DEBUG
            print id
        if id:
            ppMessage = self.postProcess(0,'',id)
            switchMessage = self.switch(0,'',id)
            if "ok" in (ppMessage and switchMessage):
                responseMessage = "ok"
            else:
                responseMessage = "failed setStreaming"
        else:
            responseMessage = "no name or id for setStreaming provided"
        return responseMessage

    def _sabResponse(self, url):
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
        except:
            responseMessage = "unable to load url: " + url
        else:
            log = response.read()
            response.close()
            if "ok" in log:
                responseMessage = 'ok'
            else:
                responseMessage = log
        return responseMessage
        
    def nzo_id(self, nzbname):
        # TODO
        url = self.baseurl + "&mode=queue&start=START&limit=LIMIT&output=xml"
        doc = _load_xml(url)
        sab_nzo_id = None
        if doc.getElementsByTagName("slot"):
            for slot in doc.getElementsByTagName("slot"):
                filename = get_node_value(slot, "filename")
                if filename.lower() == nzbname.lower():
                    sab_nzo_id  = get_node_value(slot, "nzo_id")                        
        return sab_nzo_id

    def nzo_id_history(self, nzbname):
        # TODO
        url = self.baseurl + "&mode=history&start=START&limit=LIMIT&output=xml"
        doc = _load_xml(url)
        sab_nzo_id = None
        if doc.getElementsByTagName("slot"):
            for slot in doc.getElementsByTagName("slot"):
                filename = get_node_value(slot, "name")
                if filename == nzbname:
                    sab_nzo_id  = get_node_value(slot, "nzo_id")                        
        return sab_nzo_id

def get_node_value(parent, name, ns=""):
    if ns:
        return parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data
    else:
        return parent.getElementsByTagName(name)[0].childNodes[0].data

def _load_xml(url):
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
    except:
        print("unable to load url: " + url)
    xml = response.read()
    response.close()
    return parseString(xml)