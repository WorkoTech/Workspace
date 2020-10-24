from django.urls import include, path
from rest_framework import routers

from . import views


urlpatterns = [
    path('workspace/', views.WorkspaceList.as_view()),
    path('workspace/<int:pk>/', views.WorkspaceDetail.as_view()),
    path('invitation/', views.InvitationList.as_view()),
    path('invitation/status/<str:status>', views.InvitationList.as_view()),
    path('invitation/<int:pk>/', views.InvitationDetail.as_view()),
    path('ping', views.Ping.as_view()),
    path('health', views.Health.as_view()),
]
