"""
@author HostStone
@project Bilibili视频爬取脚本
编写方法DownloadVAData时的参考文章：https://zhuanlan.zhihu.com/p/148988473
由于之前的脚本均已不可用，这里重新开一个脚本
创建于2026年9月25日12:30:56
"""

import os
import subprocess
import threading

import wx
import json
import asyncio
import aiohttp

from lxml import etree
from io import BytesIO
from selenium import webdriver
from strgen import StringGenerator

from typing import Any
from collections.abc import Coroutine
from selenium.webdriver.common.by import By


_work_path = str(os.path.split(__file__)[0])
ffmpeg_path = os.path.join(_work_path, "Ffmpeg/bin/ffmpeg.exe")  # 获取Ffmpeg目录，这仅限于Windows系统，不同系统请更换版本

_loop = asyncio.new_event_loop()
_download = asyncio.get_event_loop()
# 允许的协程数
_semaphore = asyncio.Semaphore(3)

def start_async_loop(loop, name):
    asyncio.set_event_loop(loop)
    loop.run_forever()
    print(f"loop {name} exited")

# 下面充当枚举值的意义
user_agent = "user-agent"
cookie_settings = "cookie-settings"

# 程序的基本配置字典
_config : dict  = \
    {
        user_agent: "",
    }

_request_headers : dict = dict()

"""
目前只能用Selmium模拟浏览器来加载Cookie
"""
class CookieFlag:
    cookie = "cookie"
    cookie2 = "cookie2"

_cookies = dict()
_cookies_load_state = False
_cookies_flag : str

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
    code_1080p60fps = 112
    code_1080p60fps2 = 116
    code_1080p = 80
    code_720p = 64
    code_480p = 32
    code_360p = 16

    @staticmethod
    def get_quality_str(code : int) -> str:
        match code:
            case VideoQuality.code_4k:
                return VideoQuality.q_4k
            case VideoQuality.code_1080p60fps:
                return VideoQuality.q_1080p60fps
            case VideoQuality.code_1080p60fps2:
                return VideoQuality.q_1080p60fps
            case VideoQuality.code_1080p:
                return VideoQuality.q_1080p
            case VideoQuality.code_720p:
                return VideoQuality.q_720p
            case VideoQuality.code_480p:
                return VideoQuality.q_480p
            case VideoQuality.code_360p:
                return VideoQuality.q_360p


class PlayInfo:
    codec_avc1 = "codec_avc1"
    codec_hvec = "codec_hvec"

    title: str
    description: str
    info: str
    author: str
    thumbnail_url: str


    def __init__(self, origin_playinfo : dict):
        self.video_available = []
        self.audio_available = []

        #self.video_bandwidth = set()
        # self.video_codecs = set()
        self.video_quality = set()

        for v in origin_playinfo["data"]["dash"]["video"]:
            v2 = VideoUnit()
            v2.quality = VideoQuality.get_quality_str(int(v["id"]))
            v2.bandwidth = int(v["bandwidth"])
            v2.codecs = v["codecs"]
            v2.url = v["base_url"]
            self.video_available.append(v2)
            self.video_quality.add(v2.quality)

        for a in origin_playinfo["data"]["dash"]["audio"]:
            a2 = AudioUnit()
            a2.bandwidth = int(a["bandwidth"])
            a2.codecs = a["codecs"]
            a2.url = a["base_url"]
            self.audio_available.append(a2)

    def get_video(self, video_quality, video_codec, audio_quality):
        pass

class AudioUnit:
    bandwidth : int
    codecs : str
    url : str

class VideoUnit:
    quality : str
    bandwidth : int
    codecs : str
    url : str

class DownloadSession:
    class _DownloadUnit:
        data_id : int
        data : BytesIO

    def __init__(self, progressbar : wx.Gauge):
        self.total_data_count = 0
        self._downloaded_data_count = 0
        self.re_send_count = 0
        self.progressbar = progressbar

    def _progress_set_range(self):
        wx.CallAfter(self.progressbar.SetRange, self.total_data_count)
        wx.CallAfter(self.progressbar.SetValue, 0)


    def progress_report(self):
        if not self._downloaded_data_count < self.total_data_count:
            return

        self._downloaded_data_count += 1

        if self.progressbar is not None:
            wx.CallAfter(self.progressbar.SetValue, self._downloaded_data_count)

    async def new_video(self, video_link, url : str) -> str: # return cache name
        request_headers_copy = _request_headers.copy()
        request_headers_copy.update(
            {
                "User-Agent" : _config[user_agent],
                "accept": "*/*",
                "accept-encoding": "identity",
                "origin": "https://www.bilibili.com",
                "referer": video_link,
            }  # 更新请求头，加入referer，目的都是为了反反爬虫，防止被“403 Forbidden”)
        )

        video_length : int
        data_seek_pos = 0
        cache_length = 2 * (10 ** 6)  # 设置分片大小：2MB (你想调大也可以)

        # 先让服务器只发送一个字节，探测视频长度
        request_headers_copy.update({"range": "bytes=0-1"})
        async with aiohttp.ClientSession() as session:
            # session.cookie_jar.update_cookies(_cookies)
            while True:
                async with session.get(url=url, timeout=5, headers=request_headers_copy) as response:
                    video_length = int(response.headers.get("Content-Range").split("/")[1])
                    # 必须要得到数据长度后才能继续
                    if response.headers.get("Content-Range"):
                        break

            print(f"data length {video_length}")

            tasks = []
            if video_length > cache_length:
                self.total_data_count = video_length // cache_length + 1
                for i in range(self.total_data_count):
                    request_headers_copy.update({"range" : f"bytes={data_seek_pos}-{data_seek_pos+cache_length}"})
                    tasks.append(self._data_get(session, url,request_headers_copy.copy(), i))
                    data_seek_pos += cache_length + 1
            else:
                self.total_data_count = 1
                request_headers_copy.update({"range": f"bytes=0-{video_length}"})
                tasks.append(self._data_get(session, url, request_headers_copy.copy(), 0))

            self._progress_set_range()

            results = await asyncio.gather(*tasks)
            cache = get_cache_file()
            for r in results:
                print(f"writing data {r.data_id}")
                cache.write(r.data.read())
            cache.close()
            return cache.name


    async def _data_get(self, session, url, request_head, data_id):
        async with _semaphore:
            while True:
                async with session.get(url=url, timeout=100, headers=request_head) as response:
                    if response.status == 206 or response.status == 200:
                        data = await response.content.read()
                        length = len(data)
                        if length != int(response.headers.get("Content-Length")):
                            # 检查数据长度，如果不匹配，则认定数据不完整，要求服务器重发
                            self.re_send_count += 1
                            continue
                        print(f"data {data_id} downloaded")
                        ret = DownloadSession._DownloadUnit()
                        ret.data_id = data_id
                        ret.data = BytesIO(data)

                        self.progress_report()

                        return ret
                    else:
                        print("resend")
                        origin_range = request_head["range"]
                        new = "-".join([origin_range.split("-")[0], ""])
                        request_head["range"] = new


    async def new_audio(self, audio_link, url : str) -> str:
        return await self.new_video(audio_link, url)

    @staticmethod
    async def new_image(url) -> BytesIO:
        print("启动图片下载程序")
        async with aiohttp.ClientSession(headers=_request_headers) as session:
            async with session.get(url, timeout=5) as response:
                return BytesIO(await response.content.read())

# 临时文件创建函数，后面优化的时候记得做成一个类
def get_cache_file():
    name = str(StringGenerator(r"[\w]{30}").render())
    return open(os.path.join(_work_path, "DownloadCache", name), "wb")

def combine_video(video_cache_name, audio_cache_name):
    print("combine_video")
    """
    使用Ffmpeg将音频文件和视频文件合并起来。
    :param videoPath:
    :param audioPath:
    :return: (str)数据文件路径
    """
    name = str(StringGenerator(r"[\w]{30}").render())
    temp_save_path = os.path.join(_work_path, "DownloadCache/" + name + ".mp4")
    subprocess.call("{ffmpeg} -i {video} -i {audio} -c copy {save}".format(
        ffmpeg="\"{0}\"".format(ffmpeg_path),
        video="\"{0}\"".format(os.path.join(_work_path, "DownloadCache", video_cache_name)),
        audio="\"{0}\"".format(os.path.join(_work_path, "DownloadCache", audio_cache_name)),
        save="\"{0}\"".format(temp_save_path),
    ), shell=True)  # 调用 Ffmpeg 合并视频和音频
    return temp_save_path

def cookie_check():
    global _cookies_load_state

    # 配置cookie
    print("解析Cookie。")
    if not _config[cookie_settings].strip():
        print("加载cookie文件失败")
        _cookies_load_state = False
        return

    global _cookies
    _cookies = dict()

    if _cookies_flag == CookieFlag.cookie:
        print("cookie id 1")
        groups = _config[cookie_settings].split(";")
        for s in groups:
            try:
                k, v = tuple(s.split("="))
                _cookies.update({k.strip(): v.strip()})
            except:
                print(s)
                raise
        _cookies_load_state = True
    else:
        print("cookie id 2")
        for c in json.loads(_config[cookie_settings].strip()):
            _cookies.update({c["name"].strip(): c["value"].strip()})
        _cookies_load_state = True

async def get_video_info(url : str) -> PlayInfo:
    async with aiohttp.ClientSession(headers=_request_headers) as session:
        """
        无 with 写法：
        context = await session.get(url)
        ...
        context.close()
        """

        # 若无可用cookie，加载；临时cookie
        if not len(_cookies):
            option = webdriver.EdgeOptions()
            # 添加无界面模式参数
            option.add_argument('--headless')

            # 创建Chrome驱动程序的实例，并传入选项
            browser = webdriver.Edge(options=option)
            browser.get("https://www.bilibili.com/")
            cookie_dicts: list = browser.get_cookies()
            for cookie in cookie_dicts:
                _cookies.update({cookie["name"].strip(): cookie["value"].strip()})

            print("加载Cookie成功")
        session.cookie_jar.update_cookies(_cookies)

        async with session.get(url, timeout=5) as response:
            content = await response.text()  # 视频网页HTML
            root = etree.HTML(content)
            title = root.xpath("/html/head/title")[0].text

            if len(root.xpath("/html/body//span[@class='desc-info-text']")) > 0:
                description = root.xpath("/html/body//span[@class='desc-info-text']")[0].text
            else:
                description = ""

            author = root.xpath("/html/head/meta[@name='author']")[0].get("content")

            info_meta = root.xpath("/html/body//div[@class='video-info-detail-list video-info-detail-content']//div/div/text()")
            info_text : str
            if len(info_meta) == 4:
                info_text = "观看：{0}，点赞：{1}，发布日期：{2}。{3}".format(*info_meta)
            else:
                info_text = "观看：{0}，点赞：{1}，发布日期：{2}。".format(*info_meta)

            print(title)
            print(author)
            print(info_text)
            print(description)

            thumbnail_url = root.xpath("/html/head/meta[@property='og:image']")[0].get("content")

            playinfo_str = root.xpath("/html/head/script[contains(text(), 'window.__playinfo__')]")[0]
            origin_playinfo = json.loads(playinfo_str.text.split("window.__playinfo__")[1][1:])
            with open(os.path.join(_work_path, "CookieConfig.txt"), "w") as fs:
                json.dump(origin_playinfo, fs, indent=4)

            ret = PlayInfo(origin_playinfo)
            ret.title = title
            ret.description = description
            ret.author = author
            ret.info = info_text
            ret.thumbnail_url = thumbnail_url

            return ret

class DownloadPage(wx.Panel):
    # 函数
    # in类函数是外界传递给页面类的，out类函数是用于给外界用的
    in_parse_link : Coroutine[Any, str, PlayInfo]

    #in_get_video_thumbnail : Coroutine[Any, Any, str]
    #in_download_ensure : Callable[[], None]

    #out_get_video_quality_choice : Callable[[], str]

    def __init__(self, parent):
        super().__init__(parent, -1)
        self.play_info : PlayInfo
        self.str_video_link : str
        self.selected_video : VideoUnit
        self.selected_audio : AudioUnit
        self.video_cache_name : str
        self.audio_cache_name : str

        # 必要的信息获取组件先设置
        self.video_link : wx.TextCtrl
        self.link_ensure : wx.Button
        self.image_preview : wx.StaticBitmap
        self.description : wx.TextCtrl
        self.video_quality : wx.Choice
        self.video_bandwidth : wx.Choice
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
        for i in ["画质", "视频带宽", "音质"]:
            panel = wx.Panel(sizer_panel2_right_up_static.GetStaticBox(),size = wx.Size(100, 40))
            row = wx.BoxSizer(wx.HORIZONTAL)
            c = wx.Choice(panel, size=wx.Size(200, -1))
            row.Add(wx.StaticText(panel, -1, i), 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            row.Add(c, 0, wx.EXPAND | wx.ALL, 5)
            check_boxes.append(c)
            panel.SetSizer(row)
            sizer_panel2_right_up_static.Add(panel, 0, wx.EXPAND, 5)
        self.video_quality, self.video_bandwidth, self.audio_quality = tuple(check_boxes)
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
        self.description = wx.TextCtrl(sizer_panel2_left_static.GetStaticBox(), style=wx.TE_MULTILINE | wx.TE_READONLY)
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
        self.link_ensure.Bind(wx.EVT_BUTTON, self._parse_video_link)
        self.video_bandwidth.Append("高带宽")
        self.video_bandwidth.Append("低带宽")

        self.audio_quality.Append("高带宽")
        self.audio_quality.Append("低带宽")

        self.video_bandwidth.SetSelection(0)
        self.audio_quality.SetSelection(0)

        self.download_ensure.Bind(wx.EVT_BUTTON, self._download_video)
        self.download_ensure.Disable()

    def _parse_video_link(self, _):
        self.link_ensure.Disable()
        self.download_ensure.Disable()
        self.video_quality.Clear()
        self.description.SetValue("")
        self.image_preview.SetBitmap(wx.EmptyBitmap(10, 10))
        self.str_video_link = self.video_link.GetValue().strip()
        future = asyncio.run_coroutine_threadsafe(self.in_parse_link(self.str_video_link), _loop)
        future.add_done_callback(self._update_to_page)

    async def _thumbnail_download(self):
        stream = await DownloadSession.new_image(self.play_info.thumbnail_url)
        img = wx.Image(stream)
        return img

    def _thumbnail_update(self, future):
        img = future.result()
        if not img.IsOk():
            print("图片数据无效")
            return
        img = img.Scale(wx.Size(300, 200), wx.IMAGE_QUALITY_HIGH)
        bmp = img.ConvertToBitmap()
        self.image_preview.SetBitmap(bmp)
        self.Layout()

    def _update_to_page(self, future):
        self.play_info: PlayInfo = future.result()
        for i in self.play_info.video_quality:
            self.video_quality.Append(i)
        self.video_quality.SetSelection(0)

        desc = f"标题：{self.play_info.title}\n\n作者：{self.play_info.author}\n\n{self.play_info.info}\n\n{self.play_info.description}"
        self.description.SetValue(desc)

        future = asyncio.run_coroutine_threadsafe(self._thumbnail_download(), _download)
        future.add_done_callback(self._thumbnail_update)

        self.link_ensure.Enable()
        self.download_ensure.Enable()

    def _download_video(self, _):
        self.link_ensure.Disable()
        self.download_ensure.Disable()
        print("下载视频")
        video_quality = self.video_quality.GetStringSelection()
        video_bandwidth = self.video_bandwidth.GetStringSelection()
        audio_quality = self.audio_quality.GetStringSelection()
        # print(video_quality, video_bandwidth, audio_quality)

        selected = []
        selected_vu : VideoUnit

        for vu in self.play_info.video_available:
            vu : VideoUnit
            if vu.quality == video_quality:
                selected.append(vu)
        selected_vu = selected[0]
        for vu2 in selected[1:]:
            vu2: VideoUnit
            if video_bandwidth == "高带宽":
                if selected_vu.bandwidth < vu2.bandwidth:
                    selected_vu = vu2
            else: # 低带宽
                if selected_vu.bandwidth > vu2.bandwidth:
                    selected_vu = vu2

        selected_au : AudioUnit = self.play_info.audio_available[0]
        for au in self.play_info.audio_available[1:]:
            au : AudioUnit

            if audio_quality == "高带宽":
                if selected_au.bandwidth < au.bandwidth:
                    selected_au = au
            else: # 低带宽
                if selected_au.bandwidth > au.bandwidth:
                    selected_au = au
        self.selected_video = selected_vu
        self.selected_audio = selected_au

        print(selected_vu.quality, selected_vu.bandwidth, selected_au.bandwidth)
        future = asyncio.run_coroutine_threadsafe(DownloadSession(self.download_progress).new_video(self.str_video_link, self.selected_video.url), _download)
        future.add_done_callback(self._when_video_downloaded)


    def _when_video_downloaded(self, future):
        self.video_cache_name = future.result()
        future = asyncio.run_coroutine_threadsafe(
            DownloadSession(self.download_progress).new_audio(self.str_video_link, self.selected_audio.url), _download)
        future.add_done_callback(self._when_audio_downloaded)

    def _when_audio_downloaded(self, future):
        self.audio_cache_name = future.result()
        combine_video(self.video_cache_name, self.audio_cache_name)

        self.link_ensure.Enable()
        self.download_ensure.Enable()


class CookiePage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, -1)
        self.cookie_state : wx.StaticText
        self.login : wx.Button

        panel1 = wx.Panel(self, size=wx.Size(-1, 50))
        text1 = wx.StaticText(panel1, wx.ID_ANY, "Cookie状态")
        self.cookie_state = wx.StaticText(panel1, wx.ID_ANY, "未加载")
        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(text1, 1, wx.EXPAND | wx.LEFT, 5)
        sizer1.Add(self.cookie_state, 0, wx.EXPAND | wx.RIGHT, 5)
        panel1.SetSizer(sizer1)

        panel2 = wx.Panel(self, size=wx.Size(-1, 50))
        text3 = wx.StaticText(panel2, wx.ID_ANY, "登录账号获取Cookie")
        self.login = wx.Button(panel2, wx.ID_ANY, "登录")
        sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer3.Add(text3, 1, wx.EXPAND | wx.LEFT, 5)
        sizer3.Add(self.login, 0, wx.EXPAND | wx.RIGHT, 5)
        panel2.SetSizer(sizer3)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel1, 0, wx.EXPAND | wx.CENTER, 5)
        main_sizer.Add(panel2, 0, wx.EXPAND | wx.CENTER, 5)
        self.SetSizer(main_sizer)

        self._init2()

    def _init2(self):
        if _cookies_load_state:
            self.cookie_state.SetLabel("已加载")

        self.login.Bind(wx.EVT_BUTTON, self._login)

    def _login(self, _):
        wx.MessageBox("你正在通过登录获取用户Cookie\n当登录时，程序窗口不可用", "提示", wx.OK | wx.ICON_INFORMATION)
        print("启动登录窗口")
        self.login.Disable()
        browser = webdriver.Edge()
        browser.get("https://www.bilibili.com/")
        browser.find_element(by=By.XPATH,
                             value="//*[@id='app']/div[2]/div[1]/div[1]/div[3]/div/div[1]/div/div[1]/div").click()
        while browser.find_elements(by=By.XPATH, value="//div[@class='header-avatar-unlogin-inner']"): pass
        cookie_dict: list = browser.get_cookies()

        with open(os.path.join(_work_path, "cookies2.txt"), "w", encoding="UTF-8") as cookie2:
            json.dump(cookie_dict, cookie2, ensure_ascii=False, indent=4)
        browser.close()
        self.login.Enable()

"""
class ConfigPage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, -1)
    pass
"""


class MainFrame(wx.Frame):
    page1 : DownloadPage
    page2 : CookiePage

    """page3 : ConfigPage"""

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

        """
        # 一些设置
        self.page3 = ConfigPage(self.notebook)
        self.notebook.AddPage(self.page3, "设置")
        """


        """绑定关闭事件"""
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_close(self, _):
        print("close")
        _loop.call_soon_threadsafe(_loop.stop)
        _download.call_soon_threadsafe(_download.stop)
        self.Destroy()


if __name__ == '__main__':
    # 配置文件检查
    if os.path.exists(os.path.join(_work_path, "settings.txt")):
        with open(os.path.join(_work_path, "settings.txt"), "r") as f:
            reads : dict = json.load(f)
            _config[user_agent] = reads[user_agent]
    else:
        with open(os.path.join(_work_path, "settings.txt"), "w") as f:
            json.dump(_config, f, indent=4)

    # 优先cookie2
    if os.path.exists(os.path.join(_work_path, "cookies2.txt")):
        with open(os.path.join(_work_path, "cookies2.txt"), "r") as f:
            _config[cookie_settings] = f.read()
            _cookies_flag = CookieFlag.cookie2
    else:
        with open(os.path.join(_work_path, "cookies2.txt"), "w") as f: pass

    if os.path.exists(os.path.join(_work_path, "cookies.txt")):
        if _cookies_flag != CookieFlag.cookie2:
            with open(os.path.join(_work_path, "cookies.txt"), "r") as f:
                _config[cookie_settings] = f.read()
                _cookies_flag = CookieFlag.cookie
    else:
        with open(os.path.join(_work_path, "cookies.txt"), "w") as f:
            pass

    # 检查必要文件夹
    if not os.path.exists(os.path.join(_work_path, "DownloadCache")):
        os.mkdir(os.path.join(_work_path, "DownloadCache"))

    if not os.path.exists(os.path.join(_work_path, "FetchedData")):
        os.mkdir(os.path.join(_work_path, "FetchedData"))

    # 更新request head
    _request_headers.update({"User-Agent": _config[user_agent]})

    # running gui async loop
    threading.Thread(target=start_async_loop, args=(_loop, "main"), name="main").start()
    # running download async loop
    threading.Thread(target=start_async_loop, args=(_download, "download"), daemon=True, name="download").start()

    cookie_check()

    app = wx.App()
    frame = MainFrame()
    # 配置窗体程序
    frame.page1.in_parse_link = get_video_info

    frame.Show()
    app.MainLoop()