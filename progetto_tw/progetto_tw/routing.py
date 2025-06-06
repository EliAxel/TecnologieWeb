from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/search/$', consumers.SearchConsumer.as_asgi()),
    re_path(r'ws/tags/$', consumers.SearchTags.as_asgi()),
    re_path(r'ws/notifications/$',consumers.GetNotifications.as_asgi())
]