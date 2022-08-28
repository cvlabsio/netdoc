from netbox.api.routers import NetBoxRouter
from . import views


app_name = 'nedoc'

router = NetBoxRouter()
router.register('credentials', views.CredentialViewSet)
router.register('discoverables', views.DiscoverableViewSet)
router.register('discoverylogs', views.DiscoveryLogViewSet)

urlpatterns = router.urls
