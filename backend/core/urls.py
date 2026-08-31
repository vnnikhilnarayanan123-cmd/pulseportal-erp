from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, LocationViewSet, BatchViewSet, StudentViewSet,
    AttendanceViewSet, LeaveViewSet, RegularisationViewSet,
    StudyMaterialViewSet, TestQuizViewSet, AnnouncementViewSet
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'students', StudentViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'leaves', LeaveViewSet)
router.register(r'regularisations', RegularisationViewSet)
router.register(r'materials', StudyMaterialViewSet)
router.register(r'tests', TestQuizViewSet)
router.register(r'announcements', AnnouncementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]