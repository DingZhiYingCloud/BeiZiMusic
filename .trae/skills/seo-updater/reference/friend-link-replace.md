# 外链替换为友情链接(运行时中间件)

## 数据源:小影 API 友情链接
- base 地址:`.env` 的 `XIAOYING_API_BASE`(用户提供最新地址)
- 接口:`{XIAOYING_API_BASE}/api/seo/friend_links?status=true`
- 返回:`data.items` 列表,每项含 `name` / `url` / `status` / `sort`
- 过滤规则:仅接受 `name` 非空、`status` 为启用、`url` 以 `http://` 或 `https://` 开头且不含 `"'<>`(防属性注入)
- 服务端抓取并渲染进 HTML,保证搜索引擎直接可见;**绝不通过前端 API 请求**

## 缓存
- 友情链接列表缓存 1 小时(降低小影 API 压力),供中间件与 footer 共用
- 用 Django cache 或模块级缓存均可,失败时返回空列表,页面保持可访问

## 开关
- `.env` 的 `FRIEND_LINK_REPLACE`,默认 `off`
- 解析:`'on'/'true'/'1'/'yes'` 视为开启,其余关闭
- **模块导入时读取一次**(模块级常量),改 .env 后需重启进程或 touch .py 触发 autoreload

## 中间件逻辑
只处理:状态码 200 且 `Content-Type` 含 `text/html` 的响应。

### 本站域名判定(自动识别)
`request.get_host().split(':')[0].lower()`,无需硬编码(正式环境/本地一致适用)。

### 正则
```python
_A_TAG_RE  = re.compile(r'<a\b[^>]*>.*?</a>', re.IGNORECASE | re.DOTALL)  # 完整 <a>...</a>
_HREF_RE   = re.compile(r'\bhref=(["\'])(.*?)\1', re.IGNORECASE)
_TITLE_RE  = re.compile(r'\btitle=(["\'])(.*?)\1', re.IGNORECASE)
```

### 替换规则(每条外链随机挑一条友情链接)
1. **只处理 `<a>` 标签**;`href` 非 http(s) 的相对链接/锚点跳过;域名等于本站域名跳过
2. **href** → 替换为友情链接 `url`
3. **title** → 已有则替换,否则插入到 `<a>` 标签内;名称需 `html.escape(name, quote=True)` 防注入
4. **锚文本** → 仅当链接内是**纯文本**(无 `<img>/<span>/<svg>` 等子标签,即 `inner.strip() and '<' not in inner`)才替换为网站名;含子标签的链接保持原内容,只换 href+title
5. 每条链接独立随机选一条友情链接,实现每次请求随机分布

### 响应改写
```python
html = response.content.decode('utf-8')
html = _replace_links_in_html(html, links, own_host)
response.content = html.encode('utf-8')
if response.has_header('Content-Length'):
    del response['Content-Length']
```

## 验证要点
- 外链 href 全部变为友情链接 URL(统计数量)
- 纯文本链接出现 `title="网站名">网站名</a>` 模式
- 含 `<img>` 的链接结构完整、仅换 href+title
- 本站相对链接/锚点不动;开关 off 时页面原样
