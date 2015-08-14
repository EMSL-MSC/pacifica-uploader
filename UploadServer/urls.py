"""
URLs used by the Django server
used to route to the appropriate view to handle the request
"""

from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings

#from filebrowser.sites import site
admin.autodiscover()

urlpatterns = patterns('',
                       url(r'^$', 'home.views.populate_upload_page', name='home'),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^incStatus', 'home.views.incremental_status', name='incStatus'),
                       url(r'^modify/', 'home.views.modify', name='modify'),
                       url(r'^upload/', 'home.views.upload_files', name='upload'),
                       url(r'^getChildren/', 'home.views.get_children', name='getChildren'),
                       url(r'^cookie/', 'home.views.cookie_test', name='cookie'),
                       (r'^login/$', 'home.views.login'),
                       (r'^logout/$', 'home.views.logout'),)

urlpatterns += patterns('', (r'^media/(?P<path>.*)$', \
    'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}))
