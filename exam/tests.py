from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError # For testing unique constraints
from django.utils import timezone # Import timezone
import datetime # Import datetime

from .models import Exam # Only Exam model exists
from classroom.models import Classroom # Exam model has a ForeignKey to Classroom
from user.models import Subject, Teacher as TeacherProfile # Import Subject and TeacherProfile

User = get_user_model()

# Counter for unique elements in tests
phone_counter_exam = 0
classroom_name_counter_exam = 0
exam_name_counter = 0
subject_name_counter_exam = 0 # Add counter for subject name

def get_unique_phone_number_exam():
    global phone_counter_exam
    phone_counter_exam += 1
    return f"0434567{phone_counter_exam:03d}"

def get_unique_classroom_name_exam(base_name="ExamTestClass"):
    global classroom_name_counter_exam
    classroom_name_counter_exam += 1
    return f"{base_name}{classroom_name_counter_exam}"

def get_unique_exam_name(base_name="Test Exam"):
    global exam_name_counter
    exam_name_counter += 1
    return f"{base_name} {exam_name_counter}"

def get_unique_subject_name_exam(base_name="ExamSubject"): # Re-define the helper
    global subject_name_counter_exam
    subject_name_counter_exam += 1
    return f"{base_name}{subject_name_counter_exam}"

# User creation helper - might be useful for view tests later if permissions are involved
def create_user_for_exam_tests(email_prefix, user_type_int, name_prefix="ExamUser"):
    email = f"{email_prefix.lower()}@example.com"
    user_account = User.objects.create_user(
        email=email,
        password="testpassword",
        phone_number=get_unique_phone_number_exam(),
        name=f"{name_prefix} {email_prefix.replace('_', ' ').title()}",
        user_type=user_type_int
    )
    return user_account


class ExamModelTests(TestCase):
    def setUp(self):
        self.classroom = Classroom.objects.create(
            name=get_unique_classroom_name_exam("SetupClass"), 
            total_strength=30
        )
        
        self.exam_data = {
            'name': get_unique_exam_name("Midterm Math"),
            'classroom': self.classroom,
        }
        self.exam = Exam.objects.create(**self.exam_data)

    def test_create_exam(self):
        self.assertEqual(Exam.objects.count(), 1)
        exam = Exam.objects.first()
        self.assertEqual(exam.name, self.exam_data['name'])
        self.assertEqual(exam.classroom, self.classroom)

    def test_update_exam_name(self):
        new_name = get_unique_exam_name("Final Math Exam")
        self.exam.name = new_name
        self.exam.save()
        updated_exam = Exam.objects.get(id=self.exam.id)
        self.assertEqual(updated_exam.name, new_name)

    def test_update_exam_classroom(self):
        new_classroom = Classroom.objects.create(
            name=get_unique_classroom_name_exam("NewExamClass"),
            total_strength=25
        )
        self.exam.classroom = new_classroom
        self.exam.save()
        updated_exam = Exam.objects.get(id=self.exam.id)
        self.assertEqual(updated_exam.classroom, new_classroom)

    def test_delete_exam(self):
        exam_id = self.exam.id
        self.exam.delete()
        with self.assertRaises(Exam.DoesNotExist):
            Exam.objects.get(id=exam_id)
        self.assertEqual(Exam.objects.count(), 0)

    def test_exam_name_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            Exam.objects.create(name=self.exam_data['name'], classroom=self.classroom)

    def test_exam_str_representation(self):
        # The model does not define __str__, so it will use Django's default.
        expected_str = f"Exam object ({self.exam.pk})"
        self.assertEqual(str(self.exam), expected_str)

# QuestionModelTests and AnswerModelTests removed as these models do not exist.

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch # For mocking Twilio

from user.models import Student as StudentProfile # Parent is an Account instance, not a separate model

# Helper to create student with parent for SMS test
def create_student_with_parent_for_exam_tests(email_prefix, classroom, parent_phone_base="0555123"):
    global phone_counter_exam # Reuse existing counter for uniqueness
    phone_counter_exam +=1
    
    parent_user = User.objects.create_user(
        email=f"parent_{email_prefix}@example.com",
        password="testpassword",
        phone_number=f"{parent_phone_base}{phone_counter_exam:03d}", # Unique phone for parent
        name=f"Parent of {email_prefix}",
        user_type=5 # Parent user type
    )
    # Parent model might be directly the Account, or a separate ParentProfile.
    # Based on user/models.py (from previous tasks), Student.parent is FK to Account.
    # So parent_user is the parent.

    student_user = User.objects.create_user(
        email=f"{email_prefix}@example.com",
        password="testpassword",
        phone_number=get_unique_phone_number_exam(), # Ensure this is unique from parent
        name=f"Student {email_prefix}",
        user_type=1 # Student
    )
    StudentProfile.objects.create(
        user=student_user, 
        classroom=classroom, 
        department="TestDept", 
        location="TestLoc",
        date_of_birth=timezone.make_aware(datetime.datetime(2005, 5, 5)),
        parent=parent_user # Assign parent Account instance
    )
    return student_user, parent_user


class ExamCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Classroom that the teacher is associated with
        self.teacher_classroom = Classroom.objects.create(
            name=get_unique_classroom_name_exam("TeacherClassExam"), 
            total_strength=30
        )
        
        # Teacher user, ensuring TeacherProfile is created and linked to the classroom
        self.teacher_user_account = User.objects.create_user(
            email="teacher_exam_view@example.com",
            password="testpassword",
            phone_number=get_unique_phone_number_exam(),
            name="Exam View Teacher",
            user_type=2 # Teacher
        )
        # Subject needed for TeacherProfile
        teacher_subject, _ = Subject.objects.get_or_create(name=get_unique_subject_name_exam("ExamViewSubj"))
        TeacherProfile.objects.create(
            user=self.teacher_user_account, 
            department="Science", 
            subject=teacher_subject, 
            classroom=self.teacher_classroom # Link teacher to the specific classroom
        )

        # Create some students in the teacher's classroom with parents having phone numbers
        self.student1, self.parent1 = create_student_with_parent_for_exam_tests("stud1_exam", self.teacher_classroom)
        self.student2, self.parent2 = create_student_with_parent_for_exam_tests("stud2_exam", self.teacher_classroom)

        # Non-teacher user for permission tests
        self.student_user_account = create_user_for_exam_tests("student_exam_perms", 1) # Student
        
        self.url = reverse('exam:create-question') # URL name is 'create-question'
        self.valid_payload = {
            'name': get_unique_exam_name("Finals Prep"),
            # 'classroom' is NOT in payload, derived from teacher
        }

    @patch('exam.views.Client') # Mock Twilio Client at exam.views location
    def test_create_exam_success_by_teacher(self, mock_twilio_client):
        # Configure the mock client and its messages.create method
        mock_messages_create = mock_twilio_client.return_value.messages.create
        
        self.client.force_authenticate(user=self.teacher_user_account)
        response = self.client.post(self.url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Exam created successfully')
        self.assertTrue(Exam.objects.filter(name=self.valid_payload['name']).exists())
        
        created_exam = Exam.objects.get(name=self.valid_payload['name'])
        self.assertEqual(created_exam.classroom, self.teacher_classroom) # Check correct classroom
        
        # Check if SMS sending was attempted for the parents in the teacher's classroom
        self.assertTrue(mock_messages_create.called)
        # Expected phone numbers (ensure they are prefixed with +countrycode if Twilio needs it, model stores them raw)
        # The view's send_sms adds '+', so we check for that.
        # The current model for Account.phone_number doesn't specify format. Assuming raw numbers.
        # The view's send_sms loops through phone numbers.
        
        # Get expected parent phone numbers
        expected_numbers = sorted([self.parent1.phone_number, self.parent2.phone_number])
        
        # Get actual numbers `to` which SMS was sent
        actual_to_numbers = sorted([call_args[1]['to'] for call_args in mock_messages_create.call_args_list])
        
        # Twilio expects E.164 format. The `send_sms` method prepends `+`.
        # Let's assume the phone numbers in DB are raw and `send_sms` correctly formats them.
        # The mock will receive the `to` argument as passed by `send_sms`.
        # If `send_sms` adds `+` itself, then `actual_to_numbers` will have `+`.
        # If `send_sms` does not add `+` and numbers are raw, then Twilio client would fail or format.
        # The current send_sms in view: `from_ = '+14192739589'`, `to=to` (raw number from DB)
        # This means Twilio client receives raw numbers.
        # The mock will capture whatever is passed to `to`.
        # For robustness, let's assume send_sms passes numbers as they are.
        
        # The view's send_sms method is:
        # for to in phone_number:
        #    response = client.messages.create(body=message, to=to, from_=from_)
        # So, `to` will be the raw phone number from `parents_phoneno`.
        
        self.assertEqual(actual_to_numbers, expected_numbers)
        self.assertEqual(mock_messages_create.call_count, len(expected_numbers))


    def test_create_exam_fail_by_student(self):
        self.client.force_authenticate(user=self.student_user_account)
        with patch('exam.views.Client') as mock_twilio_client: # Mock Twilio even for failure paths
            response = self.client.post(self.url, self.valid_payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsTeacher permission
            mock_twilio_client.return_value.messages.create.assert_not_called()


    def test_create_exam_unauthenticated(self):
        self.client.force_authenticate(user=None)
        with patch('exam.views.Client') as mock_twilio_client:
            response = self.client.post(self.url, self.valid_payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsAuthenticated permission
            mock_twilio_client.return_value.messages.create.assert_not_called()

    @patch('exam.views.Client')
    def test_create_exam_invalid_payload_missing_name(self, mock_twilio_client):
        self.client.force_authenticate(user=self.teacher_user_account)
        invalid_payload = {} # 'name' is the only field in serializer
        response = self.client.post(self.url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        mock_twilio_client.return_value.messages.create.assert_not_called()

    @patch('exam.views.Client')
    def test_create_exam_teacher_not_in_teacher_profile(self, mock_twilio_client):
        # Create a user with user_type=2 (Teacher) but no TeacherProfile record
        teacher_account_no_profile = User.objects.create_user(
            email="teacher_no_profile@example.com", password="testpassword",
            phone_number=get_unique_phone_number_exam(), name="No Profile Teacher", user_type=2
        )
        self.client.force_authenticate(user=teacher_account_no_profile)
        response = self.client.post(self.url, self.valid_payload, format='json')
        # View does Teacher.objects.filter(user_id=request.user).get()
        # This will raise Teacher.DoesNotExist, leading to an unhandled server error (500)
        # if not caught by DRF's exception handling or a try-except in the view.
        # DRF's default exception handler might convert DoesNotExist to 404 if it's from a get_object_or_404 type call,
        # but here it's a direct .get(). This typically results in a 500.
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR) 
        mock_twilio_client.return_value.messages.create.assert_not_called()
