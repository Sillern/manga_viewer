import urllib, urllib2, urlparse, gzip
from StringIO import StringIO

USER_AGENT = 'Python/1.0'

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):    
    def http_error_301(self, req, fp, code, msg, headers):  
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)              
        result.status = code                                
        return result                                       

    def http_error_302(self, req, fp, code, msg, headers):  
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)              
        result.status = code                                
        return result                                       

class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):   
    def http_error_default(self, req, fp, code, msg, headers):
        result = urllib2.HTTPError(                           
            req.get_full_url(), code, msg, headers, fp)       
        result.status = code                                  
        return result 


class WebPage:
    def __init__(self, source, etag=None, lastmodified=None, agent=USER_AGENT):
        self.source = source
        self.etag = etag
        self.lastmodified = lastmodified
        self.agent = agent

    def open(self, path):
        '''URL, filename, or string --> stream

        This function lets you define parsers that take any input source
        (URL, pathname to local or network file, or actual data as a string)
        and deal with it in a uniform manner.  Returned object is guaranteed
        to have all the basic stdio read methods (read, readline, readlines).
        Just .close() the object when you're done with it.

        If the etag argument is supplied, it will be used as the value of an
        If-None-Match request header.

        If the lastmodified argument is supplied, it must be a formatted
        date/time string in GMT (as returned in the Last-Modified header of
        a previous request).  The formatted date/time will be used
        as the value of an If-Modified-Since request header.

        If the agent argument is supplied, it will be used as the value of a
        User-Agent request header.
        '''

        if hasattr(self.source, 'read'):
            return self.source

        if self.source == '-':
            return sys.stdin

        url = urllib.quote(self.source + path, "/:")
        if urlparse.urlparse(url)[0] == 'http':                                      
            # open URL with urllib2                                                     
            request = urllib2.Request(url)                                           
            request.add_header('User-Agent', self.agent)                                     
            if self.etag:                                                                    
                request.add_header('If-None-Match', self.etag)                               

            if self.lastmodified:                                                            
                request.add_header('If-Modified-Since', self.lastmodified)                   

            request.add_header('Accept-encoding', 'gzip')                               
            opener = urllib2.build_opener(SmartRedirectHandler(), DefaultErrorHandler())
            return opener.open(request)                                                 
        
        # try to open with native open function (if source is a filename)
        try:
            return open(self.source + path)
        except (IOError, OSError):
            pass

        # treat source as string
        return StringIO(str(self.source + path))

    def fetch(self, path = ""):  
        '''Fetch data and metadata from a URL, file, stream, or string'''
        result = {}                                                      
        f = self.open(path)              

        result['data'] = f.read()                                         
        if hasattr(f, 'headers'):                                        
            # save ETag, if the server sent one                          
            result['etag'] = f.headers.get('ETag')                        
            # save Last-Modified header, if the server sent one          
            result['lastmodified'] = f.headers.get('Last-Modified')       
            if f.headers.get('content-encoding', '') == 'gzip':           
                # data came back gzip-compressed, decompress it          
                result['data'] = gzip.GzipFile(fileobj=StringIO(result['data'])).read()

        if hasattr(f, 'url'):                                             
            result['url'] = f.url                                        
            result['status'] = 200                                       

        if hasattr(f, 'status'):                                          
            result['status'] = f.status                                  

        f.close()                                                        

        return result    

import sgmllib

class BleachExileParser(sgmllib.SGMLParser):

    def __init__(self, source, verbose=0):
        sgmllib.SGMLParser.__init__(self, verbose)
        self.images = []
        self.pages = set()
        self.chapters = set()
        self.inside_select_chapter = 0
        self.inside_select_pages = 0

        self.feed(source)
        self.close()


    def start_select(self, attributes):
        for name, value in attributes:
            if name == "name":
                if value == "chapter":
                    self.inside_select_chapter = 1
                if value == "pages":
                    self.inside_select_pages = 1

    def end_select(self):
        self.inside_select_chapter = 0
        self.inside_select_pages = 0

    def start_option(self, attributes):
        for name, value in attributes:
            if name == "value":
                if self.inside_select_chapter == 1:
                    self.chapters.add(int(value))
                if self.inside_select_pages == 1:
                    self.pages.add(int(value))
        
    def start_img(self, attributes):
        for name, value in attributes:
            if name == "src":
                if "static" in value:
                    self.images.append(value)

    def get_data(self):
        return {"images": self.images, "chapters": self.chapters, "pages": self.pages}

import os
def make_dir(dir):
    if False == os.access(dir, os.F_OK):
        try:
            os.makedirs(dir, 0777)
        except OSError:
            pass

def check_file(file):
    return os.access(file, os.F_OK)

def save_image(cache_path, remote_source):
    try:
        if remote_source == None:
            return

        filename = remote_source.split("/")[-1]
        filepath = cache_path + os.path.sep + filename
        image_filepath = filepath
        if check_file(image_filepath):
            print "skipped", image_filepath
            return

        remote_image = WebPage(remote_source)

        fp = file(image_filepath, "wb")
        fp.write(remote_image.fetch()["data"])
        fp.close()

    except Exception, e:
        print e

def transform_chapter(manga, chapter):
    return "/%s-chapter-%d.html" % (manga, chapter)

def transform_page(manga, chapter, page):
    return "/%s-chapter-%d-page-%d.html" % (manga, chapter, page)

def fetch_mangas(url, cachepath, mangas):
    webpage = WebPage(url)
    for manga in mangas:
        for chapter in BleachExileParser(webpage.fetch("%s.html" % manga)["data"]).get_data()["chapters"]:
            manga_path = "%s/%s/%s/" % (cachepath, manga, chapter)
            make_dir(manga_path)

            pages = BleachExileParser(webpage.fetch(transform_chapter(manga, chapter))["data"]).get_data()["pages"]

            if len(pages) == len(os.listdir(manga_path)):
                print "directory list count match pagecount, skipping", manga_path
                continue

            print "fetching", manga_path
            for page in pages:
                    save_image(manga_path, BleachExileParser(webpage.fetch(transform_page(manga, chapter, page))["data"]).get_data()["images"][0])


cachepath = "mangas"
url = "http://manga.bleachexile.com/"
mangas = [
        "psyren",
        "historys-strongest-disciple-kenichi",
        "d-gray-man",
        "one-piece"
        ]

fetch_mangas(url, cachepath, mangas)   
