def ParseURL(URL: str):  # 解析视频链接
    """
    :param URL: str
    :return: None
    """

    """请求头，目的是为了反反爬虫，防止被“403 Forbidden”"""

    requestHead = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    }

    """获得视频的HTML网页数据"""

# cookies=ParseInputedCookie(Cookie)
    web: requests.models.Response = requests.get(URL, headers=requestHead)
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






if __name__ == "__main__":
    url = input("输入要解析的BiliBili视频网址:")
    try:
        ParseURL(url)
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