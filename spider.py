from datetime import datetime
import re
import ast
from urllib import parse
from selenium import webdriver
from scrapy import Selector
import requests
from models import *
# 导包

# 加载浏览器驱动
# 此方法可以打开调用谷歌浏览器打开一个网页并返回网页源代码
def get_html(url):
    brower = webdriver.Chrome(executable_path="C:\Program Files\Google\Chrome\Application\chromedriver.exe")
    brower.get(url)
    return brower.page_source
# 域名
domian = "https://bbs.csdn.net"

def get_nodes_list():
    left_menu_text = requests.get("https://bbs.csdn.net/dynamic_js/left_menu.js?csdn").text
    nodes_str_match = re.search("forumNodes: (.*])", left_menu_text)
    if nodes_str_match:
        nodes_str = nodes_str_match.group(1).replace("null", "None")
        nodes_list = ast.literal_eval(nodes_str)
        return nodes_list
    return []
# 定义一个列表用于存储获取到的URL
url_list = []
def process_nodes_list(nodes_list):
    # 将转换的nodes_list提取里面的url
    for item in nodes_list:
        # 判断是否有url字段且字段值不为空
        if "url" in item and item["url"]:
            # 将值记录进定义好的列表中
            url_list.append(item["url"])
            if "children" in item:
                # 如果存在children字段，则递归进入该字段提取url
                process_nodes_list(item["children"])

def get_level1_list(nodes_list):
    # 定义一个列表
    level1_url = []
    # 遍历
    for item in nodes_list:
        # 判断是否存在url字段且值不为空
        if "url" in item and item["url"]:
            # 是则将值添加进列表
            level1_url.append(item["url"])
    # 返回列表
    return level1_url

def get_last_urls():
    # 调用方法
    nodes_list = get_nodes_list()
    # 调用方法
    process_nodes_list(nodes_list)
    # 调用方法
    level1_url = get_level1_list(nodes_list)
    # 定义一个列表
    last_urls = []
    # 遍历
    for url in url_list:
        # 如果url_list中存储的url不在level1_list中
        if url not in level1_url:
            # 将网址拼接好后添加进列表
            last_urls.append(parse.urljoin(domian, url))
            last_urls.append(parse.urljoin(domian, url + "/recommend"))
            last_urls.append(parse.urljoin(domian, url + "/closed"))
    return last_urls

# 如果有多页评论就调用这个方法获取除第二页及以后的代码
def parse_answer(url):
    # 参数是第二页及以后页面的地址
    # 如：https://bbs.csdn.net/topics/393558574?page=2
    topic_id = url.split("/")[-1].split("?")[0]#提取topic_id
    rest_text = get_html(url)
    sel = Selector(text=rest_text)
    # 获取所有评论的div框
    all_divs = sel.xpath('//div[starts-with(@id, "post-")]')
    # 遍历
    for div in all_divs:
        author =  div.xpath('.//*[@class="nick_name"]/a/text()').extract()[0]#作者
        content = div.xpath('.//*[@class="post_body post_body_min_h"]/text()').extract()[0]#内容
        create_time_str = div.xpath('.//*[@class="date_time"]/text()').extract()[0]#创建时间
        create_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
        parised_nums = div.xpath('.//*[@class="red_praise digg"]/em/text()').extract()[0]#点赞数

        answer = Answer()#创建Answer对象
        answer.topic_id = topic_id
        answer.author = author
        answer.content = content
        answer.create_time = create_time
        answer.parised_nums = int(parised_nums)
        answer.save()#存入数据

    # 获取页面信息
    page_info = sel.xpath('//*[@class="mod_fun_wrap clearfix"]/div/div/em/text()').extract()
    if page_info:
        #如果获取到了用正则表达式得出评论页数
        page_num = re.search("\d",page_info[0])
        #转换为数字
        page_num = int(page_num.group(0))
    else:
        page_num = 0
    # 获取当前页是第几页
    cur_page = sel.xpath('//*[@class="pageliststy cur_page"]/text()').extract()
    # 如果获取到
    if cur_page:
        # 转换为整数
        cur_page = int(cur_page[0])
    else:
        cur_page = 0
    # 判断当前页是否小于页面总数
    if cur_page < page_num:
        # 小于则证明有下一页
        # 生成下一页的链接
        next_page = cur_page+1
        url = url.split('?')[0]
        next_url = url+"?page="+str(next_page)
        # 调用本方法取下一页的数据
        parse_answer(next_url)
    else:#没有下一页
        pass


def parse_topic(url):
    # 获取帖子的详情和回复
    topic_id = url.split("/")[-1]#提取主题id
    rest_text = get_html(url)
    sel = Selector(text=rest_text)
    all_divs = sel.xpath('//div[starts-with(@id, "post-")]')#获取所有div
    topic_item = all_divs[0]#第一个div是帖子
    content = topic_item.xpath('.//div[@class="post_body post_body_min_h"]').extract()[0]#获取帖子内容
    praised_nums = int(topic_item.xpath('.//label[@class="red_praise digg"]//em/text()').extract()[0])#获取点赞数
    jtl_str = topic_item.xpath('.//div[@class="close_topic"]/text()').extract()#结贴率
    jtl_match = re.search("(\d+\.\d+)", jtl_str[0])#正则表达式提取结贴率
    jtl = 0
    jtl = jtl_match.group(1)
    existed_topics = Topic.select().where(Topic.id == topic_id)
    if existed_topics:
        topic = existed_topics[0]
        topic.content = content
        topic.parised_nums = praised_nums
        topic.jtl = float(jtl)
        topic.save()
    # 获取当前页的评论   
    for answer_item in all_divs[1:]:
        answer = Answer()
        answer.topic_id = topic_id
        author_info = answer_item.xpath('.//div[@class="nick_name"]//a[1]/@href').extract()[0]
        author_id = author_info.split("/")[-1]
        answer.author = author_id
        create_time_str = answer_item.xpath('.//label[@class="date_time"]/text()').extract()[0]
        create_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
        answer.create_time = create_time
        parised_nums_str = answer_item.xpath('.//label[@class="red_praise digg"]//em/text()').extract()[0]
        answer.parised_nums = int(parised_nums_str)
        content = answer_item.xpath('.//div[@class="post_body post_body_min_h"]').extract()[0]
        answer.content = content
        answer.save()
    
    # 判断是否存在下一页，同parse_answer中的判断相同
    page_info = topic_item.xpath('//*[@id="bbs_title_bar"]/div[2]/div/div/em[1]/text()').extract()
    if page_info:
        page_num = re.search("\d",page_info[0])
        page_num = int(page_num.group(0))
    else:
        page_num = 0
    cur_page = topic_item.xpath('//*[@class="pageliststy cur_page"]/text()').extract()
    if cur_page:
        cur_page = int(cur_page[0])
    else:
        cur_page = 0
    if cur_page < page_num:
        next_page = cur_page+1
        next_url = url+"?page="+str(next_page)
        parse_answer(next_url)
    else:
        pass

def parse_anthor(url):
    # 获取用户的详情
    author_id = url.split("/")[-1]#获取作者id
    rest_text = get_html(url)
    sel = Selector(text=rest_text)
    name = sel.xpath('//p[@class="lt_title"]/text()').extract()[-1].strip()
    desc = sel.xpath('//div[@class="description clearfix"]/p/text()').extract()[0].strip()
    follower_nums_str = sel.xpath('//div[@class="fans"]/a/span/text()').extract()[0].strip()
    following_nums_str = sel.xpath('//div[@class="att"]/a/span/text()').extract()[0].strip()
    follower_nums = 0
    following_nums = 0
    if "k" in follower_nums_str:
        jtl_match = re.search("(\d+)", follower_nums_str)
        follower_nums = int(float(jtl_match.group(1)) * 1000)
    else:
        follower_nums = int(follower_nums_str)
    if "k" in following_nums_str:
        jtl_match = re.search("(\d+)", following_nums_str)
        following_nums = int(float(jtl_match.group(1)) * 1000)
    else:
        following_nums = int(following_nums_str)

    author = Author()
    author.id = author_id
    author.name = name
    author.desc = desc
    author.follower_nums = follower_nums
    author.following_nums = following_nums

    existed_author = Author.select().where(Author.id == author_id)
    if existed_author:
        author.save()
    else:
        author.save(force_insert=True)


def parse_list(url):
    rest_text = get_html(url)
    sel = Selector(text=rest_text)
    all_trs = sel.xpath('//table[@class="forums_tab_table"]//tbody//tr')
    for tr in all_trs:
        status = tr.xpath('.//td[1]/span/text()').extract()[0]#完结状态（数据1）
        score = int(tr.xpath('.//td[2]/em/text()').extract()[0])#悬赏分数（数据2）
        topic_url = parse.urljoin(domian, tr.xpath('.//td[3]/a[last()]/@href').extract()[0])#文章链接
        topic_title = tr.xpath('.//td[3]/a[last()]/text()').extract()[0]#主题（数据3）
        author_url = tr.xpath('.//td[4]/a/@href').extract()[0]#作者链接
        author_id = author_url.split("/")[-1]#获取作者id（数据4）
        create_time_str = tr.xpath('.//td[4]/em/text()').extract()[0]#作者名
        create_time = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M")#转换为时间格式（数据5）
        answer_info = tr.xpath('.//td[5]/span/text()').extract()[0]#回复、查看信息
        answer_nums = int(answer_info.split("/")[0])#回复数（数据6）
        click_nums = int(answer_info.split("/")[1])#查看数（数据7）
        last_time_str = tr.xpath('.//td[6]/em/text()').extract()[0]#最后回复信息
        last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")#转为时间格式（数据8）

        topic = Topic()#创建Topic对象，存入数据
        topic.status = status
        topic.score = score
        topic.title = topic_title
        topic.author = author_id
        topic.create_time = create_time
        topic.last_time = last_time
        topic.answer_nums = answer_nums
        topic.click_nums = click_nums
        topic.id = int(topic_url.split("/")[-1])#文章id

        existed_topic = Topic.select().where(Topic.id == topic.id)
        # 通过文章id判断文章是否存在
        if existed_topic:
            topic.save()#跟新数据
        else:
            topic.save(force_insert=True)#插入数据

        parse_topic(topic_url)
        parse_anthor("https:" + author_url)

if __name__ == "__main__":
    last_urls = get_last_urls()
    parse_list(last_urls[0])