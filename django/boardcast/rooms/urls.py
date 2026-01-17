from django.urls import path
from .views import RoomCreateView, RoomJoinView, IceConfigView

urlpatterns = [
    path("create/", RoomCreateView.as_view()),
    path("join/", RoomJoinView.as_view()),
    path("ice-config/", IceConfigView.as_view()),
]
