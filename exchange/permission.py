from rest_framework import permissions

from user.models import Teacher
from .models import Question


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.user_type == 1:
            return request.user
        return False

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanAccessComment(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanAddComment(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            teacher = Teacher.objects.get(user_id=request.user.id) # Use request.user.id
            question_id = request.data.get('question')
            if not question_id:
                return False # 'question' ID not provided in payload
            question = Question.objects.get(id=question_id)
            
            # Check if teacher's subject matches the question's tag (which is a Subject instance)
            if teacher.subject and question.tag and teacher.subject.id == question.tag.id:
                return True
        except Teacher.DoesNotExist:
            return False # User is not a teacher or has no TeacherProfile
        except Question.DoesNotExist:
            return False # Question specified in payload does not exist
        except Exception: # Catch any other unexpected errors
            return False
        return False


class CanUpvote(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user != request.user


class CanRemoveUpvote(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.user_type == 2:
            return request.user
        return False



#restxcyjgvhbklnm;,wserxtcgfbhj
