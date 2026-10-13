"""
@author HostStone
@project Bilibili视频爬取脚本
编写方法DownloadVAData时的参考文章：https://zhuanlan.zhihu.com/p/148988473
由于之前的脚本均已不可用，这里重新开一个脚本
创建于2026年9月25日12:30:56
"""

import os
import wx
import json
import asyncio
import aiohttp

from lxml import etree
from typing import Callable
from selenium import webdriver
from strgen import StringGenerator

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
    }

_request_headers = \
    {
        "User-Agent" : _config[user_agent],
    }

"""
目前只能用Selmium模拟浏览器来加载Cookie
"""
_cookies = dict()

class AudioUnit:
    quality : int
    codecs : str
    url : str

class VideoUnit:
    title : str
    description : str
    publish_date : str
    author : str

    audio : AudioUnit

    bandwidth : int
    codecs : str
    url : str



class PlayInfo:
    codec_avc1 = "codec_avc1"
    codec_hvec = "codec_hvec"

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

    def get_video(self, video_quality, video_codec, audio_quality):
        pass

_playinfo : PlayInfo # 存储视频信息的全局变量

class DownloadSession:
    def __init__(self):
        pass

    def _launch_download(self):
        pass

    async def _download(self):
        pass

# 临时文件创建函数，后面优化的时候记得做成一个类
def get_cache_file():
    name = str(StringGenerator(r"[\w]{30}").render())
    return open(os.path.join(_work_path, "DownloadCache", name), "wb")

"""
下面是自定义窗体类
子窗体类在前，父窗体类在后
"""
class ConfigurationWindow(wx.Frame):
    def __init__(self, parent):
        pass

class MainWindow(wx.App):
    pass


async def get_video_info(url : str) -> PlayInfo:
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
            content = await response.text()  # 视频网页HTML
            root = etree.HTML(content)
            title = root.xpath("/html/head/title")[0].text
            print(title)
            playinfo_str = root.xpath("/html/head/script[contains(text(), 'window.__playinfo__')]")[0]
            origin_playinfo = json.loads(playinfo_str.text.split("window.__playinfo__")[1][1:])
            return PlayInfo(origin_playinfo)

class DownloadPage(wx.Panel):
    # 函数
    # in类函数是外界传递给页面类的，out类函数是用于给外界用的
    in_parse_link : Callable[[str], None]
    in_get_video_name : Callable[[], str]
    in_get_video_description : Callable[[], str]
    in_get_video_date : Callable[[], str]
    in_get_video_author : Callable[[], str]

    in_get_video_thumbnail : Callable[[], str]
    in_download_ensure : Callable[[], None]

    out_get_video_quality_choice : Callable[[], str]

    def __init__(self, parent):
        super().__init__(parent, -1)

        # 必要的信息获取组件先设置
        self.video_link : wx.TextCtrl
        self.link_ensure : wx.Button
        self.image_preview : wx.StaticBitmap
        self.description : wx.TextCtrl
        self.codec_choice : wx.Choice
        self.video_quality : wx.Choice
        self.audio_quality : wx.Choice
        self.download_ensure : wx.Button
        self.download_progress : wx.Gauge
        """
        self.SetBackgroundColour(wx.Colour(89, 89, 89))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        sizer.Add(wx.Button(self, -1, "ceshi", size=(20, 20)), 0, wx.EXPAND | wx.ALL, 5)
        """
        # panel1
        panel1 = wx.Panel(self, wx.ID_ANY, size=wx.Size(-1, 50))
        # panel1 组件加载
        self.video_link = wx.TextCtrl(panel1, style=wx.TE_LEFT | wx.TE_MULTILINE);self.video_link.SetHint("输入视频链接...")
        self.link_ensure = wx.Button(panel1, -1, label="确认", size=wx.Size(50, 20))
        # panel1 组件布局配置
        sizer_panel1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel1.Add(self.video_link, 1, wx.EXPAND | wx.LEFT, 5)
        sizer_panel1.Add(self.link_ensure, 0, wx.EXPAND | wx.Right, 5)
        panel1.SetSizer(sizer_panel1)

        # panel2
        panel2 = wx.Panel(self)

        # panel2 组件加载
        # panel2_right
        panel2_right = wx.Panel(panel2)
        # panel2_right 组件加载
        # panel2_right_up
        panel2_right_up = wx.Panel(panel2_right)
        sizer_panel2_right_up_static = wx.StaticBoxSizer(wx.VERTICAL, panel2_right_up, "视频下载配置")
        # panel2_right_up 组件加载
        check_boxes = []
        for i in ["画质", "音质", "视频编码器"]:
            panel = wx.Panel(sizer_panel2_right_up_static.GetStaticBox(),size = wx.Size(100, 40))
            row = wx.BoxSizer(wx.HORIZONTAL)
            c = wx.Choice(panel, choices=["A", "B", "C", "D", "E"], size=wx.Size(200, -1))
            row.Add(wx.StaticText(panel, -1, i), 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            row.Add(c, 0, wx.EXPAND | wx.ALL, 5)
            check_boxes.append(c)
            panel.SetSizer(row)
            sizer_panel2_right_up_static.Add(panel, 0, wx.EXPAND, 5)
        self.video_quality, self.audio_quality, self.codec_choice = tuple(check_boxes)
        # panel2_right_up 组件布局配置（在上面已经设置完成了）
        panel2_right_up.SetSizer(sizer_panel2_right_up_static)

        # panel2_right_down
        panel2_right_down = wx.Panel(panel2_right)
        panel2_right_down.SetBackgroundColour(wx.Colour(89, 89, 89))
        # panel2_right_down 组件加载
        self.download_ensure = wx.Button(panel2_right_down, label="下载视频")
        self.download_progress = wx.Gauge(panel2_right_down)
        # panel2_right_down 组件布局配置
        sizer_panel2_right_down = wx.BoxSizer(wx.VERTICAL)
        sizer_panel2_right_down.Add(self.download_ensure, 1, wx.EXPAND | wx.CENTER, 5)
        sizer_panel2_right_down.Add(self.download_progress, 1, wx.EXPAND | wx.CENTER, 5)
        panel2_right_down.SetSizer(sizer_panel2_right_down)

        # 组件布局配置
        sizer_panel2_right = wx.BoxSizer(wx.VERTICAL)
        sizer_panel2_right.Add(panel2_right_up, 4, wx.EXPAND | wx.TOP, 5)
        sizer_panel2_right.Add(panel2_right_down, 1, wx.EXPAND | wx.BOTTOM, 5)
        panel2_right.SetSizer(sizer_panel2_right)

        # panel2_left
        # 由于使用了StaticBoxSizer所以Sizer放到前面了
        panel2_left = wx.Panel(panel2)
        sizer_panel2_left_static = wx.StaticBoxSizer(wx.VERTICAL, panel2_left, "视频信息")
        # panel2_left 组件加载
        self.image_preview = wx.StaticBitmap(sizer_panel2_left_static.GetStaticBox(), -1, bitmap=wx.EmptyBitmap(10, 10))
        self.description = wx.TextCtrl(sizer_panel2_left_static.GetStaticBox(), style=wx.TE_MULTILINE)
        # panel2_left 组件布局配置
        sizer_panel2_left_static.Add(self.image_preview, 1, wx.EXPAND | wx.TOP, 5)
        sizer_panel2_left_static.Add(self.description, 1, wx.EXPAND | wx.BOTTOM, 5)
        panel2_left.SetSizer(sizer_panel2_left_static)

        # panel2 组件布局配置
        sizer_panel2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel2.Add(panel2_right, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer_panel2.Add(panel2_left, 1, wx.EXPAND | wx.LEFT, 5)
        panel2.SetSizer(sizer_panel2)

        # load all
        sizer_panel_main = wx.BoxSizer(wx.VERTICAL)
        sizer_panel_main.Add(panel1, 0, wx.EXPAND | wx.Top, 5)
        sizer_panel_main.Add(panel2, 1, wx.EXPAND | wx.BOTTOM, 5)
        self.SetSizer(sizer_panel_main)

        self._init2()

    def _init2(self):
        self.link_ensure.Bind(wx.EVT_BUTTON, self._get_video_link)

    def _get_video_link(self, _):
        DownloadPage.in_parse_link(self.video_link.GetValue().strip())

    def out_get_video_quality_choice(self):
        print(self.video_quality.GetSelection()) # GetSelection 返回索引值

class CookiePage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, -1)

        self.cookie_state : wx.StaticText
        self.get_cookie : wx.Button
        self.login : wx.Button

        panel1 = wx.Panel(self, size=wx.Size(-1, 50))
        text1 = wx.StaticText(panel1, wx.ID_ANY, "Cookie状态")
        self.cookie_state = wx.StaticText(panel1, wx.ID_ANY, "未加载")
        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(text1, 1, wx.EXPAND | wx.LEFT, 5)
        sizer1.Add(self.cookie_state, 0, wx.EXPAND | wx.RIGHT, 5)
        panel1.SetSizer(sizer1)

        panel2 = wx.Panel(self, size=wx.Size(-1, 50))
        text2 = wx.StaticText(panel2, wx.ID_ANY, "自动获取Cookie")
        self.get_cookie = wx.Button(panel2, wx.ID_ANY, "获取")
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(text2, 1, wx.EXPAND | wx.LEFT, 5)
        sizer2.Add(self.get_cookie, 0, wx.EXPAND | wx.RIGHT, 5)
        panel2.SetSizer(sizer2)

        panel3 = wx.Panel(self, size=wx.Size(-1, 50))
        text3 = wx.StaticText(panel3, wx.ID_ANY, "登录账号获取Cookie")
        self.login = wx.Button(panel3, wx.ID_ANY, "登录")
        sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer3.Add(text3, 1, wx.EXPAND | wx.LEFT, 5)
        sizer3.Add(self.login, 0, wx.EXPAND | wx.RIGHT, 5)
        panel3.SetSizer(sizer3)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel1, 0, wx.EXPAND | wx.CENTER, 5)
        main_sizer.Add(panel2, 0, wx.EXPAND | wx.CENTER, 5)
        main_sizer.Add(panel3, 0, wx.EXPAND | wx.CENTER, 5)
        self.SetSizer(main_sizer)

class ConfigPage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, -1)
    pass

class MainFrame(wx.Frame):
    page1 : DownloadPage
    page2 : CookiePage
    page3 : ConfigPage

    def __init__(self):
        super().__init__(None, -1, "BilibiliVideoDownload")
        self.SetSize(wx.Size(800,600))
        self.CreateStatusBar()
        # 添加一个主panel
        panel_main = wx.Panel(self)
        self.notebook = wx.Notebook(panel_main, wx.ID_ANY) # 分页组件
        # 组件布局配置
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        panel_main.SetSizer(sizer)

        """下面添加页面"""
        # 下载页面
        self.page1 = DownloadPage(self.notebook)
        self.notebook.AddPage(self.page1, "下载")
        # Cookie页面
        self.page2 = CookiePage(self.notebook)
        self.notebook.AddPage(self.page2, "Cookie配置")
        # 一些设置
        self.page3 = ConfigPage(self.notebook)
        self.notebook.AddPage(self.page3, "设置")

async def main(url: str):
    app = wx.App()
    frame = MainFrame()
    # 配置窗体程序
    frame.page1.in_parse_link = get_video_info

    frame.Show()
    app.MainLoop()

async def cookie_check():
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

    # 检查必要文件夹
    if not os.path.exists(os.path.join(_work_path, "DownloadCache")):
        os.mkdir(os.path.join(_work_path, "DownloadCache"))

    if not os.path.exists(os.path.join(_work_path, "FetchedData")):
        os.mkdir(os.path.join(_work_path, "FetchedData"))

    # URL输入
    test = "https://www.bilibili.com/video/BV1ubpb6xE8T/?trackid=web_pegasus_0.router-web-pegasus-2479516-gfll4.1791629306243.631&spm_id_from=333.1007.tianma.1-1-1.click&vd_source=eb65224e9803f8419cd49292bcc71e25"
    asyncio.run(main(test))