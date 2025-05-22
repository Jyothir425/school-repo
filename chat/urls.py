from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index_view, name='chat-index'),
    path('create/', views.CreateRoomView.as_view(), name='chat-room'),
]