from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import modelformset_factory
from image_cropping import ImageCropWidget

from .models import Tweet, Comment, UserProfile, TweetImage


# ======================== ESTILOS BASE ========================
BASE_INPUT = {'class': 'input'}
BASE_AREA  = {'class': 'input min-h-[100px]'}
BASE_FILE  = {'class': 'file-input'}


# ======================== FORMULARIOS PRINCIPALES ========================

# --- TweetForm: solo texto (sin campo image, lo maneja el formset) ---
class TweetForm(forms.ModelForm):
    class Meta:
        model = Tweet
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '¿Qué está pasando? (280 máx.)',
                **BASE_AREA
            }),
        }


# --- Formulario de comentarios ---
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Escribe una respuesta…',
                **BASE_AREA
            }),
        }


# --- Formulario de registro ---
class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'tucorreo@ejemplo.com', **BASE_INPUT})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.TextInput(attrs={
            'placeholder': 'usuario',
            **BASE_INPUT
        })
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'placeholder': 'Contraseña',
            **BASE_INPUT
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'placeholder': 'Confirmar contraseña',
            **BASE_INPUT
        })


# --- Formulario de perfil ---
class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.TextInput(attrs={
                'placeholder': 'Cuéntanos algo sobre ti',
                **BASE_INPUT
            }),
            'avatar': forms.ClearableFileInput(attrs={**BASE_FILE})
        }


# ======================== MULTI-IMAGEN + RECORTE ========================

# --- Form individual por imagen (con recorte opcional) ---
class TweetImageForm(forms.ModelForm):
    class Meta:
        model = TweetImage
        fields = ("image", "cropping")
        widgets = {"cropping": ImageCropWidget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El recorte no es obligatorio
        self.fields["cropping"].required = False


# --- Formset para hasta 4 imágenes por Tweet ---
TweetImageFormSet = modelformset_factory(
    TweetImage,
    form=TweetImageForm,
    extra=4,
    max_num=4,
    can_delete=False,
)
