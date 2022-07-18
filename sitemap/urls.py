from django.urls import path
from .import views

app_name = 'sitemap'

urlpatterns = [
    path('', views.index, name='index'),
    path('map/service/', views.map_service, name='map_service'),
    path('map/gu/', views.map_gu, name='map_gu'),
    path('graph/', views.graph, name='graph'),
    path('map/starbucks/', views.starbucks, name='starbucks'),
]