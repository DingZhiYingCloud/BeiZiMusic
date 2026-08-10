# 阶段1:分析目标网址

这是强制流程的第一步。分析目标网址,为"沟通确认"阶段准备结论。

## 分析步骤

### 1. 抓取目标页面 HTML
优先用 WebFetch 抓取目标 URL。若被反爬拦截(返回验证页/403/重定向),改用临时脚本探测:

```python
# _tmp_probe.py(分析完即删)
import requests
url = 'https://目标网址'
resp = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...'
}, timeout=10, allow_redirects=False)
print('status:', resp.status_code)
print('len:', len(resp.text))
with open(r'项目根\.tmp_page.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)
```

若需带cookie/验证,参考 [anti-scraping.md](../reference/anti-scraping.md) 的探测流程。

### 2. 判断页面类型
根据页面结构判断:
| 类型 | 特征 | 示例 |
|------|------|------|
| 列表页 | 多个相似条目(li/div循环) + 分类筛选 + 分页 | 歌手列表/歌单列表/MV列表 |
| 详情页 | 单个主体信息 + 关联列表 + 简介 | 歌手详情/歌单详情/MV详情 |
| 搜索页 | 搜索框 + 结果列表 + 分页 | 搜索结果 |
| 榜单页 | 排名列表 + 热门榜单侧栏 | 新歌榜/TOP榜 |
| 首页 | 多板块聚合 | 热门歌手+飙升榜+趋势榜 |

### 3. 分析数据结构(用 XPath)
对抓取的 HTML,确定要提取的字段及其 XPath:
- **列表页**:列表容器(`div.xxx ul li`)、每项的标题/链接/图片
- **详情页**:主体信息容器(`div.xxx_info`)、标题(h1)、图片、简介
- **分页**:分页容器(`div.page`)、链接结构
- **筛选**:筛选区(`div.ilingku_fl`)、标题+选项

记录关键 XPath,后续写 `_parse_xxx` 时用。

### 4. 分析 URL 规则
- **分页规则**:第1页 vs 第N页的URL差异(如 `/list/new.html` vs `/list/new/2.html`)
- **详情链接**:列表项指向详情页的href格式(如 `/song/xxx.html`)
- **分类筛选**:筛选链接的URL参数结构(如 `/singerlist/{area}/{gender}/...`)
- **ID格式**:详情页ID是明文还是加密串(如 `bXdua2Njc3ZobQ`)

### 5. 分析反爬机制
按 [anti-scraping.md](../reference/anti-scraping.md) 的探测流程:
- 无凭证请求 → 看状态码/重定向/验证页特征
- 判断反爬类型(无反爬/表单验证/cookie鉴权/UA检测)
- 记录需要的凭证(如 PHPSESSID)

### 6. 分析视觉结构与资源(克隆必备,两种模式都需要)
为保留原网页视觉呈现与功能完整性,必须分析可克隆的资源与需手动重写的部分:

**6.1 资源清单(可直接下载的)**
- 图片:logo/图标/背景图/占位图 → 记录URL,下载到 `Web/static/images/`
- 字体:图标字体(iconfont/FontAwesome) → 下载字体文件到 `Web/static/fonts/`
- 外部CSS:目标站引用的 .css 文件 → 下载到 `Web/static/css/`
- 外部JS:目标站引用的 .js 文件(如播放器/轮播) → 下载到 `Web/static/js/`
- 前端框架:layui/bootstrap/jQuery → 用CDN或本地引入

**6.2 HTML结构(需手动重写的)**
- 页面DOM层级与关键容器(header/.nav/.main/.play_list/.page 等)
- 关键样式类名及用途
- 公共片段(顶栏/底栏/侧栏)结构

**6.3 CSS样式(需手动重写的)**
- 目标站关键样式(布局/颜色/字体/响应式)
- 内联样式与 `<style>` 块
- 记录无法直接下载的样式,需在 base.css 等价实现

**6.4 JS功能(需手动重写的)**
- 交互逻辑(导航/搜索/播放/轮播/筛选)
- 第三方插件调用
- 记录需手动实现的功能点

**6.5 克隆分类结论**
对每项资源/结构判定处理方式:
- **可直接下载**(图片/字体/外部CSS/JS):下载到本地,清理品牌词/外链
- **需手动重写**(HTML结构/CSS样式/JS功能):按行业标准重写,保持视觉/功能一致

## 输出
分析完成后,整理结论,进入 [02-confirm.md](02-confirm.md) 沟通确认阶段。

⚠️ 分析阶段产生的临时文件(`_tmp_probe.py`、`.tmp_page.html`)在分析完成后必须删除。
