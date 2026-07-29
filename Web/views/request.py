from django.shortcuts import render

from SpiderServices.Music_2t58.main import Music2t58Spider


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
    return render(request, 'song.html', data)


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
            'title': '新歌榜',
            'songs': [],
            'pagination': {'links': []},
            'hot_rankings': [],
        }
    return render(request, 'new_songs.html', data)


def singer_list(request, area='index', gender='index', style='index', letter='index', page=1):
    # 歌手列表页：area/gender/style/letter 为分类标识，page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_singer_list(area, gender, style, letter, page)
    except Exception:
        data = {
            'title': '歌手列表',
            'singers': [],
            'filters': [],
            'pagination': {'links': []},
        }
    return render(request, 'singer_list.html', data)


def playtype_list(request, playtype='index', page=1):
    # 歌单列表页：playtype 为分类标识（如 dj、huayu），page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_playtype_list(playtype, page)
    except Exception:
        data = {
            'title': '歌单列表',
            'total': '',
            'playlists': [],
            'filters': [],
            'pagination': {'links': []},
        }
    return render(request, 'playtype_list.html', data)


def mvlist(request, mvtype='index', page=1):
    # MV列表页：mvtype 为分类标识（如 huayu、rihan），page 为页码（路径参数）
    try:
        data = Music2t58Spider().fetch_mvlist(mvtype, page)
    except Exception:
        data = {
            'title': 'MV视频列表',
            'total': '',
            'videos': [],
            'filters': [],
            'pagination': {'links': []},
        }
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


def error_404(request, exception=None):
    """404 错误页：访问不存在的路径或文件时返回（DEBUG=False 时生效）"""
    return render(request, '404.html', status=404)


def error_500(request, exception=None):
    """500 错误页：服务器内部错误时返回（DEBUG=False 时生效）"""
    return render(request, '500.html', status=500)
