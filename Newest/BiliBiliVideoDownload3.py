"""
@author HostStone
@project Bilibili视频爬取脚本
编写方法DownloadVAData时的参考文章：https://zhuanlan.zhihu.com/p/148988473
由于之前的脚本均已不可用，这里重新开一个脚本
创建于2026年9月25日12:30:56
"""

import os
import json
import asyncio
import aiohttp

from lxml import etree
from selenium import webdriver

_work_path = str(os.path.split(__file__)[0])

# 下面充当枚举值的意义
user_agent = "user-agent"
xpath_video_playinfo = "xpath-video-playinfo"
xpath_video_description = "xpath-video-description"
xpath_video_thumbnail = "xpath-video-thumbnail"
cookie_settings = "cookie-settings"
auto_cookie = "auto-cookie"
quality_choice = "video-quality-choice"

class VideoQuality:
    q_highest = "highest"
    q_lowest = "lowest"

    q_4k = "4k"
    q_1080p60fps = "1080p60fps"
    q_1080p = "1080p"
    q_720p = "720p"
    q_480p = "480p"
    q_360p = "360p"

    code_4k = 120
    code_1080p60fps = 116
    code_1080p = 80
    code_720p = 64
    code_480p = 32
    code_360p = 16

# 程序的基本配置字典
_config : dict  = \
    {
        user_agent: "",
        xpath_video_playinfo: "",
        xpath_video_description: "",
        xpath_video_thumbnail: "",
        auto_cookie : False,
        quality_choice : "",
    }

_request_headers = \
    {
        "User-Agent" : _config[user_agent],
    }

"""
目前来讲的话，我还不清楚怎么自动获取Cookie
如果没有cookie的话，是获取不了视频的链接的
"""
_cookies = dict()

class VideoUnit:
    bandwidth : int
    codecs : str
    url : str

class AudioUnit:
    quality : int
    codecs : str
    url : str

class PlayInfo:
    def __init__(self, origin_playinfo : dict):
        self.video_available = []
        self.audio_available = []

        for v in origin_playinfo["dash"]["video"]:
            v2 = VideoUnit()
            v2.quality = int(v["id"])
            v2.codecs = v["codecs"]
            v2.url = v["base_url"]
            self.video_available.append(v2)

        for a in origin_playinfo["dash"]["audio"]:
            a2 = AudioUnit()
            a2.bandwidth = a["bandwidth"]
            a2.codecs = a["codecs"]
            a2.url = a["base_url"]
            self.audio_available.append(a2)

class DownloadSession:
    pass

async def main(url: str):

    async with aiohttp.ClientSession(headers=_request_headers) as session:
        """
        无 with 写法：
        context = await session.get(url)
        ...
        context.close()
        """

        # 若有可用cookie，加载cookie
        if len(_cookies):
            session.cookie_jar.update_cookies(_cookies)
            print("加载Cookie成功")

        async with session.get(url, timeout=5) as response:
            content = await response.text() # 视频网页HTML
            root = etree.HTML(content)
            title = root.xpath("/html/head/title")[0].text
            print(title)
            playinfo_str = root.xpath("/html/head/script[contains(text(), 'window.__playinfo__')]")[0]
            print(playinfo_str.text.split("window.__playinfo__")[1][1:])
            d = json.loads(playinfo_str.text.split("window.__playinfo__")[1][1:])
            with open(os.path.join(_work_path, "playinfo.txt"), "w") as f:
                json.dump(d, f, indent=4)



if __name__ == '__main__':
    # 配置文件检查
    if os.path.exists(os.path.join(_work_path, "settings.txt")):
        with open(os.path.join(_work_path, "settings.txt"), "r") as f:
            reads : dict = json.load(f)
            _config[user_agent] = reads[user_agent]
            _config[xpath_video_playinfo] = reads[xpath_video_playinfo]
            _config[xpath_video_description] = reads[xpath_video_description]
            _config[xpath_video_thumbnail] = reads[xpath_video_thumbnail]
            _config[auto_cookie] = reads[auto_cookie]
    else:
        with open(os.path.join(_work_path, "settings.txt"), "w") as f:
            json.dump(_config, f, indent=4)

    if os.path.exists(os.path.join(_work_path, "cookies.txt")):
        with open(os.path.join(_work_path, "cookies.txt"), "r") as f:
            _config[cookie_settings] = f.read()
    else:
        with open(os.path.join(_work_path, "cookies.txt"), "w") as f: pass

    # 配置cookie
    if not _config[auto_cookie]:
        print("解析Cookie。")
        groups = _config[cookie_settings].split(";")
        for s in groups:
            k, v = tuple(s.split("="))
            _cookies.update({k.strip(): v.strip()})
    else:
        # auto cookie
        option = webdriver.EdgeOptions()
        # 添加无界面模式参数
        option.add_argument('--headless')

        # 创建Chrome驱动程序的实例，并传入选项
        browser = webdriver.Edge(options=option)
        browser.get("https://www.bilibili.com/")
        cookie_dicts: list = browser.get_cookies()
        for cookie in cookie_dicts:
            _cookies.update({cookie["name"].strip(): cookie["value"].strip()})

    # URL输入
    test = "https://www.bilibili.com/video/BV1ubpb6xE8T/?trackid=web_pegasus_0.router-web-pegasus-2479516-gfll4.1791629306243.631&spm_id_from=333.1007.tianma.1-1-1.click&vd_source=eb65224e9803f8419cd49292bcc71e25"
    asyncio.run(main(test))