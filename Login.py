# coding=utf-8
"""
@author HostStone
@date 2024年10月27日7:29
模拟登录获取Cookie
浏览器打开后登录账号即可
"""
import json
import os

from selenium import webdriver
from selenium.webdriver.common.by import By

WorkPath = os.path.split(__file__)[0]  # 获取工作目录
browser = webdriver.Edge()
browser.get("https://www.bilibili.com/")
browser.find_element(by=By.XPATH, value="//*[@id='app']/div[2]/div[1]/div[1]/div[3]/div/div[1]/div/div[1]/div").click()
while browser.find_elements(by=By.XPATH, value="//div[@class='header-avatar-unlogin-inner']"): pass
cookieDict:list = browser.get_cookies()
with open(os.path.join(WorkPath, "CookieConfig.txt"),"w",encoding="UTF-8") as cookie:
    json.dump(cookieDict,cookie,ensure_ascii=False,indent=4)
browser.close()
