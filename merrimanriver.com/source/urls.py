from django.conf.urls import url, include
from django.contrib import admin
# from django.contrib.sites.models import Site ###  Not sure what we are using Sites for? Was also removed from the settings.INSTALLED_APPS
from django.conf import settings
from django.views.static import serve
from django.contrib.admindocs import urls as admin_urls
import django_apps.election.urls as election_urls
import django_apps.bulkimport.urls as bulkimport_urls
#from lookup import urls as lookup_urls

admin.autodiscover()
# admin.site.unregister(Site) # Hide the Sites group of tables in the Admin, by importing, then un-registering it.

urlpatterns = [
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # url(r'^admin/doc/', include(admin_urls)),
    url(r'^admin/doc/', include(admin_urls)),

#    url(r'^lookup/', lookup_urls),

    url(r'', include(election_urls)),

    url(r'', include(bulkimport_urls)),

    url('^admin/', include(admin.site.urls)),
]
