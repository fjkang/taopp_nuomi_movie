# taopp_nuomi_movie
爬虫实战，淘票票与百度糯米价格对比
1.crawler.py
主程序入口,有3个方法
  1）get_sessions()：
    获取场次信息
  2）min_price_sessions() ：
    获取最低价场次
  3）hot_movies()
    获取热映电影
2.settings.py
负责存放关键字及初始化浏览器和数据库
   关键字有：CITY（城市）、MOVIE（电影）、DATE（日期）
   mongo_init（）负责连接mongo数据库
   browser_init（）负责设置浏览器及初始化
3.nuomi.py
获取糯米网电影票价等信息的类
4.taopiaopiao.py
获取淘票票电影票价等信息的类
