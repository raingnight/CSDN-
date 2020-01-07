from datetime import datetime
import re
import ast
from urllib import parse
from selenium import webdriver
from scrapy import Selector
import requests

def get_html(url):
    brower = webdriver.Chrome(executable_path="C:\Program Files\Google\Chrome\Application\chromedriver.exe")
    brower.get(url)
    return brower.page_source

def parse_answer(url):
    topic_id = url.split("/")[-1].split("?")[0]
    rest_text = get_html(url)
    sel = Selector(text=rest_text)
    all_divs = sel.xpath('//div[starts-with(@id, "post-")]')
    for div in all_divs:
        author =  div.xpath('.//*[@class="nick_name"]/a/text()').extract()
        content = div.xpath('.//*[@class="post_body post_body_min_h"]/text()').extract()
        create_time = div.xpath('.//*[@class="date_time"]/text()').extract()
        parised_nums = div.xpath('.//*[@class="red_praise digg"]/em/text()').extract()
        



parse_answer("https://bbs.csdn.net/topics/393558574?page=2")
# page_num = 3
# cur_page = 1

# url = "https://bbs.csdn.net/topics/393558574?page=2"
# id = url.split("/")[-1].split("?")[0]
# print(id)


# # 把有分页的数据，就是第2,3.。。。。页的数据 全部获取出来也保存到数据库
#     page_info = topic_item.xpath('//*[@id="bbs_title_bar"]/div[2]/div/div/em[1]/text()').extract()
#     if page_info:
#         print(page_info)
#         page_num = re.search("\d",page_info[0])
#         print(page_num)
#         page_num = int(page_num.group(0))
#     else:
#         page_num = 0
#     print(page_num)#页数

#     cur_page = topic_item.xpath('//*[@class="pageliststy cur_page"]/text()').extract()
#     print(cur_page)
#     print(type(cur_page))
#     if cur_page:
#         print(cur_page[0])
#         cur_page = int(cur_page[0])
#     else:
#         cur_page = 0
#     print(cur_page)#当前页号

#     if cur_page < page_num:
#         next_page = cur_page+1
#         next_url = url+"?page="+str(next_page)
#         print(next_url)
#         parse_topic(next_url)
#     else:
#         pass