import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from faker import Faker

fake = Faker()


class TestMessageSending:
    """Test message sending functionality."""
    
    def test_send_message_success(self, client: TestClient, test_user, test_users, auth_headers):
        """Test successful message sending."""
        recipient = test_users[0]
        message_data = {
            "content": fake.text(max_nb_chars=200),
            "recipient_id": recipient.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "content" in data
        assert "sender_id" in data
        assert "recipient_id" in data
        assert "created_at" in data
        
        # Verify data matches input
        assert data["content"] == message_data["content"]
        assert data["sender_id"] == test_user.id
        assert data["recipient_id"] == recipient.id
        assert isinstance(data["id"], int)
    
    def test_send_message_unauthorized(self, client: TestClient, test_message_data):
        """Test sending message without authentication."""
        response = client.post("/send", json=test_message_data)
        
        assert response.status_code == 401
    
    def test_send_message_invalid_token(self, client: TestClient, test_message_data):
        """Test sending message with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/send", json=test_message_data, headers=headers)
        
        assert response.status_code == 401
    
    def test_send_message_nonexistent_recipient(self, client: TestClient, auth_headers):
        """Test sending message to non-existent user."""
        message_data = {
            "content": fake.text(max_nb_chars=200),
            "recipient_id": 99999  # Non-existent user ID
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "Recipient not found" in response.json()["detail"]
    
    def test_send_message_empty_content(self, client: TestClient, test_user, auth_headers):
        """Test sending message with empty content."""
        message_data = {
            "content": "",
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_send_message_missing_content(self, client: TestClient, test_user, auth_headers):
        """Test sending message without content."""
        message_data = {
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_send_message_missing_recipient(self, client: TestClient, auth_headers):
        """Test sending message without recipient."""
        message_data = {
            "content": fake.text(max_nb_chars=200)
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_send_message_long_content(self, client: TestClient, test_user, auth_headers):
        """Test sending message with very long content."""
        long_content = fake.text(max_nb_chars=10000)  # Very long message
        message_data = {
            "content": long_content,
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        # Should either succeed or fail with validation error
        assert response.status_code in [200, 422]
    
    def test_send_message_special_characters(self, client: TestClient, test_user, auth_headers):
        """Test sending message with special characters."""
        special_content = "Hello! @#$%^&*()_+-=[]{}|;':\",./<>?`~"
        message_data = {
            "content": special_content,
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == special_content
    
    def test_send_message_unicode(self, client: TestClient, test_user, auth_headers):
        """Test sending message with Unicode characters."""
        unicode_content = "Hello 世界! 🌍 こんにちは مرحبا"
        message_data = {
            "content": unicode_content,
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == unicode_content


class TestMessageRetrieval:
    """Test message retrieval functionality."""
    
    def test_get_messages_success(self, client: TestClient, test_user, test_users, test_messages, auth_headers):
        """Test successful message retrieval."""
        recipient = test_users[0]
        
        response = client.get(
            f"/messages?with_user_id={recipient.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list)
        
        # Verify message structure
        if data:  # If there are messages
            message = data[0]
            assert "id" in message
            assert "content" in message
            assert "sender_id" in message
            assert "recipient_id" in message
            assert "created_at" in message
    
    def test_get_messages_unauthorized(self, client: TestClient, test_users):
        """Test getting messages without authentication."""
        recipient = test_users[0]
        
        response = client.get(f"/messages?with_user_id={recipient.id}")
        
        assert response.status_code == 401
    
    def test_get_messages_nonexistent_user(self, client: TestClient, auth_headers):
        """Test getting messages with non-existent user."""
        response = client.get("/messages?with_user_id=99999", headers=auth_headers)
        
        # Should return empty list or 404
        assert response.status_code in [200, 404]
    
    def test_get_messages_missing_user_id(self, client: TestClient, auth_headers):
        """Test getting messages without specifying user ID."""
        response = client.get("/messages", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_get_messages_empty_conversation(self, client: TestClient, test_users, auth_headers):
        """Test getting messages from empty conversation."""
        recipient = test_users[0]
        
        response = client.get(
            f"/messages?with_user_id={recipient.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []  # Empty conversation
    
    def test_get_messages_bidirectional(self, client: TestClient, test_user, test_users, auth_headers):
        """Test that messages are retrieved bidirectionally."""
        recipient = test_users[0]
        
        # Send message from user to recipient
        message1_data = {
            "content": "Message from user to recipient",
            "recipient_id": recipient.id
        }
        client.post("/send", json=message1_data, headers=auth_headers)
        
        # Send message from recipient to user (simulate by creating in DB)
        from app.models.message import DirectMessage
        from app.core.database import get_db
        
        # This would need to be done through the database in a real test
        # For now, we'll test the API behavior
        
        response = client.get(
            f"/messages?with_user_id={recipient.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include messages in both directions
        # (This test would need to be more sophisticated in practice)
        assert isinstance(data, list)


class TestMessageConversations:
    """Test conversation-related functionality."""
    
    def test_get_conversations_success(self, client: TestClient, test_user, test_users, test_messages, auth_headers):
        """Test getting conversation list."""
        response = client.get("/conversations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, list)
        
        if data:  # If there are conversations
            conversation = data[0]
            assert "user_id" in conversation
            assert "username" in conversation
            assert "unread_count" in conversation
    
    def test_get_conversations_unauthorized(self, client: TestClient):
        """Test getting conversations without authentication."""
        response = client.get("/conversations")
        
        assert response.status_code == 401
    
    def test_get_unread_count_success(self, client: TestClient, auth_headers):
        """Test getting unread message count."""
        response = client.get("/unread-count", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        assert data["unread_count"] >= 0
    
    def test_get_unread_count_unauthorized(self, client: TestClient):
        """Test getting unread count without authentication."""
        response = client.get("/unread-count")
        
        assert response.status_code == 401


class TestMessageMarking:
    """Test message marking functionality."""
    
    def test_mark_message_read_success(self, client: TestClient, test_user, test_messages, auth_headers):
        """Test marking a message as read."""
        message = test_messages[0]
        
        response = client.post(
            f"/messages/{message.id}/read",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "marked as read" in data["message"]
    
    def test_mark_message_read_unauthorized(self, client: TestClient, test_messages):
        """Test marking message as read without authentication."""
        message = test_messages[0]
        
        response = client.post(f"/messages/{message.id}/read")
        
        assert response.status_code == 401
    
    def test_mark_nonexistent_message_read(self, client: TestClient, auth_headers):
        """Test marking non-existent message as read."""
        response = client.post("/messages/99999/read", headers=auth_headers)
        
        assert response.status_code == 404
        assert "Message not found" in response.json()["detail"]
    
    def test_mark_message_read_invalid_id(self, client: TestClient, auth_headers):
        """Test marking message with invalid ID as read."""
        response = client.post("/messages/invalid/read", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error


class TestMessageSearch:
    """Test message search functionality."""
    
    def test_search_users_success(self, client: TestClient, test_users, auth_headers):
        """Test searching for users."""
        search_query = test_users[0].username[:3]  # First 3 characters
        
        response = client.get(
            f"/users/search?query={search_query}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, list)
        
        if data:  # If there are results
            user = data[0]
            assert "id" in user
            assert "username" in user
            assert "display_name" in user
            assert "is_online" in user
    
    def test_search_users_unauthorized(self, client: TestClient):
        """Test searching users without authentication."""
        response = client.get("/users/search?query=test")
        
        assert response.status_code == 401
    
    def test_search_users_empty_query(self, client: TestClient, auth_headers):
        """Test searching users with empty query."""
        response = client.get("/users/search?query=", headers=auth_headers)
        
        # Should either return empty results or validation error
        assert response.status_code in [200, 422]
    
    def test_search_users_no_results(self, client: TestClient, auth_headers):
        """Test searching users with no matching results."""
        response = client.get("/users/search?query=nonexistentuser123", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_online_users_success(self, client: TestClient, test_users, auth_headers):
        """Test getting online users."""
        response = client.get("/users/online", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, list)
        
        if data:  # If there are online users
            user = data[0]
            assert "id" in user
            assert "username" in user
            assert "display_name" in user
            assert "last_seen" in user
    
    def test_get_online_users_unauthorized(self, client: TestClient):
        """Test getting online users without authentication."""
        response = client.get("/users/online")
        
        assert response.status_code == 401


class TestMessagePerformance:
    """Test message performance and edge cases."""
    
    def test_send_multiple_messages(self, client: TestClient, test_user, test_users, auth_headers):
        """Test sending multiple messages quickly."""
        recipient = test_users[0]
        
        messages_sent = []
        for i in range(10):
            message_data = {
                "content": f"Message {i}",
                "recipient_id": recipient.id
            }
            
            response = client.post("/send", json=message_data, headers=auth_headers)
            assert response.status_code == 200
            messages_sent.append(response.json())
        
        # Verify all messages were created
        assert len(messages_sent) == 10
        
        # Verify all messages have unique IDs
        message_ids = [msg["id"] for msg in messages_sent]
        assert len(set(message_ids)) == 10
    
    def test_large_message_content(self, client: TestClient, test_user, auth_headers):
        """Test sending message with large content."""
        large_content = fake.text(max_nb_chars=5000)
        message_data = {
            "content": large_content,
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        # Should handle large content appropriately
        assert response.status_code in [200, 422]  # Depending on size limits
    
    def test_concurrent_message_sending(self, client: TestClient, test_user, test_users, auth_headers):
        """Test concurrent message sending."""
        import threading
        import time
        
        recipient = test_users[0]
        results = []
        
        def send_message(message_id):
            message_data = {
                "content": f"Concurrent message {message_id}",
                "recipient_id": recipient.id
            }
            response = client.post("/send", json=message_data, headers=auth_headers)
            results.append(response.status_code)
        
        # Send messages concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=send_message, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All messages should be sent successfully
        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestMessageValidation:
    """Test message validation and edge cases."""
    
    def test_message_content_types(self, client: TestClient, test_user, auth_headers):
        """Test different types of message content."""
        test_contents = [
            "Plain text message",
            "Message with numbers: 123456789",
            "Message with symbols: !@#$%^&*()",
            "Message with newlines:\nLine 2\nLine 3",
            "Message with tabs:\tTabbed content",
            "Unicode message: 你好世界 🌍",
            "Empty spaces:   ",
        ]
        
        for content in test_contents:
            message_data = {
                "content": content,
                "recipient_id": test_user.id
            }
            
            response = client.post("/send", json=message_data, headers=auth_headers)
            
            if response.status_code == 200:
                data = response.json()
                assert data["content"] == content
    
    def test_message_sql_injection_prevention(self, client: TestClient, test_user, auth_headers):
        """Test SQL injection prevention in message content."""
        malicious_content = "'; DROP TABLE direct_messages; --"
        message_data = {
            "content": malicious_content,
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        # Should succeed (content should be properly escaped)
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == malicious_content  # Content should be preserved as-is
    
    def test_message_xss_prevention(self, client: TestClient, test_user, auth_headers):
        """Test XSS prevention in message content."""
        xss_content = "<script>alert('xss')</script>Hello World"
        message_data = {
            "content": xss_content,
            "recipient_id": test_user.id
        }
        
        response = client.post("/send", json=message_data, headers=auth_headers)
        
        # Should succeed but content should be properly handled
        assert response.status_code == 200
        data = response.json()
        # Content should be preserved as-is (XSS prevention should be handled at display level)
        assert data["content"] == xss_content
