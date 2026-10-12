import math
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.html import strip_tags
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count
from taggit.managers import TaggableManager


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # Tagging support
    tags = TaggableManager(blank=True)
    
    # User Interactions
    bookmarks = models.ManyToManyField(User, related_name='bookmarked_posts', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'slug': self.slug})

    @property
    def total_likes(self):
        """Returns total count of 'LIKE' type reactions."""
        return self.reactions.filter(reaction_type='LIKE').count()

    @property
    def total_reactions(self):
        """Returns overall count across all reaction types."""
        return self.reactions.count()

    def get_reaction_counts(self):
        """Returns aggregate count breakdown per reaction type."""
        counts = self.reactions.values('reaction_type').annotate(total=Count('reaction_type'))
        return {item['reaction_type']: item['total'] for item in counts}

    @property
    def total_bookmarks(self):
        return self.bookmarks.count()

    def get_read_time(self):
        clean_content = strip_tags(self.content)
        words = clean_content.split()
        word_count = len(words)
        read_time_minutes = math.ceil(word_count / 200)
        return max(read_time_minutes, 1)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Reaction(models.Model):
    REACTION_CHOICES = (
        ('LIKE', 'Like'),
        ('LOVE', 'Love'),
        ('LAUGH', 'Haha'),
        ('ANGRY', 'Angry'),
    )

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='LIKE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Enforces one reaction choice per user per post
        unique_together = ('post', 'user')
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
        ]

    def __str__(self):
        return f'{self.user.username} reacted {self.reaction_type} on {self.post.title}'


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'

    @property
    def is_reply(self):
        return self.parent is not None


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='profile_pics/', default='default_avatar.png', blank=True)
    github_link = models.URLField(max_length=200, blank=True)
    twitter_link = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)