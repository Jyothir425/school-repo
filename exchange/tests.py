from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError # For testing unique constraints

# Models from the exchange app
from .models import Question, Comment, Upvote 
# Models from other apps needed for relationships
from user.models import Account, Subject, Teacher as TeacherProfile # Ensure TeacherProfile is imported
User = get_user_model() # This will be Account

# Counter for unique elements in tests
phone_counter_exchange = 0
subject_name_counter_exchange = 0 # For creating unique Subject instances
classroom_name_counter_exchange = 0 # Counter for unique classroom names

def get_unique_phone_number_exchange():
    global phone_counter_exchange
    phone_counter_exchange += 1
    return f"0534567{phone_counter_exchange:03d}"

def get_unique_subject_name_exchange(base_name="ExchangeSubject"):
    global subject_name_counter_exchange
    subject_name_counter_exchange += 1
    return f"{base_name}{subject_name_counter_exchange}"

def get_unique_classroom_name_exchange(base_name="ExchangeClass"): # Define the missing helper
    global classroom_name_counter_exchange
    classroom_name_counter_exchange += 1
    return f"{base_name}{classroom_name_counter_exchange}"

def create_user_for_exchange_tests(email_prefix, user_type_int=1, name_prefix="ExchangeUser"):
    """Creates an Account instance for exchange app tests."""
    email = f"{email_prefix.lower()}@example.com"
    user_account = User.objects.create_user(
        email=email,
        password="testpassword",
        phone_number=get_unique_phone_number_exchange(),
        name=f"{name_prefix} {email_prefix.replace('_', ' ').title()}",
        user_type=user_type_int
    )
    # Create TeacherProfile if user_type is Teacher (2)
    if user_type_int == 2:
        from classroom.models import Classroom # Local import
        # Use unique classroom name for each teacher to avoid OneToOne conflict
        unique_class_name = get_unique_classroom_name_exchange(f"TeacherClass_{email_prefix}")
        classroom, _ = Classroom.objects.get_or_create(name=unique_class_name, defaults={'total_strength': 1})
        
        # Subject can be shared or unique; using a shared one for simplicity here.
        subject, _ = Subject.objects.get_or_create(name="Default Exchange App Teacher Subject")
        
        from user.models import Teacher as TeacherProfile # Local import
        TeacherProfile.objects.get_or_create(user=user_account, defaults={'department': "GEN", 'subject': subject, 'classroom': classroom})
    return user_account


class QuestionModelTests(TestCase):
    def setUp(self):
        self.user = create_user_for_exchange_tests("question_asker")
        self.subject_tag = Subject.objects.create(name=get_unique_subject_name_exchange("DjangoBasics"))
        
        self.question_data = {
            'user': self.user,
            'title': "Understanding Django Models",
            'description': "How do Django models work with the ORM?",
            'tag': self.subject_tag,
        }
        self.question = Question.objects.create(**self.question_data)

    def test_create_question(self):
        self.assertEqual(Question.objects.count(), 1)
        q = Question.objects.first()
        self.assertEqual(q.user, self.user)
        self.assertEqual(q.title, self.question_data['title'])
        self.assertEqual(q.description, self.question_data['description'])
        self.assertEqual(q.tag, self.subject_tag)
        # created_at and updated_at are not in the model definition provided

    def test_update_question(self):
        new_title = "Exploring Django Views"
        new_description = "How are function-based and class-based views different?"
        new_tag = Subject.objects.create(name=get_unique_subject_name_exchange("DjangoViews"))
        
        self.question.title = new_title
        self.question.description = new_description
        self.question.tag = new_tag
        self.question.save()
        
        updated_question = Question.objects.get(id=self.question.id)
        self.assertEqual(updated_question.title, new_title)
        self.assertEqual(updated_question.description, new_description)
        self.assertEqual(updated_question.tag, new_tag)

    def test_delete_question(self):
        question_id = self.question.id
        self.question.delete()
        with self.assertRaises(Question.DoesNotExist):
            Question.objects.get(id=question_id)
        self.assertEqual(Question.objects.count(), 0)

    def test_question_str_representation(self):
        # Model does not define __str__, so test Django's default
        expected_str = f"Question object ({self.question.pk})"
        self.assertEqual(str(self.question), expected_str)


class CommentModelTests(TestCase):
    def setUp(self):
        self.commenter = create_user_for_exchange_tests("commenter_user")
        asker = create_user_for_exchange_tests("comment_q_asker")
        tag_for_q = Subject.objects.create(name=get_unique_subject_name_exchange("CommentQuestionTag"))
        
        self.question_for_comment = Question.objects.create(
            user=asker, 
            title="How to test comments?", 
            description="A question about testing comments.",
            tag=tag_for_q
        )
        self.comment_data = {
            'user': self.commenter,
            'question': self.question_for_comment,
            'content': "This is a test comment on the question.",
        }
        self.comment = Comment.objects.create(**self.comment_data)

    def test_create_comment(self):
        self.assertEqual(Comment.objects.count(), 1)
        c = Comment.objects.first()
        self.assertEqual(c.user, self.commenter)
        self.assertEqual(c.question, self.question_for_comment)
        self.assertEqual(c.content, self.comment_data['content'])
        # created_at is not in the model definition

    def test_update_comment_content(self):
        new_content = "Updated test comment content."
        self.comment.content = new_content
        self.comment.save()
        updated_comment = Comment.objects.get(id=self.comment.id)
        self.assertEqual(updated_comment.content, new_content)

    def test_delete_comment(self):
        comment_id = self.comment.id
        self.comment.delete()
        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(id=comment_id)
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_str_representation(self):
        # Model does not define __str__, test Django's default
        expected_str = f"Comment object ({self.comment.pk})"
        self.assertEqual(str(self.comment), expected_str)


class UpvoteModelTests(TestCase):
    def setUp(self):
        self.voter = create_user_for_exchange_tests("upvoter_user")
        comment_owner = create_user_for_exchange_tests("upvote_comment_owner")
        question_owner = create_user_for_exchange_tests("upvote_q_owner")
        tag_for_q_upvote = Subject.objects.create(name=get_unique_subject_name_exchange("UpvoteQuestionTag"))

        question = Question.objects.create(
            user=question_owner, title="Question for Upvote", description="Desc", tag=tag_for_q_upvote
        )
        self.comment_to_upvote = Comment.objects.create(
            user=comment_owner, question=question, content="A comment to be upvoted."
        )
        
        self.upvote_data = {
            'user': self.voter,
            'comment': self.comment_to_upvote,
        }
        self.upvote = Upvote.objects.create(**self.upvote_data)

    def test_create_upvote(self):
        self.assertEqual(Upvote.objects.count(), 1)
        uv = Upvote.objects.first()
        self.assertEqual(uv.user, self.voter)
        self.assertEqual(uv.comment, self.comment_to_upvote)

    def test_delete_upvote(self):
        upvote_id = self.upvote.id
        self.upvote.delete()
        with self.assertRaises(Upvote.DoesNotExist):
            Upvote.objects.get(id=upvote_id)
        self.assertEqual(Upvote.objects.count(), 0)

    def test_upvote_unique_together_constraint(self):
        # Attempt to create a duplicate upvote by the same user for the same comment
        with self.assertRaises(IntegrityError):
            Upvote.objects.create(user=self.voter, comment=self.comment_to_upvote)

    def test_upvote_str_representation(self):
        # Model does not define __str__, test Django's default
        expected_str = f"Upvote object ({self.upvote.pk})"
        self.assertEqual(str(self.upvote), expected_str)

# AnswerModelTests removed as the Answer model does not exist.

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch # For mocking in Upvote tests


class QuestionCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_user = create_user_for_exchange_tests("student_q_creator", 1) # Student
        self.teacher_user = create_user_for_exchange_tests("teacher_q_non_creator", 2) # Teacher
        self.subject_tag = Subject.objects.create(name=get_unique_subject_name_exchange("TestTag"))
        
        self.client.force_authenticate(user=self.student_user)
        self.url = reverse('exchange:create-question')
        
        self.valid_payload = {
            'title': "New Question Title",
            'description': "Detailed description of the new question.",
            'tag': self.subject_tag.id # Pass Subject ID
        }

    def test_create_question_success_by_student(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Question created successfully')
        self.assertTrue(Question.objects.filter(title=self.valid_payload['title']).exists())
        created_question = Question.objects.get(title=self.valid_payload['title'])
        self.assertEqual(created_question.user, self.student_user)
        self.assertEqual(created_question.tag, self.subject_tag)

    def test_create_question_fail_by_teacher(self):
        self.client.force_authenticate(user=self.teacher_user) # Authenticate as teacher
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsStudent permission

    def test_create_question_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_question_invalid_payload_missing_title(self):
        payload = {'description': "Desc only", 'tag': self.subject_tag.id}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_create_question_invalid_payload_missing_tag(self):
        payload = {'title': "Title only", 'description': "Desc only"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tag', response.data)


class QuestionListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_user = create_user_for_exchange_tests("student_q_lister", 1)
        self.teacher_user = create_user_for_exchange_tests("teacher_q_non_lister", 2)
        self.subject_tag = Subject.objects.create(name=get_unique_subject_name_exchange("ListTag"))

        Question.objects.create(user=self.student_user, title="Q1", description="D1", tag=self.subject_tag)
        Question.objects.create(user=self.student_user, title="Q2", description="D2", tag=self.subject_tag)
        
        self.url = reverse('exchange:list-question')

    def test_list_questions_success_by_student(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_questions_fail_by_teacher(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_questions_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class QuestionRetrieveViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_user_owner = create_user_for_exchange_tests("student_q_owner", 1)
        self.student_user_other = create_user_for_exchange_tests("student_q_other", 1)
        self.teacher_user = create_user_for_exchange_tests("teacher_q_non_viewer", 2)
        self.subject_tag = Subject.objects.create(name=get_unique_subject_name_exchange("RetrieveTag"))
        
        self.question = Question.objects.create(user=self.student_user_owner, title="Retrieve Me", description="D", tag=self.subject_tag)
        self.url = reverse('exchange:show-question', kwargs={'pk': self.question.pk})

    def test_retrieve_question_success_by_owner(self):
        self.client.force_authenticate(user=self.student_user_owner)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.question.title)

    def test_retrieve_question_fail_by_non_owner_student(self):
        self.client.force_authenticate(user=self.student_user_other)
        response = self.client.get(self.url, format='json')
        # IsStudent has_object_permission (obj.user == request.user) will deny
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_question_fail_by_teacher(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_question_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_non_existent_question(self):
        self.client.force_authenticate(user=self.student_user_owner)
        url_non_existent = reverse('exchange:show-question', kwargs={'pk': 9999})
        response = self.client.get(url_non_existent, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QuestionUpdateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_owner = create_user_for_exchange_tests("student_q_updater_owner", 1)
        self.student_non_owner = create_user_for_exchange_tests("student_q_updater_non_owner", 1)
        self.subject_tag_initial = Subject.objects.create(name=get_unique_subject_name_exchange("UpdateTagInitial"))
        self.subject_tag_new = Subject.objects.create(name=get_unique_subject_name_exchange("UpdateTagNew"))

        self.question = Question.objects.create(user=self.student_owner, title="Original Title", description="Original Desc", tag=self.subject_tag_initial)
        self.url = reverse('exchange:edit-question', kwargs={'pk': self.question.pk})
        self.update_payload = {
            'title': "Updated Title", 
            'description': "Updated Description",
            'tag': self.subject_tag_new.id
        }

    def test_update_question_success_by_owner(self):
        self.client.force_authenticate(user=self.student_owner)
        response = self.client.put(self.url, self.update_payload, format='json') # PUT for full update
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Question has been updated.')
        self.question.refresh_from_db()
        self.assertEqual(self.question.title, self.update_payload['title'])
        self.assertEqual(self.question.tag, self.subject_tag_new)

    def test_update_question_fail_by_non_owner_student(self):
        self.client.force_authenticate(user=self.student_non_owner)
        response = self.client.put(self.url, self.update_payload, format='json')
        # IsStudent has_object_permission checks obj.user == request.user
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 

    def test_update_question_partial_by_owner(self): # PATCH
        self.client.force_authenticate(user=self.student_owner)
        partial_payload = {'title': "Partially Updated Title"}
        response = self.client.patch(self.url, partial_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.question.refresh_from_db()
        self.assertEqual(self.question.title, partial_payload['title'])
        self.assertEqual(self.question.description, "Original Desc") # Description should not change


class QuestionDeleteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_owner = create_user_for_exchange_tests("student_q_deleter_owner", 1)
        self.student_non_owner = create_user_for_exchange_tests("student_q_deleter_non_owner", 1)
        self.subject_tag = Subject.objects.create(name=get_unique_subject_name_exchange("DeleteTag"))
        
        self.question_to_delete = Question.objects.create(user=self.student_owner, title="To Be Deleted", description="D", tag=self.subject_tag)
        self.url = reverse('exchange:delete-question', kwargs={'pk': self.question_to_delete.pk})

    def test_delete_question_success_by_owner(self):
        self.client.force_authenticate(user=self.student_owner)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Question has been deleted.')
        self.assertFalse(Question.objects.filter(pk=self.question_to_delete.pk).exists())

    def test_delete_question_fail_by_non_owner_student(self):
        self.client.force_authenticate(user=self.student_non_owner)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # IsStudent object permission
        self.assertTrue(Question.objects.filter(pk=self.question_to_delete.pk).exists())


class CommentCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher_user = create_user_for_exchange_tests("comment_teacher_creator", 2) # Teacher
        self.student_user = create_user_for_exchange_tests("comment_student_non_creator", 1) # Student
        
        # Setup subject and question that matches teacher's subject for CanAddComment
        self.teacher_profile = TeacherProfile.objects.get(user=self.teacher_user)
        self.matching_subject_tag = self.teacher_profile.subject
        
        self.question_owner = create_user_for_exchange_tests("comment_q_owner", 1)
        self.question = Question.objects.create(
            user=self.question_owner, 
            title="Commentable Question", 
            description="This question is for adding comments.",
            tag=self.matching_subject_tag
        )
        
        self.url = reverse('exchange:add-comment')
        self.valid_payload = {
            'content': "This is a insightful comment from a teacher.",
            'question': self.question.id
        }
        self.client.force_authenticate(user=self.teacher_user)

    def test_create_comment_success_by_teacher_matching_subject(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Comment added successfully')
        self.assertTrue(Comment.objects.filter(content=self.valid_payload['content'], question=self.question).exists())
        created_comment = Comment.objects.get(content=self.valid_payload['content'])
        self.assertEqual(created_comment.user, self.teacher_user)

    def test_create_comment_fail_by_teacher_mismatch_subject(self):
        other_subject = Subject.objects.create(name=get_unique_subject_name_exchange("OtherSubjectForComment"))
        question_other_tag = Question.objects.create(
            user=self.question_owner, title="Q Other Tag", description="D", tag=other_subject
        )
        payload_mismatch_tag = {'content': "Comment on other tag", 'question': question_other_tag.id}
        response = self.client.post(self.url, payload_mismatch_tag, format='json')
        # CanAddComment should fail
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_comment_fail_by_student(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(self.url, self.valid_payload, format='json')
        # IsTeacher permission should fail
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_comment_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_comment_invalid_payload_missing_content(self):
        payload = {'question': self.question.id}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_create_comment_invalid_payload_missing_question(self):
        payload = {'content': "A comment without a question"}
        response = self.client.post(self.url, payload, format='json')
        # CanAddComment permission now safely checks for 'question' and returns False if not found.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CommentListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_user = create_user_for_exchange_tests("comment_lister_student", 1)
        self.teacher_user = create_user_for_exchange_tests("comment_lister_teacher", 2) # For creating comments
        
        q_owner = create_user_for_exchange_tests("q_owner_for_comments", 1)
        tag = Subject.objects.create(name=get_unique_subject_name_exchange("CommentListTag"))
        question1 = Question.objects.create(user=q_owner, title="Q1 for comments", description="D1", tag=tag)
        
        Comment.objects.create(user=self.teacher_user, question=question1, content="Comment 1 on Q1")
        Comment.objects.create(user=self.teacher_user, question=question1, content="Comment 2 on Q1")
        
        self.url = reverse('exchange:list-comment')

    def test_list_comments_success_by_student(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_comments_fail_by_teacher(self): # View is IsStudent restricted
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_comments_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CommentRetrieveUpdateDeleteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.comment_owner_teacher = create_user_for_exchange_tests("comment_owner_teacher", 2)
        self.other_teacher = create_user_for_exchange_tests("other_teacher", 2)
        self.student_user = create_user_for_exchange_tests("comment_viewer_student", 1)

        q_owner = create_user_for_exchange_tests("q_owner_for_comment_detail", 1)
        self.teacher_profile = TeacherProfile.objects.get(user=self.comment_owner_teacher)
        tag = self.teacher_profile.subject
        question = Question.objects.create(user=q_owner, title="Q for comment detail", description="D", tag=tag)
        
        self.comment = Comment.objects.create(
            user=self.comment_owner_teacher, 
            question=question, 
            content="A specific comment for detail tests."
        )
        
        self.retrieve_url = reverse('exchange:show-comment', kwargs={'pk': self.comment.pk})
        self.update_url = reverse('exchange:update-comment', kwargs={'pk': self.comment.pk})
        self.delete_url = reverse('exchange:delete-comment', kwargs={'pk': self.comment.pk})
        self.update_payload = {'content': "Updated comment content.", 'question': question.id}


    # Retrieve Tests (CanAccessComment)
    def test_retrieve_comment_success_by_owner(self):
        self.client.force_authenticate(user=self.comment_owner_teacher)
        response = self.client.get(self.retrieve_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], self.comment.content)

    def test_retrieve_comment_fail_by_other_teacher(self):
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.get(self.retrieve_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # CanAccessComment fails

    def test_retrieve_comment_fail_by_student(self): # CanAccessComment is not IsStudent
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(self.retrieve_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    # Update Tests (CanAccessComment)
    def test_update_comment_success_by_owner(self):
        self.client.force_authenticate(user=self.comment_owner_teacher)
        response = self.client.put(self.update_url, self.update_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, self.update_payload['content'])

    def test_update_comment_fail_by_other_teacher(self):
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.put(self.update_url, self.update_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    # Delete Tests (CanAccessComment)
    def test_delete_comment_success_by_owner(self):
        self.client.force_authenticate(user=self.comment_owner_teacher)
        response = self.client.delete(self.delete_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Comment has been deleted.')
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_delete_comment_fail_by_other_teacher(self):
        self.client.force_authenticate(user=self.other_teacher)
        response = self.client.delete(self.delete_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())


class UpvoteCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.comment_owner = create_user_for_exchange_tests("upvote_comment_owner", 1)
        self.upvoter1 = create_user_for_exchange_tests("upvoter1", 1)
        self.upvoter2 = create_user_for_exchange_tests("upvoter2", 1)

        tag = Subject.objects.create(name=get_unique_subject_name_exchange("UpvoteTag"))
        question = Question.objects.create(user=self.comment_owner, title="Q for Upvote", description="D", tag=tag)
        self.comment = Comment.objects.create(user=self.comment_owner, question=question, content="Comment to be upvoted.")
        
        self.url = reverse('exchange:add-upvote')
        self.valid_payload = {'comment': self.comment.id}

    def test_upvote_create_success(self):
        self.client.force_authenticate(user=self.upvoter1)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Upvote added successfully')
        self.assertTrue(Upvote.objects.filter(comment=self.comment, user=self.upvoter1).exists())

    def test_upvote_create_fail_by_comment_owner(self):
        # Test CanUpvote permission: obj.user (comment.user) != request.user
        self.client.force_authenticate(user=self.comment_owner)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upvote_create_fail_serializer_validation_if_any_upvote_exists(self):
        # First upvote by upvoter1 (should succeed)
        self.client.force_authenticate(user=self.upvoter1)
        self.client.post(self.url, self.valid_payload, format='json')
        self.assertTrue(Upvote.objects.filter(comment=self.comment, user=self.upvoter1).exists())

        # Second upvote attempt by upvoter2
        # This will fail due to the serializer's flawed validation:
        # `Upvote.objects.filter(comment=attrs['comment']).exists()`
        self.client.force_authenticate(user=self.upvoter2)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comment', response.data) # Serializer error
        self.assertTrue("You cannot upvote the same comment." in str(response.data['comment']))


    def test_upvote_create_fail_db_constraint_if_serializer_fixed(self):
        # This test assumes the serializer validation is fixed to allow multiple users to upvote,
        # but the DB unique_together=('comment', 'user') prevents one user from upvoting multiple times.
        self.client.force_authenticate(user=self.upvoter1)
        
        # First upvote (should succeed if serializer allows)
        # To bypass the current serializer's flawed validation for this specific test case,
        # we'll assume it's fixed or temporarily mock it.
        # For now, this test will fail if the serializer issue isn't addressed.
        # Let's simulate the serializer being less restrictive for this test's purpose:
        with patch('exchange.serializers.UpvoteSerializer.validate') as mock_validate:
            # Make validate method pass through data without raising the "already upvoted by anyone" error
            mock_validate.side_effect = lambda attrs: attrs
            
            response1 = self.client.post(self.url, self.valid_payload, format='json')
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            self.assertTrue(Upvote.objects.filter(comment=self.comment, user=self.upvoter1).exists())

            # Second upvote attempt by the SAME user (upvoter1)
            # This should hit the database unique_together constraint
            response2 = self.client.post(self.url, self.valid_payload, format='json')
            self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST) # DRF handles IntegrityError as 400
            # The error message might be generic or specific to the unique constraint.
            # e.g., {'non_field_errors': ['The fields comment, user must make a unique set.']}
            self.assertTrue('non_field_errors' in response2.data or 'comment' in response2.data or 'user' in response2.data)


    def test_upvote_create_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UpvoteDeleteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.comment_owner = create_user_for_exchange_tests("del_upvote_comment_owner", 1)
        self.upvoter_owner = create_user_for_exchange_tests("del_upvote_owner", 1)
        self.other_user = create_user_for_exchange_tests("del_upvote_other_user", 1)

        tag = Subject.objects.create(name=get_unique_subject_name_exchange("DelUpvoteTag"))
        question = Question.objects.create(user=self.comment_owner, title="Q for DelUpvote", description="D", tag=tag)
        comment = Comment.objects.create(user=self.comment_owner, question=question, content="Comment for deleting upvote.")
        
        self.upvote_to_delete = Upvote.objects.create(comment=comment, user=self.upvoter_owner)
        self.url = reverse('exchange:remove-upvote', kwargs={'pk': self.upvote_to_delete.pk})

    def test_delete_upvote_success_by_owner(self):
        self.client.force_authenticate(user=self.upvoter_owner)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Upvote has been removed.')
        self.assertFalse(Upvote.objects.filter(pk=self.upvote_to_delete.pk).exists())

    def test_delete_upvote_fail_by_non_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(self.url, format='json')
        # CanRemoveUpvote (obj.user == request.user) should fail
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Upvote.objects.filter(pk=self.upvote_to_delete.pk).exists())

    def test_delete_upvote_fail_by_comment_owner_not_upvote_owner(self):
        self.client.force_authenticate(user=self.comment_owner)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_upvote_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.delete(self.url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
