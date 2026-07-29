// ===== $.lrc 歌词同步滚动插件（提取自源站 play.js，配合 jPlayer timeupdate 驱动高亮滚动）=====
(function(a){a.lrc={handle:null,list:[],regex:/^[^\[]*((?:\s*\[\d+\:\d+(?:\.\d+)?\])+)([\s\S]*)$/,regex_time:/\[(\d+)\:((?:\d+)(?:\.\d+)?)\]/g,regex_trim:/^\s+|\s+$/,callback:null,interval:0.3,format:"<li>{html}</li>",prefixid:"lrc",hoverClass:"hover",hoverTop:30,duration:0,__duration:-1,start:function(b,g){if(typeof(b)!="string"||b.length<1||typeof(g)!="function"){return}this.stop();this.callback=g;var f=null,e=null,d="";b=b.split("\n");for(var c=0;c<b.length;c++){f=b[c].replace(this.regex_trim,"");if(f.length<1||!(f=this.regex.exec(f))){continue}while(e=this.regex_time.exec(f[1])){this.list.push([parseFloat(e[1])*60+parseFloat(e[2]),f[2]])}this.regex_time.lastIndex=0}if(this.list.length>0){this.list.sort(function(i,h){return i[0]-h[0]});if(this.list[0][0]>=0.1){this.list.unshift([this.list[0][0]-0.1,""])}this.list.push([this.list[this.list.length-1][0]+1,""]);for(var c=0;c<this.list.length;c++){d+=this.format.replace(/\{html\}/gi,this.list[c][1])}a("#"+this.prefixid+"_list").html(d).animate({marginTop:0},100).show();a("#"+this.prefixid+"_nofound").hide();this.handle=setInterval("$.lrc.jump($.lrc.callback());",this.interval*1000)}else{a("#"+this.prefixid+"_list").hide();a("#"+this.prefixid+"_nofound").show();a("#play_geci").hide();a("#lrc_content").show()}},jump:function(e){if(typeof(this.handle)!="number"||typeof(e)!="number"||!a.isArray(this.list)||this.list.length<1){return this.stop()}if(e<0){e=0}if(this.__duration==e){return}e+=0.2;this.__duration=e;e+=this.interval;var d=0,b=this.list.length-1,c=b;pivot=Math.floor(b/2),tmpobj=null,tmp=0,thisobj=this;while(d<=pivot&&pivot<=b){if(this.list[pivot][0]<=e&&(pivot==b||e<this.list[pivot+1][0])){break}else{if(this.list[pivot][0]>e){b=pivot}else{d=pivot}}tmp=d+Math.floor((b-d)/2);if(tmp==pivot){break}pivot=tmp}if(pivot==this.pivot){return}this.pivot=pivot;tmpobj=a("#"+this.prefixid+"_list").children().removeClass(this.hoverClass).eq(pivot).addClass(thisobj.hoverClass);tmp=tmpobj.next().offset().top-tmpobj.parent().offset().top-this.hoverTop;tmp=tmp>0?tmp*-1:0;this.animata(tmpobj.parent()[0]).animate({marginTop:tmp+"px"},this.interval*1000)},stop:function(){if(typeof(this.handle)=="number"){clearInterval(this.handle)}this.handle=this.callback=null;this.__duration=-1;this.regex_time.lastIndex=0;this.list=[]},animata:function(c){var d=j=0,g,e={},b=function(h,f,k,i){return-k*(h/=i)*(h-2)+f};e.execution=function(i,m,h){var k=(new Date()).getTime(),l=h||500,f=parseInt(c.style[i])||0,n=m-f;(function(){var o=(new Date()).getTime()-k;if(o>l){o=l;c.style[i]=b(o,f,n,l)+"px";++d==j&&g&&g.apply(c);return true}c.style[i]=b(o,f,n,l)+"px";setTimeout(arguments.callee,10)})()};e.animate=function(f,k,l){g=l;for(var h in f){j++;e.execution(h,parseInt(f[h]),k)}};return e}}})(jQuery);

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
