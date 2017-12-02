import time
import re

import pymongo
import numpy as np, pandas as pd
from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import settings


class TaoPiaoPiao():
    '''获取淘票票电影票价的类'''

    def __init__(self):
        # 初始化数据
        self.cityname = settings.CITY
        self.moviename = settings.MOVIE
        self.date = settings.DATE
        self.timestamp = settings.TIMESTAMP
        self.mongo_init = settings.mongo_init('taopp_movie')
        self.browser_init = settings.browser_init
        self.current = 0
        self.total = 0

    def get_city(self):
        # 获取城市名和对应的城市代码
        db = self.mongo_init
        col_taopp = db.taopp_cityid
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://dianying.taobao.com/'
        browser.get(url)
        city_bnt = wait.until(
            EC.element_to_be_clickable((By.ID, 'cityName'))
        )
        city_bnt.click()
        time.sleep(1)
        doc = pq(browser.page_source)
        city_list = doc('.M-cityList.scrollStyle').find('a')
        for i in range(len(city_list)):
            cityname = city_list.eq(i).text()
            cityid = city_list.eq(i).attr('data-id')
            try:
                col_taopp.update_one({'id': cityid}, {'$set': {'id': cityid, 'name': cityname}}, upsert=True)
            except Exception as e:
                print(e)
        browser.close()

    def get_cinema_ids(self):
        # 获取指定城市的电影院ID
        movieid = self.get_movie_id()
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://h5.m.taopiaopiao.com/app/moviemain/pages/cinema-list/index.html?showid={}'.format(movieid)
        browser.get(url)
        time.sleep(2)
        browser.find_element_by_id('citySelecter').click()  # 点击切换城市的按钮
        time.sleep(1)
        browser.find_element_by_link_text(self.cityname).click()  # 点击指定城市
        time.sleep(3)
        browser.find_element_by_xpath('//li[@data-schedule="{}"]'.format(self.timestamp[:-3])).click()
        # 点击指定日期
        wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'cinema-list-ul'))
        )
        html = browser.page_source
        doc = pq(html)
        cinema_list = doc('.list-item.list-normal')
        cinema_ids = []
        for i in range(len(cinema_list)):
            # cinma_name = cinema_list.eq(i).find('.list-title ').text()
            cinema_id = cinema_list.eq(i).find('.list-item-in').attr('data-id')
            cinema_ids.append(cinema_id)

        browser.close()
        return cinema_ids

    def update_movies_info(self):
        # 获取热映电影的ID
        db = self.mongo_init
        col_movies = db.taopp_movies
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://dianying.taobao.com/showList.htm'
        browser.get(url)
        time.sleep(2)
        doc = pq(browser.page_source)
        hot_movies = doc('.tab-content').find('.tab-movie-list').eq(0).find('.movie-card-wrap')
        # soon_movies = doc('.tab-content').find('.tab-movie-list').eq(1).find('.movie-card-wrap')
        for i in range(len(hot_movies)):
            movie_info = {}
            movie_info['url'] = hot_movies.eq(i).find('.movie-card').attr('href')
            movie_info['name'] = hot_movies.eq(i).find('.movie-card-name').find('.bt-l').text()
            movie_info['score'] = hot_movies.eq(i).find('.movie-card-name').find('.bt-r').text()
            pattern = re.compile(r'showId=(\d+)')
            movie_info['id'] = re.findall(pattern, movie_info['url'])[0]
            col_movies.update_one({'name': movie_info['name']}, {'$set': movie_info}, upsert=True)

        browser.close()

    def get_movie_id(self):
        # 通过电影名称获取电影的ID
        db = self.mongo_init
        col_movies = db.taopp_movies
        movie = col_movies.find_one({'name': self.moviename})
        return movie['id']

    def get_sessions(self):
        # 通过指定地区所有的影院ID和电影ID获取所有场次的数据
        cinema_ids = self.get_cinema_ids()
        movieid = self.get_movie_id()
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        self.total = len(cinema_ids)
        for id in cinema_ids:
            self.current += 1
            url = 'https://h5.m.taopiaopiao.com/app/moviemain/pages/show-list/index.html?&cinemaid={}&showid={}'. \
                format(id, movieid)
            browser.get(url)
            time.sleep(3)
            print(url, '{}/{}'.format(self.current, self.total))
            doc = pq(browser.page_source)
            cinema_name = doc('.cinema-name').text()
            showname = doc('.showname').text()
            ul = doc('.schedules-item-wrap').filter(
                lambda i: pq(this).attr('data-schedule') == self.timestamp
            )
            if ul:
                lis = ul.find('.item-wrap')
                for i in range(len(lis)):
                    session_info = {}
                    start = lis.eq(i).find('.item-clock').text()
                    end = lis.eq(i).find('.item-end').text()
                    date_close = lis.eq(i).parents('a').attr('data-close')
                    time_local = time.localtime(int(date_close[:-3]))
                    session_date = time.strftime("%Y-%m-%d", time_local)
                    session_info['cinema'] = cinema_name
                    session_info['movie'] = showname
                    session_info['date'] = session_date
                    session_info['time'] = start + ' ' + end
                    session_info['type'] = lis.eq(i).find('.item-type').text()
                    session_info['hall'] = lis.eq(i).find('.item-hall').text()
                    session_info['price'] = lis.eq(i).find('.price').text()
                    self.save_sessions_to_mongo(session_info)
                    print(session_info)
            else:
                print('影院无该日期的场次')
        browser.close()

    def save_sessions_to_mongo(self, session_info):
        # 把获取到的场次信息存进数据库
        db = self.mongo_init
        col_sessions = db.sessions

        col_sessions.update_one(
            {'time': session_info['time'], 'cinema': session_info['cinema'], 'movie': session_info['movie'],
             'date': session_info['date']},
            {'$set': session_info},
            upsert=True)

    def min_price_sessions(self):
        # 最低价场次的推荐
        print('淘票票的最低价场次推荐：---------------------------------------------')
        db = self.mongo_init
        col_sessions = db.sessions
        datas = col_sessions.find({'movie': self.moviename, 'date': self.date})
        sessions = []
        for data in datas:
            sessions.append(data)
        if sessions:
            sessions_df = pd.DataFrame(sessions)
            del sessions_df['_id']
            sessions_df['price'] = sessions_df['price'].astype('float')
            price_min = sessions_df['price'].min()  # 获取价格最低的值
            price_min_col = sessions_df['price'].isin([price_min])  # 获取价格最低所有的列的bool值得series
            print(sessions_df[price_min_col].to_string(index=False))  # 通过列的bool值获取所有行
        else:
            print('无最低价场次推荐')

    def hot_movies(self):
        # 获取最近热映的电影列表
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://dianying.taobao.com/showList.htm'
        browser.get(url)
        time.sleep(2)
        doc = pq(browser.page_source)
        hot_movies = doc('.tab-content').find('.tab-movie-list').eq(0).find('.movie-card-wrap')
        # soon_movies = doc('.tab-content').find('.tab-movie-list').eq(1).find('.movie-card-wrap')
        print('淘票票共{}部热映电影'.format(len(hot_movies)))
        for i in range(len(hot_movies)):
            name = hot_movies.eq(i).find('.movie-card-name').find('.bt-l').text()
            score = hot_movies.eq(i).find('.movie-card-name').find('.bt-r').text()
            if not score:
                score = '暂无'
            url = hot_movies.eq(i).find('.movie-card').attr('href')
            print('影片：{} 评分：{}'.format(name, score))
            print('影片详情：', url)
        browser.close()
