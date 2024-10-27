# BiliBiliVideoDownload
这目前算是一个潦草的项目，后期确实要做成软件类型再修葺罢。  
它其实有窗体版本，不过我把它砍掉了，后期有必要再加回来罢。  
**项目依赖Ffmpeg，请将下载完毕后的的Ffmpeg目录放入该项目的主目录里。**
**一定要Python12一下的版本（js2py在Python12工作会出问题！！！）**
## 项目结构说明
### 主目录文件说明
- BilibiliVideoDownload.py 目前已被废弃，你得使用 BilibiliVideoDownload2.py. 虽然前者被废弃，但我仍然把它保存在项目里，主要是里面有一项功能并没有在 BilibiliVideoDownload2.py 写，而且 BilibiliVideoDownload.py 里写得很冗杂。后期我会把这项功能加入到 BilibiliVideoDownload2.py 来的。  
- Login.py 是方便设置Cookie而写的，你登录Bilibili账号就可以了。如果你要手动设置，在浏览器复制Cookie后写入CookieConfig.txt里即可。
- UserAgentConfig.txt 是设置请求头用的，要更新它，在浏览器里复制“User-Agent”信息复制到该文本文件里。
### 文件夹说明
- DownloadCache是存储下载缓存的地方，如果下载失败，**缓存不会被清理**，就目前来讲，你需要自行删除下载失败后残留的文件。  
- FetchedData是存储下载成功后的视频的地方。
- ParsedData是为 BilibiliVideoDownload.py 设计的，它在**BilibiliVideoDownload2.py**里没有任何作用。如果你不是很想用 BilibiliVideoDownload.py 的话，可以删掉它。
- Webdriver是放置浏览器驱动的地方，本意就是为 Login.py 创建，但是它目前没什么用。
## 如何工作？
打开BilibiliVideoDownload2.py，输入Bilibili的一个视频链接，它开始下载。视频默认下载最高画质（如果你没登陆，就只有360p的画质，这就是设置Cookie的理由）。下载完之后它自动清除缓存，将视频文件拷贝到FetchedData文件夹里。
## 一些废话
其实没什么可说的。我为代码一些必要的地方做了注释，祝使用和学习愉快！
