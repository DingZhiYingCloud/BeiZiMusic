# 项目URL配置
import io
import re
import zipfile
from urllib.parse import quote

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.core.cache import cache

import requests

from SpiderServices.Music_2t58.main import Music2t58Spider


# ============ 榜单名称映射（原名称 → 本站文艺风新名称） ============
# 说明：为规避与源站（2t58.com）的名称雷同，将源站榜单/列表名称统一替换为本站
# 名称。右侧注释保留源站原名，方便后续开发者对照定位。
RENAME_MAP = {
    # —— 榜单页热榜合集（原：热门榜单侧栏 33 项）——
    'DJ舞曲大全': '律动电音集',
    '音乐热评榜': '乐评精选榜',
    '音乐先锋榜': '先锋新势力',
    '爱听电音榜': '幻彩电音榜',
    '车载歌曲榜': '旅途音乐榜',
    '英国排行榜': '英伦之声榜',
    '韩国排行榜': '韩流风尚榜',
    '日本排行榜': '和风旋律榜',
    '快手热歌榜': '短视频热歌榜',
    '抖音热歌榜': '抖音爆款榜',
    '酷我原创榜': '原创力量榜',
    'ACG新歌榜': '动漫新曲榜',
    '酷我飙升榜': '酷炫上升榜',
    '电音热歌榜': '电音浪潮榜',
    '综艺新歌榜': '综艺新声榜',
    '说唱先锋榜': '说唱前沿榜',
    '影视金曲榜': '影视原声榜',
    '粤语金曲榜': '粤语经典榜',
    '欧美金曲榜': '欧美流行榜',
    '80后热歌榜': '怀旧八零榜',
    '网红新歌榜': '网红新势力',
    '古风音乐榜': '古韵雅音榜',
    '夏日畅爽榜': '夏日清凉榜',
    '会员喜爱榜': '人气甄选榜',
    '跑步健身榜': '燃动健身榜',
    '宝宝哄睡榜': '安睡摇篮榜',
    '睡前放松榜': '夜色舒缓榜',
    '熬夜修仙榜': '夜猫陪伴榜',
    'Vlog必备榜': 'Vlog标配榜',
    'KTV点唱榜': 'KTV欢唱榜',
    '通勤路上榜': '通勤随身榜',
    '网络红歌榜': '网络热歌榜',
    '网络最新榜': '网际新声榜',
    # —— 列表页标题 ——
    '全部歌手列表': '歌手大全',          # 原：全部歌手列表
    '最新歌单歌单列表': '歌单精选',       # 原：最新歌单歌单列表
    'MV视频列表': '映像MV大全',          # 原：MV视频列表
}

# 榜单页大标题兜底（原榜单名：new=新歌榜 / top=TOP榜单 / djwuqu=DJ舞曲大全）
CHART_ID_TITLES = {
    'new': '新声速递',
    'top': '巅峰热榜',
    'djwuqu': '律动电音集',
}


def rename_title(title):
    """将源站榜单/列表名称映射为本站名称，未命中时原样返回"""
    return RENAME_MAP.get(title, title)


def index(request):
    # 调用爬虫获取首页三大板块数据；抓取失败时降级为空数据，保证页面可访问
    try:
        data = Music2t58Spider().fetch_home()
    except Exception:
        data = {'hot_singers': [], 'rising_songs': [], 'trending_songs': []}
    return render(request, 'index.html', data)


def singer(request, sid, page=1):
    # 歌手详情页：sid 为歌手id，page 为歌曲列表页码（路径参数）
    try:
        data = Music2t58Spider().fetch_singer(sid, page)
    except Exception:
        data = {
            'sid': sid,
            'singer': {},
            'songs': [],
            'pagination': {'links': []},
        }
    return render(request, 'singer.html', data)


def song(request, sid):
    # 歌曲详情页：sid 为歌曲id（路径参数）
    try:
        data = Music2t58Spider().fetch_song(sid)
    except Exception:
        data = {
            'song': {},
            'play_url': '',
            'lyrics': '',
            'daily_recommend': [],
        }
    data['sid'] = sid  # 供模板下载弹窗拼接下载地址
    return render(request, 'song.html', data)


def api_song(request, sid):
    """歌曲 JSON 接口：供全局底部播放条无刷新切歌（返回播放链接/封面/歌词等）

    路径 /api/song/<sid>.json，浏览器端在切换待播放列表歌曲时调用。
    歌词与播放链接由后端实时爬取，前端不参与解密逻辑。
    """
    try:
        data = Music2t58Spider().fetch_song(sid)
    except Exception:
        data = {'song': {}, 'play_url': '', 'lyrics': ''}
    song = data.get('song') or {}
    return JsonResponse({
        'sid': sid,
        'name': song.get('name', ''),
        'artists': song.get('artists', []),
        'cover': song.get('cover', ''),
        'play_url': data.get('play_url', ''),
        'lyrics': data.get('lyrics', ''),
        'singer_url': song.get('singer_url', ''),
    })


def search(request, keyword, page=1):
    # 搜索页：keyword 为搜索关键词，page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_search(keyword, page)
    except Exception:
        data = {
            'keyword': keyword,
            'results': [],
            'pagination': {'links': []},
        }
    return render(request, 'search.html', data)


def chart(request, chart='new', page=1):
    # 榜单页：chart 为榜单标识（如 new、djwuqu），page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_chart(chart, page)
    except Exception:
        data = {
            'title': '新声速递',        # 原：新歌榜
            'songs': [],
            'pagination': {'links': []},
            'hot_rankings': [],
        }
    # 热榜合集名称映射（规避源站榜单名）
    for item in data.get('hot_rankings', []):
        item['title'] = rename_title(item['title'])
    # 页面大标题：优先取当前榜单映射名，否则按 chart 标识兜底（<title> 仍保留源站 SEO 长句）
    page_title = next(
        (item['title'] for item in data.get('hot_rankings', []) if item.get('current')),
        None
    )
    data['page_title'] = page_title or CHART_ID_TITLES.get(chart, '热歌榜')
    return render(request, 'new_songs.html', data)


def singer_list(request, area='index', gender='index', style='index', letter='index', page=1):
    # 歌手列表页：area/gender/style/letter 为分类标识，page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_singer_list(area, gender, style, letter, page)
    except Exception:
        data = {
            'title': '歌手大全',        # 原：全部歌手列表
            'singers': [],
            'filters': [],
            'pagination': {'links': []},
        }
    data['title'] = rename_title(data.get('title', ''))
    return render(request, 'singer_list.html', data)


def playtype_list(request, playtype='index', page=1):
    # 歌单列表页：playtype 为分类标识（如 dj、huayu），page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_playtype_list(playtype, page)
    except Exception:
        data = {
            'title': '歌单精选',        # 原：最新歌单歌单列表
            'total': '',
            'playlists': [],
            'filters': [],
            'pagination': {'links': []},
        }
    data['title'] = rename_title(data.get('title', ''))
    return render(request, 'playtype_list.html', data)


def mvlist(request, mvtype='index', page=1):
    # MV列表页：mvtype 为分类标识（如 huayu、rihan），page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_mvlist(mvtype, page)
    except Exception:
        data = {
            'title': '映像MV大全',      # 原：MV视频列表
            'total': '',
            'videos': [],
            'filters': [],
            'pagination': {'links': []},
        }
    data['title'] = rename_title(data.get('title', ''))
    return render(request, 'mvlist.html', data)


def video(request, sid):
    # MV详情页：sid 为MVid（路径参数）
    try:
        data = Music2t58Spider().fetch_video(sid)
    except Exception:
        data = {
            'sid': sid,
            'title': 'MV视频',
            'singer': {},
            'album': {},
            'language_time': '',
            'qualities': [],
            'daily_recommend': [],
            'cover': '',
        }
    return render(request, 'video.html', data)


def playlist(request, sid, page=1):
    """歌单详情页：sid 为歌单id，page 为歌曲列表页码（路径参数）"""
    try:
        data = Music2t58Spider().fetch_playlist(sid, page)
    except Exception:
        data = {
            'sid': sid,
            'playlist': {},
            'total': '',
            'songs': [],
            'pagination': {'links': []},
        }
    return render(request, 'playlist.html', data)


# ============ 歌曲下载（后端代理，防防盗链与链接过期） ============
# 说明：源站 CDN（如 kuwo）防盗链规则为拒绝源站域名 Referer（2t58.com→403），
#       因此代理 CDN 直链时必须不带 Referer（无 Referer 或 CDN 自身域名→200）。
def _attachment_name(filename):
    """生成支持中文文件名的 Content-Disposition（RFC 5987 filename*）"""
    return f"attachment; filename*=UTF-8''{quote(filename)}"


# CDN 直链请求头：仅带浏览器 UA，不带 Referer（避免触发 CDN 防盗链 403）
_CDN_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
}


def _fetch_cdn_stream(play_url):
    """请求源站 CDN 直链（不带 Referer），返回流式响应；失败返回 None"""
    if not play_url:
        return None
    try:
        resp = requests.get(play_url, headers=_CDN_HEADERS, stream=True, timeout=15)
        resp.raise_for_status()
        return resp
    except requests.RequestException:
        return None


def _proxy_mp3(play_url, base):
    """后端代理下载 MP3：无 Referer 流式转发 CDN 直链，避免防盗链 403"""
    resp = _fetch_cdn_stream(play_url)
    if resp is None:
        return HttpResponse('播放链接获取失败，请稍后重试', status=502)

    def stream():
        try:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            resp.close()

    response = StreamingHttpResponse(stream(), content_type='audio/mpeg')
    response['Content-Disposition'] = _attachment_name(f'{base}.mp3')
    return response


def _text_attachment(text, filename):
    """返回文本附件（歌词 .lrc）"""
    response = HttpResponse(text, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = _attachment_name(filename)
    return response


def _zip_attachment(play_url, lyrics, base):
    """MP3 + 歌词打包为 zip（标准库 zipfile，无额外依赖）"""
    resp = _fetch_cdn_stream(play_url)
    if resp is None:
        return HttpResponse('播放链接获取失败，请稍后重试', status=502)
    try:
        mp3_data = resp.content
    finally:
        resp.close()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{base}.mp3', mp3_data)
        if lyrics:
            zf.writestr(f'{base}.lrc', lyrics)
    response = HttpResponse(buf.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = _attachment_name(f'{base}.zip')
    return response


def download(request, sid, kind='mp3'):
    """歌曲下载：kind 为 mp3（仅歌曲）/ lrc（仅歌词）/ all（两个一起打包zip）

    后端统一经爬虫获取数据，直链经无 Referer 代理转发，
    避免直链过期或防盗链导致下载失败；文件名用歌曲名-歌手。
    """
    spider = Music2t58Spider()
    try:
        data = spider.fetch_download(sid)
    except Exception:
        data = {'song': {}, 'play_url': '', 'lyrics': ''}

    song = data.get('song') or {}
    name = song.get('name') or f'song_{sid}'
    artists = '/'.join(song.get('artists') or []) or '未知歌手'
    # 清理文件名非法字符（Windows 不允许 \ / : * ? " < > | 和连续空格）
    base = re.sub(r'[\\/:*?"<>|\s]+', '_', f'{name} - {artists}').strip('_') or f'song_{sid}'

    if kind == 'mp3':
        return _proxy_mp3(data.get('play_url', ''), base)
    if kind == 'lrc':
        return _text_attachment(data.get('lyrics', ''), f'{base}.lrc')
    if kind == 'all':
        return _zip_attachment(data.get('play_url', ''), data.get('lyrics', ''), base)
    return HttpResponse('不支持的下载类型', status=400)


def error_404(request, exception=None):
    """404 错误页：访问不存在的路径或文件时返回（DEBUG=False 时生效）"""
    return render(request, '404.html', status=404)


def error_500(request, exception=None):
    """500 错误页：服务器内部错误时返回（DEBUG=False 时生效）"""
    return render(request, '500.html', status=500)


# ============ Sitemap（站点地图） ============
# 站点内容由爬虫实时获取，因此 sitemap 分为两部分：
#   1. 静态固定 URL：首页/榜单/列表页 + 首页推荐歌单（与 index.html 硬编码歌单保持一致，改动需同步）
#   2. 动态 URL：调用爬虫抓取首页，提取热门歌手、榜单歌曲生成详情页链接（爬虫失败时自动降级为仅静态 URL）
# 生成结果缓存 6 小时，避免每次请求 sitemap 都触发源站爬虫。
SITEMAP_STATIC_URLS = [
    ('/', 'daily', '1.0'),
    ('/list/new.html', 'daily', '0.8'),
    ('/list/top.html', 'daily', '0.8'),
    ('/list/djwuqu.html', 'daily', '0.8'),
    ('/singerlist/index/index/index/index.html', 'daily', '0.8'),
    ('/playtype/index.html', 'daily', '0.8'),
    ('/mvlist/index.html', 'daily', '0.8'),
    # 首页推荐歌单（10 个，与 Web/templates/index.html 中硬编码一致）
    ('/playlist/ZG53dndrY2hraA.html', 'weekly', '0.6'),
    ('/playlist/ZHZzdmR2d3ZuaA.html', 'weekly', '0.6'),
    ('/playlist/ZGNkbW54Y3hzbQ.html', 'weekly', '0.6'),
    ('/playlist/ZGNubm5tbnhraA.html', 'weekly', '0.6'),
    ('/playlist/ZHZka3duZHhtaw.html', 'weekly', '0.6'),
    ('/playlist/ZGNud3hoY3hodg.html', 'weekly', '0.6'),
    ('/playlist/ZHZudm5jY3h4Yw.html', 'weekly', '0.6'),
    ('/playlist/ZGNoa2todnNrcw.html', 'weekly', '0.6'),
    ('/playlist/ZGNueHdzeG5uaw.html', 'weekly', '0.6'),
    ('/playlist/ZHZzY254ZGtkbg.html', 'weekly', '0.6'),
]
SITEMAP_CACHE_KEY = 'sitemap_urls'
SITEMAP_CACHE_TTL = 60 * 60 * 6  # 6 小时


def sitemap(request):
    """sitemap.xml：静态 URL + 爬虫实时歌手/歌曲详情 URL，缓存 6 小时"""
    urls = cache.get(SITEMAP_CACHE_KEY)
    if urls is None:
        urls = list(SITEMAP_STATIC_URLS)
        seen = {path for path, _, _ in urls}
        try:
            data = Music2t58Spider().fetch_home()
            for singer in data.get('hot_singers', []):
                if singer.get('link') and singer['link'] not in seen:
                    urls.append((singer['link'], 'weekly', '0.6'))
                    seen.add(singer['link'])
            for song in data.get('rising_songs', []) + data.get('trending_songs', []):
                if song.get('link') and song['link'] not in seen:
                    urls.append((song['link'], 'weekly', '0.6'))
                    seen.add(song['link'])
        except Exception:
            pass  # 爬虫失败：仅返回静态 URL
        cache.set(SITEMAP_CACHE_KEY, urls, SITEMAP_CACHE_TTL)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, freq, prio in urls:
        loc = request.build_absolute_uri(path)
        lines.append(f'  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
    lines.append('</urlset>')
    return HttpResponse('\n'.join(lines), content_type='application/xml')
