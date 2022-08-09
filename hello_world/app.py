import json
import logging
import sys
import os
import io
import time
import requests
import random
import base64
import urllib3
import boto3

from datetime import datetime
from tempfile import mkdtemp
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException, NoSuchWindowException

language_list = ['en']

class ImageScraper:

    def __init__(self):
        self.driver = webdriver.Chrome("/opt/chromedriver", options=self.__get_default_chrome_options())
        
    def get_image_urls(self, query: str, max_urls: int, sleep_between_interactions: int = 1):
        search_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"
        self.driver.get(search_url.format(q=query))

        image_urls = set()
        image_count = 0
        results_start = 0
        while image_count < max_urls:
            self.__scroll_to_end(sleep_between_interactions)
            thumbnail_results = self.driver.find_elements(By.CSS_SELECTOR, "img.Q4LuWd")
            number_results = len(thumbnail_results)
            print("Found: {0} search results. Extracting links from {1}:{0}".format(number_results, results_start))

            for img in thumbnail_results[results_start:number_results]:
                self.__click_and_wait(img, sleep_between_interactions)
                self.__add_image_urls_to_set(image_urls)
                image_count = len(image_urls)
                if image_count >= max_urls:
                    print("Found: {} image links, done!".format(len(image_urls)))
                    break
            else:
                print("Found: {} image links, looking for more ...".format(len(image_urls)))

                load_more_button = self.driver.find_elements(By.CSS_SELECTOR, ".mye4qd")
                if load_more_button:
                    print("loading more...")
                    self.driver.execute_script("document.querySelector('.mye4qd').click();")

            # move the result startpoint further down
            results_start = len(thumbnail_results)

        return image_urls

    def get_in_memory_image(self, url: str, format: str):
        image_content = self.__download_image_content(url)
        try:
            image_file = io.BytesIO(image_content)
            pil_image = Image.open(image_file).convert('RGB')
            in_mem_file = io.BytesIO()
            pil_image.save(in_mem_file, format=format)
            
            return base64.b64encode(in_mem_file.getvalue())
        except Exception as e:
            print("Could not get image data: {}".format(e))

    def close_connection(self):
        self.driver.close()

    def __download_image_content(self, url):
        try:
            return requests.get(url).content
        except Exception as e:
            print("ERROR - Could not download {} - {}".format(url, e))

    def __scroll_to_end(self, sleep_time):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_time)

    def __click_and_wait(self, img, wait_time):
        try:
            img.click()
            time.sleep(wait_time)
        except Exception:
            return

    def __add_image_urls_to_set(self, image_urls: set):
        actual_images = self.driver.find_elements(By.CSS_SELECTOR, 'img.n3VNCb')
        for actual_image in actual_images:
            if actual_image.get_attribute('src') and 'http' in actual_image.get_attribute('src'):
                image_urls.add(actual_image.get_attribute('src'))

    def __get_default_chrome_options(self):
        options = webdriver.ChromeOptions()
        options.binary_location = '/opt/chrome/chrome'
        options.add_experimental_option("excludeSwitches", ['enable-automation'])
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-first-run')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-client-side-phishing-detection')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-web-security')
        options.add_argument('--lang=' + random.choice(language_list))
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280x1696")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument(f"--user-data-dir={mkdtemp()}")
        options.add_argument(f"--data-path={mkdtemp()}")
        options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        options.add_argument("--remote-debugging-port=9222")

        return options

def lambda_handler(event, context):
    start_time = datetime.now()
    
    client = boto3.client("apigatewaymanagementapi", endpoint_url="https://onedv62i9e.execute-api.ap-northeast-2.amazonaws.com/production")
    scr = ImageScraper()
    
    body = json.loads(event["body"])
    keyword = body["message"]["keyword"] #"cat" #
    count = int(body["message"]["count"]) #3 # 
    connectionId = event["requestContext"]["connectionId"]
    
    urls = list(scr.get_image_urls(query=keyword, max_urls=count, sleep_between_interactions=1))
    # files= []
    # for url in urls:
    #     img_obj = scr.get_in_memory_image(url, 'jpeg')
    #     files.append(img_obj.decode('utf-8'))
    
    #print("Successfully loaded {} images".format(count))
    
    scr.close_connection()
    
    response = client.post_to_connection(ConnectionId=connectionId, Data=json.dumps(
        {
            "imageURLs": urls,
            "duration": datetime.now().timestamp() - start_time.timestamp(),
        }
    ))
    
    return { "statusCode": 200 }
