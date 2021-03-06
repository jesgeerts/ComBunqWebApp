from django import forms
from BunqWebApp import validator
from django.contrib.auth import authenticate


class registration(forms.Form):
    """docstring for registration."""
    username = forms.CharField(
        max_length=15, validators=[validator.checkUsername])
    password = forms.CharField(
        widget=forms.PasswordInput, min_length=8
        )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )
    api_key = forms.CharField(max_length=150)

    def clean(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError('Passwords do not match')
        return self.cleaned_data


class LogInForm(forms.Form):
    username = forms.CharField(max_length=15)
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    user_file = forms.FileField()

    def clean(self):
        password = self.cleaned_data.get('password')
        username = self.cleaned_data.get('username')
        user = authenticate(username=username, password=password)

        if user is None:
            raise forms.ValidationError('Username or password incorrect')

        return self.cleaned_data


class MigrationLogIn(forms.Form):
    username = forms.CharField(max_length=15)
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    encryption_password = forms.CharField(min_length=8,
                                          widget=forms.PasswordInput)
    user_file = forms.FileField()

    def clean(self):
        password = self.cleaned_data.get('password')
        username = self.cleaned_data.get('username')
        user = authenticate(username=username, password=password)

        if user is None:
            raise forms.ValidationError('Username or password incorrect')
        return self.cleaned_data
