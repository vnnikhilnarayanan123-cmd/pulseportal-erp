from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.utils import timezone
from .models import (
    Course, InstituteLocation, Batch, StudentProfile,
    AttendanceRecord, LeaveRequest, RegularisationRequest,
    StudyMaterial, TestQuiz, Announcement
)
from .serializers import (
    CourseSerializer, LocationSerializer, BatchSerializer,
    StudentProfileSerializer, StudentRegisterSerializer,
    AttendanceRecordSerializer, LeaveRequestSerializer,
    RegularisationRequestSerializer, StudyMaterialSerializer,
    TestQuizSerializer, AnnouncementSerializer
)

# ----------------- HTML Template Views -----------------

def student_portal(request):
    return render(request, 'student_portal.html')

def faculty_portal(request):
    return render(request, 'faculty_portal.html')

# ----------------- API ViewSets -----------------

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class LocationViewSet(viewsets.ModelViewSet):
    queryset = InstituteLocation.objects.all()
    serializer_class = LocationSerializer

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = StudentRegisterSerializer(data=request.data)
        if serializer.is_valid():
            student = serializer.save()
            return Response({
                "message": "Registration successful",
                "enrollment_no": student.enrollment_no
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        student_id = request.data.get('student')
        session_type = request.data.get('session_type')
        
        try:
            student = StudentProfile.objects.get(id=student_id, is_verified=True)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Verified student profile not found."}, status=status.HTTP_404_NOT_FOUND)
            
        # Simplified for now: Assume within geofence if coordinates are sent
        return Response({
            "status": "Check-in successful",
            "is_within_geofence": True,
            "session_type": session_type,
            "date": str(timezone.now().date())
        })

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        student_id = request.data.get('student')
        try:
            student = StudentProfile.objects.get(id=student_id, is_verified=True)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Verified student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": "Check-out successful",
            "message": f"Punch out recorded successfully for {student.user.get_full_name()}."
        }, status=status.HTTP_200_OK)

class LeaveViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

class RegularisationViewSet(viewsets.ModelViewSet):
    queryset = RegularisationRequest.objects.all()
    serializer_class = RegularisationRequestSerializer

class StudyMaterialViewSet(viewsets.ModelViewSet):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer

class TestQuizViewSet(viewsets.ModelViewSet):
    queryset = TestQuiz.objects.all()
    serializer_class = TestQuizSerializer

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer