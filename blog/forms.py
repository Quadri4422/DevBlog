from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Post, Comment, Category, Profile


# --- AUTHENTICATION FORMS ---

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'name@company.com'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Enter username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically apply Tailwind classes to all form fields (username, email, password1, password2)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            })
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs['placeholder'] = '••••••••'
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs['placeholder'] = '••••••••'

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use by another user.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'github_link', 'twitter_link']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'rows': 3,
                'placeholder': 'Tell readers about yourself...'
            }),
            'github_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'https://github.com/yourusername'
            }),
            'twitter_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'https://x.com/yourusername'
            }),
        }


# --- CONTENT FORMS ---

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'category', 'tags', 'featured_image', 'content', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Enter article title'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            }),
            'featured_image': forms.FileInput(attrs={
                'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'rows': 8,
                'placeholder': 'Write your story here...'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].empty_label = "Select a category (Optional)"


class CommentForm(forms.ModelForm):
    parent_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'rows': 3,
                'placeholder': 'Write a comment...'
            })
        }
        labels = {
            'content': ''
        }