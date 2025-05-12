from django import forms
from .models import SetAdmin, User

class SetAdminForm(forms.ModelForm):
    class Meta:
        model = SetAdmin
        fields = ['user']

    def __init__(self, *args, **kwargs):
        super(SetAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.all().order_by('first_name', 'last_name')