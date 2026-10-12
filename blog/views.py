import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from taggit.models import Tag

from .models import Post, Comment, Category, Profile, Reaction
from .forms import UserRegisterForm, PostForm, CommentForm, UserUpdateForm, ProfileForm


# --- PUBLIC VIEWS ---

def home_view(request):
    """Homepage: lists published posts with search, category/tag filtering & pagination."""
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    tag_slug = request.GET.get('tag', '').strip()

    posts = Post.objects.filter(status='published').select_related('author', 'category').prefetch_related('tags').order_by('-created_at')

    # Tag Filtering
    if tag_slug:
        posts = posts.filter(tags__slug=tag_slug)

    # Category Filtering
    if category_slug:
        posts = posts.filter(category__slug=category_slug)

    # Search Filtering (Title, Content, or Tag)
    if query:
        posts = posts.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()

    # Pagination: 6 posts per page
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    selected_tag = Tag.objects.filter(slug=tag_slug).first() if tag_slug else None

    return render(request, 'blog/post_list.html', {
        'page_obj': page_obj,
        'query': query,
        'categories': categories,
        'selected_category': category_slug,
        'selected_tag': selected_tag,
    })


def post_detail_view(request, slug):
    """Detailed article view with active comments moderation, replies, reactions, and bookmark states."""
    post = get_object_or_404(
        Post.objects.select_related('author', 'author__profile', 'category').prefetch_related('tags', 'reactions'),
        slug=slug
    )

    # Allow post author or staff to preview draft posts; enforce published status for public viewers
    if post.status != 'published' and (not request.user.is_authenticated or (request.user != post.author and not request.user.is_staff)):
        return render(request, '404.html', status=404)

    # Filter comments to only display active ones
    comments = post.comments.filter(parent__isnull=True, active=True).select_related(
        'author', 'author__profile'
    ).prefetch_related(
        'replies__author', 'replies__author__profile'
    ).order_by('-created_at')

    # Calculate initial user interaction states
    user_reaction = None
    is_bookmarked = False
    
    if request.user.is_authenticated:
        reaction_obj = post.reactions.filter(user=request.user).first()
        if reaction_obj:
            user_reaction = reaction_obj.reaction_type
        is_bookmarked = post.bookmarks.filter(id=request.user.id).exists()

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'comments': comments,
        'user_reaction': user_reaction,
        'reaction_counts': post.get_reaction_counts(),
        'total_reactions': post.total_reactions,
        'is_bookmarked': is_bookmarked,
    })


@login_required
@require_POST
def add_comment_view(request, post_id):
    """Handles submission of top-level comments and nested replies."""
    post = get_object_or_404(Post, id=post_id, status='published')
    
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        
        parent_id = request.POST.get('parent_id')
        if parent_id:
            comment.parent = get_object_or_404(Comment, id=parent_id, post=post, active=True)

        comment.save()
        messages.success(request, "Comment added successfully!")
    else:
        messages.error(request, "Failed to post comment. Please check your text.")

    return redirect('post_detail', slug=post.slug)


# --- INTERACTIVE AJAX VIEWS ---

@login_required
@require_POST
def toggle_reaction(request, post_id):
    """
    Handles creating, updating, or removing emoji reactions via AJAX or standard POST.
    Accepts reaction_type in POST data or JSON payload ('LIKE', 'LOVE', 'LAUGH', 'ANGRY').
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Extract reaction_type from form-data or JSON body
    reaction_type = request.POST.get('reaction_type')
    if not reaction_type and request.body:
        try:
            data = json.loads(request.body)
            reaction_type = data.get('reaction_type')
        except json.JSONDecodeError:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)

    # Strict validation against Reaction model choices
    valid_choices = [choice[0] for choice in Reaction.REACTION_CHOICES]
    if reaction_type not in valid_choices:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'message': 'Invalid reaction type provided'}, status=400)
        messages.error(request, "Invalid reaction selected.")
        return redirect('post_detail', slug=post.slug)

    # Check existing reaction state
    existing_reaction = Reaction.objects.filter(post=post, user=request.user).first()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # Same reaction clicked -> remove it (toggle off)
            existing_reaction.delete()
            user_reaction = None
        else:
            # Different reaction clicked -> update choice
            existing_reaction.reaction_type = reaction_type
            existing_reaction.save()
            user_reaction = reaction_type
    else:
        # No reaction exists -> create new record
        Reaction.objects.create(post=post, user=request.user, reaction_type=reaction_type)
        user_reaction = reaction_type

    # Refresh post instance to update annotated/computed properties
    post.refresh_from_db()

    # Return JSON response for AJAX calls
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'status': 'success',
            'user_reaction': user_reaction,
            'total_reactions': post.total_reactions,
            'reaction_counts': post.get_reaction_counts(),
        })

    return redirect('post_detail', slug=post.slug)


@login_required
@require_POST
def toggle_bookmark(request, post_id):
    """
    Toggles post bookmark status for the authenticated user via AJAX or form POST.
    """
    post = get_object_or_404(Post, id=post_id)

    if post.bookmarks.filter(id=request.user.id).exists():
        post.bookmarks.remove(request.user)
        is_bookmarked = False
    else:
        post.bookmarks.add(request.user)
        is_bookmarked = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'status': 'success',
            'is_bookmarked': is_bookmarked,
            'total_bookmarks': post.bookmarks.count()
        })

    return redirect('post_detail', slug=post.slug)


@login_required
def bookmarked_posts(request):
    """Lists posts bookmarked by the logged-in user."""
    posts = request.user.bookmarked_posts.filter(status='published').select_related('author', 'category').prefetch_related('tags').order_by('-created_at')
    return render(request, 'blog/bookmarked_posts.html', {'posts': posts})


# --- AUTHENTICATION VIEWS ---

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
    else:
        form = UserRegisterForm()

    return render(request, 'blog/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.info(request, f"Welcome back, {user.username}!")
            
            # Handle post-login redirection with next parameter fallback
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'blog/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Successfully logged out.")
    return redirect('home')


# --- DASHBOARD & POST CRUD ---

@login_required
def dashboard_view(request):
    user_posts = Post.objects.filter(author=request.user).order_by('-created_at')
    published_count = user_posts.filter(status='published').count()
    draft_count = user_posts.filter(status='draft').count()

    context = {
        'user_posts': user_posts,
        'published_count': published_count,
        'draft_count': draft_count,
    }
    return render(request, 'blog/user_dashboard.html', context)


@login_required
def post_create_view(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # Saves django-taggit many-to-many relationship
            messages.success(request, "Post created successfully!")
            return redirect('dashboard')
    else:
        form = PostForm()

    return render(request, 'blog/post_form.html', {'form': form, 'title': 'Create New Post'})


@login_required
def post_edit_view(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully!")
            return redirect('dashboard')
    else:
        form = PostForm(instance=post)

    return render(request, 'blog/post_form.html', {'form': form, 'title': 'Edit Post'})


@login_required
def post_delete_view(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect('dashboard')

    return render(request, 'blog/post_confirm_delete.html', {'post': post})


# --- COMMENT MODIFICATION VIEWS ---

@login_required
def edit_comment_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    if request.method == 'POST':
        new_content = request.POST.get('content')
        if new_content:
            comment.content = new_content
            comment.save()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def delete_comment_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    if request.method == 'POST':
        comment.delete()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

# --- USER PROFILE VIEW ---

@login_required
def profile_edit_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
    }
    return render(request, 'blog/profile.html', context)

    