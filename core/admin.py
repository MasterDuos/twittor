from django.contrib import admin
from image_cropping import ImageCroppingMixin
from .models import Tweet, Like, Comment, UserProfile, Follow, TweetImage, Notification


# --- TweetImage con recorte visual ---
@admin.register(TweetImage)
class TweetImageAdmin(ImageCroppingMixin, admin.ModelAdmin):
    list_display = ("id", "tweet", "get_user",)
    search_fields = ("tweet__user__username", )
    raw_id_fields = ("tweet",)

    def get_user(self, obj):
        return obj.tweet.user.username
    get_user.short_description = "Usuario"


# --- Tweet principal ---
@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'created_at', 'is_retweet')
    search_fields = ('content', 'user__username')
    list_filter = ('is_retweet', 'created_at')
    raw_id_fields = ('user',)


# --- Likes ---
@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tweet', 'created_at')
    search_fields = ('user__username',)
    raw_id_fields = ('user', 'tweet')


# --- Comentarios ---
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tweet', 'created_at')
    search_fields = ('content', 'user__username')
    raw_id_fields = ('user', 'tweet')


# --- Perfiles ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)


# --- Seguidores ---
@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')
    raw_id_fields = ('follower', 'following')


# --- Notificaciones ---
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor', 'recipient', 'verb', 'tweet', 'created_at', 'read')
    list_filter = ('read', 'created_at')
    search_fields = ('actor__username', 'recipient__username', 'verb')
    raw_id_fields = ('actor', 'recipient', 'tweet')

