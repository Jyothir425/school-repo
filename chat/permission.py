from rest_framework import permissions


class CanCreateRoom(permissions.BasePermission):
    def has_permission(self, request, view):
        room_type_to_create = request.data.get('type')
        if room_type_to_create is None:
            # This will be caught by serializer validation later,
            # but returning False early if type is crucial for permission.
            return False

        try:
            room_type_to_create = int(room_type_to_create)
        except ValueError:
            return False # Invalid type format

        user_type = request.user.user_type
        
        if user_type == 2: # Teacher
            if room_type_to_create == 1: # Teacher can create Student room
                return True
        elif user_type == 3: # HOD
            if room_type_to_create == 2: # HOD can create Teacher room
                return True
        elif user_type == 4: # Management
            if room_type_to_create == 3: # Management can create HOD room
                return True
        return False
