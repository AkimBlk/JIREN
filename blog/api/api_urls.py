"""
URL configuration for blog API endpoints.
"""
from django.urls import path, re_path

from .api_views_tag import TagViewSet
from .api_views_ticket import TicketTagViewSet

# Simple tag endpoints using path converters
tag_views = TagViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

tag_detail_views = TagViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

# Ticket tag endpoints
ticket_tag_views = TicketTagViewSet()

urlpatterns = [
    # Tag listing and creation per project
    path('projects/<int:project_id>/tags/', 
         tag_views, 
         name='project-tags-list'),
    
    # Tag detail (retrieve, update, delete)
    path('projects/<int:project_id>/tags/<int:pk>/', 
         tag_detail_views, 
         name='project-tags-detail'),
    
    # Ticket tag management
    path('tickets/<int:ticket_id>/tags/add/', 
         TicketTagViewSet.as_view({'post': 'add_tag'}), 
         name='ticket-tag-add'),
    
    path('tickets/<int:ticket_id>/tags/remove/', 
         TicketTagViewSet.as_view({'post': 'remove_tag'}), 
         name='ticket-tag-remove'),
    
    path('tickets/<int:ticket_id>/tags/', 
         TicketTagViewSet.as_view({'get': 'list_tags'}), 
         name='ticket-tags-list'),
]
