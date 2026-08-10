# 小影 API 友情链接服务
#
# 职责：后端统一拉取小影 API 的友情链接，模块级缓存 1 小时，供全站模板渲染。
# 关键约束：链接必须在服务端抓取并渲染进 HTML（搜索引擎直接可见），
#          绝不通过前端 JS 请求 API（搜索引擎爬虫执行不到 JS，会漏掉链接）。
import os
import threading
import time
import logging

import requests

logger = logging.getLogger(__name__)

# 小影 API 基础地址（用户提供，可写入 .env 覆盖默认值）
API_BASE = os.getenv('XIAOYING_API_BASE', 'https://xiaoyingapi.com')
# 友情链接接口：status=true 只返回启用状态的链接
FRIEND_LINKS_URL = f'{API_BASE}/api/seo/friend_links?status=true'
# 缓存有效期：1 小时（过期后在请求时后台线程静默刷新）
CACHE_TTL = 60 * 60
# 请求超时（秒）
REQUEST_TIMEOUT = 10

# 模块级缓存：links 为 [{name, url}]，fetched_at 为拉取时间戳，fetching 标记后台刷新进行中
_cache = {'links': [], 'fetched_at': 0.0, 'fetching': False}
_lock = threading.Lock()


def _fetch_links():
    """从小影 API 拉取并过滤友情链接（失败返回空列表，页面保持可访问）"""
    try:
        resp = requests.get(FRIEND_LINKS_URL, timeout=REQUEST_TIMEOUT, headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
        })
        resp.raise_for_status()
        items = resp.json().get('data', {}).get('items', []) or []
        links = []
        for item in items:
            name = (item.get('name') or '').strip()
            url = (item.get('url') or '').strip()
            # 过滤规则：名称非空、状态启用、http(s) 链接、url 不含属性注入字符
            if not name or not url:
                continue
            if item.get('status') is False:
                continue
            if not (url.startswith('http://') or url.startswith('https://')):
                continue
            if any(ch in url for ch in '\'"<>'):
                continue
            links.append({'name': name, 'url': url})
        return links
    except Exception:
        logger.exception('拉取小影 API 友情链接失败')
        return []


def _refresh():
    """同步拉取并写入缓存（内部调用，线程安全）"""
    with _lock:
        _cache['fetching'] = True
    try:
        links = _fetch_links()
        with _lock:
            _cache['links'] = links
            _cache['fetched_at'] = time.time()
    finally:
        with _lock:
            _cache['fetching'] = False


def _refresh_in_background():
    """后台线程静默刷新，请求不阻塞"""
    threading.Thread(target=_refresh, daemon=True).start()


def get_friend_links():
    """获取友情链接列表（惰性 + 后台线程刷新）

    首次访问：同步拉取一次，保证首次渲染即有链接；
    缓存过期：后台线程静默刷新，当前请求先用旧缓存，页面永不阻塞。
    """
    with _lock:
        fetched_at = _cache['fetched_at']
        fetching = _cache['fetching']
    if fetched_at == 0:
        _refresh()
    elif time.time() - fetched_at >= CACHE_TTL and not fetching:
        _refresh_in_background()
    with _lock:
        return list(_cache['links'])


def friend_links(request):
    """Django context processor：向全站模板注入 friend_links 变量"""
    return {'friend_links': get_friend_links()}
