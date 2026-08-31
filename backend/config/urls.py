from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from core.views import (
    student_portal, faculty_portal,
    CourseViewSet, LocationViewSet, BatchViewSet,
    StudentViewSet, AttendanceViewSet, LeaveViewSet,
    RegularisationViewSet, CurriculumTopicViewSet,
    AssessmentViewSet, AnnouncementViewSet, FeePaymentViewSet
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'students', StudentViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'leaves', LeaveViewSet)
router.register(r'regularisations', RegularisationViewSet)
router.register(r'curriculum', CurriculumTopicViewSet)
router.register(r'assessments', AssessmentViewSet)
router.register(r'announcements', AnnouncementViewSet)
router.register(r'fees', FeePaymentViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('student/', student_portal, name='student_portal'),
    path('faculty/', faculty_portal, name='faculty_portal'),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)