import math
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Course(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=30, unique=True)
    duration_months = models.PositiveIntegerField(default=24)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class InstituteLocation(models.Model):
    name = models.CharField(max_length=150)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_meters = models.PositiveIntegerField(default=900)
    is_hospital = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.radius_meters}m)"

    def is_within_radius(self, user_lat, user_lon):
        r_earth = 6371000.0  # Earth's radius in meters
        phi1 = math.radians(float(self.latitude))
        phi2 = math.radians(float(user_lat))
        delta_phi = math.radians(float(user_lat) - float(self.latitude))
        delta_lambda = math.radians(float(user_lon) - float(self.longitude))

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance = r_earth * c
        return distance <= self.radius_meters

class FacultyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

class Batch(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    batch_owner = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_batches')
    start_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        owner_name = self.batch_owner.user.get_full_name() if self.batch_owner else 'No Owner Assigned'
        return f"{self.name} - {self.course.code} ({owner_name})"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    enrollment_no = models.CharField(max_length=60, unique=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='students')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=120000.00)
    fee_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def fee_due(self):
        return self.total_fee - self.fee_paid

    def get_attendance_percentage(self, days=30):
        cutoff_date = timezone.now().date() - timezone.timedelta(days=days)
        records = AttendanceRecord.objects.filter(student=self, date__gte=cutoff_date)
        total_sessions = records.count()
        if total_sessions == 0:
            return 0.0
        present_count = records.filter(status='PRESENT').count()
        return round((present_count / total_sessions) * 100, 1)

    def __str__(self):
        return f"{self.enrollment_no} - {self.user.get_full_name()}"

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LEAVE', 'Approved Leave'),
        ('HOLIDAY', 'Holiday'),
    ]
    SESSION_TYPES = [
        ('CLASSROOM', 'Classroom Theory Session'),
        ('CLINICAL', 'Clinical / OT Posting'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='CLASSROOM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    location = models.ForeignKey(InstituteLocation, on_delete=models.SET_NULL, null=True, blank=True)
    is_geofenced = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'date', 'session_type')

    def __str__(self):
        return f"{self.student.enrollment_no} | {self.date} | {self.status}"

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('SICK', 'Medical Leave'),
        ('CASUAL', 'Casual Leave'),
        ('DUTY', 'Special Duty'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES, default='SICK')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Leave: {self.student.enrollment_no} ({self.status})"

class RegularisationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='regularisation_requests')
    attendance_date = models.DateField()
    session_type = models.CharField(max_length=20, default='CLASSROOM')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Regularisation: {self.student.enrollment_no} - {self.attendance_date}"

class CurriculumTopic(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    ppt_file = models.FileField(upload_to='curriculum_ppts/', blank=True, null=True)
    is_ppt_unlocked = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.batch.name} - Topic: {self.title}"

class AssessmentRecord(models.Model):
    EXAM_TYPES = [
        ('REVISION', 'Revision Test'),
        ('MONTHLY', 'Monthly Module Test'),
        ('SEMESTER', 'Semester Final Examination'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=150)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default='REVISION')
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    conducted_date = models.DateField(default=timezone.now)

    @property
    def percentage(self):
        if self.max_marks > 0:
            return round((self.marks_obtained / self.max_marks) * 100, 1)
        return 0.0

    def __str__(self):
        return f"{self.student.enrollment_no} - {self.title} ({self.marks_obtained}/{self.max_marks})"

class Announcement(models.Model):
    ALERT_TYPES = [
        ('GENERAL', 'General Notice'),
        ('EMERGENCY', 'Emergency Alert'),
        ('FEE', 'Fee Reminder'),
        ('SCHEDULE', 'Schedule Change'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='GENERAL')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, help_text="Leave blank for institute-wide broadcast")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.alert_type}] {self.title}"

class FeePayment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Verification'),
        ('APPROVED', 'Approved / Credited'),
        ('REJECTED', 'Rejected'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('UPI', 'UPI / QR Code'),
        ('NETBANKING', 'Net Banking / NEFT / RTGS'),
        ('CARD', 'Debit / Credit Card'),
        ('CASH', 'Cash Counter'),
        ('CHEQUE', 'Cheque / DD'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fee_payments')
    installment_name = models.CharField(max_length=100, default='Semester Installment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='UPI')
    transaction_ref = models.CharField(max_length=100, blank=True, null=True, help_text="UTR / UPI Ref / Cheque No.")
    proof_document = models.FileField(upload_to='fee_proofs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    receipt_no = models.CharField(max_length=50, blank=True, null=True, unique=True)
    payment_date = models.DateField(default=timezone.now)
    approved_by = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status == 'APPROVED' and not self.receipt_no:
            year_prefix = timezone.now().strftime('%Y')
            self.receipt_no = f"MIAPE/REC/{year_prefix}/{self.id or uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.enrollment_no} - ₹{self.amount} ({self.status})"