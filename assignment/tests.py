from django.test import TestCase
from django.contrib.auth import get_user_model # Import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Assignment, AssignmentMark
from .serializers import AssignmentSerializer, AssignmentMarkSerializer
import datetime

User = get_user_model() # Use the custom user model


class AssignmentModelTests(TestCase):
    def setUp(self):
        self.assignment_data = {'name': 'Test Assignment', 'type': 1}
        self.assignment = Assignment.objects.create(**self.assignment_data)

    def test_create_assignment(self):
        self.assertEqual(Assignment.objects.count(), 1)
        self.assertEqual(self.assignment.name, self.assignment_data['name'])
        self.assertEqual(self.assignment.type, self.assignment_data['type'])

    def test_update_assignment(self):
        new_name = "Updated Assignment Name"
        self.assignment.name = new_name
        self.assignment.save()
        updated_assignment = Assignment.objects.get(id=self.assignment.id)
        self.assertEqual(updated_assignment.name, new_name)

    def test_delete_assignment(self):
        self.assignment.delete()
        self.assertEqual(Assignment.objects.count(), 0)


# Create your tests here.


class AssignmentMarkModelTests(TestCase):
    def setUp(self):
        self.assignment = Assignment.objects.create(name='Test Assignment', type=1)
        self.assignment_mark_data = {'assignment': self.assignment, 'mark': 'A+'}
        self.assignment_mark = AssignmentMark.objects.create(**self.assignment_mark_data)

    def test_create_assignment_mark(self):
        self.assertEqual(AssignmentMark.objects.count(), 1)
        self.assertEqual(self.assignment_mark.assignment, self.assignment_mark_data['assignment'])
        self.assertEqual(self.assignment_mark.mark, self.assignment_mark_data['mark'])

    def test_update_assignment_mark(self):
        new_mark = "B-"
        self.assignment_mark.mark = new_mark
        self.assignment_mark.save()
        updated_assignment_mark = AssignmentMark.objects.get(id=self.assignment_mark.id)
        self.assertEqual(updated_assignment_mark.mark, new_mark)

    def test_delete_assignment_mark(self):
        self.assignment_mark.delete()
        self.assertEqual(AssignmentMark.objects.count(), 0)


class AssignmentCreateViewTests(TestCase): # Changed APIClient to TestCase
    def setUp(self):
        # Removed username='testuser' as the custom Account model uses email as USERNAME_FIELD
        self.user = User.objects.create_user(email='testuser@example.com', password='testpassword', phone_number='1234567890', name='Test User')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.assignment_data = {'name': 'Test Assignment View', 'type': 2}

    def test_create_assignment_view_success(self):
        url = '/assignment/create/'  # Assuming this is the correct URL from urls.py
        response = self.client.post(url, self.assignment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Based on view logic, it returns 200 OK
        self.assertEqual(Assignment.objects.count(), 1)
        self.assertEqual(Assignment.objects.get().name, self.assignment_data['name'])

    def test_create_assignment_view_invalid_data(self):
        url = '/assignment/create/'
        invalid_data = {'name': '', 'type': 1} # Invalid name
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) # serializer.is_valid(raise_exception=True)
        self.assertEqual(Assignment.objects.count(), 0)

    def test_create_assignment_view_unauthenticated(self):
        self.client.force_authenticate(user=None) # Logout
        url = '/assignment/create/'
        response = self.client.post(url, self.assignment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Changed from 401 to 403
        self.assertEqual(Assignment.objects.count(), 0)


class AssignmentMarkCreateViewTests(TestCase):
    def setUp(self):
        # Removed username='testuser' and added 'name' as it's a required field for Account model based on its fields
        self.user = User.objects.create_user(email='testuser@example.com', password='testpassword', phone_number='1234567890', name='Test User Mark')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.assignment = Assignment.objects.create(name='Test Assignment for Mark', type=1)
        self.assignment_mark_data = {'assignment': self.assignment.id, 'mark': 'A'}

    def test_create_assignment_mark_view_success(self):
        url = '/assignment/mark/add/' # Assuming this is the correct URL from urls.py
        response = self.client.post(url, self.assignment_mark_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Based on view logic
        self.assertEqual(AssignmentMark.objects.count(), 1)
        self.assertEqual(AssignmentMark.objects.get().mark, self.assignment_mark_data['mark'])

    def test_create_assignment_mark_view_invalid_data(self):
        url = '/assignment/mark/add/'
        # Invalid data: non-existent assignment id
        invalid_data = {'assignment': 999, 'mark': 'B'}
        response = self.client.post(url, invalid_data, format='json')
        # The serializer will raise an error because the assignment_id is not valid.
        # Depending on how DRF handles this, it could be a 400 or if the serializer is not robust, a 500.
        # Assuming AssignmentMarkSerializer uses PrimaryKeyRelatedField for 'assignment'
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AssignmentMark.objects.count(), 0)

    def test_create_assignment_mark_view_unauthenticated(self):
        self.client.force_authenticate(user=None) # Logout
        url = '/assignment/mark/add/'
        response = self.client.post(url, self.assignment_mark_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Changed from 401 to 403
        self.assertEqual(AssignmentMark.objects.count(), 0)


@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
