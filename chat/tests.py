from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone # Keep for potential future use, not strictly needed for current models

from .models import Room, Message
# Classroom is not directly linked to Room model, so removing direct import for that purpose.
# from classroom.models import Classroom 
# StudentProfile/TeacherProfile not directly used by Room/Message models, only Account.
# from user.models import Student as StudentProfile, Teacher as TeacherProfile 

User = get_user_model()

# Counter for unique phone numbers
phone_counter_chat = 0

def get_unique_phone_number_chat():
    global phone_counter_chat
    phone_counter_chat += 1
    return f"0234567{phone_counter_chat:03d}"

def create_user_for_chat(email_prefix, user_type_int, name_prefix="ChatUser"):
    """Creates an Account instance for chat tests."""
    email = f"{email_prefix.lower()}@example.com"
    user_account = User.objects.create_user(
        email=email,
        password="testpassword",
        phone_number=get_unique_phone_number_chat(),
        name=f"{name_prefix} {email_prefix.replace('_', ' ').title()}",
        user_type=user_type_int # Ensure this aligns with Account model's user_type definition
    )
    return user_account


class RoomModelTests(TestCase):
    def setUp(self):
        self.creator_user = create_user_for_chat("room_creator", 2) # e.g., a Teacher creates a room
        self.user_online1 = create_user_for_chat("online_user1", 1)
        self.user_online2 = create_user_for_chat("online_user2", 1)
        
        self.room_data = {
            'name': "Tech Discussion Room",
            'type': 2, # Assuming 2 for 'Teacher' type room, based on Room.ROOM_TYPE_CHOOSES
            'created_by': self.creator_user,
        }
        self.room = Room.objects.create(**self.room_data)
        # Note: 'online' users are added via join() method or directly for testing setup.
        # For testing get_online_count, join, leave, it's better to use the methods.

    def test_create_room(self):
        self.assertEqual(Room.objects.count(), 1)
        room = Room.objects.first()
        self.assertEqual(room.name, self.room_data['name'])
        self.assertEqual(room.type, self.room_data['type'])
        self.assertEqual(room.created_by, self.room_data['created_by'])
        # created_at is not on the model
        # self.assertIsNotNone(self.room.created_at) 

    def test_update_room_name(self):
        new_name = "Advanced Tech Discussion Room"
        self.room.name = new_name
        self.room.save()
        updated_room = Room.objects.get(id=self.room.id)
        self.assertEqual(updated_room.name, new_name)

    def test_delete_room(self):
        room_id = self.room.id
        self.room.delete()
        with self.assertRaises(Room.DoesNotExist):
            Room.objects.get(id=room_id)
        self.assertEqual(Room.objects.count(), 0)

    def test_room_online_methods_and_count(self):
        self.assertEqual(self.room.get_online_count(), 0) # Initially no one is online via join()

        self.room.join(self.user_online1)
        self.assertEqual(self.room.get_online_count(), 1)
        self.assertIn(self.user_online1, self.room.online.all())

        self.room.join(self.user_online2)
        self.assertEqual(self.room.get_online_count(), 2)
        self.assertIn(self.user_online2, self.room.online.all())

        self.room.leave(self.user_online1)
        self.assertEqual(self.room.get_online_count(), 1)
        self.assertNotIn(self.user_online1, self.room.online.all())
        self.assertIn(self.user_online2, self.room.online.all())

        self.room.leave(self.user_online2)
        self.assertEqual(self.room.get_online_count(), 0)
        self.assertNotIn(self.user_online2, self.room.online.all())
        
    def test_room_unique_name_constraint(self):
        with self.assertRaises(Exception): # Django raises IntegrityError for unique constraints
            Room.objects.create(
                name=self.room_data['name'], # Same name
                type=1, 
                created_by=self.creator_user
            )

    # __str__ is not defined in the model, so Django's default will be "Room object (PK)"
    # A specific test for this default isn't usually necessary unless a specific format is expected.
    # def test_room_str_representation(self):
    #     self.assertEqual(str(self.room), f"Room object ({self.room.pk})")


class MessageModelTests(TestCase):
    def setUp(self):
        self.message_sender = create_user_for_chat("msg_sender", 1)
        room_creator = create_user_for_chat("msg_room_creator", 2)
        
        self.test_room = Room.objects.create(
            name="Messaging Test Room",
            type=1, # Student room
            created_by=room_creator
        )
        
        self.message_data = {
            'room': self.test_room,
            'user': self.message_sender, # Changed from 'sender'
            'content': "A test message for the chat room.",
            # 'receiver' and 'message_type' are not in the model
        }
        self.message = Message.objects.create(**self.message_data)

    def test_create_message(self):
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.room, self.message_data['room'])
        self.assertEqual(message.user, self.message_data['user'])
        self.assertEqual(message.content, self.message_data['content'])
        self.assertIsNotNone(message.timestamp) # auto_now_add=True sets this

    def test_update_message_content(self):
        # Messages are often immutable in chat systems, but the model allows field updates.
        new_content = "An updated test message."
        self.message.content = new_content
        self.message.save()
        updated_message = Message.objects.get(id=self.message.id)
        self.assertEqual(updated_message.content, new_content)

    def test_delete_message(self):
        message_id = self.message.id
        self.message.delete()
        with self.assertRaises(Message.DoesNotExist):
            Message.objects.get(id=message_id)
        self.assertEqual(Message.objects.count(), 0)

    # __str__ is not defined for Message model.
    # def test_message_str_representation(self):
    #     # Default would be "Message object (PK)"
    #     self.assertEqual(str(self.message), f"Message object ({self.message.pk})")

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class IndexViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user_for_chat("index_viewer", 1) # Any authenticated user
        self.room1 = Room.objects.create(name="General Discussion", type=1, created_by=self.user)
        self.room2 = Room.objects.create(name="Tech Talk", type=2, created_by=self.user)
        self.url = reverse('chat:chat-index')

    def test_index_view_unauthenticated_access(self):
        # Requesting JSON explicitly
        response_json = self.client.get(self.url, HTTP_ACCEPT='application/json')
        self.assertEqual(response_json.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_json.data['rooms']), 2) # Serialized data should be under 'rooms'

    def test_index_view_authenticated_access_json(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, HTTP_ACCEPT='application/json') # Request JSON
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['rooms']), 2)
        room_names_in_response = [room_data['name'] for room_data in response.data['rooms']]
        self.assertIn(self.room1.name, room_names_in_response)
        self.assertIn(self.room2.name, room_names_in_response)

    def test_index_view_html_response(self):
        # This test assumes a template 'chat/index.html' exists and can render Room objects.
        # If the template is very basic or non-existent, this might still have issues,
        # but the ImproperlyConfigured error should be gone.
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # A more robust check would be for specific HTML structure if the template was known.
        # For now, checking if room names are present in the content is a basic test.
        # The view now passes 'rooms_queryset' to the template context.
        self.assertContains(response, self.room1.name)
        self.assertContains(response, self.room2.name)


class CreateRoomViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # User who can create rooms (assuming CanCreateRoom allows user_type 2 - Teacher)
        self.creator_user = create_user_for_chat("room_creator_view", 2) 
        self.student_user = create_user_for_chat("room_student_view", 1) # User who might not be able to create
        self.client.force_authenticate(user=self.creator_user)
        
        self.url = reverse('chat:chat-room')
        self.valid_payload = {
            'name': "New Test Room from View",
            'type': 1, # Student room type
            # created_by is set by the view
        }

    def test_create_room_success(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # View returns 200 OK
        self.assertEqual(response.data['message'], 'Student room created successfully.')
        self.assertTrue(Room.objects.filter(name=self.valid_payload['name']).exists())
        created_room = Room.objects.get(name=self.valid_payload['name'])
        self.assertEqual(created_room.created_by, self.creator_user)
        self.assertEqual(created_room.type, self.valid_payload['type'])

    def test_create_room_invalid_payload_missing_name(self):
        invalid_payload = {'type': 1}
        response = self.client.post(self.url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data) # Check for error message related to 'name'

    def test_create_room_invalid_payload_missing_type(self):
        invalid_payload = {'name': "Room Without Type"}
        response = self.client.post(self.url, invalid_payload, format='json')
        # CanCreateRoom permission now returns False if 'type' is missing, leading to 403
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # self.assertIn('type', response.data) # This won't be reached if permission fails first

    def test_create_room_duplicate_name(self):
        # To test unique name, permission must pass first.
        # self.creator_user (Teacher) can create type 1 (Student) rooms.
        Room.objects.create(name="Existing Room", type=1, created_by=self.creator_user)
        payload_duplicate_name = {'name': "Existing Room", 'type': 1} # Valid type for this user
        response = self.client.post(self.url, payload_duplicate_name, format='json')
        # Now serializer's unique validation for name should be triggered
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_create_room_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_payload, format='json')
        # IsAuthenticated permission should deny
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_room_not_permitted_user(self):
        # Authenticate as a student user, assuming CanCreateRoom denies students
        self.client.force_authenticate(user=self.student_user)
        response = self.client.post(self.url, self.valid_payload, format='json')
        # CanCreateRoom permission should deny
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter # For wrapping application
from chat.routing import websocket_urlpatterns # The app's routing
from channels.auth import AuthMiddlewareStack # To populate scope['user']
import asyncio # For timeout


class ChatConsumerTests(TestCase):
    # Note: Using TestCase and manually wrapping application for WebsocketCommunicator
    # is often cleaner than ChannelsLiveServerTestCase if not testing HTTP part of Channels.
    
    async def connect_user_to_room(self, user, room_name):
        """Helper to connect a user to a room and return the communicator."""
        communicator = WebsocketCommunicator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),  # Wrap with Auth
            f"/ws/chat/{room_name}/"
        )
        if user: # Authenticate the scope if user is provided
            communicator.scope['user'] = user
            
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_consumer_connect_accept_valid_user_student_room(self):
        creator = await User.objects.acreate(email="creator_sroom@example.com", phone_number=get_unique_phone_number_chat(), name="CreatorS", user_type=2) # Teacher
        room = await Room.objects.acreate(name="StudentRoom1", type=1, created_by=creator) # Type 1: Student room
        
        student_user = await User.objects.acreate(email="student_sroom@example.com", phone_number=get_unique_phone_number_chat(), name="StudentS", user_type=1)
        
        communicator, connected = await self.connect_user_to_room(student_user, room.name)
        self.assertTrue(connected, "Student should connect to Student room")
        await communicator.disconnect()

    async def test_consumer_connect_accept_teacher_in_student_room(self):
        creator = await User.objects.acreate(email="creator_sroom_t@example.com", phone_number=get_unique_phone_number_chat(), name="CreatorST", user_type=2)
        room = await Room.objects.acreate(name="StudentRoom2", type=1, created_by=creator) # Type 1: Student room
        
        teacher_user = await User.objects.acreate(email="teacher_sroom@example.com", phone_number=get_unique_phone_number_chat(), name="TeacherS", user_type=2)
        
        communicator, connected = await self.connect_user_to_room(teacher_user, room.name)
        self.assertTrue(connected, "Teacher should connect to Student room")
        await communicator.disconnect()

    async def test_consumer_connect_reject_student_in_teacher_room(self):
        # Student (type 1) trying to connect to a Teacher room (type 2)
        creator = await User.objects.acreate(email="creator_troom@example.com", phone_number=get_unique_phone_number_chat(), name="CreatorT", user_type=3) # HOD
        room = await Room.objects.acreate(name="TeacherRoom1", type=2, created_by=creator) # Type 2: Teacher room
        
        student_user = await User.objects.acreate(email="student_troom@example.com", phone_number=get_unique_phone_number_chat(), name="StudentT", user_type=1)
        
        communicator, connected = await self.connect_user_to_room(student_user, room.name)
        # Based on consumer logic: room.type == 2, user.user_type == 1. This combination is NOT explicitly accepted.
        # The consumer does not call self.accept() for this case.
        # A well-behaved consumer might call self.close() if not accepted.
        # If self.accept() is not called, `connected` from `communicator.connect()` should be False or the connection should close.
        # If it's True, it implies an issue with the consumer's accept logic or default behavior.
        # For this test, we expect the connection not to be functionally established for this user type.
        # The current consumer logic does not explicitly call self.close() if a user type is not allowed.
        # However, if self.accept() is not called, the default behavior of WebsocketConsumer is to close the connection.
        self.assertFalse(connected, "Student should not connect to Teacher room if not explicitly accepted.")
        await communicator.disconnect()


    async def test_consumer_connect_non_existent_room(self):
        test_user = await User.objects.acreate(email="user_noroom@example.com", phone_number=get_unique_phone_number_chat(), name="NoRoomUser", user_type=1)
        # WebsocketCommunicator will try to connect, consumer's connect() will fail at Room.objects.get()
        communicator = WebsocketCommunicator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns)), "/ws/chat/NonExistentRoom/")
        communicator.scope['user'] = test_user
        
        connected, _ = await communicator.connect()
        self.assertFalse(connected, "Connection should fail for a non-existent room.")

    async def test_consumer_receive_message_authenticated_user(self):
        creator = await User.objects.acreate(email="creator_msg_room@example.com", phone_number=get_unique_phone_number_chat(), name="CreatorMsg", user_type=2)
        room = await Room.objects.acreate(name="MsgReceiveRoom", type=1, created_by=creator) # Student Room
        
        sender = await User.objects.acreate(email="sender_msg_room@example.com", phone_number=get_unique_phone_number_chat(), name="SenderMsg", user_type=1) # Student
        
        communicator, connected = await self.connect_user_to_room(sender, room.name)
        self.assertTrue(connected, "Sender should connect to send message.")

        message_content = "Hello from consumer test!"
        await communicator.send_json_to({'message': message_content})
        
        response = await communicator.receive_json_from(timeout=1) # Add timeout
        self.assertEqual(response['type'], 'chat_message')
        self.assertEqual(response['user'], sender.name)
        self.assertEqual(response['message'], message_content)
        
        db_message_exists = await Message.objects.filter(room=room, user=sender, content=message_content).aexists()
        self.assertTrue(db_message_exists, "Message should be saved to DB.")
        
        await communicator.disconnect()

    async def test_consumer_receive_message_unauthenticated_user(self):
        creator = await User.objects.acreate(email="creator_unauth@example.com", phone_number=get_unique_phone_number_chat(), name="CreatorUnauth", user_type=2)
        room = await Room.objects.acreate(name="UnauthMsgRoom", type=1, created_by=creator)
        
        # For an unauthenticated user, AuthMiddlewareStack provides AnonymousUser to scope['user']
        communicator = WebsocketCommunicator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns)), f"/ws/chat/{room.name}/")
        
        connected, _ = await communicator.connect()
        # The consumer's connect logic currently accepts based on room.type and user.user_type.
        # AnonymousUser does not have user_type, so it will likely not call self.accept().
        # If not accepted, connection should be closed by WebsocketConsumer's default behavior.
        
        if not connected: # If connection was correctly refused or closed.
            # This is the desired path for an unauthenticated user if connect logic is strict.
            self.assertFalse(connected, "Unauthenticated user should not connect or connection should be closed.")
        else:
            # If connection is somehow made (e.g. flaw in connect logic or default accept),
            # then the receive method's `if not self.user.is_authenticated: return` should prevent message processing.
            message_content = "Attempt by unauthenticated user"
            await communicator.send_json_to({'message': message_content})
            
            with self.assertRaises(asyncio.TimeoutError):
                 await communicator.receive_json_from(timeout=0.1) 
            
            message_exists = await Message.objects.filter(room=room, content=message_content).aexists()
            self.assertFalse(message_exists, "Message from unauthenticated user should not be saved.")
            await communicator.disconnect()


    async def test_consumer_disconnect_path(self):
        # Test that the disconnect path is exercised without errors.
        creator = await User.objects.acreate(email="creator_dc@example.com", phone_number=get_unique_phone_number_chat(), name="CreatorDC", user_type=2)
        room = await Room.objects.acreate(name="DisconnectTestRoom", type=1, created_by=creator)
        user = await User.objects.acreate(email="user_dc@example.com", phone_number=get_unique_phone_number_chat(), name="UserDC", user_type=1)

        communicator, connected = await self.connect_user_to_room(user, room.name)
        self.assertTrue(connected)
        await communicator.disconnect()
        # group_discard should have been called. No specific assertion here other than clean disconnect.
        # To truly test group_discard, one might mock channel_layer or have another consumer listen.
        # For now, this ensures the code path runs.
