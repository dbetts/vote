from django.conf.urls.defaults import *

urlpatterns = patterns('lookup.views',

    (r'^$', 'index', {}, 'lookup_index'),
    (r'^thanks/$', 'thanks', {}, 'lookup_thanks'),
)
