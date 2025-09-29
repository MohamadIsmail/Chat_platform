import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from faker import Faker

fake = Faker()


class TestCompleteUserWorkflow:
    """Test complete user workflow from registration to messaging."""
    
    def test_complete_user_journey(self, client: TestClient, data_factory):
        """Test complete user journey: register -> login -> send messages -> retrieve messages."""
        # Step 1: Register user
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        
        assert register_response.status_code == 200
        user_id = register_response.json()["id"]
        
        # Step 2: Login
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Register another user to send messages to
        user2_data = data_factory.create_user_data()
        register2_response = client.post("/register", json=user2_data)
        
        assert register2_response.status_code == 200
        user2_id = register2_response.json()["id"]
        
        # Step 4: Send message
        message_data = {
            "content": "Hello from integration test!",
            "recipient_id": user2_id
        }
        send_response = client.post("/send", json=message_data, headers=headers)
        
        assert send_response.status_code == 200
        message_id = send_response.json()["id"]
        
        # Step 5: Retrieve messages
        messages_response = client.get(f"/messages?with_user_id={user2_id}", headers=headers)
        
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) == 1
        assert messages[0]["id"] == message_id
        assert messages[0]["content"] == message_data["content"]
        
        # Step 6: Get conversations
        conversations_response = client.get("/conversations", headers=headers)
        
        assert conversations_response.status_code == 200
        conversations = conversations_response.json()
        assert len(conversations) == 1
        assert conversations[0]["user_id"] == user2_id
    
    def test_multi_user_conversation(self, client: TestClient, data_factory):
        """Test conversation between multiple users."""
        # Register 3 users
        users_data = data_factory.create_multiple_users(3)
        user_tokens = []
        
        for user_data in users_data:
            # Register user
            register_response = client.post("/register", json=user_data)
            assert register_response.status_code == 200
            
            # Login user
            login_response = client.post("/login", data={
                "username": user_data["username"],
                "password": user_data["password"]
            })
            assert login_response.status_code == 200
            
            token = login_response.json()["access_token"]
            user_tokens.append({
                "id": register_response.json()["id"],
                "token": token,
                "headers": {"Authorization": f"Bearer {token}"}
            })
        
        # User 1 sends message to User 2
        message1_data = {
            "content": "Hello User 2!",
            "recipient_id": user_tokens[1]["id"]
        }
        response1 = client.post("/send", json=message1_data, headers=user_tokens[0]["headers"])
        assert response1.status_code == 200
        
        # User 2 sends message to User 1
        message2_data = {
            "content": "Hello User 1!",
            "recipient_id": user_tokens[0]["id"]
        }
        response2 = client.post("/send", json=message2_data, headers=user_tokens[1]["headers"])
        assert response2.status_code == 200
        
        # User 1 sends message to User 3
        message3_data = {
            "content": "Hello User 3!",
            "recipient_id": user_tokens[2]["id"]
        }
        response3 = client.post("/send", json=message3_data, headers=user_tokens[0]["headers"])
        assert response3.status_code == 200
        
        # User 1 checks conversations
        conversations_response = client.get("/conversations", headers=user_tokens[0]["headers"])
        assert conversations_response.status_code == 200
        conversations = conversations_response.json()
        assert len(conversations) == 2  # Should have conversations with User 2 and User 3
        
        # User 1 checks messages with User 2
        messages_response = client.get(
            f"/messages?with_user_id={user_tokens[1]['id']}",
            headers=user_tokens[0]["headers"]
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) == 2  # Both messages in the conversation
    
    def test_user_search_and_messaging(self, client: TestClient, data_factory):
        """Test user search and subsequent messaging."""
        # Register multiple users
        users_data = data_factory.create_multiple_users(5)
        user_tokens = []
        
        for user_data in users_data:
            # Register and login
            register_response = client.post("/register", json=user_data)
            login_response = client.post("/login", data={
                "username": user_data["username"],
                "password": user_data["password"]
            })
            
            user_tokens.append({
                "id": register_response.json()["id"],
                "username": user_data["username"],
                "token": login_response.json()["access_token"],
                "headers": {"Authorization": f"Bearer {login_response.json()['access_token']}"}
            })
        
        # User 1 searches for other users
        search_response = client.get("/users/search?query=user", headers=user_tokens[0]["headers"])
        assert search_response.status_code == 200
        search_results = search_response.json()
        
        # Should find other users (excluding self)
        assert len(search_results) == 4  # 5 users - 1 self = 4
        
        # User 1 sends message to first search result
        if search_results:
            target_user = search_results[0]
            message_data = {
                "content": f"Hello {target_user['username']}!",
                "recipient_id": target_user["id"]
            }
            
            send_response = client.post("/send", json=message_data, headers=user_tokens[0]["headers"])
            assert send_response.status_code == 200


class TestErrorHandling:
    """Test error handling across the application."""
    
    def test_authentication_errors(self, client: TestClient, data_factory):
        """Test various authentication error scenarios."""
        user_data = data_factory.create_user_data()
        
        # Register user
        client.post("/register", json=user_data)
        
        # Test invalid login
        invalid_login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": "wrongpassword"
        })
        assert invalid_login_response.status_code == 400
        
        # Test accessing protected endpoint without auth
        protected_response = client.get("/conversations")
        assert protected_response.status_code == 401
        
        # Test accessing protected endpoint with invalid token
        invalid_token_response = client.get("/conversations", headers={
            "Authorization": "Bearer invalid_token"
        })
        assert invalid_token_response.status_code == 401
    
    def test_message_errors(self, client: TestClient, data_factory):
        """Test various message-related error scenarios."""
        # Register and login user
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # Test sending message to non-existent user
        message_data = {
            "content": "Hello!",
            "recipient_id": 99999
        }
        send_response = client.post("/send", json=message_data, headers=headers)
        assert send_response.status_code == 404
        
        # Test sending message with invalid data
        invalid_message_data = {
            "content": "",
            "recipient_id": "invalid"
        }
        invalid_send_response = client.post("/send", json=invalid_message_data, headers=headers)
        assert invalid_send_response.status_code == 422
    
    def test_concurrent_operations(self, client: TestClient, data_factory):
        """Test concurrent operations and race conditions."""
        import threading
        import time
        
        # Register and login user
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        user_id = register_response.json()["id"]
        
        # Register another user
        user2_data = data_factory.create_user_data()
        register2_response = client.post("/register", json=user2_data)
        user2_id = register2_response.json()["id"]
        
        results = []
        
        def send_message(message_id):
            message_data = {
                "content": f"Concurrent message {message_id}",
                "recipient_id": user2_id
            }
            response = client.post("/send", json=message_data, headers=headers)
            results.append(response.status_code)
        
        # Send messages concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=send_message, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All messages should be sent successfully
        assert all(status == 200 for status in results)
        assert len(results) == 10


class TestDataConsistency:
    """Test data consistency across operations."""
    
    def test_message_consistency(self, client: TestClient, data_factory):
        """Test that message data remains consistent across operations."""
        # Register and login two users
        user1_data = data_factory.create_user_data()
        user2_data = data_factory.create_user_data()
        
        # Register users
        user1_response = client.post("/register", json=user1_data)
        user2_response = client.post("/register", json=user2_data)
        
        user1_id = user1_response.json()["id"]
        user2_id = user2_response.json()["id"]
        
        # Login users
        user1_login = client.post("/login", data={
            "username": user1_data["username"],
            "password": user1_data["password"]
        })
        user2_login = client.post("/login", data={
            "username": user2_data["username"],
            "password": user2_data["password"]
        })
        
        user1_headers = {"Authorization": f"Bearer {user1_login.json()['access_token']}"}
        user2_headers = {"Authorization": f"Bearer {user2_login.json()['access_token']}"}
        
        # Send message from user1 to user2
        message_data = {
            "content": "Test message for consistency",
            "recipient_id": user2_id
        }
        send_response = client.post("/send", json=message_data, headers=user1_headers)
        assert send_response.status_code == 200
        
        message_id = send_response.json()["id"]
        
        # Verify message appears in both users' conversation
        user1_messages = client.get(f"/messages?with_user_id={user2_id}", headers=user1_headers)
        user2_messages = client.get(f"/messages?with_user_id={user1_id}", headers=user2_headers)
        
        assert user1_messages.status_code == 200
        assert user2_messages.status_code == 200
        
        user1_messages_data = user1_messages.json()
        user2_messages_data = user2_messages.json()
        
        # Both should see the same message
        assert len(user1_messages_data) == 1
        assert len(user2_messages_data) == 1
        
        message1 = user1_messages_data[0]
        message2 = user2_messages_data[0]
        
        # Messages should be identical
        assert message1["id"] == message2["id"]
        assert message1["content"] == message2["content"]
        assert message1["sender_id"] == message2["sender_id"]
        assert message1["recipient_id"] == message2["recipient_id"]
    
    def test_user_data_consistency(self, client: TestClient, data_factory):
        """Test that user data remains consistent."""
        user_data = data_factory.create_user_data()
        
        # Register user
        register_response = client.post("/register", json=user_data)
        assert register_response.status_code == 200
        
        user_id = register_response.json()["id"]
        registered_username = register_response.json()["username"]
        registered_email = register_response.json()["email"]
        
        # Login user
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        
        # Verify user data consistency
        assert registered_username == user_data["username"]
        assert registered_email == user_data["email"]
        assert isinstance(user_id, int)
        assert user_id > 0


class TestPerformance:
    """Test performance characteristics."""
    
    def test_bulk_message_creation(self, client: TestClient, data_factory):
        """Test creating many messages quickly."""
        # Register and login user
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        user_id = register_response.json()["id"]
        
        # Register another user
        user2_data = data_factory.create_user_data()
        register2_response = client.post("/register", json=user2_data)
        user2_id = register2_response.json()["id"]
        
        # Send many messages
        message_count = 50
        successful_messages = 0
        
        for i in range(message_count):
            message_data = {
                "content": f"Bulk message {i}",
                "recipient_id": user2_id
            }
            response = client.post("/send", json=message_data, headers=headers)
            if response.status_code == 200:
                successful_messages += 1
        
        # Verify most messages were sent successfully
        assert successful_messages >= message_count * 0.95  # Allow for some failures
        
        # Verify messages can be retrieved
        messages_response = client.get(f"/messages?with_user_id={user2_id}", headers=headers)
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) == successful_messages
    
    def test_concurrent_user_registration(self, client: TestClient, data_factory):
        """Test concurrent user registration."""
        import threading
        
        users_data = data_factory.create_multiple_users(20)
        results = []
        
        def register_user(user_data):
            response = client.post("/register", json=user_data)
            results.append(response.status_code)
        
        # Register users concurrently
        threads = []
        for user_data in users_data:
            thread = threading.Thread(target=register_user, args=(user_data,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All registrations should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 20


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_long_message(self, client: TestClient, data_factory):
        """Test sending very long message."""
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        user_id = register_response.json()["id"]
        
        # Create very long message
        long_message = "A" * 10000  # 10KB message
        
        message_data = {
            "content": long_message,
            "recipient_id": user_id
        }
        
        response = client.post("/send", json=message_data, headers=headers)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 422, 413]  # 413 = Payload Too Large
    
    def test_special_characters_in_message(self, client: TestClient, data_factory):
        """Test message with various special characters."""
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        user_id = register_response.json()["id"]
        
        special_message = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?`~ \n\t\r"
        
        message_data = {
            "content": special_message,
            "recipient_id": user_id
        }
        
        response = client.post("/send", json=message_data, headers=headers)
        assert response.status_code == 200
        
        # Verify message was stored correctly
        data = response.json()
        assert data["content"] == special_message
    
    def test_unicode_message(self, client: TestClient, data_factory):
        """Test message with Unicode characters."""
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        user_id = register_response.json()["id"]
        
        unicode_message = "Hello 世界! 🌍 こんにちは مرحبا Здравствуй"
        
        message_data = {
            "content": unicode_message,
            "recipient_id": user_id
        }
        
        response = client.post("/send", json=message_data, headers=headers)
        assert response.status_code == 200
        
        # Verify message was stored correctly
        data = response.json()
        assert data["content"] == unicode_message
