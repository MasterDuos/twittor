from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import FileExtensionValidator
from image_cropping import ImageRatioField

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.CharField(max_length=180, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Perfil de {self.user.username}'

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f'{self.follower.username} → {self.following.username}'

class Tweet(models.Model):
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children'
    )
    is_retweet = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.CharField(max_length=280)
    image = models.ImageField(upload_to='tweets/', blank=True, null=True)

    # 🔗 NUEVO: relación con LinkPreview (vista previa de enlaces)
    link_preview = models.ForeignKey(
        "LinkPreview",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tweets"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.content[:30]}'

    def get_absolute_url(self):
        return reverse('tweet_detail', args=[self.pk])

    @property
    def like_count(self) -> int:
        return self.likes.count()

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tweet')

    def __str__(self):
        return f'{self.user.username} ♥ {self.tweet_id}'

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='comments')
    content = models.CharField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Coment de {self.user.username} en {self.tweet_id}'


class Notification(models.Model):
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    verb = models.CharField(max_length=80)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor} -> {self.recipient}: {self.verb}'

from django.utils import timezone
from datetime import timedelta


class LinkPreview(models.Model):
    url = models.URLField(unique=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """Determina si la información cacheada tiene más de 24h"""
        return timezone.now() - self.fetched_at > timedelta(hours=24)

    def __str__(self):
        return self.url

from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_image_size(image):
    """Valida que la imagen no supere 5 MB."""
    max_size = 5 * 1024 * 1024  # 5 MB
    if image.size > max_size:
        raise ValidationError("La imagen no debe superar los 5 MB.")


def validate_image_size(image):
    """Valida que la imagen no supere 10 MB."""
    max_size = 10 * 1024 * 1024  # 10 MB
    if image.size > max_size:
        raise ValidationError("La imagen no debe superar los 10 MB.")


class TweetImage(models.Model):
    tweet = models.ForeignKey('Tweet', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='tweets/multi/',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif']),
            validate_image_size
        ]
    )
    cropping = ImageRatioField('image', '500x500')  # ✅ campo aparte, fuera del ImageField

    def __str__(self):
        return f"Imagen de {self.tweet.user.username} ({self.tweet.id})"