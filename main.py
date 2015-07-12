# -*- coding:utf-8 -*-
from collections import deque
from urllib.parse import urlparse
import urllib.request as request
import urllib.error as error
import re
import os
import os.path
import time

# 从HTML中提取url时使用的正则
LINK_RE = re.compile(r'(?:href|src)="([^"]*?([^/"]*))"')
ROOT_PATH = './pages'

# 主机的正则
# 1: host, 2: http(s)://
HOST_RE = re.compile(r'((https?://)[^/]+(?:\d+)*)')

PARENT_RE = re.compile(r'([^/]+/\.\./)')

HTML_LIST = ['', '.html', '.htm', '.asp', '.aspx', '.jsp', '.action', '.php', '.do']

# 下载器
class Downloader(object):
    def __init__(self, url):
        self.startUrl = url

        # 可选编码列表
        self.encoding_queue = deque(['utf-8', 'gbk', 'ISO-8859-1'])

        # 获取主机和协议头
        m = HOST_RE.match(url)
        self.host = m.group(1)
        self.scheme = m.group(2)

        # 待处理的url的队列
        self.queue = deque([url])

        # 已处理过的url的集合
        self.handled_set = set()

    # 获取图片的URL
    def get_normal_url(self, href, html_url):
        assert isinstance(href, str)

        if href.startswith(self.scheme):
            url = href
        elif href.startswith('//'):
            url = self.scheme + href[2:]
        elif href.startswith('/'):
            url = self.host + href
        elif href.startswith('../'):
            url = os.path.split(html_url)[0] + '/' + href
            while PARENT_RE.search(url):
                url = PARENT_RE.sub('', url)
        else:
            url = os.path.split(html_url)[0] + '/' + href

        o = urlparse(url)
        url = '%s://%s%s' % (o.scheme, o.netloc, o.path)
        if o.query:
            url += ('?' + o.query)

        return url

    # 开始运行下载器
    def start(self):
        begin_time = time.time()
        while len(self.queue) > 0:
            self.work(self.queue.popleft())
            # time.sleep(0.01)

        print('共处理%d个页面' % len(self.handled_set))
        print('Download Over!')
        print('耗时：%s秒' % (time.time() - begin_time))

    # 获取用于解码html的编码格式
    def get_encoding(self):
        return self.encoding_queue[0]

    # 如果当前的编码格式不合适，调用此方法可以更换编码
    def change_encoding(self):
        encoding = self.encoding_queue.popleft()
        self.encoding_queue.append(encoding)
        return encoding

    # 请求url获取响应
    def request_url(self, url):
        try:
            # print('请求:', url)
            b = request.urlopen(url).read()
        except error.HTTPError:
            print('请求失败:', url)
            return ''
        except error.URLError:
            print('请求失败:', url)
            return ''

        # 解码
        for i in range(len(self.encoding_queue) - 1):
            try:
                html = b.decode(self.get_encoding())
                if url.endswith('.ico'):
                    print(html)
                return html
            except UnicodeDecodeError:
                self.change_encoding()

        return ''

    # 保证目录存在，若不存在则创建。
    @staticmethod
    def ensure_dir_exist(directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    # 获取url的本地保存路径
    @staticmethod
    def get_save_path(url):
        path = urlparse(url).path

        if path.endswith('/'):
            path += 'index.html'
        elif path == '' or '.' not in path.split('/')[-1]:
            path += '/index.html'

        return ROOT_PATH + path

    # 从html中提取所有url，加入到待处理队列中。
    def extract_more_url(self, html, html_url):
        for match in LINK_RE.finditer(html):
            page_url = self.get_normal_url(match.group(1), html_url)

            # 如果此url已经处理过，则跳过
            if page_url in self.handled_set or page_url in self.queue:
                continue

            # 如果此url不是当前主机下的，则跳过
            host_match = HOST_RE.match(page_url)
            if host_match and host_match.group(1) != self.host:
                continue

            self.queue.append(page_url)

    def work(self, url):
        save_path = self.get_save_path(url)
        if os.path.splitext(save_path)[1] in HTML_LIST:
            html = self.request_url(url)
            self.extract_more_url(html, url)

        # TODO 处理(url, html)
        print('处理: %s [%d]' % (url, len(self.queue)))
        Downloader.ensure_dir_exist(os.path.split(save_path)[0])
        if not os.path.exists(save_path):
            try:
                request.urlretrieve(url, save_path)
            except error.HTTPError:
                print('下载失败:', url)
            except error.URLError:
                print('下载失败:', url)

        # 已处理过的url的集合
        self.handled_set.add(url)

if __name__ == '__main__':
    # start_url = 'http://book.douban.com'
    # start_url = 'https://docs.python.org/3/library/index.html'
    start_url = 'http://w3school.com.cn/sql/index.asp'

    downloader = Downloader(start_url)
    downloader.start()
