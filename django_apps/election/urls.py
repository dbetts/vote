from django.conf.urls import url, include
from django_apps.election.views import *
from django.conf.urls import i18n
from django.contrib.auth.views import logout

urlpatterns = [
    url(r'^$', index, None, name='selection_index'),
    url(r'^pin/$', pin, None, name='election_pin'),
    url(r'^validate/$', validate, name='election_validate'),

    url(r'^ballot/(?P<election_id>[0-9]+)/$', ballot, name='election_ballot'),
    url(r'^ballot/(?P<election_id>[0-9]+)/cast/$', ballot, {'cast':True}, name='election_ballot_cast'),
    url(r'^ballot/(?P<election_id>[0-9]+)/change/$', ballot, {'change':True}, name='election_ballot_change'),

    url(r'^confirm/(?P<uuid>[a-z0-9-]+)/$', confirm, name='election_confirm'),
    url(r'^verify/$', verify, name='election_verify'),
    url(r'^welcome/(?P<election_id>[0-9]+)/$', welcome, name='election_welcome'),

    # url(r'^i18n/', include('django.conf.urls.i18n'), election_set_lang),
    # include((i18n, r'^i18n/'), 'election_set_lang'),
    url(r'^i18n/', include(i18n), name='election_set_lang'),


    url(r'^logout/$', logout, {'next_page': settings.LOGOUT_REDIRECT_URL}, name='logout'),


    url(r'^status/(?P<election_id>[0-9]+)/$', pin_status, name='election_pin_status'),
    url(r'^status/ballots/(?P<election_id>[0-9]+)/$', vote_status, name='election_vote_status'),
    url(r'^results/(?P<election_id>[0-9]+)/$', results, name='election_results'),

    # These must be re-introduced once the twillio upgrade is complete.
    url(r'^phone/(?P<election_id>[0-9]+)/$', phone_index, name='election_phone_index'),
    url(r'^phone/(?P<election_id>[0-9]+)/welcome/$', phone_welcome, name='election_phone_welcome'),
    url(r'^phone/(?P<election_id>[0-9]+)/info/$', phone_info, name='election_phone_info'),
    url(r'^phone/(?P<election_id>[0-9]+)/ballot/$', phone_ballot, name='election_phone_ballot'),
    url(r'^phone/(?P<election_id>[0-9]+)/ballot_digits/$', phone_ballot_digits, name='election_phone_ballot_digits'),
    url(r'^phone/(?P<election_id>[0-9]+)/verify/$', phone_verify, name='election_phone_verify'),
    url(r'^phone/question/(?P<question_id>[0-9]+)/$', phone_question, name='election_phone_question'),
    url(r'^phone/answer/(?P<question_id>[0-9]+)/$', phone_answer, name='election_phone_answer'),
    url(r'^phone/finish/$', phone_finished, name='election_phone_finished'),
    url(r'^phone/cast-ballot/$', phone_cast_ballot, name='election_phone_cast_ballot'),
]
