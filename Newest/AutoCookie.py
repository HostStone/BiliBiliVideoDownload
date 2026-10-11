import os
import json
import selenium

from selenium import webdriver

WorkPath = os.path.split(__file__)[0]  # 获取工作目录
browser = webdriver.Edge()
browser.get("https://www.bilibili.com/")

cookieDict:list = browser.get_cookies()
with open(os.path.join(WorkPath, "CookieConfig.txt"),"w",encoding="UTF-8") as cookie:
    json.dump(cookieDict,cookie,indent=4)
browser.close()