# pylint: disable=invalid-name
# justification: django

"""
URLs used by the Django server
used to route to the appropriate view to handle the request
"""

from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from django.views.static import serve
import home.views

# from filebrowser.sites import site
admin.autodiscover()
urlpatterns = [
    url(r'^$', home.views.populate_upload_page, name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^incStatus', home.views.incremental_status, name='incStatus'),
    url(r'^showStatus', home.views.show_initial_status, name='showStatus'),
    url(r'^upload/', home.views.upload_files, name='upload'),
    url(r'^postData/', home.views.post_upload_metadata, name='postData'),
    url(r'^setRoot/', home.views.set_data_root, name='setRoot'),
    url(r'^getChildren/', home.views.get_children, name='getChildren'),
    url(r'^getBundle/', home.views.get_bundle, name='getBundle'),
    url(r'^getState/', home.views.get_status, name='getState'),
    url(r'^initializeFields/', home.views.initialize_fields, name='initializeFields'),
    url(r'^selectChanged/', home.views.select_changed, name='selectChanged'),
    url(r'^login/$', home.views.login),
    url(r'^logout/$', home.views.logout),
    url(r'^test/$', home.views.test),
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    url(r'^resources/(?P<path>.*)$', serve, {'document_root': settings.RESOURCES_ROOT})
]
