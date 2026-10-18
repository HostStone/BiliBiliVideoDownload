import os
import json
import subprocess

import js2py
import aiohttp
import asyncio

from io import BytesIO
from lxml import etree

from strgen import StringGenerator


work_path = str(os.path.split(__file__)[0])
ffmpeg_path = os.path.join(work_path, "Ffmpeg/bin/ffmpeg.exe")

request_header = \
    {
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0"
    }
cookies = {}
semaphore = asyncio.Semaphore(7)

async def parse(url : str):
    playinfo_str : str
    playinfo : dict
    async with aiohttp.ClientSession(headers=request_header) as session:
        session.cookie_jar.update_cookies(cookies)
        async with session.get(url) as response:
            content = await response.text()  # 视频网页HTML
            root = etree.HTML(content)
            playinfo_str = root.xpath("/html/head/script[contains(text(), 'window.__playinfo__')]/text()")[0].strip().split("\n")[0]
    content = js2py.EvalJs()
    content.execute(playinfo_str)
    playinfo = js2py.base.JsObjectWrapper.to_dict(content.playurlSSRData)
    with open(os.path.join(work_path, "playinfo.txt"), "w") as playinfo_file:
        json.dump(playinfo, playinfo_file, indent=4)

    return playinfo


async def get_high_video_quality(playinfo):
    highest = playinfo["data"]["result"]["video_info"]["dash"]["video"][0]
    for c in playinfo["data"]["result"]["video_info"]["dash"]["video"]:
        if int(highest["id"]) < int(c["id"]):
            highest = c
        else:
            if int(highest["bandwidth"]) < int(c["bandwidth"]):
                highest = c
    return highest["base_url"]

async def get_high_audio_quality(playinfo):
    highest = playinfo["data"]["result"]["video_info"]["dash"]["audio"][0]
    for c in playinfo["data"]["result"]["video_info"]["dash"]["audio"]:
        if int(highest["bandwidth"]) < int(c["bandwidth"]):
            highest = c
    return highest["base_url"]

class DownloadUnit:
        data_id : int
        data : BytesIO

async def get_data(session, url, request_head, data_id):
    async with aiohttp.ClientSession(headers=request_header) as session:
        async with semaphore:
            while True:
                async with session.get(url=url, timeout=100, headers=request_head) as response:
                    if response.status == 206:
                        data = await response.content.read()
                        length = len(data)
                        if length != int(response.headers.get("Content-Length")):
                            # 检查数据长度，如果不匹配，则认定数据不完整，要求服务器重发
                            continue
                        print(f"data {data_id} downloaded")
                        ret = DownloadUnit()
                        ret.data_id = data_id
                        ret.data = BytesIO(data)
                        return ret
                    else:
                        origin_range = request_head["range"]
                        new = "-".join([origin_range.split("-")[0], ""])
                        request_head["range"] = new

# 临时文件创建函数，后面优化的时候记得做成一个类
def get_cache_file():
    name = str(StringGenerator(r"[\w]{30}").render())
    return open(os.path.join(work_path, "DownloadCache", name), "wb")


async def download(video_link, url):
    request_headers_copy = request_header.copy()
    request_headers_copy.update(
        {
            "accept": "*/*",
            "accept-encoding": "identity",
            "origin": "https://www.bilibili.com",
            "referer": video_link,
        }
    )

    video_length: int
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
            total_data_count = video_length // cache_length + 1
            for i in range(total_data_count):
                request_headers_copy.update({"range": f"bytes={data_seek_pos}-{data_seek_pos + cache_length}"})
                tasks.append(get_data(session, url, request_headers_copy.copy(), i))
                data_seek_pos += cache_length + 1
        else:
            total_data_count = 1
            request_headers_copy.update({"range": f"bytes=0-{video_length}"})
            tasks.append(get_data(session, url, request_headers_copy.copy(), 0))

        results = await asyncio.gather(*tasks)
        cache = get_cache_file()
        for r in results:
            print(f"writing data {r.data_id}")
            cache.write(r.data.read())
        cache.close()
        return cache.name

def combine_video(video_cache_name, audio_cache_name):
    print("combine_video")
    """
    使用Ffmpeg将音频文件和视频文件合并起来。
    :param videoPath:
    :param audioPath:
    :return: (str)数据文件路径
    """
    name = str(StringGenerator(r"[\w]{30}").render())
    temp_save_path = os.path.join(work_path, "DownloadCache/" + name + ".mp4")
    subprocess.call("{ffmpeg} -i {video} -i {audio} -c copy {save}".format(
        ffmpeg="\"{0}\"".format(ffmpeg_path),
        video="\"{0}\"".format(os.path.join(work_path, "DownloadCache", video_cache_name)),
        audio="\"{0}\"".format(os.path.join(work_path, "DownloadCache", audio_cache_name)),
        save="\"{0}\"".format(temp_save_path),
    ), shell=True)  # 调用 Ffmpeg 合并视频和音频
    return temp_save_path

async def main(url: str):
    playinfo = await parse(url)
    video_link = await get_high_video_quality(playinfo)
    audio_link = await get_high_audio_quality(playinfo)
    video_cache_name = await download(url, video_link)
    audio_cache_name = await download(url, audio_link)
    combine_video(video_cache_name, audio_cache_name)

if __name__ == "__main__":
    if os.path.exists(os.path.join(work_path, "cookies2.txt")):
        with open(os.path.join(work_path, "cookies2.txt"), "r") as f:
            for c in json.loads(f.read().strip()):
                cookies.update({c["name"].strip(): c["value"].strip()})
    else:
        with open(os.path.join(work_path, "cookies2.txt"), "w") as f: pass

    asyncio.run(main("https://www.bilibili.com/bangumi/play/ep744167?spm_id_from=333.1387.0.0&from_spmid=666.25.episode.0"))