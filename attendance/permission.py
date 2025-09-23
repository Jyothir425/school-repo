from rest_framework import permissions

from .models import MainAttendance
from user.models import Student


class CanAddAttendance(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.data['attendance_type'] == 1:
            if request.user.user_type == 2:
                return True
        elif request.data['attendance_type'] == 2:
            if request.user.user_type == 3:
                return True
        elif request.data['attendance_type'] == 3:
            if request.user.user_type == 4:
                return True
        else:
            return False


class CanMarkAttendance(permissions.BasePermission):
    def has_permission(self, request, view):
        # Ensure 'attendance' key exists in request data
        attendance_id = request.data.get('attendance')
        if not attendance_id:
            return False # Should be caught by serializer ideally, but good to be safe

        try:
            attendance = MainAttendance.objects.get(id=attendance_id)
        except MainAttendance.DoesNotExist:
            return False # MainAttendance record does not exist

        # This permission, when used with StudentAttendanceCreateView, assumes IsStudent has already passed.
        # If used elsewhere, it might need to be more robust or split.
        # For StudentAttendanceCreateView, request.user IS a student.
        try:
            student_profile = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            # This case should ideally not be reached if IsStudent permission is checked first.
            return False 

        # Logic for student marking their own attendance (type 1)
        if attendance.attendance_type == 1 and attendance.classroom == student_profile.classroom:
            # User type check already handled by IsStudent if ordered correctly
            return True
        
        # The original permission had logic for type 2 and 3 based on student.classroom,
        # which seems incorrect. If this permission is *only* for students marking *student* attendance,
        # then the following is not needed.
        # For TeacherAttendanceCreateView, a different permission or logic will apply.
        # For now, let's assume CanMarkAttendance for Student view only cares about student attendance (type 1).

        # Example for teacher marking their own, if IsTeacher and a similar CanMarkTeacherAttendance perm existed:
        # elif attendance.attendance_type == 2: # and some logic for teacher profile classroom/subject
        #     # teacher_profile = Teacher.objects.get(user=request.user) # (requires Teacher model import)
        #     # if request.user.user_type == 2 and relevant_teacher_condition:
        #     #     return True
        #     pass

        return False # Default to deny if no specific condition met


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.user_type == 1:
            return True # Corrected to return True/False
        return False


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        # The original logic `if request.method in permissions.SAFE_METHODS: return True`
        # might be too permissive for a CreateAPIView if it's not read-only.
        # For a CreateAPIView (POST), we usually only care about the user type for creation.
        if request.user.user_type == 2:
                return True
        else:
            return False


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.user_type == 1:
            return request.user
        return False


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.user_type == 2:
            return True
        return False
