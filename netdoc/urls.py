from django.urls import path

from netbox.views.generic import ObjectChangeLogView
from . import models, views


urlpatterns = (
    #
    # ARPEntry urls
    #
    
    path('arptable/', views.ArpTableListView.as_view(), name='arptable_list'),
    
    #
    # Credential urls
    #

    path('credentials/', views.CredentialListView.as_view(), name='credential_list'),
    path('credentials/add/', views.CredentialEditView.as_view(), name='credential_add'),
    path('credentials/import/', views.CredentialBulkImportView.as_view(), name='credential_import'),
    path('credentials/edit/', views.CredentialBulkEditView.as_view(), name='credential_bulk_edit'),
    path('credentials/delete/', views.CredentialBulkDeleteView.as_view(), name='credential_bulk_delete'),
    path('credentials/<int:pk>/', views.CredentialView.as_view(), name='credential'),
    path('credentials/<int:pk>/edit/', views.CredentialEditView.as_view(), name='credential_edit'),
    path('credentials/<int:pk>/delete/', views.CredentialDeleteView.as_view(), name='credential_delete'),
    path('credentials/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='credential_changelog', kwargs={
        'model': models.Credential
    }),


    #
    # Discoverable urls
    #
    
    path('discoverable/', views.DiscoverableListView.as_view(), name='discoverable_list'),
    path('discoverable/add/', views.DiscoverableEditView.as_view(), name='discoverable_add'),
    path('discoverable/import/', views.DiscoverableBulkImportView.as_view(), name='discoverable_import'),
    path('discoverable/edit/', views.DiscoverableBulkEditView.as_view(), name='discoverable_bulk_edit'),
    path('discoverable/delete/', views.DiscoverableBulkDeleteView.as_view(), name='discoverable_bulk_delete'),
    path('discoverable/discover/', views.DiscoverableBulkDiscoverView.as_view(), name='discoverable_bulk_discover'),
    path('discoverable/<int:pk>/', views.DiscoverableView.as_view(), name='discoverable'),
    path('discoverable/<int:pk>/edit/', views.DiscoverableEditView.as_view(), name='discoverable_edit'),
    path('discoverable/<int:pk>/delete/', views.DiscoverableDeleteView.as_view(), name='discoverable_delete'),
    path('discoverable/<int:pk>/discover/', views.DiscoverableDiscoverView.as_view(), name='discoverable_discover'),
    path('discoverable/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='discoverable_changelog', kwargs={
        'model': models.Discoverable
    }),

    #
    # DiscoveryLog urls
    #
    
    path('discoverylog/', views.DiscoveryLogListView.as_view(), name='discoverylog_list'),
    path('discoverylog/delete/', views.DiscoveryLogBulkDeleteView.as_view(), name='discoverylog_bulk_delete'),
    path('discoverylog/<int:pk>/', views.DiscoveryLogView.as_view(), name='discoverylog'),
    path('discoverylog/<int:pk>/delete/', views.DiscoveryLogDeleteView.as_view(), name='discoverylog_delete'),

    #
    # MacAddressTableEntry urls
    #
    
    path('macaddresstable/', views.MacAddressTableListView.as_view(), name='macaddresstable_list'),

    #
    # RoutingTableEntry urls
    #

    path('routingtable/', views.RouteTableEntryListView.as_view(), name='routingtable_list')
)
