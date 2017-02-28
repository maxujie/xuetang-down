#!/usr/env python3
# -*- coding: utf-8 -*-

import gzip
import json
import os
import sys
import re
import requests
import tempfile
from bs4 import BeautifulSoup


class XuetangDown(object):
    def __init__(self):
        self.config_path = 'config.json'
        self.redownload = None
        self.root_url = None
        self.course_url = None
        self.cookie_path = None
        self.cookie = None
        self.session = None
        self.subsections = []
        self.pattern = re.compile(r'\/course.*transcript\/download')
        self.chunk_size = 4096

        self.load_config()
        self.load_cookie()
        self.make_session()

        self.get_chapters()

    def load_config(self):
        if not os.path.exists(self.config_path):
            print('Error: File "config.json" not exists!')
            sys.exit(-1)
        try:
            with open(self.config_path, 'rt') as f:
                config = json.load(f)
            assert isinstance(config, dict)
            assert 'cookie_path' in config.keys()
            assert 'root_url' in config.keys()
            assert 'course_url' in config.keys()
            assert 'redownload_existing_subtitles' in config.keys()
        except Exception as err:
            print('Error: Invalid "config.json"!')
            sys.exit(-1)

        self.root_url = config['root_url']
        self.course_url = config['course_url']
        self.cookie_path = config['cookie_path']
        self.redownload = config['redownload_existing_subtitles']

    def load_cookie(self):
        if not os.path.exists(self.cookie_path):
            print('Error: File "cookie.json" not exists!')
            sys.exit(-1)
        try:
            with open(self.cookie_path, 'rt') as f:
                cookie = json.load(f)
            assert isinstance(cookie, dict)
            for key, val in cookie.items():
                if not isinstance(val, str):
                    cookie[key] = str(val)
                    if isinstance(val, bool):
                        cookie[key] = cookie[key].lower()

        except Exception as err:
            print('Error: Invalid "cookie.json"!')
            sys.exit(-1)

        self.cookie = cookie

    def make_session(self):
        sess = requests.Session()
        sess.cookies = requests.utils.cookiejar_from_dict(self.cookie)

        # TODO: Cookie validity check
        pass

        self.session = sess

    def get_chapters(self):
        progress_url = self.root_url + '/courses/' + self.course_url + '/' + 'progress'
        sess = self.session
        assert isinstance(sess, requests.Session)
        progress_page = sess.get(progress_url)

        soup = BeautifulSoup(progress_page.text, 'lxml')

        sections = soup.find_all(class_='sections')

        for section in sections:
            for subsection in section.children:
                h3 = subsection.find('h3')
                if h3 == -1 or h3.find('a') == -1:
                    continue
                title = h3.text.lstrip().rstrip()
                subsection_url = h3.a['href']
                s = {'title': title, 'url': subsection_url}
                self.subsections.append(s)

    def download_subtitle(self, subsection):
        title = subsection['title']
        print(title)
        save_filename = 'download/' + title + '.txt'
        if os.path.exists(save_filename) and not self.redownload:
            return

        url = self.root_url + subsection['url']
        page = self.session.get(url)

        match = self.pattern.findall(page.text)

        if not match:
            return

        sub_url = self.root_url + match[0]

        sub = self.session.get(sub_url)
        assert sub.status_code == 200

        if sub.headers.get('Content-Encoding') == 'gzip':
            with open(save_filename, 'wb') as f:
                for chunk in sub.iter_content(self.chunk_size):
                    f.write(chunk)
        else:
            content = sub.content
            unzipped_data = gzip_decompress(content)
            with open(save_filename, 'wb') as f:
                f.write(unzipped_data)

    def download_all_subtitles(self):
        if not os.path.exists('download'):
            os.mkdir('download')

        for subsection in self.subsections:
            self.download_subtitle(subsection)


def gzip_decompress(gzdata):
    # TODO: This method is dirty. Rewrite it.
    tempfilename = '__temp.gz'
    with open(tempfilename, 'wb') as f:
        f.write(gzdata)
    with gzip.open(tempfilename, 'rb') as f:
        unzipped_data = f.read()
    os.remove(tempfilename)
    return unzipped_data


def main():
    xtdown = XuetangDown()
    xtdown.download_all_subtitles()

if __name__ == '__main__':
    main()
