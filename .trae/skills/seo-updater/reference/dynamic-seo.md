# 动态 SEO(title/keywords/description)

## 目标
每个内容页 `<title>` / `<meta name="keywords">` / `<meta name="description">` 由后端动态生成,按站点主题定制,突出核心产品词,兼顾热门大词与长尾词。

## 词库定制(AI 按站点内容生成,不写死)
1. 由阶段1分析的站点主题提炼核心词,示例方向:
   - 热门大词(5 个):如 `向日葵远程` / `向日葵远程下载` / `向日葵下载` / `向日葵远程安装` / `向日葵官网`
   - 长尾词(10+ 个):带场景/用途/疑问的修饰组合,如 `向日葵远程控制电脑软件下载`、`手机远程控制电脑用什么软件`
2. 词库须与当前站点内容真实相关,杜绝无关堆砌

## 生成规则
```python
SEO_HOT_WORDS      = [...]   # 5 个热门大词
SEO_LONG_TAIL_WORDS = [...]  # 10+ 个长尾词

def _mix_words():
    # 热词与长尾词交错排序,热词优先:
    # 输出顺序 = 热词1, 长尾1, 热词2, 长尾2, ...(不足时热词排前)

def build_seo(page_type, subject, original=None):
    # subject: 当前页面主题(如"向日葵新闻资讯")
    # original: 可选,原站抓取的 SEO(若有,与本地词库合并去重后再交错)
    # 返回 {'title': ..., 'keywords': ..., 'description': ...}
```
- title:`{subject} - {核心词...}` 形式,突出主题与核心大词
- keywords:交错排序后的词列表(逗号分隔),热门大词排前
- description:围绕 subject 与核心词写 1~2 句自然描述,含 2~3 个核心词
- 若爬虫可抓原站 SEO,则抓取后与本地词库合并去重再交错排序(更贴近原站权重)

## 模板接入
所有内容页模板改为:
```html
<title>{{ seo.title }}</title>
<meta name="keywords" content="{{ seo.keywords }}">
<meta name="description" content="{{ seo.description }}">
```
所有视图在 render 上下文补 `'seo': build_seo(...)`,页面类型与主题按实际情况传参。

## 验证要点
- 各类型页面(首页/列表/详情/专题)源码中 title/keywords/description 均动态输出
- keywords 含核心热门大词,且热词+长尾词交错
