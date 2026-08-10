# 通用反爬框架

不同站点的反爬机制各异,本框架提供通用处理流程,新站点先探测再适配。

## 爬虫类基础骨架(每个新站点照此结构)

```python
import os
import requests
from lxml import etree
from dotenv import load_dotenv

load_dotenv()


class MovieXxxSpider:
    """xxx.com 站点爬虫

    反爬说明:[在此填写探测结论,如:需要PHPSESSID / 无反爬 / 需要登录等]
    凭证配置:在 .env 中设置 MOVIE_XXX_PHPSESSID(或对应变量)
    """

    HOME_URL = 'https://www.xxx.com/'

    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://www.xxx.com/',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # 注入反爬凭证(按需,从 .env 读取)
        cookie_val = os.getenv('MOVIE_XXX_PHPSESSID', '')
        if cookie_val:
            self.session.cookies.set('PHPSESSID', cookie_val)

    def _get_html(self, url):
        """获取页面 HTML,自动处理编码与人机验证"""
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        # 编码处理:无声明或 ISO-8859-1 时用 chardet 检测
        if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
            resp.encoding = resp.apparent_encoding
        html = resp.text
        # 命中人机验证页时,提交表单通过验证后重新请求
        if 'csrf_token' in html and '安全人机验证' in html:
            html = self._pass_verification(url, html)
        return html

    def _pass_verification(self, url, html):
        """提交人机验证表单(csrf_token + human_check),返回通过后的真实 HTML"""
        tree = etree.HTML(html)
        csrf_nodes = tree.xpath('//input[@name="csrf_token"]')
        if not csrf_nodes:
            return html
        csrf_token = csrf_nodes[0].get('value', '')
        self.session.post(url, data={'csrf_token': csrf_token, 'human_check': 'on'}, timeout=10)
        resp = self.session.get(url, timeout=10)
        if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
            resp.encoding = resp.apparent_encoding
        return resp.text
```

## 反爬探测流程(分析阶段执行)

对目标站先做探测,判断反爬类型,再决定爬虫实现策略:

1. **无凭证直接请求**
   ```python
   resp = requests.get(url, headers={'User-Agent': '标准UA'}, timeout=10, allow_redirects=False)
   ```
2. **判断响应**:
   - **200 + 内容正常**(含目标数据/无验证关键词) → 无反爬,`__init__` 无需注入cookie
   - **200 + 含验证页特征**(`csrf_token` / "安全人机验证" / "人机验证" / "verify") → 表单验证型,实现 `_pass_verification`
   - **302/301 重定向到登录/验证页** → 需要登录态或cookie,在 .env 配置凭证
   - **403/412** → UA/Referer 检测或风控,补全请求头,必要时加cookie
   - **5xx** → 可能IP被限,需延迟/代理(本框架不内置,提示用户)
3. **验证探测**:若疑似验证页,检查 HTML 是否含 `csrf_token` + 验证关键词,确认是否表单验证型

## 各反爬类型适配策略

| 反爬类型 | 探测特征 | 适配方式 |
|---------|---------|---------|
| 无反爬 | 200+正常内容 | 仅设 UA/Referer |
| 表单验证 | 200+csrf_token+验证关键词 | 实现 `_pass_verification`(提交表单) |
| Cookie鉴权 | 302到登录 / 403 | .env 配置cookie,`__init__` 注入 |
| UA检测 | 403 | 补全浏览器UA+Referer |
| 频率限制 | 偶发403/超时 | 加 sleep(本框架提示用户,不内置) |

## .env 凭证配置约定
- 变量名:`<站点名大写>_<凭证类型>`,如 `MOVIE_XXX_PHPSESSID`
- 凭证获取:浏览器登录/通过验证后,从开发者工具 Application→Cookies 复制
- 过期需更新:在爬虫类 docstring 注明"过期需更新"

## 编码处理(易踩坑)
目标站可能不声明编码,requests 默认 ISO-8859-1 导致中文乱码:
```python
if not resp.encoding or resp.encoding.lower() == 'iso-8859-1':
    resp.encoding = resp.apparent_encoding  # chardet 检测
```
务必在 `_get_html` 中处理。
