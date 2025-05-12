
from .models import User, Category, Battle, Test, History, Results, SetAdmin, SetBio
from .models import Test
from django.contrib import admin
from .models import SetAdmin, User
from .forms import SetAdminForm

class UserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name',  'lang_id', 'chat_id')
    list_display_links = ('first_name', 'last_name')  # Assuming you want both to be clickable
    search_fields = ['first_name', 'last_name', ]  # Enable search functionality
    list_filter = ['lang_id']  # Enable filtering by language ID

admin.site.register(User, UserAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'name_ru', 'name_en', 'parent')
    search_fields = ['name_uz', 'name_ru', 'name_en']
    list_filter = ['parent']  # Assuming filtering by parent could be useful

admin.site.register(Category, CategoryAdmin)

class BattleAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'name_ru', 'name_en', 'parent')
    search_fields = ['name_uz', 'name_ru', 'name_en']
    list_filter = ['parent']  # Same reasoning as for CategoryAdmin

admin.site.register(Battle, BattleAdmin)

class TestAdmin(admin.ModelAdmin):
    # form = TestAdminForm
    list_display = ('question',"answer_a","category","battle")
    list_filter = ('category','battle')
    search_fields = ("battle","category")

    # Specify any other admin options needed

admin.site.register(Test, TestAdmin)

@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'quiz_id', 'unique_id', 'quiz_number', 'quiz_time', 'created_at')
    search_fields = ('user_id', 'quiz_id', 'unique_id', 'quiz_number')
    list_filter = ('created_at', )

@admin.register(Results)
class ResultsAdmin(admin.ModelAdmin):

    list_display = ('unique_id', 'user', 'user_name', 'true_answers', 'false_answers')

    list_filter = ('user', 'true_answers', 'false_answers')


class SetAdminAdmin(admin.ModelAdmin):
    form = SetAdminForm
    list_display = ('user', 'user_first_name', 'user_chat_id')
    search_fields = ('user__first_name', 'user__chat_id')

    def user_first_name(self, obj):
        return obj.user.first_name
    user_first_name.short_description = 'First Name'

    def user_chat_id(self, obj):
        return obj.user.chat_id
    user_chat_id.short_description = 'Chat ID'

admin.site.register(SetAdmin, SetAdminAdmin)


@admin.register(SetBio)
class SetBioAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'uz_text', 'ru_text')