from django.contrib import admin
from django_apps.election.models import *

class PINAdmin(admin.ModelAdmin):
    list_display = ('pin', 'election')
    search_fields = ('pin',)
    list_filter = ('election',)

# ('sub_domain', 'default_phone', 'default_email', 'header_image', 'validation_text', 'ballot_extra', 'exit_url')
class AssetInline1(admin.TabularInline):
    model = Asset
    extra = 1
    class Media:
        css = {
            'all': ('css/custom_admin.css',)
        }

#class AssetInline2(admin.TabularInline):
#    model = Asset
#    extra = 1
#    exclude = ('sub_domain', 'default_phone', 'default_email', 'header_image', 'ballot_extra',)

#class AssetInline3(admin.TabularInline):
#    model = Asset
#    extra = 1
#    exclude = ('sub_domain', 'default_phone', 'default_email', 'header_image', 'validation_text', 'exit_url')

class ElectionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,              {'fields': ((), ('name', 'start_time', 'end_time',
                                             'active_election'
                                             ))}),
        ('Audio Files',     {'fields': ['audio_start','audio_end','audio_finished','audio_repeat',
                                        'audio_invalid_response','audio_error','audio_if_done',
                                        'audio_privacy','audio_pin','audio_already_voted','audio_if_banned'], 'classes': ['collapse']}),
    ]
    readonly_fields = ('active_election',)
    inlines = [
        AssetInline1,
    ]

class QuestionInline(admin.TabularInline):
    model = Ballot_Question
    extra = 1
        
class BallotAdmin(admin.ModelAdmin):
    list_display = ('name', 'election')
    list_filter = ('election',)
    inlines = (QuestionInline,)

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'election')
    list_filter = ('election',)
    filter_horizontal = ('choices',)
    
class ChoiceAdmin(admin.ModelAdmin):
    list_filter = ('question',)
    
class LogAdmin(admin.ModelAdmin):
    list_display = ('pin', 'time', 'election')
    list_filter = ('election',)

class MailLogAdmin(admin.ModelAdmin):
    list_display = ('pin', 'time', 'election')

class VoteAdmin(admin.ModelAdmin):
    list_filter = ('election',)
        
admin.site.register(PIN, PINAdmin)
admin.site.register(Election, ElectionAdmin)
# admin.site.register(Asset, AssetAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(Mail_Log, MailLogAdmin)
admin.site.register(Ballot, BallotAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(Invalid_Response, admin.ModelAdmin)
