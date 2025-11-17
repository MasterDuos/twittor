from datetime import timedelta
from urllib.parse import urlparse

import re

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from .forms import (
    CommentForm,
    ProfileForm,
    SignUpForm,
    TweetForm,
    TweetImageFormSet,
)
from .models import (
    Comment,
    Follow,
    Like,
    Tweet,
    TweetImage,
    UserProfile,
)
from .utils import get_or_create_link_preview


# ========================= SIGNUP =========================

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('timeline')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('timeline')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


# ========================= TIMELINE =========================

@login_required
def timeline(request):
    # Usuarios a mostrar: yo + los que sigo
    following_ids = list(
        Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    )
    qs = (
        Tweet.objects.filter(user_id__in=[request.user.id, *following_ids])
        .select_related('user', 'user__userprofile', 'link_preview')
        .prefetch_related('images')
    )

    if request.method == 'POST':
        form = TweetForm(request.POST)

        # Formset para tests y compatibilidad (camino "viejo")
        formset = TweetImageFormSet(
            request.POST,
            request.FILES,
            queryset=TweetImage.objects.none(),
            prefix='form',
        )

        # Nuevo input múltiple de la UI
        images = request.FILES.getlist('images')

        # --- Caso 1: UI nueva (input name="images") ---
        if images:
            if not form.is_valid():
                return render(request, 'core/timeline.html', {
                    'tweets': qs,
                    'form': form,
                    'formset': formset,
                })

            with transaction.atomic():
                tw = form.save(commit=False)
                tw.user = request.user

                # OpenGraph / Link preview
                m = re.search(r'(https?://[^\s]+)', tw.content or '')
                if m:
                    try:
                        tw.link_preview = get_or_create_link_preview(m.group(1))
                    except Exception:
                        pass

                tw.save()

                # Guardar hasta 4 imágenes
                for f in images[:4]:
                    TweetImage.objects.create(tweet=tw, image=f)

            return redirect('timeline')

        # --- Caso 2: Camino formset (tests, fallback) ---
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                tw = form.save(commit=False)
                tw.user = request.user

                m = re.search(r'(https?://[^\s]+)', tw.content or '')
                if m:
                    try:
                        tw.link_preview = get_or_create_link_preview(m.group(1))
                    except Exception:
                        pass

                tw.save()

                for cd in formset.cleaned_data:
                    if cd and cd.get('image'):
                        TweetImage.objects.create(tweet=tw, image=cd['image'])

            return redirect('timeline')

        # Si algo no es válido, se re-renderiza con errores
        return render(request, 'core/timeline.html', {
            'tweets': qs,
            'form': form,
            'formset': formset,
        })

    # GET
    form = TweetForm()
    formset = TweetImageFormSet(
        queryset=TweetImage.objects.none(),
        prefix='form',
    )

    return render(request, 'core/timeline.html', {
        'tweets': qs,
        'form': form,
        'formset': formset,
    })


# ========================= EXPLORE =========================

@login_required
def explore(request):
    qs = Tweet.objects.select_related('user', 'user__userprofile').all()[:100]
    form = TweetForm()
    formset = TweetImageFormSet(
        queryset=TweetImage.objects.none(),
        prefix='form',
    )
    return render(request, 'core/timeline.html', {
        'tweets': qs,
        'form': form,
        'formset': formset,
    })


# ========================= DETALLE / PERFIL =========================

@login_required
def tweet_detail(request, pk):
    tw = get_object_or_404(Tweet.objects.select_related('user', 'user__userprofile'), pk=pk)
    if request.method == 'POST':
        cform = CommentForm(request.POST)
        if cform.is_valid():
            c = cform.save(commit=False)
            c.user = request.user
            c.tweet = tw
            c.save()
            return redirect(tw.get_absolute_url())
    else:
        cform = CommentForm()
    return render(request, 'core/tweet_detail.html', {'tweet': tw, 'cform': cform})


@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(UserProfile, user=user)
    is_me = request.user == user
    is_following = Follow.objects.filter(follower=request.user, following=user).exists()
    tweets = Tweet.objects.filter(user=user)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'follow':
            if request.user != user:
                Follow.objects.get_or_create(follower=request.user, following=user)
        elif action == 'unfollow':
            Follow.objects.filter(follower=request.user, following=user).delete()
        elif action == 'edit' and is_me:
            form = ProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
        return redirect('profile', username=username)

    form = ProfileForm(instance=profile) if is_me else None
    ctx = {
        'profile_user': user,
        'profile': profile,
        'is_me': is_me,
        'is_following': is_following,
        'tweets': tweets,
        'form': form,
    }
    return render(request, 'core/profile.html', ctx)


# ========================= BÚSQUEDA, TAGS, NOTIFS =========================

HASHTAG_RE = re.compile(r"(#\w+)")


def _create_notification(actor, recipient, verb, tweet=None):
    if actor == recipient:
        return
    from .models import Notification
    Notification.objects.create(actor=actor, recipient=recipient, verb=verb, tweet=tweet)


@login_required
def search(request):
    q = request.GET.get('q', '').strip()
    tweets = Tweet.objects.none()
    users = User.objects.none()
    if q:
        tweets = Tweet.objects.filter(
            Q(content__icontains=q) | Q(user__username__icontains=q)
        ).select_related('user')[:100]
        users = User.objects.select_related('userprofile').filter(username__icontains=q)[:50]
    return render(request, 'core/search.html', {'q': q, 'tweets': tweets, 'users': users})


@login_required
def tag(request, tag):
    tag_lower = tag.lower()
    tweets = Tweet.objects.filter(
        content__iregex=rf'(^|\s)#({tag_lower})\b'
    ).select_related('user')
    return render(request, 'core/tag.html', {'tag': tag, 'tweets': tweets})


@login_required
def notifications(request):
    from .models import Notification
    notifs = Notification.objects.filter(recipient=request.user).select_related(
        'actor', 'actor__userprofile', 'tweet'
    ).order_by('-created_at')[:50]
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return render(request, 'core/notifications.html', {'notifs': notifs})


# ========================= RETWEET / QUOTE =========================

@login_required
def retweet(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Solo POST')
    tw = get_object_or_404(Tweet.objects.select_related('user', 'user__userprofile'), pk=pk)
    exists = Tweet.objects.filter(user=request.user, parent=tw, is_retweet=True).exists()
    if not exists:
        new_tw = Tweet.objects.create(user=request.user, content='', parent=tw, is_retweet=True)
        _create_notification(request.user, tw.user, 'retwitteó tu publicación', tweet=tw)
    return redirect(request.META.get('HTTP_REFERER', 'timeline'))


@login_required
def quote(request, pk):
    tw = get_object_or_404(Tweet.objects.select_related('user', 'user__userprofile'), pk=pk)
    if request.method == 'POST':
        form = TweetForm(request.POST, request.FILES)
        if form.is_valid():
            quote_tw = form.save(commit=False)
            quote_tw.user = request.user
            quote_tw.parent = tw
            quote_tw.is_retweet = False
            quote_tw.save()
            _create_notification(request.user, tw.user, 'citó tu publicación', tweet=tw)
            return redirect('timeline')
    else:
        form = TweetForm()
    return render(request, 'core/quote.html', {'original': tw, 'form': form})


# ========================= LIKE TOGGLE (HTMX READY) =========================

@login_required
def like_toggle(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Solo POST')
    tweet = get_object_or_404(Tweet, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, tweet=tweet)
    if not created:
        like.delete()
    else:
        _create_notification(request.user, tweet.user, 'le gustó tu publicación', tweet=tweet)

    if request.headers.get('Hx-Request'):
        html = render_to_string('components/like_button.html', {'t': tweet, 'user': request.user})
        return JsonResponse({'html': html})
    return redirect(request.META.get('HTTP_REFERER', tweet.get_absolute_url()))


# ========================= TRENDING LINKS =========================

@login_required
def trending_links(request):
    """
    Muestra los dominios más compartidos en los últimos 24 h.
    """
    since = timezone.now() - timedelta(hours=24)

    recent = Tweet.objects.filter(
        created_at__gte=since,
        link_preview__isnull=False
    ).select_related('link_preview')

    domains = {}
    for tw in recent:
        if tw.link_preview and tw.link_preview.url:
            try:
                domain = urlparse(tw.link_preview.url).netloc.replace("www.", "")
                domains[domain] = domains.get(domain, 0) + 1
            except Exception:
                pass

    trending = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]

    ctx = {
        "trending": trending,
        "total_links": sum(domains.values()),
    }
    return render(request, "core/trending.html", ctx)
