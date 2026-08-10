# 阶段3:实施 (implement)

按用户确认的方案实现三大模块。每个模块完成后立即验证,再进入下一模块。

## 3.1 模块一:外链替换中间件
1. 按 [reference/friend-link-replace.md](../reference/friend-link-replace.md) 规范实现:
   - `<app>/middleware.py`:小影 API 拉取 + 缓存 + `<a>` 外链替换(正则/安全规则)
   - `<app>/views.py`(或独立模块):`get_friend_links()` 缓存函数供中间件与 footer 共用
2. 在 `settings.py` 的 `MIDDLEWARE` 注册中间件(放最后)
3. `.env` 新增 `FRIEND_LINK_REPLACE=off`(默认关闭,让用户手动开启)
4. **验证**:临时 `.env=on` + curl/浏览器确认外链已替换、title/锚文本同步、含图链接保持结构;验证后是否恢复 off 由用户决定

## 3.2 模块二:动态 SEO
1. 按 [reference/dynamic-seo.md](../reference/dynamic-seo.md) 规范实现 `build_seo(...)` 与词库(词库按用户确认的草案)
2. 将所有内容页模板的 `<title>/<meta keywords>/<meta description>` 改为 `{{ seo.title }}/{{ seo.keywords }}/{{ seo.description }}`
3. 所有视图渲染上下文补 `seo`
4. **验证**:访问各类型页面,查看源码确认 title/keywords/description 已动态输出且含核心词

## 3.3 模块三:sitemap(离线预生成文件)
1. 按 [reference/sitemap.md](../reference/sitemap.md) 规范实现:
   - `generate_sitemap_file()`:离线爬取全部 URL + 原子写入项目根 `sitemap.xml`(文件内 loc 存相对路径)
   - `sitemap()` 视图:读文件毫秒级返回, 无文件时返回静态降级版; 文件超期则后台线程静默刷新(带锁防并发)
   - 注册管理命令 `<app>/management/commands/generate_sitemap.py`(供部署环境定时任务调用)
2. `urls.py` 注册 `sitemap.xml`
3. **验证**:访问 `/sitemap.xml` 毫秒级返回(不 504)、XML 合法、loc 为绝对地址、含首页与全部详情 URL; 删除文件后访问立即返回降级版且后台自动重新生成

## 3.4 交付说明
向用户输出:
- 改动文件清单(新增/修改)
- `.env` 新增配置项:`XIAOYING_API_BASE`、`FRIEND_LINK_REPLACE`(默认 off 说明)
- 如何开启/关闭外链替换(改 `.env` 后重启或 touch .py 触发重载)
