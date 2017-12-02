import time

import pymongo
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

CITY = '广州'
MOVIE = '这就是命'
DATE = '2017-12-05'
timeArray = time.strptime(DATE, "%Y-%m-%d")
TIMESTAMP = str(int(time.mktime(timeArray))) + '000'


def mongo_init(db_name):
    # mongo数据库初始化
    client = pymongo.MongoClient()
    db = client[db_name]
    return db

def browser_init():
    # 浏览器初始化
    path = r'C:\phantomjs\bin\phantomjs.exe'
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap['phantomjs.page.settings.userAgent'] = (
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36'
    )
    # headers = {
    #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    #     'Accept-Language': 'zh-CN,zh;q=0.8',
    #     'Cache-Control': 'max-age=0',
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
    #     # 这种修改 UA 也有效
    #     'Connection': 'keep-alive',
    #     'Referer': 'https://dianying.taobao.com/',
    #
    # }
    # for key, value in headers.items():
    #     dcap['phantomjs.page.customHeaders.{}'.format(key)] = value
    browser = webdriver.PhantomJS(executable_path=path, desired_capabilities=dcap)
    browser.set_window_size(768, 1024)
    # 以上是浏览器配置的代码
    return browser

