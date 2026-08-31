import uuid
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth import authenticate
from django.db.models import Q

from .models import (
    Course, InstituteLocation, FacultyProfile, Batch, StudentProfile,
    AttendanceRecord, LeaveRequest, RegularisationRequest,
    CurriculumTopic, AssessmentRecord, Announcement, FeePayment
)
from .serializers import (
    CourseSerializer, InstituteLocationSerializer, FacultyProfileSerializer,
    BatchSerializer, StudentProfileSerializer, StudentRegisterSerializer,
    AttendanceRecordSerializer, LeaveRequestSerializer, RegularisationRequestSerializer,
    CurriculumTopicSerializer, AssessmentRecordSerializer, AnnouncementSerializer,
    FeePaymentSerializer
)

# ----------------- UI Views -----------------

def student_portal(request):
    return render(request, 'student_portal.html')

def faculty_portal(request):
    return render(request, 'faculty_portal.html')

# ----------------- REST ViewSets -----------------

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

class LocationViewSet(viewsets.ModelViewSet):
    queryset = InstituteLocation.objects.all()
    serializer_class = InstituteLocationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.filter(is_active=True)
    serializer_class = BatchSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

class StudentViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all().select_related('user', 'batch', 'batch__course', 'batch__batch_owner__user')
    serializer_class = StudentProfileSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def register(self, request):
        try:
            serializer = StudentRegisterSerializer(data=request.data)
            if serializer.is_valid():
                student = serializer.save()
                profile_data = StudentProfileSerializer(student, context={'request': request}).data
                return Response(profile_data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def login(self, request):
        enrollment = request.data.get('enrollment', '').strip().upper()
        password = request.data.get('password', '').strip()
        device_id = request.data.get('device_id', '').strip()

        if not enrollment or not password:
            return Response({"error": "Enrollment number and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=enrollment, password=password)
        if not user:
            return Response({"error": "Invalid enrollment number or password."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            student = StudentProfile.objects.get(user=user)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Student record not found."}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(student, 'active_device_id'):
            if not student.active_device_id:
                student.active_device_id = device_id or str(uuid.uuid4())
                student.is_device_approved = True
                student.save()
            elif student.active_device_id != device_id:
                if not student.is_device_approved:
                    return Response({
                        "error": "New Device / Multiple System Login Detected. Please contact your Batch Owner to approve this system.",
                        "device_requires_approval": True,
                        "enrollment_no": student.enrollment_no
                    }, status=status.HTTP_403_FORBIDDEN)

        profile_data = StudentProfileSerializer(student, context={'request': request}).data
        return Response(profile_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def reset_password(self, request):
        enrollment = request.data.get('enrollment', '').strip().upper()
        email = request.data.get('email', '').strip().lower()
        dob = request.data.get('dob', '').strip()
        new_password = request.data.get('new_password', '').strip()

        if not enrollment or not email or not dob or not new_password:
            return Response({"error": "Enrollment, Email, DOB, and New Password are all required."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({"error": "Password must be at least 6 characters long."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = StudentProfile.objects.get(
                enrollment_no__iexact=enrollment,
                user__email__iexact=email,
                date_of_birth=dob
            )
            user = student.user
            user.set_password(new_password)
            user.save()
            return Response({"status": "success", "message": "Password updated successfully. Please sign in."}, status=status.HTTP_200_OK)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Identity verification failed. Information does not match MIAPE records."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny], authentication_classes=[])
    def find_by_enrollment(self, request):
        enrollment = request.query_params.get('enrollment', '').strip().upper()
        if not enrollment:
            return Response({"error": "Enrollment parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = StudentProfile.objects.get(enrollment_no__iexact=enrollment)
            return Response(StudentProfileSerializer(student, context={'request': request}).data)
        except StudentProfile.DoesNotExist:
            return Response({"error": f"No student found with enrollment '{enrollment}'"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def toggle_approval(self, request, pk=None):
        student = self.get_object()
        approved = request.data.get('is_verified', True)
        student.is_verified = approved
        student.verification_date = timezone.now() if approved else None
        student.save()
        return Response({
            "status": "success",
            "is_verified": student.is_verified,
            "message": f"Student {student.enrollment_no} status updated to {'Approved' if approved else 'Pending'}."
        })

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def mark_dropout(self, request, pk=None):
        student = self.get_object()
        student.is_verified = False
        if student.user:
            student.user.is_active = False
            student.user.save()
        student.save()
        return Response({"status": "success", "message": f"Student {student.enrollment_no} marked as Drop Out."})

    @action(detail=True, methods=['delete'], permission_classes=[AllowAny], authentication_classes=[])
    def remove_student(self, request, pk=None):
        student = self.get_object()
        user = student.user
        student.delete()
        if user:
            user.delete()
        return Response({"status": "success", "message": "Student record permanently deleted."})

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def approve_device(self, request, pk=None):
        student = self.get_object()
        new_device_id = request.data.get('device_id')
        if new_device_id and hasattr(student, 'active_device_id'):
            student.active_device_id = new_device_id
        if hasattr(student, 'is_device_approved'):
            student.is_device_approved = True
            student.save()
        return Response({"status": "success", "message": f"Device authorized for {student.enrollment_no}."})

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def reset_device(self, request, pk=None):
        student = self.get_object()
        if hasattr(student, 'active_device_id'):
            student.active_device_id = None
        if hasattr(student, 'is_device_approved'):
            student.is_device_approved = False
            student.save()
        return Response({"status": "success", "message": f"Device session reset for {student.enrollment_no}. Next login will register their current device."})

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.all().select_related('student', 'student__user', 'location').order_by('-date', '-check_in_time')
    serializer_class = AttendanceRecordSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def check_in(self, request):
        student_id = request.data.get('student')
        lat = request.data.get('latitude')
        lon = request.data.get('longitude')
        session_type = request.data.get('session_type', 'CLASSROOM')

        if not student_id or lat is None or lon is None:
            return Response({"error": "Missing student ID or GPS coordinates."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = StudentProfile.objects.get(id=student_id, is_verified=True)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Verified student profile not found. Please obtain faculty approval first."}, status=status.HTTP_403_FORBIDDEN)

        valid_location = None
        for loc in InstituteLocation.objects.all():
            if loc.is_within_radius(lat, lon):
                valid_location = loc
                break

        if not valid_location:
            return Response({
                "error": "Geofence Violation: You are outside the 900m radius of all MIAPE campuses and Max Hospitals.",
                "is_within_geofence": False
            }, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()
        record, created = AttendanceRecord.objects.get_or_create(
            student=student,
            date=today,
            session_type=session_type,
            defaults={
                'status': 'PRESENT',
                'check_in_time': timezone.now(),
                'location': valid_location,
                'is_geofenced': True
            }
        )

        if not created and record.check_in_time:
            return Response({
                "message": "Check-in already logged for this session today.",
                "check_in_time": record.check_in_time,
                "location": valid_location.name
            }, status=status.HTTP_200_OK)

        record.check_in_time = timezone.now()
        record.status = 'PRESENT'
        record.location = valid_location
        record.save()

        return Response({
            "status": "Check-in successful",
            "location": valid_location.name,
            "session_type": session_type,
            "time": record.check_in_time
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def check_out(self, request):
        student_id = request.data.get('student')
        session_type = request.data.get('session_type', 'CLASSROOM')
        today = timezone.now().date()

        try:
            record = AttendanceRecord.objects.get(student_id=student_id, date=today, session_type=session_type)
            record.check_out_time = timezone.now()
            record.save()
            return Response({
                "status": "Check-out successful",
                "check_out_time": record.check_out_time
            })
        except AttendanceRecord.DoesNotExist:
            return Response({"error": "No check-in record found to punch out for today's session."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def manual_override(self, request):
        student_id = request.data.get('student')
        date_str = request.data.get('date')
        session_type = request.data.get('session_type', 'CLASSROOM')
        status_val = request.data.get('status', 'PRESENT')
        reason = request.data.get('reason', 'Faculty Manual Override')
        location_id = request.data.get('location')

        if not student_id or not date_str:
            return Response({"error": "Student ID and Target Date are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = StudentProfile.objects.get(id=student_id)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        loc = None
        if location_id:
            try:
                loc = InstituteLocation.objects.get(id=location_id)
            except InstituteLocation.DoesNotExist:
                loc = InstituteLocation.objects.first()
        else:
            loc = InstituteLocation.objects.first()

        record, created = AttendanceRecord.objects.get_or_create(
            student=student,
            date=date_str,
            session_type=session_type,
            defaults={
                'status': status_val,
                'check_in_time': timezone.now() if status_val in ['PRESENT', 'ON_DUTY'] else None,
                'location': loc,
                'is_geofenced': False
            }
        )

        record.status = status_val
        if status_val in ['PRESENT', 'ON_DUTY'] and not record.check_in_time:
            record.check_in_time = timezone.now()
        record.location = loc
        record.is_geofenced = False
        record.save()

        return Response({
            "status": "success",
            "message": f"Attendance for {student.enrollment_no} on {date_str} manually updated to {status_val} ({reason}).",
            "date": date_str,
            "record_id": record.id
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def bulk_override(self, request):
        batch_id = request.data.get('batch')
        date_str = request.data.get('date')
        session_type = request.data.get('session_type', 'CLASSROOM')
        status_val = request.data.get('status', 'PRESENT')
        reason = request.data.get('reason', 'Batch Wide Official Exemption')

        if not batch_id or not date_str:
            return Response({"error": "Batch ID and Date are required."}, status=status.HTTP_400_BAD_REQUEST)

        students = StudentProfile.objects.filter(batch_id=batch_id, is_verified=True)
        loc = InstituteLocation.objects.first()

        updated_count = 0
        for st in students:
            record, _ = AttendanceRecord.objects.get_or_create(
                student=st,
                date=date_str,
                session_type=session_type,
                defaults={
                    'status': status_val,
                    'check_in_time': timezone.now() if status_val in ['PRESENT', 'ON_DUTY'] else None,
                    'location': loc,
                    'is_geofenced': False
                }
            )
            record.status = status_val
            record.is_geofenced = False
            record.save()
            updated_count += 1

        return Response({
            "status": "success",
            "message": f"Bulk attendance applied for {updated_count} students in Batch {batch_id} on {date_str}."
        }, status=status.HTTP_200_OK)

class LeaveViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all().select_related('student', 'approved_by', 'student__batch', 'student__user').order_by('-created_at')
    serializer_class = LeaveRequestSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def perform_create(self, serializer):
        student = serializer.validated_data.get('student')
        batch_owner = student.batch.batch_owner if (student and student.batch) else None
        serializer.save(approved_by=batch_owner, status='PENDING')

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def approve_leave(self, request, pk=None):
        leave = self.get_object()
        leave.status = 'APPROVED'
        leave.save()
        return Response({"status": "success", "message": "Leave approved successfully."})

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def reject_leave(self, request, pk=None):
        leave = self.get_object()
        leave.status = 'REJECTED'
        leave.save()
        return Response({"status": "success", "message": "Leave request rejected."})

class RegularisationViewSet(viewsets.ModelViewSet):
    queryset = RegularisationRequest.objects.all().select_related('student', 'reviewed_by').order_by('-created_at')
    serializer_class = RegularisationRequestSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=True, methods=['post'], url_path='approve_request', permission_classes=[AllowAny], authentication_classes=[])
    def approve_request(self, request, pk=None):
        try:
            reg = self.get_object()
            reg.status = 'APPROVED'
            reg.reviewed_at = timezone.now()
            reg.save()

            # Identify target date & session type from request
            target_date = getattr(reg, 'attendance_date', None) or getattr(reg, 'date', None)
            target_session = getattr(reg, 'session_type', 'CLASSROOM')
            loc = InstituteLocation.objects.first()

            if target_date:
                record, _ = AttendanceRecord.objects.get_or_create(
                    student=reg.student,
                    date=target_date,
                    session_type=target_session,
                    defaults={
                        'status': 'PRESENT',
                        'check_in_time': timezone.now(),
                        'location': loc,
                        'is_geofenced': False
                    }
                )
                record.status = 'PRESENT'
                if not record.check_in_time:
                    record.check_in_time = timezone.now()
                record.is_geofenced = False
                record.save()

            return Response({
                "status": "success",
                "message": f"Regularisation for {reg.student.enrollment_no} approved and marked Present."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reject_request', permission_classes=[AllowAny], authentication_classes=[])
    def reject_request(self, request, pk=None):
        try:
            reg = self.get_object()
            reg.status = 'REJECTED'
            reg.reviewed_at = timezone.now()
            reg.save()
            return Response({
                "status": "success",
                "message": f"Regularisation request for {reg.student.enrollment_no} rejected."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class FeePaymentViewSet(viewsets.ModelViewSet):
    queryset = FeePayment.objects.all().select_related('student', 'student__user', 'student__batch', 'approved_by', 'approved_by__user').order_by('-created_at')
    serializer_class = FeePaymentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student')
        status_param = self.request.query_params.get('status')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if status_param:
            queryset = queryset.filter(status__iexact=status_param)
        return queryset

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else request.data
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        payment = serializer.save(status='PENDING')
        return Response(FeePaymentSerializer(payment, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def approve_payment(self, request, pk=None):
        payment = self.get_object()
        if payment.status == 'APPROVED':
            return Response({"message": "Payment is already approved and credited."}, status=status.HTTP_200_OK)

        payment.status = 'APPROVED'
        if not payment.receipt_no:
            year_prefix = timezone.now().strftime('%Y')
            payment.receipt_no = f"MIAPE/REC/{year_prefix}/{payment.id:04d}"
        
        # Credit fee to student balance
        student = payment.student
        student.fee_paid = Decimal(str(student.fee_paid)) + Decimal(str(payment.amount))
        student.save()
        payment.save()

        return Response({
            "status": "success",
            "message": f"Payment of ₹{payment.amount} approved for {student.enrollment_no}. Receipt #{payment.receipt_no} generated.",
            "receipt_no": payment.receipt_no,
            "total_fee_paid": float(student.fee_paid),
            "fee_due": float(student.fee_due)
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def reject_payment(self, request, pk=None):
        payment = self.get_object()
        reason = request.data.get('reason', 'Payment proof verification failed / UTR mismatch.')

        # If it was previously approved, revert credited amount
        if payment.status == 'APPROVED':
            student = payment.student
            student.fee_paid = max(Decimal('0.00'), Decimal(str(student.fee_paid)) - Decimal(str(payment.amount)))
            student.save()

        payment.status = 'REJECTED'
        payment.rejection_reason = reason
        payment.save()

        return Response({
            "status": "success",
            "message": f"Payment proof rejected for {payment.student.enrollment_no}."
        }, status=status.HTTP_200_OK)

class CurriculumTopicViewSet(viewsets.ModelViewSet):
    queryset = CurriculumTopic.objects.all().order_by('order', 'id')
    serializer_class = CurriculumTopicSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else request.data
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def toggle_unlock(self, request, pk=None):
        topic = self.get_object()
        unlocked = request.data.get('is_ppt_unlocked', not topic.is_ppt_unlocked)
        topic.is_ppt_unlocked = unlocked
        topic.save()
        return Response({"status": "success", "is_ppt_unlocked": topic.is_ppt_unlocked})

class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = AssessmentRecord.objects.all().select_related('student', 'student__user').order_by('-conducted_date', '-id')
    serializer_class = AssessmentRecordSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        student_id = request.data.get('student')
        title = request.data.get('title')
        exam_type = request.data.get('exam_type', 'REVISION')
        marks_obtained = request.data.get('marks_obtained')
        max_marks = request.data.get('max_marks', 100)

        if not student_id or not title or marks_obtained is None:
            return Response({"error": "Student, Title, and Marks Obtained are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = StudentProfile.objects.get(id=student_id)
            assessment = AssessmentRecord.objects.create(
                student=student,
                title=title,
                exam_type=exam_type,
                marks_obtained=marks_obtained,
                max_marks=max_marks,
                conducted_date=timezone.now().date()
            )
            serializer = self.get_serializer(assessment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [AllowAny]
    authentication_classes = []