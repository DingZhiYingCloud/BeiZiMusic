// 拦截搜索表单默认提交，实际搜索逻辑由 jQuery submit 事件处理
function CheckPost() { return false; }

$(document).ready(function() {
	$('.search').on('submit',function() {
		var key = $(".seh_v").val();
		if (key == '') {
			layer.msg('请输入您要搜索的内容！',{icon: 2});
		} else {
			window.open("/so/" + key + '.html', "_so2t");
		}
		return false;
	});
	var tags = $(".tags a");
	tags.each(function(){
		var rand = Math.floor(Math.random()*10);
		$(this).addClass("tag"+rand);
	});
	// 根据当前 URL 高亮导航菜单
	var path = window.location.pathname;
	$('.nav a').removeClass('active');
	$('.nav a').each(function() {
		var href = $(this).attr('href');
		if (href === '/') {
			// 首页：匹配 / 和 /index/
			if (path === '/' || path.indexOf('/index') === 0) $(this).addClass('active');
		} else if (href.indexOf('/singerlist/') === 0 || href.indexOf('/playtype/') === 0 || href.indexOf('/mvlist/') === 0) {
			// 歌手/歌单/MV列表：URL 含可变分类段，仅按首段前缀匹配
			var firstSeg = '/' + href.split('/')[1] + '/';
			if (path.indexOf(firstSeg) === 0) $(this).addClass('active');
		} else {
			// 去掉 .html 后比较前缀，匹配分页等子路径
			var prefix = href.replace(/\.html$/, '');
			if (path.indexOf(prefix) === 0) $(this).addClass('active');
		}
	});
	// 根据当前 URL 高亮底部移动端导航（fed-text-green 为高亮类）
	$('.fed-tabr-info a').removeClass('fed-text-green');
	$('.fed-tabr-info a').each(function() {
		var href = $(this).attr('href');
		if (href === '/') {
			// 首页：匹配 / 和 /index
			if (path === '/' || path.indexOf('/index') === 0) $(this).addClass('fed-text-green');
		} else if (href.indexOf('/list/') === 0) {
			// 排行榜
			if (path.indexOf('/list/') === 0) $(this).addClass('fed-text-green');
		} else if (href.indexOf('/playtype/') === 0) {
			// 歌单列表与详情
			if (path.indexOf('/playtype/') === 0 || path.indexOf('/playlist/') === 0) $(this).addClass('fed-text-green');
		} else if (href.indexOf('/singerlist/') === 0) {
			// 歌手列表与详情
			if (path.indexOf('/singerlist/') === 0 || path.indexOf('/singer/') === 0) $(this).addClass('fed-text-green');
		} else if (href.indexOf('/mvlist/') === 0) {
			// MV列表与详情
			if (path.indexOf('/mvlist/') === 0 || path.indexOf('/video/') === 0) $(this).addClass('fed-text-green');
		}
	});
});