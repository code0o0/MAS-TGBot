
#VERSION: 1.00
#AUTHORS: xyau (xyauhideto@gmail.com)

# MIT License
#
# Copyright (c) 2018 xyau
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the right
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software i
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# qBT
from re import findall as re_findall
from bs4 import BeautifulSoup
from helpers import download_file, retrieve_url
from novaprinter import prettyPrinter
from urllib.parse import quote, urljoin

class dmhy(object):
    url = "https://share.dmhy.org"
    name = "DMHY"
    supported_categories = {"all":0,"anime":2,"pictures":3,"music":4,"tv":6,"games":9}

    def download_torrent(self, info):
        print(download_file(info))
    
    def get_data(self, url):
        html = retrieve_url(url)
        soup = BeautifulSoup(html, "lxml")
        nac_tag = soup.select('.nav_title .fl a')
        next_page = True if [i for i in nac_tag if "下一" in i.text] else False
        desc_links = [urljoin(self.url, i.get('href')) for i in soup.select('.tablesorter  tbody tr td.title >a')]
        titles = [i.get_text() for i in soup.select('.tablesorter  tbody tr td.title >a')]
        links = [i.get('href') for i in soup.select('a.download-arrow.arrow-magnet')]
        sizes = [i.text for i in soup.select('tr td:nth-of-type(5)')]
        seeds = [i.get_text() for i in soup.select('td .btl_1')]
        leech = [i.get_text() for i in soup.select('td .bts_1')]
        return zip(desc_links, titles, links, sizes, seeds, leech), next_page

    # DO NOT CHANGE the name and parameters of this function
    # This function will be the one called by nova2.py
    def search(self, what, cat="all"):
        """ Performs search """
        pagenumber = 1
        while pagenumber <= 5:
            query = f"{self.url}/topics/list/page/{pagenumber}?keyword={quote(what, encoding='utf8')}&sort_id={self.supported_categories.get(cat,0)}"
            data, next_page = self.get_data(query)
            for item in data:
                size = re_findall(r'(.*?)([a-zA-Z]+)', item[3])[0]
                prettyPrinter({
                    "desc_link":item[0],
                    "name":item[1],
                    "link":item[2],
                    "size":str(int(float(size[0]) * 2 ** (10 * (1 + 'kmgtpezy'.find(size[1][0].lower()))))),
                    "seeds":0 if "-" == item[4] else int(item[4]),
                    "leech":0 if "-" == item[5] else int(item[5]),
                    "engine_url":self.url
                })
            if next_page:
                pagenumber = pagenumber + 1
            else:
                break

if __name__ == "__main__":
    engine = dmhy()
    engine.search('鬼')