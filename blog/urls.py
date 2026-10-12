from django.urls import path
from . import views

urlpatterns = [
    # Public Blog & Search
    path('', views.home_view, name='home'),
    path('bookmarks/', views.bookmarked_posts, name='bookmarked_posts'),

    # Auth Routing
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # User Profile & Dashboard
    path('profile/', views.profile_edit_view, name='profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Post Management
    path('post/create/new/', views.post_create_view, name='post_create'),
    path('post/<slug:slug>/', views.post_detail_view, name='post_detail'),
    path('post/<slug:slug>/edit/', views.post_edit_view, name='post_edit'),
    path('post/<slug:slug>/delete/', views.post_delete_view, name='post_delete'),

    # Post Actions (Reactions, Bookmarks, Comments)
    path('post/<int:post_id>/comment/', views.add_comment_view, name='add_comment'),
    path('post/<int:post_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('post/<int:post_id>/react/', views.toggle_reaction, name='toggle_reaction'),

    # Comment Modification (Includes both names to prevent template NoReverseMatch errors)
    path('comment/<int:comment_id>/edit/', views.edit_comment_view, name='edit_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment_view, name='comment_edit'),
    path('comment/<int:comment_id>/delete/', views.delete_comment_view, name='delete_comment'),
]