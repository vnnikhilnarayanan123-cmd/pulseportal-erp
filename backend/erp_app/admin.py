from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import (
    Course, InstituteLocation, FacultyProfile, Batch, StudentProfile,
    AttendanceRecord, LeaveRequest, RegularisationRequest,
    CurriculumTopic, AssessmentRecord, Announcement
)

# Custom header branding
admin.site.site_header = "MIAPE Academic ERP - Super Admin Console"
admin.site.site_title = "MIAPE Admin"
admin.site.index_title = "Academic Operations & Faculty Governance Desk"


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'get_full_name', 'get_email', 'department', 'phone', 'is_admin', 'get_active_status']
    list_filter = ['is_admin', 'department', 'user__is_active']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'user__email', 'phone']
    actions = ['approve_faculty_logins', 'revoke_faculty_logins']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "Faculty Name"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"

    def get_active_status(self, obj):
        return obj.user.is_active
    get_active_status.boolean = True
    get_active_status.short_description = "Login Authorized"

    @admin.action(description="✓ Approve & Authorize Faculty Logins")
    def approve_faculty_logins(self, request, queryset):
        for profile in queryset:
            profile.user.is_active = True
            profile.user.is_staff = True
            profile.user.save()
        self.message_user(request, f"{queryset.count()} faculty member(s) login access approved successfully.")

    @admin.action(description="✗ Revoke / Block Faculty Logins")
    def revoke_faculty_logins(self, request, queryset):
        for profile in queryset:
            profile.user.is_active = False
            profile.user.save()
        self.message_user(request, f"{queryset.count()} faculty member(s) login access revoked.")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'course', 'batch_owner', 'start_date', 'is_active']
    list_filter = ['is_active', 'course', 'batch_owner']
    search_fields = ['name', 'course__name', 'batch_owner__user__first_name', 'batch_owner__user__last_name']
    list_editable = ['batch_owner', 'is_active']
    autocomplete_fields = ['batch_owner']


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['enrollment_no', 'get_full_name', 'batch', 'is_verified', 'verification_date', 'fee_paid', 'fee_due']
    list_filter = ['is_verified', 'batch', 'batch__course']
    search_fields = ['enrollment_no', 'user__first_name', 'user__last_name', 'user__email', 'phone']
    list_editable = ['is_verified']
    actions = ['approve_students', 'revoke_students']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "Student Name"

    @admin.action(description="✓ Approve Selected Student Admissions")
    def approve_students(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} student(s) approved.")

    @admin.action(description="✗ Revoke Student Admissions")
    def revoke_students(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f"{queryset.count()} student(s) set to pending.")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'duration_months']
    search_fields = ['code', 'name']


@admin.register(InstituteLocation)
class InstituteLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'latitude', 'longitude', 'radius_meters', 'is_active']
    list_editable = ['radius_meters', 'is_active']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'leave_type', 'start_date', 'end_date', 'status', 'approved_by']
    list_filter = ['status', 'leave_type']
    list_editable = ['status']


@admin.register(CurriculumTopic)
class CurriculumTopicAdmin(admin.ModelAdmin):
    list_display = ['batch', 'title', 'is_ppt_unlocked', 'order']
    list_editable = ['is_ppt_unlocked', 'order']
    list_filter = ['batch', 'is_ppt_unlocked']


@admin.register(AssessmentRecord)
class AssessmentRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'exam_type', 'marks_obtained', 'max_marks', 'percentage', 'conducted_date']
    list_filter = ['exam_type', 'conducted_date']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'batch', 'created_at']
    list_filter = ['batch', 'created_at']