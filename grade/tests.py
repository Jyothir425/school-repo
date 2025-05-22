from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone # For user creation helper consistency
import datetime # For user creation helper consistency

from .models import Mark
# No direct Exam model import needed here based on actual grade.models.Mark
# from exam.models import Exam 
# No direct Subject model import needed here for Mark model fields
# from user.models import Subject 
from user.models import Account # Mark model links to Account for student and teacher
# For setting up StudentProfile/TeacherProfile if needed by other logic (e.g. views)
from user.models import Student as StudentProfile, Teacher as TeacherProfile 
from classroom.models import Classroom # For setting up Student/Teacher profiles

User = get_user_model()

# Counter for unique elements in tests
phone_counter_grade = 0
classroom_name_counter_grade = 0
# subject_name_counter_grade = 0 # Not directly used by Mark model
# exam_name_counter_grade = 0 # Not directly used by Mark model

def get_unique_phone_number_grade():
    global phone_counter_grade
    phone_counter_grade += 1
    return f"0634567{phone_counter_grade:03d}"

def get_unique_classroom_name_grade(base_name="GradeTestClass"):
    global classroom_name_counter_grade
    classroom_name_counter_grade += 1
    return f"{base_name}{classroom_name_counter_grade}"

# def get_unique_subject_name_grade(base_name="GradeSubject"): # Not needed for Mark model
#     global subject_name_counter_grade
#     subject_name_counter_grade += 1
#     return f"{base_name}{subject_name_counter_grade}"
    
# def get_unique_exam_name_grade(base_name="GradeExam"): # Not needed for Mark model
#     global exam_name_counter_grade
#     exam_name_counter_grade += 1
#     return f"{base_name}{exam_name_counter_grade}"


def create_user_for_grade_tests(email_prefix, user_type_int, name_prefix="GradeUser"):
    """Creates an Account instance and associated profiles if needed for grade app tests."""
    email = f"{email_prefix.lower()}@example.com"
    user_account = User.objects.create_user(
        email=email,
        password="testpassword",
        phone_number=get_unique_phone_number_grade(),
        name=f"{name_prefix} {email_prefix.replace('_', ' ').title()}",
        user_type=user_type_int
    )
    
    # Create profiles which might be indirectly relevant for views, though not for Mark model fields itself
    if user_type_int == 1: # Student
        classroom, _ = Classroom.objects.get_or_create(name=get_unique_classroom_name_grade(f"StudentClassG_{email_prefix}"), defaults={'total_strength': 30})
        parent_account = User.objects.create_user(
            email=f"parentg2_{email_prefix.lower()}@example.com", password="testpassword",
            phone_number=get_unique_phone_number_grade(), name=f"ParentG2 {email_prefix.replace('_', ' ').title()}", user_type=5
        )
        aware_date_of_birth = timezone.make_aware(datetime.datetime(2000, 1, 1, 0, 0, 0))
        StudentProfile.objects.get_or_create(user=user_account, defaults={'classroom': classroom, 'department': "CS", 'location': "Test Location", 'date_of_birth': aware_date_of_birth, 'parent': parent_account})
    elif user_type_int == 2: # Teacher
        classroom, _ = Classroom.objects.get_or_create(name=get_unique_classroom_name_grade(f"TeacherClassG_{email_prefix}"), defaults={'total_strength': 30})
        # Subject model import needed for TeacherProfile
        from user.models import Subject 
        subject, _ = Subject.objects.get_or_create(name=f"TeacherSubjG_{email_prefix}")
        TeacherProfile.objects.get_or_create(user=user_account, defaults={'department': "CS", 'subject': subject, 'classroom': classroom})
    return user_account


class MarkModelTests(TestCase):
    def setUp(self):
        self.student_user = create_user_for_grade_tests("student_for_mark", 1)
        self.teacher_user = create_user_for_grade_tests("teacher_for_mark", 2)
        
        self.mark_data = {
            'student': self.student_user,
            'teacher': self.teacher_user,
            'sub1': "85",
            'sub2': "90",
            'sub3': "78",
        }
        self.mark_instance = Mark.objects.create(**self.mark_data)

    def test_create_mark(self):
        self.assertEqual(Mark.objects.count(), 1)
        mark = Mark.objects.first()
        self.assertEqual(mark.student, self.student_user)
        self.assertEqual(mark.teacher, self.teacher_user)
        self.assertEqual(mark.sub1, "85")
        self.assertEqual(mark.sub2, "90")
        self.assertEqual(mark.sub3, "78")

    def test_update_mark_fields(self):
        self.mark_instance.sub1 = "88"
        self.mark_instance.sub2 = "92"
        # Test updating only some fields
        new_teacher = create_user_for_grade_tests("new_teacher_for_mark", 2)
        self.mark_instance.teacher = new_teacher
        self.mark_instance.save()
        
        updated_mark = Mark.objects.get(id=self.mark_instance.id)
        self.assertEqual(updated_mark.sub1, "88")
        self.assertEqual(updated_mark.sub2, "92")
        self.assertEqual(updated_mark.sub3, "78") # Should remain unchanged
        self.assertEqual(updated_mark.teacher, new_teacher)


    def test_delete_mark(self):
        mark_id = self.mark_instance.id
        self.mark_instance.delete()
        with self.assertRaises(Mark.DoesNotExist):
            Mark.objects.get(id=mark_id)
        self.assertEqual(Mark.objects.count(), 0)

    def test_mark_str_representation(self):
        # Model does not define __str__, so test Django's default
        expected_str = f"Mark object ({self.mark_instance.pk})"
        self.assertEqual(str(self.mark_instance), expected_str)

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class MarkCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher_user = create_user_for_grade_tests("creator_teacher", 2)
        self.student_user_for_mark = create_user_for_grade_tests("mark_student", 1)
        self.non_teacher_user = create_user_for_grade_tests("non_teacher_creator_attempt", 1) # Student

        self.url = reverse('grade:add-mark')
        self.valid_payload = {
            'student': self.student_user_for_mark.id,
            'sub1': "A+",
            'sub2': "B-",
            'sub3': "C"
        }

    def test_create_mark_success_by_teacher(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Mark has been added')
        self.assertTrue(Mark.objects.filter(student=self.student_user_for_mark, teacher=self.teacher_user).exists())
        created_mark = Mark.objects.get(student=self.student_user_for_mark)
        self.assertEqual(created_mark.sub1, self.valid_payload['sub1'])

    def test_create_mark_fail_by_non_teacher(self):
        self.client.force_authenticate(user=self.non_teacher_user)
        response = self.client.post(self.url, self.valid_payload, format='json')
        # IsTeacher permission: For POST, user_type must be 2. Safe methods are allowed for all.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_mark_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsAuthenticated

    def test_create_mark_invalid_payload_missing_student(self):
        self.client.force_authenticate(user=self.teacher_user)
        payload = {'sub1': "A", 'sub2': "B", 'sub3': "C"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('student', response.data)

    def test_create_mark_invalid_payload_missing_sub1(self):
        self.client.force_authenticate(user=self.teacher_user)
        payload = {'student': self.student_user_for_mark.id, 'sub2': "B", 'sub3': "C"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sub1', response.data)


class MarkListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher_user = create_user_for_grade_tests("list_teacher_grade", 2)
        self.student_user_subject_of_mark = create_user_for_grade_tests("list_student_grade_subj", 1)
        self.student_user_viewer = create_user_for_grade_tests("list_student_grade_viewer", 1) # Another student

        Mark.objects.create(student=self.student_user_subject_of_mark, teacher=self.teacher_user, sub1="A", sub2="B", sub3="C")
        Mark.objects.create(student=self.student_user_subject_of_mark, teacher=self.teacher_user, sub1="A-", sub2="B+", sub3="C+")
        
        self.url = reverse('grade:show-mark')

    def test_list_marks_success_by_teacher(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_marks_success_by_student(self):
        # IsTeacher perm allows SAFE_METHODS for all, IsAuthenticated is also there.
        self.client.force_authenticate(user=self.student_user_viewer)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Allowed due to IsTeacher SAFE_METHODS rule
        self.assertEqual(len(response.data), 2)


    def test_list_marks_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Blocked by IsAuthenticated


class MarkDeleteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher_creator = create_user_for_grade_tests("deleter_teacher_creator", 2)
        self.other_teacher = create_user_for_grade_tests("deleter_other_teacher", 2)
        self.student_user_marked = create_user_for_grade_tests("deleter_student_marked", 1)
        self.student_user_non_teacher = create_user_for_grade_tests("deleter_student_non_teacher", 1)


        self.mark_to_delete = Mark.objects.create(
            student=self.student_user_marked, 
            teacher=self.teacher_creator, 
            sub1="X", sub2="Y", sub3="Z"
        )
        self.url = reverse('grade:delete-mark', kwargs={'pk': self.mark_to_delete.pk})

    def test_delete_mark_success_by_creating_teacher(self):
        self.client.force_authenticate(user=self.teacher_creator)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT) # DestroyAPIView default
        self.assertFalse(Mark.objects.filter(pk=self.mark_to_delete.pk).exists())

    def test_delete_mark_success_by_other_teacher(self):
        # IsTeacher does not have object-level permission, so any teacher can delete
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Mark.objects.filter(pk=self.mark_to_delete.pk).exists())

    def test_delete_mark_fail_by_student(self):
        self.client.force_authenticate(user=self.student_user_non_teacher)
        response = self.client.delete(self.url, format='json')
        # IsTeacher will fail for non-safe method
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Mark.objects.filter(pk=self.mark_to_delete.pk).exists())

    def test_delete_mark_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsAuthenticated
        self.assertTrue(Mark.objects.filter(pk=self.mark_to_delete.pk).exists())
