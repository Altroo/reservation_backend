from django.urls import path
from .views import AssistView, TranslateView

app_name = "ai_assistant"
urlpatterns = [
    path("translate/", TranslateView.as_view(), name="translate"),
    path("assist/", AssistView.as_view(), name="assist"),
]
