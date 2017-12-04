import time
import json
from collections import OrderedDict

import numpy as np, pandas as pd
import pymongo
from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import settings


class NuoMi():
    '''获取糯米网电影票价信息的类'''

    def __init__(self):
        # 初始化数据
        self.cityname = settings.CITY
        self.moviename = settings.MOVIE
        self.date = settings.DATE
        self.timestamp = settings.TIMESTAMP
        self.mongo_init = settings.mongo_init('nuomi_movie')
        self.browser_init = settings.browser_init
        self.current = 0
        self.total = 0

    def get_city(self):
        # 获取糯米电影里的city代码，并存入mongo数据库中，以便以后调用
        db = self.mongo_init
        col_city = db.nuomi_cityid
        # 以上是连接城市数据库的代码
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://dianying.baidu.com/common/city/citylist?hasLetter=false&isjson=false&channel=&client='
        browser.get(url)

        doc = pq(browser.page_source)
        city_json = json.loads(doc('html').text())
        data = city_json['data']['all']
        for city in data:
            try:
                col_city.update_one({'id': city['id']}, {'$set': city}, upsert=True)
                # 把每个城市对应的数据存入mongo中
            except Exception as e:
                print(e)
        browser.close()

    def cityname_to_cityid(self):
        # 把城市名称转成城市代码
        db = self.mongo_init
        col_city = db.nuomi_cityid
        # 以上是数据的连接的代码
        if not col_city.find_one({'name': self.cityname}):
            self.get_city() 
            # 假如第一次运行，获取一次数据，写入数据库
        city = col_city.find_one({'name': self.cityname})
        return city['id']

    def update_movies_info(self):
        # 通过url获取上映电影的相关信息
        db = self.mongo_init
        col_movies = db.nuomi_movies
        # 以上是连接电影数据库的代码
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://dianying.nuomi.com/common/ranklist?sortType=1&date={}&channel=&client='.format(self.timestamp)
        browser.get(url)
        doc = pq(browser.page_source)
        data = json.loads(doc('html').text())
        movies = data['data']['movies']
        for movie in movies:
            col_movies.update_one({'movieName': movie['movieName']}, {'$set': movie}, upsert=True)
            print('save:', movie['movieName'])
            # 把最近每部电影的信息存进数据库
        browser.close()

    def moviename_to_movieid(self):
        # 通过电影名称获取电影编号
        db = self.mongo_init
        col_movies = db.nuomi_movies
        # 以上是连接电影数据库的代码
        if not col_movies.find_one({'movieName': self.moviename})['movieId']:
            self.update_movies_info()
            # 假如第一次运行，获取一次数据，写入数据库
        movieid = col_movies.find_one({'movieName': self.moviename})['movieId']
        return movieid

    def get_cinema_list(self):
        # 通过城市和电影获取电影院列表
        cityid = self.cityname_to_cityid()
        movieid = self.moviename_to_movieid()
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        url = 'https://dianying.nuomi.com/movie/detail?cityId={}&movieId={}'.format(cityid, movieid)
        browser.get(url)
        time.sleep(3)
        browser.find_element_by_xpath('//li[@data-id="{}"]'.format(self.timestamp)).click()
        time.sleep(1)
        doc = pq(browser.page_source)
        moreCinema_bnt = doc('html').find('#moreCinema').text()
        print(moreCinema_bnt)
        while moreCinema_bnt == '点击查看更多影院  >':
            moreCinema_bnt = wait.until(
                EC.element_to_be_clickable((By.ID, 'moreCinema'))
            )
            moreCinema_bnt.click()
            time.sleep(2)
            doc = pq(browser.page_source)
            moreCinema_bnt = doc('html').find('#moreCinema').text()
            print(moreCinema_bnt)
        doc = pq(browser.page_source)
        datas = doc('.btn.seat-btn.fr')
        cinema_list = []
        for i in range(len(datas)):
            data = eval(datas.eq(i).attr('data-data'))
            cinema_list.append(data)
        browser.close()
        return cinema_list

    def get_sessions(self):
        # 获取每个影院所有的场次信息
        cinema_list = self.get_cinema_list()
        browser = self.browser_init()
        wait = WebDriverWait(browser, 10)
        self.total = len(cinema_list)
        for cinema in cinema_list:
            self.current += 1
            cinemaId = cinema['cinemaId']
            movieId = cinema['movieId']
            date = cinema['date']
            url = 'https://dianying.baidu.com/cinema/cinemadetail?cinemaId={}&movieId={}&date={}'.format(cinemaId,
                                                                                                         movieId,
                                                                                                         date)
            print(url, '{}/{}'.format(self.current, self.total))
            browser.get(url)
            doc = pq(browser.page_source)
            cinema_name = doc('.title').text().split(' ')[0]
            movie_name = doc('.movie-detail.font-color.active.hide.clearfix').text().split(' ')[0]
            movie = doc('#datelist').find('.date.active.hide').find('.session-list.hide.active')
            session_time = movie.attr('data-id')
            if session_time == self.timestamp:
                time_local = time.localtime(int(session_time[:-3]))
                session_date = time.strftime("%Y-%m-%d", time_local)
                lis = movie.find('.clearfix')
                for i in range(len(lis)):
                    session_info = {}
                    session_info['movie'] = movie_name
                    session_info['cinema'] = cinema_name
                    session_info['date'] = session_date
                    session_info['time'] = lis.eq(i).find('.time').text()
                    session_info['type'] = lis.eq(i).find('.type').text()
                    session_info['hall'] = lis.eq(i).find('.hall').text()
                    session_info['price'] = lis.eq(i).find('.num').text()
                    # session_info['seat'] = lis.eq(i).find('.seat').text()
                    # session_info['btn_select'] = lis.eq(i).find('.btn-select').text()
                    self.save_sessions_to_mongo(session_info)
                    print(session_info)
            else:
                print('影院无该日期的场次')
            time.sleep(2)
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
        print('糯米电影的最低价场次推荐：---------------------------------------------')
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
        url = 'https://dianying.baidu.com'
        browser.get(url)
        time.sleep(2)
        doc = pq(browser.page_source)
        hot_movies = doc('.slides').eq(0).find('.item')
        # soon_movies = doc('.slides').eq(1).find('.item')
        print('糯米网共{}部热映电影'.format(len(hot_movies)))
        for i in range(len(hot_movies)):
            name = hot_movies.eq(i).find('.text.font14').text()
            score = hot_movies.eq(i).find('.fr.record.nuomi-orange').text()
            data_url = hot_movies.eq(i).find('.buy').attr('data-url')
            data_data = eval(hot_movies.eq(i).find('.buy').attr('data-data'))
            url = 'https://dianying.nuomi.com{}?movieId={}'.format(data_url, data_data['movieId'])
            print('影片：{} 评分：{}'.format(name, score))
            print('影片详情：', url)
        browser.close()
