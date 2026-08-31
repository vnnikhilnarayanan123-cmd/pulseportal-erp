from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, 
    LocationViewSet, 
    BatchViewSet, 
    StudentViewSet,
    AttendanceViewSet, 
    LeaveViewSet, 
    RegularisationViewSet,
    StudyMaterialViewSet, 
    TestQuizViewSet, 
    AnnouncementViewSet,
    FeePaymentViewSet  # Ensure FeePaymentViewSet is imported from .views
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'students', StudentViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'leaves', LeaveViewSet)
router.register(r'regularisations', RegularisationViewSet)

# Endpoints matching student and faculty portal JavaScript:
router.register(r'curriculum', StudyMaterialViewSet, basename='curriculum')
router.register(r'materials', StudyMaterialViewSet, basename='materials')
router.register(r'assessments', TestQuizViewSet, basename='assessments')
router.register(r'tests', TestQuizViewSet, basename='tests')
router.register(r'fees', FeePaymentViewSet, basename='fees')
router.register(r'announcements', AnnouncementViewSet, basename='announcements')

urlpatterns = [
    path('', include(router.urls)),
]