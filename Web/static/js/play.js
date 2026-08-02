// ===== $.lrc 歌词同步滚动插件（改造自源站插件，核心改动见下）=====
// 原版用 marginTop 负值强制滚动歌词列表，与用户手动滚动冲突（播放过的歌词无法回看）；
// 现改为容器 scrollTop 滚动 + 用户滚动时暂停自动跟随（停止滚动 3 秒后恢复），
// 并为每句歌词注入 data-t 时间戳，支持点击歌词跳转播放到对应时间。
(function($) {
    var geciTimer = null;
    // 监听用户滚动歌词区（滚轮/触摸），滚动期间暂停自动跟随
    function bindUserScroll() {
        var box = document.getElementById('play_geci');
        if (!box || box.__lrcBound) return;
        box.__lrcBound = true;
        var mark = function() {
            $.lrc.userScrolling = true;
            clearTimeout(geciTimer);
            geciTimer = setTimeout(function() { $.lrc.userScrolling = false; }, 3000);
        };
        box.addEventListener('wheel', mark, { passive: true });
        box.addEventListener('touchstart', mark, { passive: true });
        box.addEventListener('touchmove', mark, { passive: true });
    }
    $.lrc = {
        handle: null, list: [], callback: null, interval: 0.3,
        prefixid: 'lrc', hoverClass: 'hover', hoverTop: 34,
        pivot: -1, userScrolling: false,
        // 解析 lrc 文本并渲染歌词；cb 为回调，返回当前播放秒数
        start: function(text, cb) {
            if (typeof text != 'string' || text.length < 1 || typeof cb != 'function') return;
            this.stop();
            this.callback = cb;
            this.list = [];
            var re = /^[^\[]*((?:\s*\[\d+:\d+(?:\.\d+)?\])+)([\s\S]*)$/;
            var reT = /\[(\d+):((?:\d+)(?:\.\d+)?)\]/g;
            text.split('\n').forEach(function(line) {
                line = line.replace(/^\s+|\s+$/g, '');
                if (!line) return;
                var m = re.exec(line);
                if (!m) return;
                var tm;
                reT.lastIndex = 0;
                while ((tm = reT.exec(m[1]))) {
                    this.list.push([parseFloat(tm[1]) * 60 + parseFloat(tm[2]), m[2]]);
                }
            }, this);
            var ul = $('#' + this.prefixid + '_list');
            if (this.list.length > 0) {
                this.list.sort(function(x, y) { return x[0] - y[0]; });
                if (this.list[0][0] >= 0.1) this.list.unshift([this.list[0][0] - 0.1, '']);
                this.list.push([this.list[this.list.length - 1][0] + 1, '']);
                var html = '';
                for (var i = 0; i < this.list.length; i++) {
                    html += '<li data-t="' + this.list[i][0] + '">' + this.list[i][1] + '</li>';
                }
                ul.html(html).show();
                $('#lrc_nofound').hide();
                $('#play_geci').show();
                $('#lrc_content').hide();
                this.pivot = -1;
                bindUserScroll();
                this.handle = setInterval('$.lrc.jump($.lrc.callback());', this.interval * 1000);
            } else {
                ul.hide();
                $('#lrc_nofound').show();
                $('#play_geci').hide();
                $('#lrc_content').show();
            }
        },
        // 根据当前播放秒数滚动并高亮对应歌词
        jump: function(e) {
            if (typeof this.handle != 'number' || typeof e != 'number' || this.list.length < 1) return this.stop();
            if (e < 0) e = 0;
            e += 0.2 + this.interval;
            // 二分查找当前时间对应的歌词索引
            var lo = 0, hi = this.list.length - 1, pivot = 0;
            while (lo <= hi) {
                var mid = (lo + hi) >> 1;
                if (this.list[mid][0] <= e) { pivot = mid; lo = mid + 1; }
                else hi = mid - 1;
            }
            if (pivot == this.pivot) return;
            this.pivot = pivot;
            var li = $('#' + this.prefixid + '_list').children().removeClass(this.hoverClass).eq(pivot).addClass(this.hoverClass);
            if (this.userScrolling) return; // 用户手动滚动查看时暂停自动滚动
            var box = document.getElementById('play_geci');
            if (!box) return;
            // 容器 scrollTop 定位到当前句（距可视区顶部 hoverTop 像素）
            var target = li.offset().top - li.parent().offset().top - this.hoverTop;
            if (target < 0) target = 0;
            box.scrollTop = target;
        },
        stop: function() {
            if (typeof this.handle == 'number') clearInterval(this.handle);
            this.handle = this.callback = null;
            this.pivot = -1;
            this.list = [];
        }
    };
    // 点击歌词跳转播放到对应时间（并恢复自动跟随）
    $(document).on('click', '#lrc_list li', function() {
        var t = parseFloat($(this).attr('data-t'));
        if (!isNaN(t) && t >= 0) {
            $.lrc.userScrolling = false;
            $('#player').jPlayer('play', t);
        }
    });
})(jQuery);

// 预初始化 layer 模块（common.js 搜索提示等依赖 window.layer）
layui.use(['layer'], function(){ window.layer = layui.layer; });

// ===== jPlayer 播放器初始化（改造自源站 player()，直接用后端已解密的播放链接，无需前端调 play.php）=====
function initPlayer(playUrl, coverUrl, lrcText) {
    var time = 0;
    // 播放链接缺失：仅展示封面与失败提示，不初始化 jPlayer
    if (!playUrl) {
        $(".djpic").html('<img class="rotate" id="mcover" src="' + coverUrl + '"/><div class="state"><span>播放链接获取失败</span></div>');
        return;
    }
    // 播放状态事件：更新旋转封面图与状态文字
    $("#player").bind($.jPlayer.event.pause, function() {
        $(".djpic").html('<img class="rotate" id="mcover" src="' + coverUrl + '"/><div class="state"><span>已暂停</span></div>');
        $("#mcover").css("animation-play-state", "paused");
    });
    $("#player").bind($.jPlayer.event.waiting, function() {
        $(".djpic").html('<img class="rotate" id="mcover" src="' + coverUrl + '"/><div class="state"><span>加载中</span></div>');
    });
    $("#player").bind($.jPlayer.event.playing, function() {
        $(".djpic").html('<img class="rotate" id="mcover" src="' + coverUrl + '"/><div class="state"><span class="play">播放中</span></div>');
        $("#mcover").css("animation-play-state", "running");
    });
    $("#player").jPlayer({
        ready: function() {
            $(this).jPlayer("setMedia", { mp3: playUrl });
            $(this).jPlayer("volume", 25);
            // 浏览器自动播放策略：用户未交互前 play() 会被拒绝(NotAllowedError)，
            // 监听首次交互后再播放，用户点任意位置/按键即开始
            var tryPlay = function() { $("#player").jPlayer("play"); };
            ['click', 'keydown', 'touchstart'].forEach(function(evt) {
                document.addEventListener(evt, tryPlay, { once: true });
            });
        },
        timeupdate: function(event) { time = event.jPlayer.status.currentTime; },
        play: function() {
            if (lrcText) { setTimeout(function() { $.lrc.start(lrcText, function(){ return time; }); }, 300); }
        },
        ended: function() { $(this).jPlayer("play"); },
        swfPath: "/static/js",
        solution: "html, flash",
        supplied: "m4a,mp3",
        wmode: "window"
    });
}
