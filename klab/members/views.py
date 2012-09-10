from .models import *
from smartmin.views import *
from django.conf import settings
from django.contrib.auth.models import User, Group
from projects.models import *
import random
import string

class ApplicationCRUDL(SmartCRUDL):
    model = Application
    actions = ('create', 'read', 'update', 'list', 'thanks', 'csv')
    permissions = True

    class Read(SmartReadView):
        fields = ('professional_status', 'applying_for', 'frequency',
                  'goals', 'education', 'experience', 'approve')

        def get_approve(self, obj):
            return '<a class="btn posterize" href="%s?application=%d">Approve</a>' % (reverse('members.member_new'), obj.id)


        def get_name(self, obj):
            return str(obj)

        def get_professional_status(self, obj):
            return obj.get_professional_status_display()

        def get_applying_for(self, obj):
            return obj.get_applying_for_display()

        def get_frequency(self, obj):
            return obj.get_frequency_display()

    class Csv(SmartCsvView):
        fields = ('created_on', 'name', 'email', 'professional_status', 'applying_for', 'frequency', 'city', 'country', 'goals', 'education', 'experience')

        def derive_queryset(self, **kwargs):
            queryset = super(ApplicationCRUDL.Csv, self).derive_queryset(**kwargs)
            return queryset.filter(is_active=True)

        def get_professional_status(self, obj):
            return obj.get_professional_status_display()

        def get_applying_for(self, obj):
            return obj.get_applying_for_display()

        def get_frequency(self, obj):
            return obj.get_frequency_display()
        
    class List(SmartListView):
        fields = ('name', 'email', 'applying_for', 'city', 'country', 'created_on')
        search_fields = ('first_name__icontains', 'last_name__icontains')
        field_config = { 'applying_for': dict(label="Membership Type") }

        

        def derive_queryset(self, **kwargs):
            queryset = super(ApplicationCRUDL.List, self).derive_queryset(**kwargs)
            return queryset.filter(is_active=True)

        def get_name(self, obj):
            return "%s %s" % (obj.first_name, obj.last_name)

        def get_applying_for(self, obj):
            return obj.get_applying_for_display()

    class Create(SmartCreateView):
        permission = None
        success_url = 'id@members.application_thanks'
        field_config = { 'goals': dict(label="Your goals in 1K"),
                         'education': dict(label="Your education in 1K"),
                         'experience': dict(label="Your experience in 1K") }
        submit_button_name = "Apply for Membership"

        def pre_save(self, obj):
            obj = super(ApplicationCRUDL.Create, self).pre_save(obj)
            anon_user = User.objects.get(id=settings.ANONYMOUS_USER_ID)
            obj.created_by = anon_user
            obj.modified_by = anon_user

            return obj

        def post_save(self, obj):
            obj = super(ApplicationCRUDL.Create, self).post_save(obj)

            anon_user = User.objects.get(id=settings.ANONYMOUS_USER_ID)
            obj.created_by = anon_user
            obj.modified_by = anon_user
            
            # make any applications with the same email inactive
            Application.objects.filter(is_active=True, email=obj.email).exclude(id=obj.id).update(is_active=False)

            return obj

        def form_valid(self, form):
            # is our hidden field displayed?  we are probably a bot, return a 200 request
            if 'message' in self.request.REQUEST and len(self.request.REQUEST['message']) > 0:
                return HttpResponse("Thanks for your application.  You appear to be slightly automated however so we may not actually use it.  If you think you have received this in error, please contact the kLab team.")
            else:
                return super(ApplicationCRUDL.Create, self).form_valid(form)

            def get_context_data(self, **kwargs):
                context = super(ApplicationCRUDL.Create, self).get_context_data(**kwargs)
                context['base_template'] = 'smartmin/public_base.html'
                return context

    class Thanks(SmartReadView):
        permission = None



class MemberCRUDL(SmartCRUDL):
    model = Member
    actions = ('create','read', 'update', 'list','new', 'myprofile', 'activate')
    permissions = True

    class Activate(SmartUpdateView):
        fields =('password',)
        permission = None
        
        def get_object(self, queryset=None):
            token = self.request.get('token')
            return Member.objects.get(token=token)
        
        def pre_save(self, obj):
            token = self.request.get('token')
            obj = super(MemberCRUDL.Activate, self).pre_save(obj)
            obj.user.set_password.cleaned_data['password']

            return obj

        def post_save(self, obj):
            obj = super(MemberCRUDL.Activate, self).post_save(obj)
            return obj

    class Myprofile(SmartUpdateView):

        fields = ('first_name','last_name','phone','email','picture','country','city','neighborhood','education','experience')
        def has_permission(self, request, *args, **kwargs):
            
            super(MemberCRUDL.Myprofile,self).has_permission(request, *args, **kwargs)
            return True

        def get_object(self, queryset=None):
            return Member.objects.get(user=self.request.user)


    class List(SmartListView):
        fields = ('name','email','phone','country','city',)
        field_config = { 'email': dict(label="Email / User") }
        

        def derive_queryset(self, **kwargs):
            queryset = super(MemberCRUDL.List, self).derive_queryset(**kwargs)
            return queryset.filter(is_active=True)

        def get_name(self, obj):
            return "%s %s" % (obj.first_name, obj.last_name)


    class New(SmartCreateView):
        fields = ('application',)
        success_url = 'id@members.member_read'
        
        def pre_save(self, obj):
            obj = super(MemberCRUDL.New, self).pre_save(obj)
            userapp = obj.application
            obj.first_name = userapp.first_name
            obj.last_name = userapp.last_name
            obj.phone = userapp.phone
            obj.email = userapp.email
            obj.picture = userapp.picture
            obj.country = userapp.country
            obj.city = userapp.city
            obj.neighborhood = userapp.neighborhood
            obj.education = userapp.education
            obj.experience = userapp.experience
            obj.token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))

            user = User.objects.create(username=obj.application.email,email=obj.application.email)
            import pdb;pdb.set_trace()




            user.email_user("kLab account activation","Your membership to kLab has been approved go to the following link to activate your account http:/klab.rw/members/activate?token=%s" % obj.token,from_email="info@klab.rw")
            group = Group.objects.get(name='Members')
            user.groups.add(group)
            user.first_name = userapp.first_name
            user.last_name = userapp.last_name
            user.email = userapp.email
            user.save()

            obj.user = user

            
            return obj

        def post_save(self, obj):
            obj = super(MemberCRUDL.New, self).post_save(obj)
            obj.update_member_picture()
            project = Project.objects.create(owner=obj,description="gh",created_by=obj.user, modified_by= obj.user)
            
            project.save()
            return obj
