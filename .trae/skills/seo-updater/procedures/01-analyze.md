# 阶段1:分析 (analyze)

目标:摸清站点现状,为方案设计提供依据。**本阶段只读不改。**

## 1.1 站点主题分析(用于 SEO 词库)
- 抓取首页 `<title>` / 顶部导航 / 页面主体内容,提炼站点主题与核心产品名
- 示例:向日葵远程控制软件 → 主题词"向日葵远程"
- 记录 3~5 个热门大词候选 + 10 个以上长尾词候选方向

## 1.2 路由清单(用于 sitemap)
- 阅读项目 `urls.py`,列出全部 URL pattern:类型(列表页/详情页/专题页/静态页)
- 区分:单数页(首页/关于/专题地图) vs 复数页(列表分页/详情 id 序列)
- 详情页的 id 范围来源需确认(见 1.4)

## 1.3 模板与 SEO 现状
- 列出全部模板文件(含公共 header/footer),确认:
  - `<title>` / `<meta name="keywords">` / `<meta name="description">` 是否已由 `{{ seo.* }}` 动态输出
  - 外链分布:哪些模板存在 `<a href="http(s)://...">` 外链(指向非本站域名的)
- 本站域名 = 请求 Host(自动识别,无需配置)

## 1.4 数据源分析(用于 sitemap 全量 URL)
- 找站点内容的列表数据源:接口(如 `questions` 分页接口)或 Django 模型
- 确认能否拿到:总条数(recordcount)、每页条数(pagesize)、详情 id 规则
- 评估全量抓取成本,确定缓存策略

## 1.5 小影 API 可用性
- 读取 `.env` 的 `XIAOYING_API_BASE`
- 实际请求 `{XIAOYING_API_BASE}/api/seo/friend_links?status=true`,确认返回 `data.items` 且含 name/url
- 若失败,向用户报告并等待 `.env` 配置正确后再继续

## 1.6 输出
整理为结构化结论,交给阶段2与用户沟通。
