from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

from .models import (
    Course, InstituteLocation, FacultyProfile, Batch, StudentProfile,
    AttendanceRecord, LeaveRequest, RegularisationRequest,
    CurriculumTopic, AssessmentRecord, Announcement, FeePayment
)

class InstituteLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstituteLocation
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class FacultyProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = FacultyProfile
        fields = ['id', 'employee_id', 'full_name', 'email', 'department', 'phone', 'is_admin']

    def get_full_name(self, obj):
        if obj.user:
            name = obj.user.get_full_name().strip()
            return name if name else obj.user.username
        return "Faculty Member"

class BatchSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = ['id', 'name', 'course', 'course_name', 'course_code', 'batch_owner', 'owner_name', 'start_date', 'is_active']

    def get_owner_name(self, obj):
        if obj.batch_owner and obj.batch_owner.user:
            user = obj.batch_owner.user
            name = user.get_full_name().strip()
            return name if name else user.username
        return "Not Assigned"

class StudentRegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    batch_name = serializers.CharField(write_only=True, required=True)
    pilot_passcode = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = StudentProfile
        fields = ['enrollment_no', 'phone', 'date_of_birth', 'batch_name', 'pilot_passcode', 'first_name', 'last_name', 'email', 'password']

    def validate_enrollment_no(self, value):
        normalized = value.strip().upper()
        if StudentProfile.objects.filter(enrollment_no__iexact=normalized).exists() or User.objects.filter(username__iexact=normalized).exists():
            raise serializers.ValidationError(f"Student with Enrollment No '{normalized}' is already registered.")
        return normalized

    def validate(self, data):
        # 1. Pilot Passcode Verification
        PILOT_KEY = "PILOT2026"
        if data.get('pilot_passcode', '').strip() != PILOT_KEY:
            raise serializers.ValidationError({"pilot_passcode": "Invalid Pilot Access Passcode. Registration is restricted to authorized pilot testers only."})

        # 2. Resolve or dynamically auto-create batch
        batch_name_input = data.get('batch_name', '').strip()
        if not batch_name_input:
            raise serializers.ValidationError({"batch_name": "Batch name is required."})

        batch = Batch.objects.filter(name__iexact=batch_name_input, is_active=True).first()

        if not batch:
            default_course = Course.objects.first()
            if not default_course:
                default_course = Course.objects.create(
                    name="Diploma in Operation Theatre Technology",
                    code="DOTT",
                    duration_months=24
                )
            batch = Batch.objects.create(
                name=batch_name_input,
                course=default_course,
                is_active=True
            )

        data['resolved_batch'] = batch
        return data

    def create(self, validated_data):
        enrollment = validated_data['enrollment_no']
        batch = validated_data['resolved_batch']

        user = User.objects.create_user(
            username=enrollment,
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        student = StudentProfile.objects.create(
            user=user,
            enrollment_no=enrollment,
            batch=batch,
            phone=validated_data.get('phone', ''),
            date_of_birth=validated_data.get('date_of_birth', None),
            is_verified=False
        )
        return student

class CurriculumTopicSerializer(serializers.ModelSerializer):
    ppt_url = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumTopic
        fields = ['id', 'batch', 'title', 'description', 'ppt_file', 'is_ppt_unlocked', 'order', 'ppt_url']
        extra_kwargs = {
            'ppt_file': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_blank': True},
            'is_ppt_unlocked': {'required': False},
            'order': {'required': False}
        }

    def get_ppt_url(self, obj):
        if obj.is_ppt_unlocked and obj.ppt_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.ppt_file.url)
            return obj.ppt_file.url
        return None

class AssessmentRecordSerializer(serializers.ModelSerializer):
    percentage = serializers.ReadOnlyField()

    class Meta:
        model = AssessmentRecord
        fields = ['id', 'student', 'title', 'exam_type', 'max_marks', 'marks_obtained', 'percentage', 'conducted_date']

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'

class AttendanceRecordSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format='%Y-%m-%d')
    student_name = serializers.SerializerMethodField()
    enrollment_no = serializers.CharField(source='student.enrollment_no', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'student', 'student_name', 'enrollment_no', 'date',
            'session_type', 'status', 'check_in_time', 'check_out_time',
            'location', 'location_name', 'is_geofenced'
        ]

    def get_student_name(self, obj):
        if obj.student and obj.student.user:
            name = obj.student.user.get_full_name().strip()
            return name if name else obj.student.user.username
        return "Student"

class LeaveRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    enrollment_no = serializers.CharField(source='student.enrollment_no', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'student', 'student_name', 'enrollment_no', 'leave_type', 'start_date', 'end_date', 'reason', 'status', 'approved_by', 'created_at']

    def get_student_name(self, obj):
        if obj.student and obj.student.user:
            name = obj.student.user.get_full_name().strip()
            return name if name else obj.student.user.username
        return "Student"

class RegularisationRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    enrollment_no = serializers.CharField(source='student.enrollment_no', read_only=True)

    class Meta:
        model = RegularisationRequest
        fields = ['id', 'student', 'student_name', 'enrollment_no', 'attendance_date', 'session_type', 'reason', 'status', 'reviewed_by', 'created_at']

    def get_student_name(self, obj):
        if obj.student and obj.student.user:
            name = obj.student.user.get_full_name().strip()
            return name if name else obj.student.user.username
        return "Student"

class FeePaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    enrollment_no = serializers.CharField(source='student.enrollment_no', read_only=True)
    batch_name = serializers.CharField(source='student.batch.name', read_only=True)
    course_name = serializers.CharField(source='student.batch.course.name', read_only=True)
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = FeePayment
        fields = [
            'id', 'student', 'student_name', 'enrollment_no', 'batch_name', 'course_name',
            'installment_name', 'amount', 'payment_mode', 'transaction_ref',
            'proof_document', 'proof_url', 'status', 'receipt_no', 'payment_date',
            'approved_by', 'rejection_reason', 'created_at'
        ]
        extra_kwargs = {
            'proof_document': {'required': False, 'allow_null': True},
            'receipt_no': {'read_only': True}
        }

    def get_student_name(self, obj):
        if obj.student and obj.student.user:
            name = obj.student.user.get_full_name().strip()
            return name if name else obj.student.user.username
        return "Student"

    def get_proof_url(self, obj):
        if obj.proof_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proof_document.url)
            return obj.proof_document.url
        return None

class StudentProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    course_name = serializers.CharField(source='batch.course.name', read_only=True)
    batch_owner_name = serializers.SerializerMethodField()
    fee_due = serializers.ReadOnlyField()
    weekly_attendance = serializers.SerializerMethodField()
    monthly_attendance = serializers.SerializerMethodField()
    yearly_attendance = serializers.SerializerMethodField()
    is_birthday_today = serializers.SerializerMethodField()
    curriculum_topics = serializers.SerializerMethodField()
    assessments = serializers.SerializerMethodField()
    announcements = serializers.SerializerMethodField()
    fee_payments = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'enrollment_no', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'date_of_birth',
            'batch', 'batch_name', 'course_name', 'batch_owner_name', 'is_verified', 'verification_date',
            'total_fee', 'fee_paid', 'fee_due', 'weekly_attendance', 'monthly_attendance', 'yearly_attendance',
            'is_birthday_today', 'active_device_id', 'is_device_approved',
            'curriculum_topics', 'assessments', 'announcements', 'fee_payments'
        ]

    def get_full_name(self, obj):
        if obj.user:
            name = obj.user.get_full_name().strip()
            return name if name else obj.user.username
        return "Student"

    def get_batch_owner_name(self, obj):
        if obj.batch and obj.batch.batch_owner and obj.batch.batch_owner.user:
            user = obj.batch.batch_owner.user
            name = user.get_full_name().strip()
            return name if name else user.username
        return "Pending Assignment"

    def get_weekly_attendance(self, obj):
        return obj.get_attendance_percentage(days=7)

    def get_monthly_attendance(self, obj):
        return obj.get_attendance_percentage(days=30)

    def get_yearly_attendance(self, obj):
        return obj.get_attendance_percentage(days=365)

    def get_is_birthday_today(self, obj):
        if not obj.date_of_birth:
            return False
        today = timezone.now().date()
        return obj.date_of_birth.month == today.month and obj.date_of_birth.day == today.day

    def get_curriculum_topics(self, obj):
        if not obj.batch:
            return []
        topics = CurriculumTopic.objects.filter(batch=obj.batch).order_by('order')
        return CurriculumTopicSerializer(topics, many=True, context=self.context).data

    def get_assessments(self, obj):
        records = AssessmentRecord.objects.filter(student=obj).order_by('-conducted_date', '-id')
        return AssessmentRecordSerializer(records, many=True).data

    def get_announcements(self, obj):
        if obj.batch:
            records = Announcement.objects.filter(Q(batch=obj.batch) | Q(batch__isnull=True)).order_by('-created_at')[:8]
        else:
            records = Announcement.objects.filter(batch__isnull=True).order_by('-created_at')[:8]
        return AnnouncementSerializer(records, many=True).data

    def get_fee_payments(self, obj):
        payments = FeePayment.objects.filter(student=obj).order_by('-created_at')
        return FeePaymentSerializer(payments, many=True, context=self.context).data