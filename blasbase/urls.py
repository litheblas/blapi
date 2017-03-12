from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^api/person/$', PersonList.as_view()),
    url(r'^api/person/(?P<pk>[0-9]+)/$', PersonDetail.as_view()),
]
