from django.conf.urls import url
from django_apps.bulkimport.views import *

urlpatterns = [

    url(r'^admin/bulkimport/job/(?P<job_id>(\d+))/change/$', job_change, name='bulkimport_job_change'),
    url(r'^admin/bulkimport/job/add/$', job_add),
    url(r'^admin/bulkimport/job/(?P<job_id>(\d+))/change/delete/$', job_delete),
    url(r'^admin/bulkimport/template/(?P<template_id>(\d+))/$', template_change),
    url(r'^admin/bulkimport/job_from_template/(?P<template_id>(\d+))/$', template_new_import, name='bulkimport_new_from_template'),
]
