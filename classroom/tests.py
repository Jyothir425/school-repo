from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from .models import Classroom

User = get_user_model()

# Helper to create users if needed for 'created_by' or 'modified_by' fields, if they exist.
# Based on classroom/models.py, Classroom model does not have user foreign keys.

class ClassroomModelTests(TestCase):
    def setUp(self):
        self.classroom_data = {
            'name': "Class 10A",
            'total_strength': 30
        }
        self.classroom = Classroom.objects.create(**self.classroom_data)

    def test_create_classroom(self):
        self.assertEqual(Classroom.objects.count(), 1)
        created_classroom = Classroom.objects.first()
        self.assertEqual(created_classroom.name, self.classroom_data['name'])
        self.assertEqual(created_classroom.total_strength, self.classroom_data['total_strength'])
        # Assuming models.py from previous task (name unique=True, total_strength IntegerField)

    def test_update_classroom_name(self):
        new_name = "Class 10B"
        self.classroom.name = new_name
        self.classroom.save()
        updated_classroom = Classroom.objects.get(id=self.classroom.id)
        self.assertEqual(updated_classroom.name, new_name)

    def test_update_classroom_strength(self):
        new_strength = 35
        self.classroom.total_strength = new_strength
        self.classroom.save()
        updated_classroom = Classroom.objects.get(id=self.classroom.id)
        self.assertEqual(updated_classroom.total_strength, new_strength)

    def test_delete_classroom(self):
        classroom_id = self.classroom.id
        self.classroom.delete()
        with self.assertRaises(Classroom.DoesNotExist):
            Classroom.objects.get(id=classroom_id)
        self.assertEqual(Classroom.objects.count(), 0)

    def test_classroom_name_unique_constraint(self):
        # Attempt to create another classroom with the same name
        with self.assertRaises(IntegrityError): # Django raises IntegrityError for unique constraints
            Classroom.objects.create(name=self.classroom_data['name'], total_strength=25)
            
    def test_classroom_str_representation(self):
        # The model does not define __str__, so it will use Django's default.
        # Default is typically "<ClassName> object (<pk>)"
        expected_str = f"Classroom object ({self.classroom.pk})"
        self.assertEqual(str(self.classroom), expected_str)

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

# Helper function to create users of specific types for permission testing
# Counter for unique phone numbers for classroom tests
phone_counter_classroom = 0

def get_unique_phone_number_classroom():
    global phone_counter_classroom
    phone_counter_classroom += 1
    return f"0334567{phone_counter_classroom:03d}"

def create_user_for_classroom_tests(email_prefix, user_type_int, name_prefix="ClassroomTestUser"):
    email = f"{email_prefix.lower()}@example.com"
    user_account = User.objects.create_user(
        email=email,
        password="testpassword",
        phone_number=get_unique_phone_number_classroom(), # Use helper for unique phone
        name=f"{name_prefix} {email_prefix.replace('_', ' ').title()}",
        user_type=user_type_int
    )
    # No specific classroom-related profiles needed for these Account instances for now
    return user_account


class ClassroomCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # User with Management type (user_type=4, assuming based on IsManagement perm name)
        self.management_user = create_user_for_classroom_tests("mgmt_user", 4)
        # User without Management type (e.g., Teacher, user_type=2)
        self.teacher_user = create_user_for_classroom_tests("teacher_user_no_mgmt", 2)
        
        self.url = reverse('classroom:add-classroom')
        self.valid_payload = {
            'name': "New Class Alpha",
            'total_strength': 25
        }

    def test_create_classroom_success_by_management(self):
        self.client.force_authenticate(user=self.management_user)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # View returns 200 OK
        # The message "Classroom attendance successfully." is likely a typo in the view.
        # Test for it as is, but note it.
        self.assertEqual(response.data['message'], 'Classroom attendance successfully.')
        self.assertTrue(Classroom.objects.filter(name=self.valid_payload['name']).exists())
        created_classroom = Classroom.objects.get(name=self.valid_payload['name'])
        self.assertEqual(created_classroom.total_strength, self.valid_payload['total_strength'])

    def test_create_classroom_fail_by_non_management(self):
        self.client.force_authenticate(user=self.teacher_user) # Teacher user
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsManagement permission

    def test_create_classroom_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsAuthenticated permission

    def test_create_classroom_invalid_payload_missing_name(self):
        self.client.force_authenticate(user=self.management_user)
        invalid_payload = {'total_strength': 30}
        response = self.client.post(self.url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_create_classroom_invalid_payload_missing_strength(self):
        self.client.force_authenticate(user=self.management_user)
        invalid_payload = {'name': "Class Beta"}
        response = self.client.post(self.url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_strength', response.data)

    def test_create_classroom_duplicate_name(self):
        self.client.force_authenticate(user=self.management_user)
        # Create first classroom
        Classroom.objects.create(name="Duplicate Test Class", total_strength=20)
        # Attempt to create another with the same name
        duplicate_payload = {'name': "Duplicate Test Class", 'total_strength': 22}
        response = self.client.post(self.url, duplicate_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data) # Serializer should raise validation error for unique name


class ClassroomListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher_user = create_user_for_classroom_tests("list_teacher", 2) # Teacher
        self.management_user = create_user_for_classroom_tests("list_mgmt", 4) # Management (not a Teacher)
        
        # Create some classrooms
        self.classroom1 = Classroom.objects.create(name="Listed Class 1", total_strength=30)
        self.classroom2 = Classroom.objects.create(name="Listed Class 2", total_strength=25)
        
        self.url = reverse('classroom:show-classroom')

    def test_list_classrooms_success_by_teacher(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        classroom_names_in_response = [c['name'] for c in response.data]
        self.assertIn(self.classroom1.name, classroom_names_in_response)
        self.assertIn(self.classroom2.name, classroom_names_in_response)

    def test_list_classrooms_fail_by_non_teacher(self):
        # e.g., Management user trying to access teacher-only list view
        self.client.force_authenticate(user=self.management_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsTeacher permission

    def test_list_classrooms_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsAuthenticated permission

    def test_list_classrooms_empty(self):
        # Delete existing classrooms for this test
        Classroom.objects.all().delete()
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


!@##$%^&*
