# sitemap.xml(离线预生成静态文件)

## 目标
动态生成 `sitemap.xml`,收录站点全部可索引 URL(单数页 + 列表分页 + 详情页),供搜索引擎抓取。

## 关键设计:预生成文件,绝不在请求链路中爬取
站点内容来自源站接口,全量收集需几百次请求。若放在请求时实时爬取,首次/缓存过期后的访问会超时(常见 504)。
**改为离线预生成 sitemap.xml 静态文件**:

```
管理命令 generate_sitemap 或 后台刷新线程  ──►  离线爬取全部 URL  ──►  写 sitemap.xml 到项目根
                                                                    │
请求 sitemap.xml ──► 视图直接读文件(毫秒级)  ◄──────────────────────┘
                    文件超期 ──► 后台线程静默重生成, 前台先用旧文件(请求永不阻塞)
```

## URL 收集(基于站点数据源)
1. **单数页**:项目 `urls.py` 中的固定页面(首页等),注意空串要归一为 `/`
2. **复数页**(列表分页 + 详情 id 序列):从站点列表数据源获取全量:
   - 接口型:列表接口返回 `recordcount`(总条数)+ `pagesize`(每页条数),按页遍历拼出全部详情 URL
   - 模型型:查询模型得到全部 id
   - 注意:**详情 id 不一定从 1 开始**,必须以数据源实际返回为准
3. 大数据量时用多线程并发抓取(如 ThreadPoolExecutor)

## 文件内容与绝对地址
- 文件中 `<loc>` 存**相对路径**(如 `/news/57278.html`),视图读取时用 `request.scheme + get_host()` 正则拼接为绝对地址
- 好处:生成不依赖域名,换域名/换环境无需重新生成

## 实现要点
```python
SITEMAP_FILE = os.path.join(settings.BASE_DIR, 'sitemap.xml')  # 生成文件路径
SITEMAP_TTL  = 60 * 60 * 6                                     # 文件有效期 6 小时

def generate_sitemap_file():      # 离线爬取 + 原子写入(临时文件 + os.replace)
def _sitemap_needs_refresh():     # 文件不存在或超期 → 需要刷新
def _spawn_sitemap_refresh():     # 后台线程静默刷新(带锁防并发), 前台不等待
def sitemap(request):             # 视图: 读文件返回; 无文件时返回降级版(仅静态 URL)
```
- 写文件用临时文件 + `os.replace` 原子替换,避免读到半写内容
- 后台刷新线程用模块级锁 + 进行中标志,防止多个请求并发重复生成
- 降级兜底:文件不存在(首次部署)时返回仅静态 URL 的 XML,同时后台线程开始生成
- 注册管理命令:`<app>/management/commands/generate_sitemap.py`,供部署环境定时任务(如每日)刷新

## 路由注册
`urls.py` 增加:`path('sitemap.xml', <sitemap_view>, name='sitemap')`

## 验证要点
- 首次访问 `/sitemap.xml` 毫秒级返回(读文件),不再 504
- XML 合法,`<loc>` 为绝对地址,首页为 `scheme://host/`,新闻首条/末条 id 与数据源一致
- 删除文件后访问:立即返回降级版,后台线程自动重新生成完整文件
- 超期后访问:返回旧文件,后台线程静默刷新
