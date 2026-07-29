import os
import re
import hashlib
import urllib.parse

import requests
from lxml import etree
from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

load_dotenv()


class Music2t58Spider:
    """2t58.com 首页数据爬虫

    目标站点有人机验证，需在 .env 配置有效的 MUSIC_2T58_PHPSESSID
    （浏览器通过验证后从 cookie 获取，过期需更新）。
    """

    HOME_URL = 'https://www.2t58.com/'

    # 模拟浏览器请求头，避免基础反爬拦截
    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://www.2t58.com/',
    }

    # 歌曲详情页相关配置
    # 播放链接/歌词接口
    PLAY_API = 'https://www.2t58.com/js/play.php'
    LRC_API = 'https://js.eev3.com/lrc.php'
    # AES 解密密钥（提取自 playen.js，经 SHA256 后用于 AES-ECB 解密播放链接）
    DECRYPT_KEY = 'SklaBTy1aTSEEtMjAyNg'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # 注入人机验证通过后的 PHPSESSID
        phpsessid = os.getenv('MUSIC_2T58_PHPSESSID', '')
        if phpsessid:
            self.session.cookies.set('PHPSESSID', phpsessid)

    def _get_html(self, url):
        """获取页面 HTML，自动处理人机验证

        目标站点验证机制：首次访问返回含 csrf_token 的验证页，
        需 POST 表单（勾选"我不是人机"）通过验证后才返回真实内容，
        验证状态在 session 中保留约 1 小时。
        """
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        # 优先用 Content-Type 声明的编码；无声明（requests 默认 ISO-8859-1）时回退到 chardet 检测
        if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
            resp.encoding = resp.apparent_encoding
        html = resp.text
        # 命中人机验证页时，提交表单通过验证后重新请求原页面
        if 'csrf_token' in html and '安全人机验证' in html:
            html = self._pass_verification(url, html)
        return html

    def _pass_verification(self, url, html):
        """提交人机验证表单（csrf_token + human_check），返回通过验证后的真实页面 HTML"""
        tree = etree.HTML(html)
        csrf_nodes = tree.xpath('//input[@name="csrf_token"]')
        if not csrf_nodes:
            return html
        csrf_token = csrf_nodes[0].get('value', '')
        # 勾选"我不是人机"并提交，session 自动保存验证状态
        self.session.post(url, data={'csrf_token': csrf_token, 'human_check': 'on'}, timeout=10)
        resp = self.session.get(url, timeout=10)
        if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
            resp.encoding = resp.apparent_encoding
        return resp.text

    def fetch_home(self):
        """抓取首页三大板块：热门歌手 / 歌曲飙升榜 / 流行趋势榜

        失败时抛出异常，由调用方捕获降级处理。
        """
        tree = etree.HTML(self._get_html(self.HOME_URL))

        return {
            'hot_singers': self._parse_singers(tree),
            'rising_songs': self._parse_songs(tree, '歌曲飙升榜'),
            'trending_songs': self._parse_songs(tree, '流行趋势榜'),
        }

    def _section(self, tree, h1_keyword):
        """通过 h1 文本定位所在的 .layui-row.lkbj 区块"""
        expr = (
            '//div[contains(@class,"layui-row") and contains(@class,"lkbj") '
            'and .//h1[contains(text(),"%s")]]'
        ) % h1_keyword
        rows = tree.xpath(expr)
        return rows[0] if rows else None

    def _parse_singers(self, tree):
        """解析热门歌手：name / link / pic"""
        row = self._section(tree, '热门歌手')
        if row is None:
            return []
        result = []
        for li in row.xpath('.//li'):
            a = li.xpath('.//div[@class="name"]/a')
            img = li.xpath('.//div[@class="pic"]//img/@src')
            if not a:
                continue
            result.append({
                'name': (a[0].text or '').strip(),
                'link': a[0].get('href', ''),
                'pic': img[0] if img else '',
            })
        return result

    def _parse_songs(self, tree, h1_keyword):
        """解析歌曲榜单：title / link"""
        row = self._section(tree, h1_keyword)
        if row is None:
            return []
        result = []
        for li in row.xpath('.//li'):
            a = li.xpath('.//div[@class="name"]/a')
            if not a:
                continue
            result.append({
                'title': (a[0].text or '').strip(),
                'link': a[0].get('href', ''),
            })
        return result

    def fetch_singer(self, sid, page=1):
        """抓取歌手详情页：歌手信息 / 歌曲列表 / 分页

        sid 为歌手id（如 d2t3eA），page 为歌曲列表页码。
        """
        url = f'{self.HOME_URL}singer/{sid}/{page}.html'
        tree = etree.HTML(self._get_html(url))

        return {
            'sid': sid,
            'singer': self._parse_singer_info(tree),
            'songs': self._parse_singer_songs(tree),
            'pagination': self._parse_pagination(tree),
        }

    def _parse_singer_info(self, tree):
        """解析歌手信息：name / pic / intro"""
        box = tree.xpath('//div[@class="singer_info"]')
        if not box:
            return {}
        box = box[0]
        name = box.xpath('.//h1/text()')
        pic = box.xpath('.//div[@class="pic"]//img/@src')
        intro = box.xpath('.//div[@class="info"]//p//text()')
        return {
            'name': name[0].strip() if name else '',
            'pic': pic[0] if pic else '',
            'intro': ''.join(intro).strip(),
        }

    def _parse_singer_songs(self, tree):
        """解析歌手歌曲列表：title / link"""
        result = []
        for li in tree.xpath('//div[@class="play_list"]//li'):
            a = li.xpath('.//div[@class="name"]/a')
            if not a:
                continue
            result.append({
                'title': (a[0].text or '').strip(),
                'link': a[0].get('href', ''),
            })
        return result

    def _parse_pagination(self, tree):
        """解析分页：提取分页区所有链接（text / href / class / current）

        直接复用源站分页链接，避免其尾页页码在不同页不一致的问题。
        """
        page_div = tree.xpath('//div[@class="page"]')
        if not page_div:
            return {'links': []}
        links = []
        for a in page_div[0].xpath('.//a'):
            text = (a.text or '').strip()
            if not text:
                continue
            cls = a.get('class', '')
            links.append({
                'text': text,
                'href': a.get('href', ''),
                'class': cls,
                'current': 'current' in cls,
            })
        return {'links': links}

    def fetch_song(self, sid):
        """抓取歌曲详情页：歌曲信息 / 播放链接 / 歌词 / 每日推荐

        sid 为歌曲id（如 d2ttY2R2bg）。
        """
        url = f'{self.HOME_URL}song/{sid}.html'
        tree = etree.HTML(self._get_html(url))

        song_info = self._parse_song_info(tree)
        daily = self._parse_daily_recommend(tree)
        play_info = self._fetch_play_info(sid, url)
        lyrics = self._fetch_lyrics(play_info['cid'])

        # 封面图优先用页面解析的，为空时用 play.php 返回的
        if not song_info['cover']:
            song_info['cover'] = play_info['cover']

        return {
            'song': song_info,
            'play_url': play_info['play_url'],
            'lyrics': lyrics,
            'daily_recommend': daily,
        }

    def fetch_search(self, keyword, page=1):
        """抓取搜索结果页：结果列表 / 分页

        keyword 为搜索关键词，page 为页码。
        URL 规则：第1页 /so/{kw}.html，第N页 /so/{kw}/{N}.html
        """
        encoded = urllib.parse.quote(keyword)
        if page > 1:
            url = f'{self.HOME_URL}so/{encoded}/{page}.html'
        else:
            url = f'{self.HOME_URL}so/{encoded}.html'
        tree = etree.HTML(self._get_html(url))

        return {
            'keyword': keyword,
            'results': self._parse_search_results(tree),
            'pagination': self._parse_pagination(tree),
        }

    def fetch_chart(self, chart, page=1):
        """抓取榜单页：热门榜单 / 结果列表 / 分页

        chart 为榜单标识（如 new、djwuqu），page 为页码。
        URL 规则：第1页 /list/{chart}.html，第N页 /list/{chart}/{N}.html
        """
        if page > 1:
            url = f'{self.HOME_URL}list/{chart}/{page}.html'
        else:
            url = f'{self.HOME_URL}list/{chart}.html'
        tree = etree.HTML(self._get_html(url))

        # 解析页面标题（.play_list .title h1）
        title_nodes = tree.xpath('//div[@class="play_list"]//div[@class="title"]//h1//text()')
        title = ''.join(title_nodes).strip()

        return {
            'title': title,
            'songs': self._parse_search_results(tree),
            'pagination': self._parse_pagination(tree),
            'hot_rankings': self._parse_hot_rankings(tree, chart),
        }

    def _parse_hot_rankings(self, tree, chart=None):
        """解析热门榜单列表：title / link / current（div.ilingku_fl > li > a）

        源站不一定标记 current，传入 chart 时自动匹配当前榜单。
        """
        result = []
        for li in tree.xpath('//div[@class="ilingku_fl"]/li'):
            a = li.xpath('./a')
            if not a:
                continue
            title = (a[0].text or '').strip()
            if not title:
                continue
            link = a[0].get('href', '')
            is_current = 'current' in (a[0].get('class') or '')
            # 源站不一定标记 current，根据 chart 参数补充判断
            if not is_current and chart and link.replace('.html', '').split('/')[-1] == chart:
                is_current = True
            result.append({
                'title': title,
                'link': link,
                'current': is_current,
            })
        return result

    def fetch_singer_list(self, area='index', gender='index', style='index', letter='index', page=1):
        """抓取歌手列表页：分类筛选 / 歌手列表 / 分页

        URL 规则：/singerlist/{area}/{gender}/{style}/{letter}/{page}.html
        area/gender/style/letter 为分类标识，index 表示全部。
        """
        base = f'{self.HOME_URL}singerlist/{area}/{gender}/{style}/{letter}'
        url = f'{base}/{page}.html' if page > 1 else f'{base}.html'
        tree = etree.HTML(self._get_html(url))

        # 解析页面标题（.singer_list h1）
        title_nodes = tree.xpath('//div[@class="singer_list"]//h1//text()')
        title = ''.join(title_nodes).strip()

        return {
            'title': title,
            'singers': self._parse_singer_list(tree),
            'filters': self._parse_singer_filters(tree),
            'pagination': self._parse_pagination(tree),
        }

    def _parse_singer_list(self, tree):
        """解析歌手列表：name / link / pic（div.singer_list ul li）"""
        result = []
        for li in tree.xpath('//div[@class="singer_list"]//ul/li'):
            name_a = li.xpath('.//div[@class="name"]/a')
            if not name_a:
                continue
            img = li.xpath('.//div[@class="pic"]//img/@src')
            result.append({
                'name': name_a[0].get('title', '') or (name_a[0].text or '').strip(),
                'link': name_a[0].get('href', ''),
                'pic': img[0] if img else '',
            })
        return result

    def _parse_singer_filters(self, tree):
        """解析歌手列表页4个分类筛选区域（div.ilingku_fl）

        每个 ilingku_fl 的第一个 li 是标题文字，后续 li > a 是分类选项。
        返回 [{label, options: [{title, link, current}]}]
        """
        result = []
        for fl in tree.xpath('//div[@class="ilingku_fl"]'):
            lis = fl.xpath('./li')
            if not lis:
                continue
            # 第一个 li 是标题文字（如"歌手分类:"）
            label = ''.join(lis[0].itertext()).strip()
            options = []
            for li in lis[1:]:
                a = li.xpath('./a')
                if not a:
                    continue
                title = (a[0].text or '').strip()
                if not title:
                    continue
                options.append({
                    'title': title,
                    'link': a[0].get('href', ''),
                    'current': 'current' in (a[0].get('class') or ''),
                })
            result.append({'label': label, 'options': options})
        return result

    def fetch_playtype_list(self, playtype='index', page=1):
        """抓取歌单列表页：分类筛选 / 歌单列表 / 分页

        URL 规则：/playtype/{playtype}/{page}.html，playtype 为分类标识，index 表示全部。
        """
        if page > 1:
            url = f'{self.HOME_URL}playtype/{playtype}/{page}.html'
        else:
            url = f'{self.HOME_URL}playtype/{playtype}.html'
        tree = etree.HTML(self._get_html(url))

        # 解析页面标题（.video_list .title h1）和歌单总数（.pagedata span）
        title_nodes = tree.xpath('//div[@class="video_list"]//div[@class="title"]//h1//text()')
        title = ''.join(title_nodes).strip()
        total_nodes = tree.xpath('//div[@class="pagedata"]//span//text()')
        total = total_nodes[0].strip() if total_nodes else ''

        return {
            'title': title,
            'total': total,
            'playlists': self._parse_playlist_list(tree),
            'filters': self._parse_playtype_filters(tree, playtype),
            'pagination': self._parse_pagination(tree),
        }

    def _parse_playlist_list(self, tree):
        """解析歌单列表：title / link / pic（div.video_list ul.play li）"""
        result = []
        for li in tree.xpath('//div[@class="video_list"]//ul[contains(@class,"play")]/li'):
            name_a = li.xpath('.//div[@class="name"]/a')
            if not name_a:
                continue
            img = li.xpath('.//div[@class="pic"]//img/@src')
            result.append({
                'title': name_a[0].get('title', '') or (name_a[0].text or '').strip(),
                'link': name_a[0].get('href', ''),
                'pic': img[0] if img else '',
            })
        return result

    def _parse_playtype_filters(self, tree, playtype='index'):
        """解析歌单列表页6个分类筛选区域（div.ilingku_fl）

        源站不标记 current，传入 playtype 时按 link 末段标识自动匹配当前分类。
        playtype=index（全部）时无任何选项高亮，与源站一致。
        返回 [{label, options: [{title, link, current}]}]
        """
        result = []
        for fl in tree.xpath('//div[@class="ilingku_fl"]'):
            lis = fl.xpath('./li')
            if not lis:
                continue
            # 第一个 li 是标题文字（如"主题:"）
            label = ''.join(lis[0].itertext()).strip()
            options = []
            for li in lis[1:]:
                a = li.xpath('./a')
                if not a:
                    continue
                title = (a[0].text or '').strip()
                if not title:
                    continue
                link = a[0].get('href', '')
                # 源站不标记 current，按 link 末段标识匹配当前 playtype
                link_type = link.replace('.html', '').rstrip('/').split('/')[-1]
                is_current = bool(playtype) and playtype != 'index' and link_type == playtype
                options.append({
                    'title': title,
                    'link': link,
                    'current': is_current,
                })
            result.append({'label': label, 'options': options})
        return result

    def fetch_mvlist(self, mvtype='index', page=1):
        """抓取MV列表页：分类筛选 / MV列表 / 分页

        URL 规则：/mvlist/{mvtype}/{page}.html，mvtype 为分类标识，index 表示全部。
        """
        if page > 1:
            url = f'{self.HOME_URL}mvlist/{mvtype}/{page}.html'
        else:
            url = f'{self.HOME_URL}mvlist/{mvtype}.html'
        tree = etree.HTML(self._get_html(url))

        # 解析页面标题（.video_list .title h1）和视频总数（.pagedata span）
        title_nodes = tree.xpath('//div[@class="video_list"]//div[@class="title"]//h1//text()')
        title = ''.join(title_nodes).strip()
        total_nodes = tree.xpath('//div[@class="pagedata"]//span//text()')
        total = total_nodes[0].strip() if total_nodes else ''

        return {
            'title': title,
            'total': total,
            'videos': self._parse_video_list(tree),
            'filters': self._parse_mvlist_filters(tree),
            'pagination': self._parse_pagination(tree),
        }

    def _parse_video_list(self, tree):
        """解析MV列表：title / link / pic（div.video_list ul li）"""
        result = []
        for li in tree.xpath('//div[@class="video_list"]//ul/li'):
            name_a = li.xpath('.//div[@class="name"]/a')
            if not name_a:
                continue
            img = li.xpath('.//div[@class="pic"]//img/@src')
            result.append({
                'title': name_a[0].get('title', '') or (name_a[0].text or '').strip(),
                'link': name_a[0].get('href', ''),
                'pic': img[0] if img else '',
            })
        return result

    def _parse_mvlist_filters(self, tree):
        """解析MV列表页分类筛选区域（div.ilingku_fl）

        源站标记 current（与歌手列表一致），直接读取 class。
        返回 [{label, options: [{title, link, current}]}]
        """
        result = []
        for fl in tree.xpath('//div[@class="ilingku_fl"]'):
            lis = fl.xpath('./li')
            if not lis:
                continue
            label = ''.join(lis[0].itertext()).strip()
            options = []
            for li in lis[1:]:
                a = li.xpath('./a')
                if not a:
                    continue
                title = (a[0].text or '').strip()
                if not title:
                    continue
                options.append({
                    'title': title,
                    'link': a[0].get('href', ''),
                    'current': 'current' in (a[0].get('class') or ''),
                })
            result.append({'label': label, 'options': options})
        return result

    def _resolve_vplay_url(self, sid, q):
        """请求 vplay 接口获取 302 重定向的 CDN mp4 直链

        浏览器无源站 PHPSESSID，直访 vplay 会被重定向到首页导致视频加载失败，
        故由后端预解析真实 CDN 直链供前端 DPlayer 直接播放。
        """
        url = f'{self.HOME_URL}plug/down.php?ac=vplay&id={sid}&q={q}'
        try:
            r = self.session.get(url, allow_redirects=False, timeout=10)
            if r.status_code == 302:
                return r.headers.get('Location', '')
        except Exception:
            pass
        return ''

    def fetch_video(self, sid):
        """抓取MV详情页：MV标题 / 歌手信息 / 专辑 / 下载 / 每日推荐 / DPlayer配置

        sid 为MVid（如 d3Ntd2tkY3Nz）。
        """
        url = f'{self.HOME_URL}video/{sid}.html'
        html = self._get_html(url)
        tree = etree.HTML(html)

        # DPlayer 封面图（从初始化脚本 pic 字段正则提取）
        cover_m = re.search(r'pic:\s*"([^"]+)"', html)
        cover = cover_m.group(1) if cover_m else ''

        detail = self._parse_video_detail(tree, sid)
        detail['cover'] = cover
        return detail

    def _parse_video_detail(self, tree, sid):
        """解析MV详情页各模块：标题 / 歌手 / 专辑 / 下载 / 清晰度 / 每日推荐"""
        # MV 标题（.play_left .title h1）
        title_nodes = tree.xpath('//div[@class="play_left"]//div[@class="title"]//h1//text()')
        title = ''.join(title_nodes).strip()

        # 歌手信息（.play_singer）
        singer = {}
        singer_box = tree.xpath('//div[@class="play_singer"]')
        if singer_box:
            box = singer_box[0]
            name_a = box.xpath('.//div[@class="name"]/a')
            pic_img = box.xpath('.//div[@class="pic"]//img/@src')
            info_text = box.xpath('.//div[@class="info"]//text()')
            singer = {
                'name': (name_a[0].text or '').strip() if name_a else '',
                'link': name_a[0].get('href', '') if name_a else '',
                'pic': pic_img[0] if pic_img else '',
                'video_count': ''.join(info_text).strip(),
            }

        # 专辑 / 语言时间（.play_right .sm 按内容区分）
        album = {}
        language_time = ''
        for sm in tree.xpath('//div[@class="play_right"]//div[@class="sm"]'):
            text = ''.join(sm.itertext()).strip()
            if '所属专辑' in text:
                a = sm.xpath('.//a')
                album = {
                    'name': (a[0].text or '').strip() if a else '',
                    'link': a[0].get('href', '') if a else '',
                }
            elif '所属语言' in text:
                language_time = text

        # 下载清晰度（.download li，onclick lkdown('sid','q','ilingku')）
        downloads = []
        for li in tree.xpath('//div[@class="download"]//li'):
            text = ''.join(li.itertext()).strip()
            label = text.split('：')[0] if '：' in text else ''
            lines = []
            for a in li.xpath('.//a'):
                m = re.search(r"lkdown\('([^']+)','([^']+)','([^']+)'\)", a.get('onclick', ''))
                if m:
                    lkid, q, ilingku = m.groups()
                    line_name = ''.join(a.itertext()).strip()
                    lines.append({
                        'name': line_name,
                        'q': q,
                        'url': f'{self.HOME_URL}down.php?ac=video&id={lkid}&q={q}&ilingku={ilingku}',
                    })
            if label and lines:
                downloads.append({'label': label, 'lines': lines})

        # DPlayer 清晰度：预解析 vplay 接口 302 的 CDN mp4 直链
        # 浏览器无源站 PHPSESSID，直访 vplay 会被重定向到首页导致视频加载失败
        qualities = sorted([
            {'name': d['label'], 'q': d['lines'][0]['q'],
             'url': self._resolve_vplay_url(sid, d['lines'][0]['q'])}
            for d in downloads if d['lines']
        ], key=lambda x: int(x['q']), reverse=True)

        # 每日推荐（.play_list ul li，部分含 mv 链接）
        daily = []
        for li in tree.xpath('//div[@class="play_list"]//ul/li'):
            name_a = li.xpath('.//div[@class="name"]/a')
            if not name_a:
                continue
            title_text = (name_a[0].text or '').strip()
            if not title_text:
                continue
            mv_a = li.xpath('.//div[@class="mv"]/a')
            daily.append({
                'title': title_text,
                'link': name_a[0].get('href', ''),
                'mv_link': mv_a[0].get('href', '') if mv_a else '',
            })

        return {
            'sid': sid,
            'title': title,
            'singer': singer,
            'album': album,
            'language_time': language_time,
            'qualities': qualities,
            'daily_recommend': daily,
        }

    def _parse_search_results(self, tree):
        """解析搜索结果列表：title / link（结构与每日推荐一致，div.play_list ul li）"""
        result = []
        for li in tree.xpath('//div[@class="play_list"]//ul/li'):
            a = li.xpath('.//div[@class="name"]/a')
            if not a:
                continue
            title = (a[0].text or '').strip()
            if not title:
                continue
            result.append({
                'title': title,
                'link': a[0].get('href', ''),
            })
        return result

    @staticmethod
    def _parse_song_title(title):
        """解析歌曲标题，拆分歌手列表与歌曲名。

        标题格式: "歌手1&歌手2 - 歌曲名"
        """
        if ' - ' in title:
            artist_str, song_name = title.split(' - ', 1)
            artists = [a.strip() for a in artist_str.split('&') if a.strip()]
        else:
            artists = []
            song_name = title
        return artists, song_name

    def _parse_song_info(self, tree):
        """解析歌曲基本信息：name / artists / cover / singer_url / pack_url

        结构:
            - 歌名: div.djname > h1 文本，格式 "歌手 - 歌名"
            - 封面图: div.play_singer > div.pic > img @src
            - 歌手: div.play_singer > div.center > div.name > a @title / @href
            - 打包下载: div.play_singer > div.center > div.info > a @href（外部网盘搜索）
        """
        h1_texts = tree.xpath('//div[@class="djname"]/h1/text()')
        title = ''.join(h1_texts).strip()
        artists, song_name = self._parse_song_title(title)

        img_nodes = tree.xpath('//div[@class="play_singer"]//div[@class="pic"]//img')
        cover = img_nodes[0].get('src', '') if img_nodes else ''

        name_a = tree.xpath('//div[@class="play_singer"]//div[@class="name"]/a')
        singer_url = ''
        singer_name = ''
        if name_a:
            # 歌手页链接（相对路径，如 /singer/d2t3eA.html），复用源站路径
            singer_url = name_a[0].get('href', '')
            singer_name = (name_a[0].get('title', '') or name_a[0].text or '').strip()
            if not artists and singer_name:
                artists = [singer_name]

        # 打包下载链接: 源站 a#sdown 的 href 由 JS 动态设置（wuqupan 搜索歌手名），
        # 静态 HTML 中为空，按相同规则构造
        pack_url = (
            f'http://www.wuqupan.com/share/search?key={urllib.parse.quote(singer_name)}'
            if singer_name else ''
        )

        return {'name': song_name, 'artists': artists, 'cover': cover,
                'singer_url': singer_url, 'pack_url': pack_url}

    def _parse_daily_recommend(self, tree):
        """解析"每日推荐"歌曲列表：title / link"""
        result = []
        for li in tree.xpath('//div[@class="play_list"]//ul/li'):
            a = li.xpath('.//div[@class="name"]/a')
            if not a:
                continue
            title = (a[0].text or '').strip()
            if not title:
                continue
            result.append({
                'title': title,
                'link': a[0].get('href', ''),
            })
        return result

    def _fetch_play_info(self, song_id, page_url):
        """请求 play.php 获取播放信息：加密播放链接 / 封面图 / 歌词cid"""
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': page_url,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        try:
            resp = self.session.post(
                self.PLAY_API,
                data={'id': song_id, 'type': 'music'},
                headers=headers,
                timeout=10,
            )
            data = resp.json()
        except (requests.RequestException, ValueError):
            return {'play_url': '', 'cover': '', 'cid': ''}

        if data.get('msg') != 1:
            return {'play_url': '', 'cover': '', 'cid': ''}

        return {
            'play_url': self._decrypt_play_url(data.get('url', '')),
            'cover': data.get('pic', ''),
            'cid': str(data.get('lkid', '')),
        }

    def _fetch_lyrics(self, cid):
        """请求 lrc.php 获取 LRC 格式歌词文本（带时间标签，供前端 $.lrc 同步滚动）"""
        if not cid:
            return ''
        try:
            resp = self.session.get(self.LRC_API, params={'cid': cid}, timeout=10)
            data = resp.json()
            return data.get('lrc', '')
        except (requests.RequestException, ValueError):
            return ''

    def _decrypt_play_url(self, encrypted):
        """解密播放链接：AES-ECB，密钥由固定明文经 SHA256 生成"""
        if not encrypted:
            return ''
        try:
            key = hashlib.sha256(self.DECRYPT_KEY.encode('utf-8')).digest()
            ciphertext = bytes.fromhex(encrypted)
            cipher = AES.new(key, AES.MODE_ECB)
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
            return decrypted.decode('utf-8')
        except (ValueError, KeyError):
            return ''
