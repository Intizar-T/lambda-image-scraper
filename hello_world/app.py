import io
import time
import requests
import random

from zipfile import ZipFile
from tempfile import mkdtemp
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By

language_list = ['en']

class ImageScraper:

    def __init__(self):
        self.driver = webdriver.Chrome("../chromedriver", options=self.__get_default_chrome_options())
        
    def get_image_urls(self, query: str, max_urls: int, sleep_between_interactions: int = 1):
        search_url = "https://search.naver.com/search.naver?where=image&sm=tab_jum&query={q}"
        # "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"
        self.driver.get(search_url.format(q=query))

        image_urls = set()
        image_count = 0
        results_start = 0
        while image_count < max_urls:
            self.__scroll_to_end(sleep_between_interactions)
            thumbnail_results = self.driver.find_elements(By.CSS_SELECTOR, "img._image._listImage")
            number_results = len(thumbnail_results)
            print("Found: {0} search results. Extracting links from {1}:{0}".format(number_results, results_start))

            for img in thumbnail_results[results_start:number_results]:
                self.__click_and_wait(img, sleep_between_interactions)
                self.__add_image_urls_to_set(image_urls, max_urls)
                image_count = len(image_urls)
                if image_count >= max_urls:
                    print("Found: {} image links, done!".format(len(image_urls)))
                    break
                else:
                    print("Found: {} image links, looking for more ...".format(len(image_urls)))

                load_more_button = self.driver.find_elements(By.CSS_SELECTOR, ".mye4qd")
                if load_more_button:
                    self.driver.execute_script("document.querySelector('.mye4qd').click();")

            # move the result startpoint further down
            results_start = len(thumbnail_results)

        return image_urls

    def get_in_memory_image(self, url: str, format: str):
        image_content = self.__download_image_content(url)
        try:
            image_file = io.BytesIO(image_content)
            pil_image = Image.open(image_file).convert('RGB')
            #in_mem_file = io.BytesIO()
            #pil_image.save(in_mem_file, format=format)
            
            return pil_image #base64.b64encode(in_mem_file.getvalue())
        except Exception as e:
            print("Could not get image data: {}".format(e))
            return None

    def close_connection(self):
        print("closing the connection...")
        self.driver.close()
        print("closed the connection...")

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

    def __add_image_urls_to_set(self, image_urls: set, count: int):
        actual_images = self.driver.find_elements(By.CSS_SELECTOR, 'img._image')
        print("actual_image size = ", len(actual_images))
        for i in range(count):
            image_urls.add(actual_images[i].get_attribute('src'))

    def __get_default_chrome_options(self):
        options = webdriver.ChromeOptions()
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

def lambda_handler(keyword, count):
    scr = ImageScraper()
    urls = list(scr.get_image_urls(query=keyword, max_urls=count, sleep_between_interactions=1))
    images = []
    
    for i in range(count):
        pil_image = scr.get_in_memory_image(urls[i], 'PNG')
        if not pil_image:
            continue
        file_object = io.BytesIO()
        pil_image.save(file_object, 'PNG')
        pil_image.close()
        images.append([str(i), file_object])
    
    path = keyword + '.zip'    
    with ZipFile(path, 'w') as zip_file:
        for i, (image_name, bytes_stream) in enumerate (images):
            if not images[i]:
                continue
            zip_file.writestr(image_name+'.png', bytes_stream.getvalue())
        
    print("Successfully loaded {} images".format(count))
    
    return { "statusCode": 200 }

def main():
    lambda_handler("cherry", 10)
    return

if __name__ == "__main__":
    main()