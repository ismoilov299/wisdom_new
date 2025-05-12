import pandas as pd
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.utils import timezone



current_time = timezone.now()

class User(models.Model):
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    lang_id = models.IntegerField(blank=True, null=True)  # Consider using choices for predefined languages
    chat_id = models.BigIntegerField(unique=True, blank=True, null=True)  # Consider using BigIntegerField if chat_id can be large

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.chat_id})" if self.first_name and self.last_name else str(self.chat_id)

    class Meta:
        verbose_name_plural = 'Users'



class Category(models.Model):
    name_uz = models.CharField(max_length=150)
    name_ru = models.CharField(max_length=150)
    name_en = models.CharField(max_length=150, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    def __str__(self):
        return self.name_uz

    class Meta:
        verbose_name_plural = 'Categories'

class Battle(models.Model):
    name_uz = models.CharField(max_length=150)
    name_ru = models.CharField(max_length=150)
    name_en = models.CharField(max_length=150, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_battles')

    def __str__(self):
        return self.name_uz

    class Meta:
        verbose_name_plural = 'Battles'



class Test(models.Model):
    battle = models.ForeignKey(Battle, on_delete=models.CASCADE,blank=True,null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE,blank=True,null=True)
    question = models.TextField(blank=True, null=True)  # Question is optional
    answer_a = models.CharField(max_length=255, blank=True, null=True)  # Optional answer A
    answer_b = models.CharField(max_length=255, blank=True, null=True)  # Optional answer B
    answer_c = models.CharField(max_length=255, blank=True, null=True)  # Optional answer C
    answer_d = models.CharField(max_length=255, blank=True, null=True)  # Optional answer D
    excel_file = models.FileField(upload_to='uploads/tests/', null=True, blank=True)  # For uploading associated Excel files

    def __str__(self):
        return self.question or "Unnamed Test"

    def save(self, *args, **kwargs):
        if self.question:
            super().save(*args, **kwargs)

        if self.excel_file:
            df = pd.read_excel(self.excel_file)
            for index, row in df.iterrows():
                Test.objects.create(
                    battle=self.battle,
                    category=self.category,  # Add category ID here
                    question=row['Savol'],
                    answer_a=row['Variant A'],
                )






class History(models.Model):
    quiz_id = models.CharField(max_length=150)  # Text field for quiz ID
    quiz_number = models.CharField(max_length=150)  # Text field for quiz number
    quiz_time = models.CharField(max_length=150)  # Text field for time taken for the quiz
    unique_id = models.CharField(max_length=150,  editable=False, unique=True)  # Text field for unique identifier
    user_id = models.CharField(max_length=150)  # Text field for user ID
    created_at = models.CharField(max_length=150, blank=True, null=True)  # Text field for preformatted quiz time



    def __str__(self):
        return f'History {self.quiz_number} for User {self.user_id}'
    class Meta:
        verbose_name_plural = 'History'

class Results(models.Model):
    unique_id = models.CharField(max_length=150)  # Text field for unique identifier
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Foreign key to the User model
    user_name = models.CharField(max_length=150, editable=False)  # Text field for the user's name, not editable
    true_answers = models.PositiveIntegerField()  # Integer field for the count of true answers
    false_answers = models.PositiveIntegerField()  # Integer field for the count of false answers

    def save(self, *args, **kwargs):
        # Automatically set the user_name to match the User model's username
        self.user_name = self.user.first_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Results for {self.user_name} (User ID: {self.user.id})'

    class Meta:
        verbose_name_plural = 'Results'


class SetAdmin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} ({self.user.chat_id})" if self.user.first_name else str(self.user.chat_id)

    class Meta:
        verbose_name_plural = 'Set Admins'

class SetBio(models.Model):
    uz_text = models.TextField(verbose_name='Uzbek Text', blank=True, null=True)
    ru_text = models.TextField(verbose_name='Russian Text', blank=True, null=True)

    def __str__(self):
        if self.uz_text:
            return self.uz_text[:50]  # Return first 50 characters of Uzbek text
        elif self.ru_text:
            return self.ru_text[:50]  # Return first 50 characters of Russian text
        else:
            return "No bio provided"

    class Meta:
        verbose_name_plural = 'Set about'
