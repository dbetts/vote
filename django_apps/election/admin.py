from django.contrib import admin
from django_apps.election.models import *

class PINAdmin(admin.ModelAdmin):
    list_display = ('pin', 'election')
    search_fields = ('pin',)
    list_filter = ('election',)


class AssetInline(admin.StackedInline):
    model = Asset
    verbose_name_plural = 'Election Assets'
    can_delete = False
    show_change_link = True
    classes = ('collapse',)
    ### Asset has 'election = models.OneToOneField(Election)', so extra and max_num are irrelevant.
    # extra = 6
    # max_num = 10

    # fields = ['sub_domain', 'default_phone', 'default_email', 'header_image', 'validation_text', 'ballot_extra', 'exit_url']

    # class Media:
    #     css = {
    #         'all': ('css/custom_admin.css',)
    #     }

class ElectionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,              {'fields': ((), ('name', 'start_time', 'end_time',
                                             # 'active_election', DSB disabled this for show. May need to be re-enabled.
                                             'live_election', # The live_election field literally does nothing. It is for show only.
                                             'logic_and_accuracy'
                                             # 'enable_cast_vote_record' DSB The DB field was renamed and then renamed here as well.
                                             ))}),
        ('Audio Files',     {'fields': ['audio_start','audio_end','audio_finished','audio_repeat',
                                        'audio_invalid_response','audio_error','audio_if_done',
                                        'audio_privacy','audio_pin','audio_already_voted','audio_if_banned'], 'classes': ['collapse']}),
    ]

    readonly_fields = ('active_election',)

    inlines = [
        AssetInline,
    ]

class QuestionInline(admin.TabularInline):
    model = Ballot_Question
    extra = 0
        
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
# admin.site.register(Asset, AssetInline)
admin.site.register(Log, LogAdmin)
admin.site.register(Mail_Log, MailLogAdmin)
admin.site.register(Ballot, BallotAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(Invalid_Response, admin.ModelAdmin)
