---
name: "seo-updater"
description: "Update the Django clone site's SEO: replace all external <a> links with friend links from Xiaoying API via runtime middleware (off by default), generate dynamic title/keywords/description with site-specific hot words, and build sitemap.xml from site data. Invoke when user asks to do a whole-site SEO update, replace external links with friend links, or generate a sitemap after content collection."
---

# 全站 SEO 更新器 (seo-updater)

## 用途
在站点采集(site-collector)完成之后,对 Django 克隆站执行全站 SEO 更新,包含三大模块:
```
① 外链替换 → 全站 <a> 外链运行时替换为小影 API 友情链接(中间件,默认关闭)
② 动态 SEO → title/keywords/description 按站点主题定制热词+长尾词
③ sitemap   → 基于站点数据源自动收集全部 URL 生成 sitemap.xml
```

## 前置条件(实施前必须确认)
- `.env` 中已配置小影 API 基础地址 `XIAOYING_API_BASE`(用户会提供最新地址)
- 站点采集已完成,路由/视图/模板已就绪

## 强制流程(必须全部遵循,严禁跳过沟通直接写代码)
1. **分析** → [procedures/01-analyze.md](procedures/01-analyze.md)
   分析站点:主题/路由/模板/外链分布/数据源/现有 SEO 状态
2. **沟通确认** → [procedures/02-confirm.md](procedures/02-confirm.md)
   输出分析结论 + 实施方案(中间件放置/词库/数据源/URL 列表),**等用户明确确认后再动手**
3. **实施** → [procedures/03-implement.md](procedures/03-implement.md)
   按确认方案实现三大模块(逐一验证)
4. **交付说明**:列出改动文件清单 + `.env` 配置项(开关默认 off)

## 触发场景
- 用户说"对整个网站做 SEO 更新""把全部外部链接替换成友情链接""生成 sitemap"
- site-collector 采集完成后,用户要求接续做全站 SEO

## 实施规范参考(实施时必读)
- 外链替换中间件(小影 API 数据源/替换规则/安全) → [reference/friend-link-replace.md](reference/friend-link-replace.md)
- 动态 SEO 词库与生成规则 → [reference/dynamic-seo.md](reference/dynamic-seo.md)
- sitemap 数据收集与生成规则 → [reference/sitemap.md](reference/sitemap.md)

## 关键原则
- **通用化**:不写死具体站点域名/接口,AI 按当前项目分析后落地(友情链接接口固定为小影 API)
- **服务端渲染**:友情链接必须后端获取并渲染进 HTML,保证搜索引擎直接可见,绝不通过前端 API 请求
- **安全默认**:外链替换开关 `FRIEND_LINK_REPLACE` 默认 off,由用户在 .env 手动开启
- **最小改动**:仅修改与 SEO 更新直接相关的代码,不重构无关代码
- **降级兜底**:小影 API/数据源失败时返回空数据,页面保持可访问
- **尊重现有风格**:遵循项目既有代码风格与命名规范
