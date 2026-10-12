from django.contrib import admin
from django.db.models import Count
from .models import Post, Comment, Category, Profile, Reaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(total_posts=Count('posts'))

    def post_count(self, obj):
        return obj.total_posts
    post_count.short_description = 'Total Posts'
    post_count.admin_order_field = 'total_posts'


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('user__username', 'post__title')
    raw_id_fields = ('user', 'post')
    list_select_related = ('user', 'post')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'author', 
        'category', 
        'status', 
        'get_reactions_count', 
        'get_bookmarks_count', 
        'created_at'
    )
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    filter_horizontal = ('bookmarks',)
    date_hierarchy = 'created_at'
    list_select_related = ('author', 'category')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            num_reactions=Count('reactions', distinct=True),
            num_bookmarks=Count('bookmarks', distinct=True)
        )

    def get_reactions_count(self, obj):
        return obj.num_reactions
    get_reactions_count.short_description = 'Reactions'
    get_reactions_count.admin_order_field = 'num_reactions'

    def get_bookmarks_count(self, obj):
        return obj.num_bookmarks
    get_bookmarks_count.short_description = 'Bookmarks'
    get_bookmarks_count.admin_order_field = 'num_bookmarks'


class CommentInline(admin.TabularInline):
    model = Comment
    fk_name = 'parent'
    extra = 0
    raw_id_fields = ('author', 'post')
    readonly_fields = ('created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'is_reply', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('author__username', 'content', 'post__title')
    raw_id_fields = ('post', 'author', 'parent')
    date_hierarchy = 'created_at'
    list_select_related = ('author', 'post', 'parent')
    inlines = [CommentInline]

    def is_reply(self, obj):
        return obj.parent is not None
    is_reply.boolean = True
    is_reply.short_description = 'Is Reply?'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'has_avatar', 'github_link', 'twitter_link')
    search_fields = ('user__username', 'user__email', 'bio')
    raw_id_fields = ('user',)
    list_select_related = ('user',)

    def has_avatar(self, obj):
        return bool(obj.avatar)
    has_avatar.boolean = True
    has_avatar.short_description = 'Avatar Uploaded'