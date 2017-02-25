from django import template
from django.conf import settings
from django.template import Variable
from django.utils.datastructures import SortedDict

try:
    import json
except ImportError:
    import simplejson as json

register = template.Library()

@register.tag
def load_answers(parser, token):
        
    try:
        tag_name, answers = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument"
    return AnswersNode(answers)

@register.tag
def get_question_choices(parser, token):
        
    try:
        tag_name, question, as_sugar, varname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly two arguments"
    return GetQuestionNode(question, varname)

class AnswersNode(template.Node):
    def __init__(self, answers):
        self.answers = Variable(answers)
    
    def render(self, context):
        context['_answers_node'] = self.answers.resolve(context)
        return ''
    
class GetQuestionNode(template.Node):
    def __init__(self, question, varname):
        self.question   = Variable(question)
        self.varname    = varname

    def render(self, context):
        context[self.varname] = []
        
        q = self.question.resolve(context)
        
        for a in context['_answers_node']:
            if q == a.question:
                context[self.varname].append(a.choice)
        
        return ''
        
@register.filter(name='percentage')
def percentage(fraction, population):
    try:
        return "%3.2f%%" % ((float(fraction) / float(population)) * 100)
    except ValueError:
        return ''


@register.filter
def hash(h, k):
    if hasattr(h, "__iter__"):
        if k in h:
            return h[k]
        if str(k) in h:
            return h[str(k)]
    return None
    
@register.tag
def votes_for_question(parser, token):
        
    try:
        tag_name, question, in_sugar, votes, as_sugar, varname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly two arguments"
    return VotesForQuestion(question, votes, varname)

class VotesForQuestion(template.Node):
    def __init__(self, question, votes, varname):
        self.question = Variable(question)
        self.votes = Variable(votes)
        self.varname = Variable(varname)
    
    def render(self, context):
        question = self.question.resolve(context)
        votes = self.votes.resolve(context)
        choices = question.choice_set.all()
        
        votes_by_questions = {}
        
        for v in votes:
            answers = json.loads(v.choices)
            
            for a_id, a in answers.items():
                if not votes_by_questions.has_key(a_id):
                    votes_by_questions[a_id] = []
                    
                votes_by_questions[a_id].append(a['answer'])
                        
        totals = []
        
        for choice in choices:
            
            try:
                total = 0
            
                for vote in votes_by_questions[str(choice.question.id)]:
                    if type(vote) == list:
                        for vote_choice in vote:
                            if int(vote_choice) == choice.id:
                                total = total + 1
                    else:
                        if int(vote) == choice.id:
                            total = total + 1
                totals.append({'answer': choice.answer, 'total': total })
            except KeyError:
                totals.append({'answer': choice.answer, 'total': 0 })
            
        context[str(self.varname)] = totals
        
        return ''

def register_render_tag(renderer):
    """
        Decorator that creates a template tag using the given renderer as the
        render function for the template tag node - the render function takes two
        arguments - the template context and the tag token
    """

    def tag(parser, token):
        class TagNode(template.Node):
            def render(self, context):
                return renderer(context, token)

        return TagNode()

    for copy_attr in ("__dict__", "__doc__", "__name__"):
        setattr(tag, copy_attr, getattr(renderer, copy_attr))
    return register.tag(tag)


@register_render_tag
def admin_reorder(context, token):
    """
        Called in admin/base_site.html template override and applies custom ordering
        of apps/models defined by settings.ADMIN_REORDER
    """
    # sort key function - use index of item in order if exists, otherwise item
    sort = lambda order, item: (order.index(item), "") if item in order else (
        len(order), item)
    if "app_list" in context:
        # sort the app list
        order = SortedDict(settings.ADMIN_REORDER)
        #context["app_list"].sort(key=lambda app: sort(order.keys(), app["app_url"][:-1]))
        context["app_list"].sort(key=lambda app: sort(order.keys(), app["app_url"].strip("/").split("/")[-1]))

        for i, app in enumerate(context["app_list"]):
            # sort the model list for each app
            #app_name = app["app_url"][:-1]
            app_name = app["app_url"].strip("/").split("/")[-1]
            if not app_name:
                #app_name = context["request"].path.strip("/").split("/")[-1]
                app_name = app["name"].lower()


            model_order = [m.lower() for m in order.get(app_name, [])]
            context["app_list"][i]["models"].sort(key=lambda model:
            sort(model_order, model["admin_url"].strip("/").split("/")[-1]))
    return ""