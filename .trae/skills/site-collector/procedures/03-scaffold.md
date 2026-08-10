# 模式A:框架搭建

**触发**:用户新建 Django 项目后,需要搭建采集框架。
**前置**:已完成 [01-analyze.md](01-analyze.md) 分析 + [02-confirm.md](02-confirm.md) 沟通确认。

## 搭建步骤

### 1. 创建爬虫服务目录与骨架
按 [anti-scraping.md](../reference/anti-scraping.md) 的基础骨架创建:
```
SpiderServices/<站点名>/main.py
```
包含:
- 爬虫类(`<站点名>PascalCaseSpider`)
- `HOME_URL` / `HEADERS` 常量
- `__init__`(session + UA/Referer + cookie注入)
- `_get_html`(请求 + 编码处理 + 验证页检测)
- `_pass_verification`(表单验证,按探测结论决定是否需要)
- `_parse_pagination`(分页解析,通用)
- 类 docstring 注明反爬说明 + 凭证配置

### 2. 确认 Django 项目配置
检查 `项目配置包/settings.py`:
- `INSTALLED_APPS` 含 App 配置(如 `'Web.apps.WebConfig'`)
- `STATIC_ROOT` 指向 `<App>/static`
- `MEDIA_ROOT` 指向 `media`
- `TEMPLATES` 的 `APP_DIRS=True`
- `ROOT_URLCONF` 指向根 urls

检查根 `urls.py`:
- `path('', include('Web.views.urls'))`
- 静态/媒体文件服务(DEBUG=False 时手动 serve)
- `handler404` / `handler500`(可选)

若缺失,按现有项目模板补齐。

### 3. 创建基础模板 template.html
若 `Web/templates/template.html` 不存在,创建之。包含:
- `<head>`:meta(charset/viewport/keywords/description) + CSS引入(base.css/layui/Font Awesome) + JS引入(jQuery/common.js)
- `{% block title/keywords/description/head %}`
- `<body>`:`{% include 'common_html/headers.html' %}` + `{% block content %}` + `{% block js %}`

参考现有项目的 template.html 结构。

### 4. 创建公共片段
- `common_html/headers.html`:顶部导航 + logo + 搜索框
- `common_html/footer.html`:底部移动端导航(用 Font Awesome 图标)
- `common_html/friend_links.html`:友情链接(可选)

### 5. 完整克隆目标站视觉与资源
按 [01-analyze.md](01-analyze.md) 第6步的克隆分类结论执行,目标是保留原网页视觉呈现与功能完整性:

**5.1 下载可自动克隆的资源**
- 图片/logo/背景图 → `Web/static/images/`(清理品牌词/外链,替换为自己的)
- 图标字体 → `Web/static/fonts/`
- 外部 CSS 文件 → `Web/static/css/`
- 外部 JS 文件 → `Web/static/js/`
- 在 template.html 中引入下载的资源
- ⚠️ 清理资源内目标站的域名/品牌词/统计代码/外链,替换为自己的

**5.2 手动重写无法自动克隆的部分**
- **HTML结构**:按原站DOM层级重写 template.html 与公共片段,保持关键容器与类名
- **CSS样式**:在 base.css 中等价实现原站样式(布局/颜色/字体/响应式),保持类名一致
- **JS功能**:重写交互逻辑(导航/搜索/播放等),功能与原站一致

**5.3 手动代码质量标准(必须满足)**
- 符合行业标准:语义化HTML、模块化CSS、无侵入JS
- 可维护性:清晰注释、合理命名、DRY 不重复
- 兼容性:主流浏览器兼容、响应式适配
- 视觉一致:布局/配色/字体/间距与原站一致
- 功能完整:原站的交互行为都要实现,不遗漏

### 6. 配置 .env
在 `.env` 添加反爬凭证占位:
```
# <站点名> 爬虫:[反爬说明]
<站点名大写>_PHPSESSID=
```
告知用户去浏览器获取凭证填入。

### 7. 创建目录占位
确保目录存在:
- `Web/static/css/`、`Web/static/js/`、`Web/static/images/`
- `Web/templates/common_html/`
- `media/`

## 交付说明
框架搭建完成后,向用户输出:
- 创建的目录与文件清单
- .env 需填写的凭证
- 如何启动验证(`python manage.py runserver` 访问首页)
- 提示:框架就绪后,可用模式B逐个新增页面采集功能
