from django.db.models import Count

import django_rq

from netbox.views import generic
from utilities.permissions import get_permission_for_model
from . import models, tables, forms, filtersets


import logging
import re
from collections import defaultdict
from copy import deepcopy

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import ManyToManyField, ProtectedError
from django.forms import Form, ModelMultipleChoiceField, MultipleHiddenInput
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2.export import TableExport

from extras.models import ExportTemplate
from extras.signals import clear_webhooks
from utilities.error_handlers import handle_protectederror
from utilities.exceptions import PermissionsViolation
from utilities.forms import (
    BootstrapMixin, BulkRenameForm, ConfirmationForm, CSVDataField, CSVFileField, restrict_form_fields,
)
from utilities.htmx import is_htmx
from utilities.permissions import get_permission_for_model
from utilities.views import GetReturnURLMixin
from netbox.views.generic.base import BaseMultiObjectView
from utilities.utils import get_viewname, normalize_querydict, prepare_cloned_fields
from django.urls import reverse
from . import tasks
from . import filtersets


#
# ARPEntry views
#

class ArpTableListView(generic.ObjectListView):
    queryset = models.ArpTableEntry.objects.all()
    table = tables.ArpTableEntryTable
    actions = ()
    filterset = filtersets.ArpTableEntryFilterSet


#
# Credential views
#

class CredentialListView(generic.ObjectListView):
    queryset = models.Credential.objects.annotate(
        discoverables_count=Count('discoverables')
    )
    table = tables.CredentialTable
    filterset = filtersets.CredentialFilterSet


class CredentialView(generic.ObjectView):
    queryset = models.Credential.objects.all()

    def get_extra_context(self, request, instance):
        table = tables.DiscoverableTable(instance.discoverables.all())
        table.configure(request)

        return {
            'discoverables_table': table,
        }


class CredentialEditView(generic.ObjectEditView):
    queryset = models.Credential.objects.all()
    form = forms.CredentialForm


class CredentialDeleteView(generic.ObjectDeleteView):
    queryset = models.Credential.objects.all()


class CredentialBulkImportView(generic.BulkImportView):
    queryset = models.Credential.objects.all()
    model_form = forms.CredentialCSVForm
    table = tables.CredentialTable


class CredentialBulkEditView(generic.BulkEditView):
    queryset = models.Credential.objects.all()
    table = tables.CredentialTable
    form = forms.CredentialBulkEditForm


class CredentialBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Credential.objects.all()
    table = tables.CredentialTable
    default_return_url = 'netdoc:credential_list'


#
# Discoverable views
#

class DiscoverableListView(generic.ObjectListView):
    queryset = models.Discoverable.objects.annotate(
        discoverylogs_count=Count('discoverylogs')
    )
    table = tables.DiscoverableTable
    actions = ('add', 'import', 'export', 'discover', 'bulk_edit', 'bulk_delete', 'bulk_discover')
    template_name = 'netdoc/discoverable_list.html'
    filterset = filtersets.DiscoverableFilterSet


class DiscoverableView(generic.ObjectView):
    queryset = models.Discoverable.objects.annotate(
        discoverylogs_count=Count('discoverylogs')
    )

    def get_extra_context(self, request, instance):
        table = tables.DiscoveryLogTable(instance.discoverylogs.all())
        table.configure(request)

        return {
            'discoverylogs_table': table,
        }


class DiscoverableEditView(generic.ObjectEditView):
    queryset = models.Discoverable.objects.all()
    form = forms.DiscoverableForm


class DiscoverableDeleteView(generic.ObjectDeleteView):
    queryset = models.Discoverable.objects.all()


class DiscoverableBulkImportView(generic.BulkImportView):
    queryset = models.Discoverable.objects.all()
    model_form = forms.DiscoverableCSVForm
    table = tables.DiscoverableTable


class DiscoverableBulkEditView(generic.BulkEditView):
    queryset = models.Discoverable.objects.prefetch_related('credential')
    table = tables.DiscoverableTable
    form = forms.DiscoverableBulkEditForm


class DiscoverableBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Discoverable.objects.prefetch_related('credential')
    table = tables.DiscoverableTable
    default_return_url = 'netdoc:discoverable_list'


class DiscoverableDiscoverView(generic.ObjectDeleteView):
    """
    Discover a single object.

    Called from:
    * DiscoverableListView clicking on the Discovery button on a specific Discoverable row.
    * DiscoverableView clicking on the Discovery button.
    """
    queryset = models.Discoverable.objects.all()
    template_name = 'netdoc/discoverable_discover.html'

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, 'change')

    #
    # Request handlers
    #

    def get(self, request, *args, **kwargs):
        """
        Return the confirmation page.
        """
        obj = self.get_object(**kwargs)
        form = ConfirmationForm(initial=request.GET)

        # If this is an HTMX request, return only the rendered deletion form as modal content
        if is_htmx(request):
            # Called from DiscoverableView
            viewname = get_viewname(self.queryset.model, action='discover')
            form_url = reverse(viewname, kwargs={'pk': obj.pk})
            return render(request, 'netdoc/htmx/discover_form.html', {
                'object': obj,
                'object_type': self.queryset.model._meta.verbose_name,
                'form': form,
                'form_url': form_url,
                **self.get_extra_context(request, obj),
            })

        # Called from DiscoverableViewList
        return render(request, self.template_name, {
            'object': obj,
            'form': form,
            'return_url': self.get_return_url(request, obj),
            **self.get_extra_context(request, obj),
        })

    def post(self, request, *args, **kwargs):
        """
        Start the discovery.
        """
        logger = logging.getLogger('netbox.plugins.netdoc')
        obj = self.get_object(**kwargs)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            logger.debug("Form validation was successful")
            queryset = self.queryset.filter(pk=obj.pk)
            addresses = [obj.address]

            # Starting discovery job on default queue
            queue = django_rq.get_queue('default')
            queue.enqueue(tasks.discovery, addresses)

            msg = 'Stareted discovery on {}'.format(obj)
            logger.info(msg)
            messages.success(request, msg)

            return_url = form.cleaned_data.get('return_url')
            if return_url and return_url.startswith('/'):
                return redirect(return_url)
            return redirect(self.get_return_url(request, obj))

        else:
            logger.debug("Form validation failed")
            pass

        return render(request, self.template_name, {
            'object': obj,
            'form': form,
            'return_url': self.get_return_url(request, obj),
            **self.get_extra_context(request, obj),
        })


class DiscoverableBulkDiscoverView(generic.BulkDeleteView):
    """
    Disocver devices in bulk.

    Called from:
    * DiscoverableListView selecting Discoverable(s) and clicking on Disocver Selected button.
    """
    template_name = 'netdoc/discoverable_bulk_discover.html'
    queryset = models.Discoverable.objects.prefetch_related('credential')
    filterset = None
    table = tables.DiscoverableTable
    default_return_url = 'netdoc:discoverable_list'

    def get_required_permission(self):
        """
        Return the confirmation page.
        """
        return get_permission_for_model(self.queryset.model, 'change')

    def post(self, request, **kwargs):
        """
        Start the discovery.
        """
        logger = logging.getLogger('netbox.plugins.netdoc')
        model = self.queryset.model

        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get('_all'):
            qs = model.objects.all()
            if self.filterset is not None:
                qs = self.filterset(request.GET, qs).qs
            pk_list = qs.only('pk').values_list('pk', flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist('pk')]

        form_cls = self.get_form()

        if '_confirm' in request.POST:
            form = form_cls(request.POST)
            if form.is_valid():
                logger.debug("Form validation was successful")
                queryset = self.queryset.filter(pk__in=pk_list)
                discovery_count = queryset.count()
                addresses = list(queryset.values_list('address', flat=True))

                # Starting discovery job on default queue
                queue = django_rq.get_queue('default')
                queue.enqueue(tasks.discovery, addresses)

                msg = f"Started discovery on {discovery_count} {model._meta.verbose_name_plural}"
                logger.info(msg)
                messages.success(request, msg)
                return redirect(self.get_return_url(request))

            else:
                logger.debug("Form validation failed")

        else:
            form = form_cls(initial={
                'pk': pk_list,
                'return_url': self.get_return_url(request),
            })

        # Retrieve objects being deleted
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(request, "No {} were selected for discovery.".format(model._meta.verbose_name_plural))
            return redirect(self.get_return_url(request))

        return render(request, self.template_name, {
            'model': model,
            'form': form,
            'table': table,
            'return_url': self.get_return_url(request),
            **self.get_extra_context(request),
        })


#
# DiscoveryLog views
#

class DiscoveryLogListView(generic.ObjectListView):
    queryset = models.DiscoveryLog.objects.all()
    table = tables.DiscoveryLogTable
    actions = ('delete', 'bulk_delete')
    filterset = filtersets.DiscoveryLogFilterSet
    filterset_form = forms.DiscoveryLogListFilterForm


class DiscoveryLogView(generic.ObjectView):
    queryset = models.DiscoveryLog.objects.all()


class DiscoveryLogDeleteView(generic.ObjectDeleteView):
    queryset = models.DiscoveryLog.objects.all()


class DiscoveryLogBulkDeleteView(generic.BulkDeleteView):
    queryset = models.DiscoveryLog.objects.all()
    table = tables.DiscoveryLogTable
    default_return_url = 'netdoc:discoverylog_list'


#
# MacAddressTableEntry views
#

class MacAddressTableListView(generic.ObjectListView):
    queryset = models.MacAddressTableEntry.objects.all()
    table = tables.MacAddressTableEntryTable
    actions = ()
    filterset = filtersets.MacAddressTableEntryFilterSet


#
# RouteTableEntry view
#

class RouteTableEntryListView(generic.ObjectListView):
    queryset = models.RouteTableEntry.objects.all()
    table = tables.RouteTableEntryTable
    actions = ()
    filterset = filtersets.RouteTableEntryFilterSet
