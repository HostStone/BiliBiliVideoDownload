# coding=utf-8
"""
@author HostStone
@date 2022年10月5日20:29:21
@project Bilibili视频爬取脚本
编写方法DownloadVAData时的参考文章：https://zhuanlan.zhihu.com/p/148988473
"""
import json
import os
import subprocess
import time
import urllib.parse
import uuid
import zipfile
from pickletools import read_uint1

import js2py
from typing import BinaryIO

import lxml.etree as etree
import requests

WorkPath = os.path.split(__file__)[0]  # 获取工作目录
FfmpegPath = os.path.join(WorkPath, "Ffmpeg/bin/ffmpeg.exe")  # 获取Ffmpeg目录，这仅限于Windows系统，不同系统请更换版本。
RefererURL: str = ""


def ParseInputedCookie(CookieString: str):
    if not CookieString:
        return dict()
    print("解析Cookie。")
    groups = CookieString.split(";")
    cookie = dict()
    for s in groups:
        k, v = tuple(s.split("="))
        cookie.update({k.strip(): v.strip()})
    return cookie

def ParseURL(URL: str, Cookie:str = ""):  # 解析视频链接
    global RefererURL
    RefererURL = URL

    """
    :param URL:
    :return: None
    """

    """请求头，目的是为了反反爬虫，防止被“403 Forbidden”"""

    requestHead = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    }

    """获得视频的HTML网页数据"""

    web: requests.models.Response = requests.get(URL, headers=requestHead, cookies=ParseInputedCookie(Cookie))
    html = etree.HTML(web.text)

    """获取视频标题，位于网页HTML数据里的”head/title“里，这个是固定的。"""

    name: str = html.xpath("/html/head/title")[0].text

    """
    下面这些代码，获取视频信息，先获取视频的观看信息，如观看次数、创作日期，再获取反馈信息，如点赞数、投币数。
    这些数据归于视频HTML网页数据里的‘video-data’的class对象里，xpath为 //*[@id="viewbox_report"]/div
    这里说一下xpath是定位网页标签的一个XML路径语言，教程在网上一搜一大堆，比较简单，这里提供一个学习网址：
                        https://www.runoob.com/xpath/xpath-intro.html
    至于下面的xpath路径是怎么找到的，需要打开网页调试界面（F12），或PC端右键查看网页源代码。
    """

    videoInfoList: list = html.xpath("//*[@id='viewbox_report']/div/div/span")  # xpath定位观看信息
    videoRatingsList: list = html.xpath("//*[@id='arc_toolbar_report']/div[1]/span")  # xpath获取反馈信息
    videoTextData: list = []  # 准备一个变量（列表）videoTextData，存储抓取的视频信息
    for vil in videoInfoList:  # 循环
        if vil.get("title"):  #
            videoTextData.append(vil.get("title"))
        else:
            videoTextData.append(
                "创作日期：" + vil.xpath("//span[contains(@class,'pudate-text')]/text()")[0].strip("\n").strip()
            )
    for vrl in videoRatingsList:
        if vrl.get("title"):
            videoTextData.append(vrl.get("title") + vrl.xpath("span[contains(@class,'info-text')]/text()")[0])
    try:
        describe: str = html.xpath("//*[@id='v_desc']/div[1]/span")[0].text
    except IndexError:
        describe: str = "-"
    if not describe:
        describe: str = "-"
    # 获取视频封面图片数据的连接
    coverLink = urllib.parse.urljoin("https:", html.xpath("//meta[contains(@itemprop, 'thumbnailUrl')]/@content")[0])

    """打印视频信息"""

    print("\n视频名称：", name)
    print("\n视频描述:\n  ", describe)
    print("\n视频信息：")
    for t in videoTextData:
        print("     " + t)

    """
    视频数据抓取，这个也是一样，需要翻源代码。
    第一行就是视频数据链接获取的实现，它是一段内联JavaScript脚本，主要就是存储一个“window.__playinfo__”变量，这个变量又存储视频数据链接。
    """

    data = html.xpath("/html/head/script[4]/text()")
    """
    接下来使用js2py解析javascript文件
    """
    content = js2py.EvalJs()
    content.execute(data[0])
    playInfo = js2py.base.JsObjectWrapper.to_dict(content.window.__playinfo__)

    # 旧版的实现方式
    # playInfo = json.loads(data[0][20:])  # 跳过“window.__playinfo__”字符，将获取的字典字符串加载到Python里解析。

    """
    下面也是数据链接的获取。
    （网上翻的资料）2018年起，Bilibili把视频分为了画面和音频两个部分，这两个部分都有自己的数据链接，
    Bilibili的视频数据链接，分为“BaseUrl”（主要链接，一般都使用它下载数据）和“BackupUrl”（备份数据链接）。
    链接块分为：高清1080P+60FPS，高清1080P，清晰480P和流畅360P，对应编号分别为：122,80,64,32和16。这里取当前最高播放画质。
    每个链接块都有一个备份链接块，链接块下又分一般链接和备份链接。
    详细信息，还得去手动翻，我这里不能一次性说完。
    """

    video = playInfo["data"]["dash"]["video"][0]
    audio = playInfo["data"]["dash"]["audio"][0]
    print("画质：{width}x{height}".format(width=video["width"], height=video["height"]))
    with open(os.path.join(WorkPath, "ParsedData/Video_Info.txt"), "w") as out:
        json.dump(video, out, indent=4)
    with open(os.path.join(WorkPath, "ParsedData/Audio_Info.txt"), "w") as out:
        json.dump(audio, out, indent=4)
    print("\n视频和音频链接解析完毕，下载数据：")
    videoLink = video["baseUrl"]
    audioLink = audio["baseUrl"]

    """
    开始下载数据前，更新一下爬虫的请求头，设置成Bilibili的数据请求格式。
    """

    requestHead.update(
        {
            "accept": "*/*",
            "accept-encoding": "identity",
            "origin": "https://www.bilibili.com",
            "referer": URL,
        }  # 更新请求头，加入referer，目的都是为了反反爬虫，防止被“403 Forbidden”
    )

    """下载画面、音频和视频封面数据，到缓存文件夹里（DownloadCache），返回文件路径，方便下面代码调用。"""

    tempVideoPath: str = DownloadVAData(videoLink, requestHead)
    tempAudioPath: str = DownloadVAData(audioLink, requestHead)
    # 因为是返回文件路径，所以可以直接使用open方法返回IO方便下面代码调用，这里是方便获取封面数据。
    cover_stream: BinaryIO = open(DownloadCoverPicture(coverLink, requestHead), "rb")

    """
    因为画面和音频是分开的，所以要把它们进行合并。Ffmpeg是一个开源的视频处理程序，使用它可以方便地处理视频数据，如合成，转码等。
    教程请自行到网上搜索
    """

    print("\n视频和音频数据下载完毕，合并：")
    tempSavePath = CombineVideo(tempVideoPath, tempAudioPath)
    print("\n视频合并完成，输出：")

    """创建zip文件，方便将获取的视频信息和数据整合到一起。"""

    latestVideoStream = open(tempSavePath, "rb")  # 合并完成的视频此时在缓存文件夹里
    with zipfile.ZipFile(os.path.join(WorkPath, ("FetchedData/" + name + ".zip")), "w") as out:
        out.writestr(str(name) + ".mp4", latestVideoStream.read())
        out.writestr("视频封面" + os.path.splitext(coverLink)[1], cover_stream.read())
        out.comment = ("Downloaded from:" + URL + "\n").encode("ANSI")
        out.comment += "The following description relies on ANSI decoding, otherwise garbled characters will occur!\n" \
            .encode("ANSI")
        out.comment += describe.encode("ANSI")
        out.writestr("视频信息.txt", "".join(["，" + d for d in videoTextData]).strip("，"))
    latestVideoStream.close()
    cover_stream.close()

    """删除缓存"""

    print("\n删除缓存：")
    os.remove(tempVideoPath)
    os.remove(tempAudioPath)
    os.remove(tempSavePath)
    os.remove(cover_stream.name)
    print("\n完成！视频文件位于：", os.path.join(WorkPath, ("FetchedData\\" + name + ".zip")))
    web.close()


def DownloadVAData(URL: str, requestHead: dict, code: int = 0):
    """
    :param code:
    :param URL:
    :param requestHead:
    :return: (str)数据文件路径
    """
    print("\n下载数据从：", URL, end="，")
    urlAddress = urllib.parse.urlparse(URL)[1]
    print("地址：", urlAddress, end="，")
    cacheName = str(uuid.uuid4())

    """
    分片下载策略，
    """

    cacheLen = 5 * (10 ** 6)  # 设置分片大小：5MB
    dataSeek = 0  # 数据指针，方便检测下载进度
    print("分片大小：{}MB".format(cacheLen / 10 ** 6))

    """下面代码到while循环是进度条的实现"""

    dataLong, getDataLong = 0, False
    scale, bar, progress = 0, 0, 0
    downloadStart = time.perf_counter()
    reSendCount = 0

    cacheInfo, dataType = ReadCacheInfo(), "video"
    if RefererURL in cacheInfo:
        if cacheInfo[RefererURL][dataType]["finished"]:
            return cacheInfo[RefererURL][dataType]["path"]
        else:
            if code == 0:
                pass  # dataType = "video"
            else:
                dataType = "audio"
        dataSeek = cacheInfo[RefererURL][dataType]["seek"]
        cacheName: str = cacheInfo[RefererURL][dataType]["path"]
        bar = cacheInfo[RefererURL][dataType]["bar"]
        cache = open(cacheName, "ab")
    else:
        CreateURLInfo(RefererURL, cacheInfo)
        cache = open(os.path.join(WorkPath, ("DownloadCache/" + cacheName)), "wb")
        cacheInfo[RefererURL][dataType]["path"] = cache.name
        UpdateCacheInfo(cacheInfo)
    while True:
        requestHead.update(
            {
                "range": "bytes={0}-{1}".format(dataSeek, dataSeek + cacheLen),
            }
        )
        web: requests.models.Response = requests.get(URL, headers=requestHead)
        responseHeader = web.headers  # 响应头

        """进度条实现"""

        if not getDataLong:
            if responseHeader.get("Content-Range"):
                dataLong = int(responseHeader.get("Content-Range").split("/")[1])
                print("数据大小：", dataLong)
                scale = int(dataLong / cacheLen)
                if not scale:
                    scale = 1
                    bar = scale
                getDataLong = True
        else:
            # 进度条实现
            progress = (bar / scale) * 100
            during = time.perf_counter() - downloadStart
            print("\r               {:^3.0f}%[{}->{}]{:.2f}s".format(
                progress,
                "*" * int((bar / scale) * 100),
                "." * int(((scale - bar) / scale) * 100),
                during
            ), end="")
            bar += 1
            cacheInfo[RefererURL][dataType]["bar"] = bar
            UpdateCacheInfo(cacheInfo)

        """一般206响应码表示正常返回数据，如果响应码不是206，则一般判定为数据下载完，服务器报错"""

        if web.status_code == 206:
            data = web.content
            length: int = len(data)
            if length != int(responseHeader.get("Content-Length")):  # 检查数据长度，如果不匹配，则认定数据不完整，要求服务器重发
                reSendCount += 1
                bar -= 1
                continue
            cache.write(data)
            cache.flush()
            dataSeek += cacheLen + 1
            cacheInfo[RefererURL][dataType]["seek"] = dataSeek
            UpdateCacheInfo(cacheInfo)
        else:

            """服务器报错时，一般还有部分数据没有下载完，这时一次性请求完所有数据"""

            requestHead.update(
                {
                    "range": "bytes={0}-".format(dataSeek),
                }
            )
            cacheInfo[RefererURL][dataType]["finished"] = True
            web: requests.models.Response = requests.get(URL, headers=requestHead)
            data: bytes = web.content
            cache.write(data)
            cache.close()
            break
    print("\n\n重新请求数据次数：", reSendCount)
    cache.close()
    web.close()
    del cacheInfo[RefererURL]
    UpdateCacheInfo(cacheInfo)
    return cache.name


def DownloadCoverPicture(URL: str, requestHead: dict):
    """
    下载视频封面数据，与方法DownloadVAData相似，不做过多解释
    :param URL:
    :param requestHead:
    :return: (str)数据文件路径
    """
    print("\n下载视频封面数据数据从：", URL)
    cacheName = str(uuid.uuid4())
    cache = open(os.path.join(WorkPath, ("DownloadCache/" + cacheName)), "wb")
    del requestHead["range"]
    while True:
        web: requests.models.Response = requests.get(URL, headers=requestHead)
        responseHeader = web.headers  # 响应头
        data = web.content
        length = len(data)
        if length != int(responseHeader.get("Content-Length")):  # 检查数据长度，如果不匹配，则认定数据不完整，要求服务器重发
            continue
        cache.write(data)
        break
    cache.close()
    web.close()
    return cache.name


def CombineVideo(videoPath, audioPath):
    """
    :param videoPath:
    :param audioPath:
    :return: (str)数据文件路径
    """
    tempSavePath = os.path.join(WorkPath, "DownloadCache/" + str(uuid.uuid4()) + ".mp4")
    subprocess.call("{ffmpeg} -i {video} -i {audio} -c copy {save}".format(
        ffmpeg="\"{0}\"".format(FfmpegPath),
        video="\"{0}\"".format(videoPath),
        audio="\"{0}\"".format(audioPath),
        save="\"{0}\"".format(tempSavePath),
    ), shell=True)  # 调用 Ffmpeg 合并视频和音频
    return tempSavePath


def CreateNewCacheInfo():
    new = open(os.path.join(WorkPath, "DownloadCache/CacheInfo.info"), "wb")
    new.write(json.dumps(dict(), indent=4).encode("UTF-8"))


def CreateURLInfo(URL: str, cacheInfo):
    newInfo = {
        "video": {
            "seek": 0,
            "path": None,
            "finished": False,
            "bar": 0
        },
        "audio": {
            "seek": 0,
            "path": None,
            "finished": False,
            "bar": 0
        },
    }
    UpdateCacheInfo(cacheInfo)
    cacheInfo[URL] = newInfo


def UpdateCacheInfo(cacheInfo):
    with open(os.path.join(WorkPath, "DownloadCache/CacheInfo.info"), "wb") as update:
        update.write(json.dumps(cacheInfo, indent=4).encode("UTF-8"))


def ReadCacheInfo():
    if not os.path.isfile(os.path.join(WorkPath, "DownloadCache/CacheInfo.info")):
        CreateNewCacheInfo()
    stream = open(os.path.join(WorkPath, "DownloadCache/CacheInfo.info"), "rb")
    cacheInfo = json.loads(stream.read().decode("UTF-8"))
    return cacheInfo


if __name__ == "__main__":
    cookie = input("（不可乱输入）输入Cookie，可以跳过：\n")
    url = input("输入要解析的BiliBili视频网址:")
    try:
        ParseURL(url, cookie)
    except requests.exceptions.MissingSchema as e:
        print("发生错误！", e)
    except IndexError as e:
        print("发生错误！", e)
        print("发生此类错误，原因可能是没有输入正确的视频网址，请检查后重试。")
    except KeyboardInterrupt:
        print("\n用户中断了操作。")
    except requests.exceptions.ConnectTimeout as e:
        print("服务器响应超时：", e)
    print("\n三秒后退出......")
    time.sleep(3)
