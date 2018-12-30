import json
from urllib.parse import urlencode
import re

import os
import pymongo
from bs4 import BeautifulSoup
from lxml import html as HTML
import requests
from requests import RequestException
from config import *
from hashlib import md5
from multiprocessing import Pool
from json.decoder import JSONDecodeError

client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

headers = {
    'user-agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
    }

def get_page_index(offset, keyword):
    data = {
        'offset':  offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab':1,
        'from': 'search_tab',
        'pd': 'synthesis'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None

def parse_page_index(html):
    try:
        data = json.loads(html)
        # print(data.keys())
        # print(data)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                # print(1)
                yield item.get('article_url')
    except JSONDecodeError:
        pass

def get_page_detail(url):
    try:
        response = requests.get(url,headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页出错')
        return None

def parse_page_detail(html,url):
    # print(html)
    # etree = HTML.etree
    # html = etree.HTML(html)
    # title = html.xpath("//title/text()")
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    # print(title)
    images_pattern = re.compile(r'parse[(]"(.*?)"[)]',re.S)
    result = re.search(images_pattern,html)
    # print(result)
    if result:
        data = json.loads(result.group(1).replace('\\',''))
        # print(data)
        # print(result.group(1))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                download_image(image)
            return {
                'title': title,
                'url': url,
                'images': images
            }

def download_image(url):
    print("正在下载",url)
    try:
        response = requests.get(url,headers=headers)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print('请求图片出错',url)
        return None

def save_image(content):
    mkr = '{0}/{1}'.format(os.getcwd(),'images')
    if not os.path.exists(mkr): os.mkdir(mkr)
    file_path = mkr+'/','{0}.{1}'.format(md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
            f.close()

def save_to_mongo(result):
    # print(result)
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False

def main(offset):
    html = get_page_index(offset,KEYWORD)
    # print(html)
    for url in parse_page_index(html):
        # print(url)
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html,url)
            if result:
                save_to_mongo(result)
            # print(url)

if __name__ == '__main__':
    # main()
    groups = [x*20 for x in range(GROUP_START,GROUP_END+1)]
    pool = Pool()
    pool.map(main,groups)