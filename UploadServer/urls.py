from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings 

#from filebrowser.sites import site
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'UploadServer.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'home.views.list', name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^status/', 'home.views.status', name='status'), 
    url(r'^incStatus/', 'home.views.incStatus', name='incStatus'), 
    url(r'^modify/', 'home.views.modify', name='modify'), 
        (r'^login/$', 'home.views.Login'),
        (r'^logout/$', 'home.views.Logout'),

        
	url(r'^celery_test/', 'home.views.test_celery'),

    #url(r'^login/authenticate/', 'home.views.Authenticate', name='authenticate'),
)

urlpatterns += patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}))