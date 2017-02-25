from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.sites.models import Site
from django.conf import settings

admin.autodiscover()
admin.site.unregister(Site) # Hide the Sites group of tables in the Admin, by importing, then un-registering it.

urlpatterns = patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),

    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),

    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^lookup/', include('lookup.urls')),

    (r'', include('election.urls')),
    (r'', include('bulkimport.urls')),
    (r'^admin/', include(admin.site.urls)),
    
)
