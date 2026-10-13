import wx

from typing import Callable

class DownloadPage(wx.Panel):
    # 函数
    # in类函数是外界传递给页面类的，out类函数是用于给外界用的
    in_parse_link : Callable[[str], None]
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


app = wx.App()
frame = MainFrame()
frame.Show()
app.MainLoop()