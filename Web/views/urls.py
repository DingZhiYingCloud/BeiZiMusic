# 项目URL配置
from django.urls import path, include

from Web.views import request

urlpatterns = [
    path('', request.index, name='home'),
    path('index/', request.index, name='index'),
    path('singer/<sid>.html', request.singer, name='singer'),
    path('singer/<sid>/<int:page>.html', request.singer, name='singer_page'),
    path('song/<sid>.html', request.song, name='song'),
    path('so/<str:keyword>.html', request.search, name='search'),
    path('so/<str:keyword>/<int:page>.html', request.search, name='search_page'),
    path('list/<str:chart>.html', request.chart, name='chart'),
    path('list/<str:chart>/<int:page>.html', request.chart, name='chart_page'),
    path('singerlist/<str:area>/<str:gender>/<str:style>/<str:letter>.html', request.singer_list, name='singer_list'),
    path('singerlist/<str:area>/<str:gender>/<str:style>/<str:letter>/<int:page>.html', request.singer_list, name='singer_list_page'),
    path('playtype/<str:playtype>.html', request.playtype_list, name='playtype_list'),
    path('playtype/<str:playtype>/<int:page>.html', request.playtype_list, name='playtype_list_page'),
    path('mvlist/<str:mvtype>.html', request.mvlist, name='mvlist'),
    path('mvlist/<str:mvtype>/<int:page>.html', request.mvlist, name='mvlist_page'),
    path('video/<sid>.html', request.video, name='video'),
    path('playlist/<sid>.html', request.playlist, name='playlist'),
    path('playlist/<sid>/<int:page>.html', request.playlist, name='playlist_page'),
]