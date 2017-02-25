from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^admin/bulkimport/job/(?P<job_id>(\d+))/$', 'bulkimport.views.job_change', {}, 'bulkimport_job_change'),
    (r'^admin/bulkimport/job/add/$', 'bulkimport.views.job_add'),
    (r'^admin/bulkimport/job/(?P<job_id>(\d+))/delete/$', 'bulkimport.views.job_delete'),
    (r'^admin/bulkimport/template/(?P<template_id>(\d+))/$', 'bulkimport.views.template_change'),
    (r'^admin/bulkimport/job_from_template/(?P<template_id>(\d+))/$',
        'bulkimport.views.template_new_import',
        {},
        'bulkimport_new_from_template'
     ),
)
