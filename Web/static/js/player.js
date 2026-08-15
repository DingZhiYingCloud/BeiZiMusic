/* ============ 全局底部悬浮播放条（网易云 m-playbar 风格） ============
 * 单一 jPlayer 实例挂载于 #m-playbar-player，由本文件统一管理：
 *   - 待播放列表：点歌曲旁 ＋ 手动加歌（不入队自动播放），存 localStorage(bz_queue)
 *   - 我的喜欢：♥ 收藏，存 localStorage(bz_likes)，播放条面板内可直接播放
 *   - 播放模式：列表循环 / 随机播放 / 单曲循环，存 localStorage(bz_mode)
 *   - 切歌：调 /api/song/<sid>.json 无刷新拉取播放链接/歌词/封面
 *   - 歌曲详情页(song.html)：window.BZ_PAGE_SONG 提供本页歌曲完整数据，
 *     播放该歌曲时由本文件接管页面封面旋转/状态与歌词同步（依赖 play.js 的 $.lrc）
 */
(function ($) {
    'use strict';

    /* 浏览器拦截自动播放时，jPlayer 内部 media.play() 的 Promise 会 reject 且无人 catch。
       这里接管该异常：吞掉避免控制台 Uncaught，并立即对"自动续播被拦截"做兜底（切回待播放状态+提示）。
       放在 catch 内处理与时序无关：无论媒体何时加载完成、何时被拒，都能可靠兜底。 */
    var _mediaPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
        var p = _mediaPlay.apply(this, arguments);
        if (p && typeof p.catch === 'function') {
            p.catch(function (e) {
                if (e && e.name === 'NotAllowedError' && state.autoResume) {
                    state.autoResume = false;
                    state.playing = false;
                    write(KEY.playing, false);
                    $('#m-playbar-player').jPlayer('pause');
                    renderBar();
                    toast('已恢复歌曲，浏览器拦截自动播放，点击播放按钮继续');
                }
            });
        }
        return p;
    };

    /* ---------- 轻提示（不依赖 layer，全站可用） ---------- */
    var toastTimer = null;
    function toast(msg) {
        var $t = $('#bz-toast');
        if (!$t.length) $t = $('<div id="bz-toast"></div>').appendTo('body');
        $t.text(msg).addClass('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { $t.removeClass('show'); }, 1600);
    }

    /* ---------- localStorage 读写 ---------- */
    var KEY = {
        queue: 'bz_queue', likes: 'bz_likes', mode: 'bz_mode',
        current: 'bz_current', volume: 'bz_volume', muted: 'bz_muted',
        progress: 'bz_progress', rate: 'bz_rate',
        playing: 'bz_playing'           // 上次离开时是否正在播放（刷新后决定是否自动续播）
    };
    function read(key, def) {
        try {
            var v = JSON.parse(localStorage.getItem(key));
            return (v === null || v === undefined) ? def : v;
        } catch (e) { return def; }
    }
    function write(key, val) {
        try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* 隐私模式等忽略 */ }
    }

    /* ---------- 全局状态 ---------- */
    var state = {
        queue: read(KEY.queue, []),            // [{sid, name, artists:[], cover:''}]
        likes: read(KEY.likes, []),            // 同上
        mode: read(KEY.mode, 'list'),          // list 列表循环 / random 随机 / single 单曲循环
        current: null,                         // {sid, source:'queue'|'likes', name, artists:[], cover:''}
        curMediaSid: null,                     // 已 setMedia 的 sid
        volume: read(KEY.volume, 80),
        muted: read(KEY.muted, false),
        playing: false,
        curTime: 0,
        loading: false,
        lrcStarted: false,
        tab: 'queue',
        rate: read(KEY.rate, 1),         // 倍速：1 / 1.25 / 1.5 / 2
        pendingSeek: null,               // 记忆续播：{sid, time}，媒体加载完成后 seek
        autoResume: false                // 自动续播中（刷新后自动播放），play 事件触发后清除
    };

    /* ---------- 工具 ---------- */
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    // 列表标题形如 "歌手1&歌手2 - 歌名"，拆分出歌名与歌手数组
    function parseTitle(title) {
        title = title || '';
        var i = title.indexOf(' - ');
        if (i > -1) {
            return {
                name: title.slice(i + 3).trim(),
                artists: title.slice(0, i).split('&').map(function (s) { return s.trim(); }).filter(Boolean)
            };
        }
        return { name: title.trim(), artists: [] };
    }
    function indexOfSid(list, sid) {
        for (var i = 0; i < list.length; i++) if (list[i].sid === sid) return i;
        return -1;
    }
    function getSourceList(source) { return source === 'likes' ? state.likes : state.queue; }
    // 应用倍速到 jPlayer 媒体元素（setMedia/切歌后需重新应用）
    function applyRate() {
        var el = $('#m-playbar-player audio, #m-playbar-player video').first();
        if (el.length) { try { el.prop('playbackRate', state.rate); } catch (e) { } }
    }
    // 保存当前播放进度（记忆续播用），由 timeupdate 节流调用；进度为 0（尚未真正播放）时不覆盖已有记录
    var lastProgSave = 0;
    function saveProgress() {
        if (!state.current || !(state.curTime > 0)) return;
        write(KEY.progress, { sid: state.current.sid, time: state.curTime });
    }
    function pageSong() { return window.BZ_PAGE_SONG || null; }

    /* ---------- 持久化 ---------- */
    function saveState() {
        write(KEY.queue, state.queue);
        write(KEY.likes, state.likes);
        write(KEY.mode, state.mode);
        write(KEY.current, state.current ? { sid: state.current.sid, source: state.current.source } : null);
        write(KEY.volume, state.volume);
        write(KEY.muted, state.muted);
        write(KEY.rate, state.rate);
    }

    /* ---------- DOM 引用 ---------- */
    var $bar, els = {};

    /* ---------- 渲染：播放条 ---------- */
    function renderBar() {
        var cur = state.current;
        els.name.text(state.loading ? '加载中...' : (cur ? cur.name : '暂无播放任务'));
        els.name.attr('title', cur ? (cur.artists && cur.artists.length ? cur.name + ' - ' + cur.artists.join('/') : cur.name) : '');
        els.name.attr('href', cur ? '/song/' + cur.sid + '.html' : 'javascript:;');
        els.artist.text(cur ? (cur.artists || []).join('/') : '');
        els.cover.css('display', cur && cur.cover ? '' : 'none');
        if (cur && cur.cover) els.cover.attr('src', cur.cover);
        els.like.toggleClass('on', !!(cur && indexOfSid(state.likes, cur.sid) > -1));
        els.like.find('i').attr('class', (cur && indexOfSid(state.likes, cur.sid) > -1) ? 'fa fa-heart' : 'fa fa-heart-o');
        $bar.toggleClass('playing', state.playing).attr('data-mode', state.mode);
        renderModeBtn();
        renderRateBtn();
        renderPlaylist();
    }

    function renderModeBtn() {
        var cfg = {
            list: { cls: 'fa fa-repeat', title: '列表循环' },
            random: { cls: 'fa fa-random', title: '随机播放' },
            single: { cls: 'fa fa-repeat', title: '单曲循环' }
        }[state.mode] || { cls: 'fa fa-repeat', title: '列表循环' };
        els.mode.find('i').attr('class', cfg.cls);
        els.mode.attr('title', cfg.title);
    }

    function renderRateBtn() {
        if (!els.rate) return;
        els.rate.text(state.rate === 1 ? '1x' : state.rate + 'x');
        // 非 1x 时高亮，提示当前已开启倍速
        els.rate.toggleClass('on', state.rate !== 1);
    }

    /* ---------- 渲染：待播放列表面板 ---------- */
    function renderPlaylist() {
        els.tabs.removeClass('active').filter('[data-tab="' + state.tab + '"]').addClass('active');
        var list = state.tab === 'likes' ? state.likes : state.queue;
        if (!list.length) {
            els.body.html('<div class="m-pl-empty">' + (state.tab === 'likes' ? '还没有喜欢的歌曲，点歌曲旁的 ♥ 收藏吧' : '待播放列表还是空的，去点歌曲旁的 ＋ 加入') + '</div>');
            return;
        }
        var html = '';
        for (var i = 0; i < list.length; i++) {
            var s = list[i];
            var artist = (s.artists || []).join('/');
            var playing = !!(state.current && state.current.sid === s.sid);
            html += '<div class="m-pl-item' + (playing ? ' playing' : '') + '" data-sid="' + esc(s.sid) + '" data-source="' + state.tab + '">'
                + '<span class="m-pl-cover">' + (s.cover ? '<img src="' + esc(s.cover) + '">' : '<i class="fa fa-music"></i>') + '</span>'
                + '<span class="m-pl-name">' + esc(s.name)
                + (artist ? ' <em class="m-pl-artist">' + esc(artist) + '</em>' : '') + '</span>'
                + '<a href="javascript:;" class="m-pl-del" title="' + (state.tab === 'likes' ? '取消喜欢' : '移除') + '"><i class="fa fa-times"></i></a>'
                + '</div>';
        }
        els.body.html(html);
    }

    /* ---------- 歌曲详情页（song.html）封面/歌词同步 ---------- */
    function isPageSongCurrent() {
        var ps = pageSong();
        return !!(ps && state.current && ps.sid === state.current.sid);
    }
    function syncPageView() {
        var ps = pageSong();
        if (!ps) return;
        var $cover = $('#mcover');
        var $state = $cover.closest('.djpic').find('.state span');
        if ($state.length) {
            if (state.loading) $state.text('加载中');
            else if (state.playing) $state.text('播放中').addClass('play');
            else $state.text('已暂停').removeClass('play');
        }
        $cover.css('animation-play-state', state.playing ? 'running' : 'paused');
        if (isPageSongCurrent()) {
            // 歌词首次加载时启动同步（切歌时 lrcStarted 已被重置）
            if ($.lrc && ps.lyrics && !state.lrcStarted) {
                $.lrc.start(ps.lyrics, function () { return state.curTime; });
                state.lrcStarted = true;
            }
        } else if ($.lrc) {
            $.lrc.stop();
        }
    }

    /* ---------- 数据拉取：优先本页数据，其次 JSON 接口 ---------- */
    function ensureSong(sid) {
        var ps = pageSong();
        if (ps && ps.sid === sid && ps.play_url) {
            return $.Deferred().resolve({
                sid: ps.sid, name: ps.name,
                artists: ps.artists ? String(ps.artists).split('/') : [],
                cover: ps.cover || '', play_url: ps.play_url, lyrics: ps.lyrics || ''
            }).promise();
        }
        return $.getJSON('/api/song/' + encodeURIComponent(sid) + '.json').then(function (d) {
            return {
                sid: d.sid, name: d.name, artists: d.artists || [],
                cover: d.cover || '', play_url: d.play_url || '', lyrics: d.lyrics || ''
            };
        });
    }

    /* ---------- 播放核心 ---------- */
    function setCurrent(song) {
        state.current = {
            sid: song.sid, source: song.source || 'queue',
            name: song.name, artists: song.artists || [], cover: song.cover || ''
        };
        saveState();
        renderBar();
    }

    function playSong(sid, source) {
        // 同一首歌且媒体已加载：直接播放/继续
        if (state.current && state.current.sid === sid && state.curMediaSid === sid) {
            $('#m-playbar-player').jPlayer('play');
            return;
        }
        // 手动切到别的新歌时，取消遗留的记忆续播进度
        if (state.pendingSeek && state.pendingSeek.sid !== sid) state.pendingSeek = null;
        var list = getSourceList(source);
        var entry = indexOfSid(list, sid) > -1 ? list[indexOfSid(list, sid)] : null;
        state.loading = true;
        state.lrcStarted = false;
        renderBar();
        ensureSong(sid).done(function (full) {
            state.loading = false;
            if (entry) {   // 用真实数据补全队列/喜欢条目（封面/歌名/歌手）
                entry.name = full.name || entry.name;
                if (full.artists && full.artists.length) entry.artists = full.artists;
                if (full.cover) entry.cover = full.cover;
                saveState();
            }
            setCurrent({ sid: sid, source: source, name: full.name, artists: full.artists, cover: full.cover });
            state.curMediaSid = sid;
            $('#m-playbar-player').jPlayer('setMedia', { mp3: full.play_url }).jPlayer('play');
            applyRate();
        }).fail(function () {
            state.loading = false;
            toast('播放链接获取失败，请稍后重试');
            renderBar();
        });
    }

    /* ---------- 上一首 / 下一首 / 播放结束 ---------- */
    function playNext(auto) {
        var source = state.current ? state.current.source : 'queue';
        var list = getSourceList(source);
        if (!list.length) return;
        var pos = state.current ? indexOfSid(list, state.current.sid) : -1;
        var next;
        if (auto && state.mode === 'single') next = pos;            // 单曲循环：重播当前
        else if (state.mode === 'random') {                          // 随机
            next = Math.floor(Math.random() * list.length);
            if (list.length > 1 && next === pos) next = (next + 1) % list.length;
        } else next = (pos + 1) % list.length;                       // 列表循环
        playSong(list[next].sid, source);
    }
    function playPrev() {
        var source = state.current ? state.current.source : 'queue';
        var list = getSourceList(source);
        if (!list.length) return;
        var pos = state.current ? indexOfSid(list, state.current.sid) : 0;
        playSong(list[(pos - 1 + list.length) % list.length].sid, source);
    }

    /* ---------- 加歌 / 喜欢 ---------- */
    function addToQueue(song, silent) {
        if (indexOfSid(state.queue, song.sid) > -1) {
            if (!silent) toast('已在播放列表中');
            return;
        }
        var parsed = song.title ? parseTitle(song.title) : {};
        state.queue.push({
            sid: song.sid,
            name: song.name || parsed.name || song.sid,
            artists: song.artists || parsed.artists || [],
            cover: song.cover || ''
        });
        saveState();
        if (!silent) toast('已加入播放列表');
        renderPlaylist();
    }

    function toggleLike(song) {
        var i = indexOfSid(state.likes, song.sid);
        if (i > -1) {
            state.likes.splice(i, 1);
            toast('已取消喜欢');
        } else {
            var parsed = song.title ? parseTitle(song.title) : {};
            state.likes.push({
                sid: song.sid,
                name: song.name || parsed.name || song.sid,
                artists: song.artists || parsed.artists || [],
                cover: song.cover || ''
            });
            toast('已加入我的喜欢');
        }
        saveState();
        renderBar();
        refreshLikeBadges();
    }

    // 从按钮所在 li 解析 sid/标题（列表按钮无 data-sid，从歌曲链接提取）
    function resolveSong($el) {
        var sid = $el.data('sid');
        var title = $el.data('title');
        if (!sid) {
            var $li = $el.closest('li');
            var $link = $li.length ? $li.find('a[href*="/song/"]').first() : null;
            var m = $link && $link.length ? ($link.attr('href') || '').match(/\/song\/([^/]+)\.html/) : null;
            if (m) sid = m[1];
            if (!title && $link && $link.length) {
                title = $link.attr('title') || $link.text() || '';
            }
        }
        if (!sid) return null;
        return { sid: sid, title: title ? title.trim() : '' };
    }

    // 刷新页面所有 ♥ 按钮的喜欢态（列表 + 歌曲页）
    function refreshLikeBadges() {
        $('.bz-like').each(function () {
            var song = resolveSong($(this));
            if (!song) return;
            var on = indexOfSid(state.likes, song.sid) > -1;
            $(this).toggleClass('liked', on);
            $(this).find('i').attr('class', on ? 'fa fa-heart' : 'fa fa-heart-o');
        });
    }

    /* ---------- jPlayer 初始化 ---------- */
    function initJPlayer() {
        if (!$.jPlayer) return;
        $('#m-playbar-player').jPlayer({
            ready: function () {
                $(this).jPlayer('volume', state.volume);
                if (state.muted) $(this).jPlayer('mute', true);
            },
            timeupdate: function (e) {
                state.curTime = e.jPlayer.status.currentTime;
                var now = Date.now();
                if (now - lastProgSave > 5000) { saveProgress(); lastProgSave = now; }
            },
            loadedmetadata: function () {
                applyRate();
            },
            volumechange: function (e) {
                var st = e.jPlayer.status;
                state.volume = Math.round(st.volume * 100);
                state.muted = st.muted;
                saveState();
            },
            play: function () {
                state.playing = true;
                state.autoResume = false;   // 真正开始播放，自动续播流程结束
                write(KEY.playing, true);   // 标记"离开时正在播放"，供刷新后自动续播判定
                applyRate();
                // 记忆续播：仅当恢复的当前歌与保存进度匹配时 seek（手动切歌时 pendingSeek 已被清除）
                // 注：CDN 流式播放时 jPlayer status.duration 可能为空，故直接操作媒体元素 currentTime
                if (state.pendingSeek && state.pendingSeek.sid === (state.current && state.current.sid)) {
                    var t = state.pendingSeek.time;
                    state.pendingSeek = null;
                    var el = $('#m-playbar-player audio, #m-playbar-player video').first();
                    if (el.length) {
                        var ad = el[0].duration;
                        if (!isFinite(ad) || ad === 0 || t < ad - 3) {
                            try { el[0].currentTime = t; } catch (e) { }
                        }
                    }
                }
                renderBar();
                syncPageView();
            },
            pause: function () {
                state.playing = false;
                write(KEY.playing, false);  // 暂停即标记为"未在播放"，刷新后不自动续播
                saveProgress();
                lastProgSave = Date.now();
                renderBar();
                syncPageView();
            },
            ended: function () { playNext(true); },
            swfPath: '/static/js',
            supplied: 'm4a,mp3',
            wmode: 'window',
            cssSelectorAncestor: '#m-playbar'
        });
    }

    /* ---------- 初始化 ---------- */
    $(function () {
        $bar = $('#m-playbar');
        if (!$bar.length) return;
        els.name = $('#m-song-name');
        els.artist = $('#m-song-artist');
        els.cover = $('#m-cover');
        els.like = $('#m-btn-like');
        els.mode = $('#m-btn-mode');
        els.rate = $('#m-btn-rate');
        els.tabs = $('.m-tab', $('#m-playlist'));
        els.body = $('#m-playlist-body');

        // 恢复上次播放的歌曲（仅元信息，不自动播放）
        var c = read(KEY.current, null);
        if (c && c.sid) {
            var list = getSourceList(c.source === 'likes' ? 'likes' : 'queue');
            var pos = indexOfSid(list, c.sid);
            if (pos > -1) {
                var e = list[pos];
                state.current = { sid: c.sid, source: c.source, name: e.name, artists: e.artists || [], cover: e.cover || '' };
            }
            // 记忆续播：播放进度与恢复的当前歌一致时，播放时从断点继续
            var prog = read(KEY.progress, null);
            if (prog && prog.sid === c.sid && prog.time > 3) {
                state.pendingSeek = { sid: c.sid, time: prog.time };
            }
        }
        renderBar();
        refreshLikeBadges();
        initJPlayer();
        // 离开页面（刷新/关闭/切走）时立即保存进度，保证续播位置精准
        $(window).on('pagehide', saveProgress);

        // 自动续播：刷新前正在播放时，加载完成后自动从断点继续播放（无需再点播放按钮）。
        // 若被浏览器自动播放策略拦截，play() 的 catch 会立即兜底（见文件顶部 play 补丁）
        if (state.current && read(KEY.playing, false) === true) {
            state.autoResume = true;
            playSong(state.current.sid, state.current.source);
        }

        /* --- 播放条控制 --- */
        // 播放：媒体已加载则直接播放；否则优先播放恢复的当前歌曲，其次待播放列表第一首
        $('#m-btn-play').on('click', function (e) {
            e.preventDefault();
            if (state.current && state.curMediaSid === state.current.sid) {
                $('#m-playbar-player').jPlayer('play');
                return;
            }
            var src = state.current ? state.current.source : (state.queue.length ? 'queue' : 'likes');
            var list = getSourceList(src);
            var sid = null;
            if (state.current && indexOfSid(list, state.current.sid) > -1) sid = state.current.sid;
            else if (list.length) sid = list[0].sid;
            if (sid) playSong(sid, src);
        });
        $('#m-btn-prev').on('click', function (e) { e.preventDefault(); playPrev(); });
        $('#m-btn-next').on('click', function (e) { e.preventDefault(); playNext(false); });
        $('#m-btn-mode').on('click', function (e) {
            e.preventDefault();
            state.mode = state.mode === 'list' ? 'random' : (state.mode === 'random' ? 'single' : 'list');
            saveState();
            renderModeBtn();
            $bar.attr('data-mode', state.mode);
        });
        // 倍速：1x → 1.25x → 1.5x → 2x 循环
        els.rate.on('click', function (e) {
            e.preventDefault();
            var rates = [1, 1.25, 1.5, 2];
            var i = rates.indexOf(state.rate);
            state.rate = rates[i < 0 ? 0 : (i + 1) % rates.length];
            saveState();
            renderRateBtn();
            applyRate();
            toast('播放速度 ' + (state.rate === 1 ? '1x' : state.rate + 'x'));
        });
        // 喜欢（播放条 ♥）
        els.like.on('click', function (e) {
            e.preventDefault();
            if (!state.current) { toast('请先添加一首歌曲'); return; }
            toggleLike({ sid: state.current.sid, name: state.current.name, artists: state.current.artists, cover: state.current.cover });
        });
        // 展开/收起播放条
        $('#m-btn-unlock').on('click', function (e) {
            e.preventDefault();
            $bar.toggleClass('m-playbar-unlock');
            $(this).find('i').attr('class', $bar.hasClass('m-playbar-unlock') ? 'fa fa-angle-down' : 'fa fa-angle-up');
        });

        /* --- 待播放列表面板 --- */
        $('#m-btn-list').on('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            $('#m-playlist').toggle();
        });
        $(document).on('click', function (e) {
            if (!$(e.target).closest('#m-playlist, #m-btn-list').length) $('#m-playlist').hide();
        });
        els.tabs.on('click', function () {
            state.tab = $(this).data('tab');
            renderPlaylist();
        });
        $('#m-btn-clear').on('click', function (e) {
            e.preventDefault();
            var list = state.tab === 'likes' ? state.likes : state.queue;
            if (!list.length) return;
            list.length = 0;
            if (state.current && state.tab === state.current.source) {
                state.current = null;
                state.curMediaSid = null;
            }
            saveState();
            renderBar();
            refreshLikeBadges();
            toast(state.tab === 'likes' ? '已清空我的喜欢' : '已清空播放列表');
        });
        els.body.on('click', '.m-pl-item', function (e) {
            var $it = $(this);
            if ($(e.target).closest('.m-pl-del').length) return;
            playSong($it.data('sid'), $it.data('source'));
        });
        els.body.on('click', '.m-pl-del', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var $it = $(this).closest('.m-pl-item');
            var sid = $it.data('sid');
            var isLikes = $it.data('source') === 'likes';
            var list = isLikes ? state.likes : state.queue;
            var i = indexOfSid(list, sid);
            if (i > -1) list.splice(i, 1);
            if (state.current && state.current.sid === sid) {
                state.current = null;
                state.curMediaSid = null;
                $('#m-playbar-player').jPlayer('pause');
            }
            saveState();
            renderBar();
            refreshLikeBadges();
            toast(isLikes ? '已取消喜欢' : '已从播放列表移除');
        });

        /* --- 全站加歌 / 喜欢 / 播放按钮（事件委托，覆盖所有歌曲列表） --- */
        $(document).on('click', '.bz-add', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var song = resolveSong($(this));
            if (song) addToQueue(song);
        });
        $(document).on('click', '.bz-like', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var song = resolveSong($(this));
            if (song) toggleLike(song);
        });
        $(document).on('click', '.bz-play-ico', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var song = resolveSong($(this));
            if (!song) return;
            if (indexOfSid(state.queue, song.sid) === -1) addToQueue(song, true);
            playSong(song.sid, 'queue');
        });
    });

    /* ---------- 对外接口（play.js 歌词点击跳转等） ---------- */
    window.BZPlayer = {
        seek: function (t) {
            if (state.curMediaSid) $('#m-playbar-player').jPlayer('play', t);
        }
    };
})(jQuery);
