from django.conf.urls.defaults import *

urlpatterns = patterns('election.views',

    (r'^$', 'index', {}, 'election_index'),
    (r'^pin/$', 'pin', {}, 'election_pin'),
    (r'^validate/$', 'validate', {}, 'election_validate'),
    
    (r'^ballot/(?P<election_id>[0-9]+)/$', 'ballot', {}, 'election_ballot'),
    (r'^ballot/(?P<election_id>[0-9]+)/cast/$', 'ballot', {'cast':True}, 'election_ballot_cast'),
    (r'^ballot/(?P<election_id>[0-9]+)/change/$', 'ballot', {'change':True}, 'election_ballot_change'),
    
    (r'^confirm/(?P<uuid>[a-z0-9-]+)/$', 'confirm', {}, 'election_confirm'),
    (r'^verify/$', 'verify', {}, 'election_verify'),
    (r'^welcome/(?P<election_id>[0-9]+)/$', 'welcome', {}, 'election_welcome'),
    (r'^i18n/', include('django.conf.urls.i18n'), {}, 'election_set_lang'),
    (r'^status/(?P<election_id>[0-9]+)/$', 'pin_status', {}, 'election_pin_status'),
    (r'^status/ballots/(?P<election_id>[0-9]+)/$', 'vote_status', {}, 'election_vote_status'),
    (r'^results/(?P<election_id>[0-9]+)/$', 'results', {}, 'election_results'),
    
    (r'^phone/(?P<election_id>[0-9]+)/$', 'phone_index', {}, 'election_phone_index'),
    (r'^phone/(?P<election_id>[0-9]+)/welcome/$', 'phone_welcome', {}, 'election_phone_welcome'),
    (r'^phone/(?P<election_id>[0-9]+)/info/$', 'phone_info', {}, 'election_phone_info'),
    (r'^phone/(?P<election_id>[0-9]+)/ballot/$', 'phone_ballot', {}, 'election_phone_ballot'),
    (r'^phone/(?P<election_id>[0-9]+)/verify/$', 'phone_verify', {}, 'election_phone_verify'),
    (r'^phone/question/(?P<question_id>[0-9]+)/$', 'phone_question', {}, 'election_phone_question'),
    (r'^phone/answer/(?P<question_id>[0-9]+)/$', 'phone_answer', {}, 'election_phone_answer'),
    (r'^phone/finish/$', 'phone_finished', {}, 'election_phone_finished'),
    (r'^phone/cast-ballot/$', 'phone_cast_ballot', {}, 'election_phone_cast_ballot'),
    
)
