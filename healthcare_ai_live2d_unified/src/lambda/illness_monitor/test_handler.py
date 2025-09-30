"""
Test file for Illness Monitor Lambda Function
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from handler import lambda_handler, IllnessMonitorAgent, BedrockClient, DynamoDBClient


class TestIllnessMonitorAgent:
    """Test cases for Illness Monitor Agent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = IllnessMonitorAgent()
        self.test_context = {
            'user_id': 'test_user',
            'conversation_id': 'test_conv',
            'language_preference': 'zh',
            'age_group': 'adult',
            'cultural_context': {'region': 'hong_kong'},
            'conversation_history': []
        }
    
    def test_can_handle_illness_keywords(self):
        """Test agent can handle illness-related messages."""
        test_cases = [
            ("I have a headache", True),
            ("我頭痛", True),
            ("My diabetes is acting up", True),
            ("糖尿病問題", True),
            ("I'm taking medication", True),
            ("Hello how are you", False),
            ("What's the weather", False)
        ]
        
        for message, expected in test_cases:
            can_handle, confidence = self.agent.can_handle(message, self.test_context)
            assert can_handle == expected, f"Failed for message: {message}"
            if expected:
                assert confidence > 0.0
    
    def test_emergency_deferral(self):
        """Test agent defers emergency cases."""
        emergency_messages = [
            "I'm having chest pain",
            "胸痛",
            "Can't breathe",
            "呼吸困難",
            "I think I'm having a stroke"
        ]
        
        for message in emergency_messages:
            can_handle, confidence = self.agent.can_handle(message, self.test_context)
            assert can_handle == False, f"Should defer emergency: {message}"
    
    def test_detect_urgency(self):
        """Test urgency detection."""
        test_cases = [
            ("Emergency help needed", "high"),
            ("緊急", "high"),
            ("I'm worried about my pain", "medium"),
            ("擔心", "medium"),
            ("How to prevent diabetes", "low")
        ]
        
        for message, expected_urgency in test_cases:
            urgency = self.agent.detect_urgency(message)
            assert urgency == expected_urgency, f"Wrong urgency for: {message}"
    
    def test_system_prompt_language(self):
        """Test system prompt adapts to language preference."""
        # Chinese context
        zh_context = self.test_context.copy()
        zh_context['language_preference'] = 'zh'
        zh_prompt = self.agent.get_system_prompt(zh_context)
        assert "慧心助手" in zh_prompt
        assert "Wise Heart Assistant" in zh_prompt
        
        # English context
        en_context = self.test_context.copy()
        en_context['language_preference'] = 'en'
        en_prompt = self.agent.get_system_prompt(en_context)
        assert "Wise Heart Assistant" in en_prompt
    
    def test_system_prompt_age_adaptation(self):
        """Test system prompt adapts to age group."""
        elderly_context = self.test_context.copy()
        elderly_context['age_group'] = 'elderly'
        elderly_context['language_preference'] = 'zh'
        
        elderly_prompt = self.agent.get_system_prompt(elderly_context)
        assert "長者專用指導" in elderly_prompt
    
    @patch('handler.bedrock_runtime')
    def test_bedrock_client_claude_response(self, mock_bedrock):
        """Test Bedrock client with Claude model."""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test response from Claude'}],
            'usage': {'total_tokens': 100}
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        client = BedrockClient()
        result = client.get_response("Test message", "Test prompt", "balanced")
        
        assert result['content'] == 'Test response from Claude'
        assert result['model_used'] == 'anthropic.claude-3-haiku-20240307-v1:0'
        assert result['tokens_used'] == 100
    
    @patch('handler.bedrock_runtime')
    def test_bedrock_client_fallback(self, mock_bedrock):
        """Test Bedrock client fallback mechanism."""
        # Mock Bedrock to raise exception first, then succeed
        mock_bedrock.invoke_model.side_effect = [
            Exception("Model unavailable"),
            Mock(body=Mock(read=Mock(return_value=json.dumps({
                'results': [{'outputText': 'Fallback response'}]
            }).encode())))
        ]
        
        client = BedrockClient()
        result = client.get_response("Test message", "Test prompt", "advanced")
        
        # Should fallback to fast model
        assert "response" in result['content'].lower()
        assert mock_bedrock.invoke_model.call_count == 2
    
    def test_post_process_response_safety_disclaimer(self):
        """Test post-processing adds safety disclaimers."""
        content_with_medication = "You should take your medication as prescribed."
        
        processed = self.agent.post_process_response(content_with_medication, self.test_context)
        assert "重要提醒" in processed
        assert "教育用途" in processed
        
        # Test English version
        en_context = self.test_context.copy()
        en_context['language_preference'] = 'en'
        processed_en = self.agent.post_process_response(content_with_medication, en_context)
        assert "Important Note" in processed_en
        assert "educational purposes" in processed_en
    
    def test_post_process_response_emergency_contact(self):
        """Test post-processing adds emergency contacts for concerning symptoms."""
        content_with_pain = "Your chest pain could be serious."
        
        processed = self.agent.post_process_response(content_with_pain, self.test_context)
        assert "999" in processed
        assert "緊急情況" in processed


class TestDynamoDBClient:
    """Test cases for DynamoDB client."""
    
    @patch('handler.conversations_table')
    def test_store_conversation(self, mock_table):
        """Test conversation storage."""
        client = DynamoDBClient()
        
        client.store_conversation(
            'test_conv', 'test_user', 'test input', 'test response'
        )
        
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        
        assert call_args['conversation_id'] == 'test_conv'
        assert call_args['user_id'] == 'test_user'
        assert call_args['user_input'] == 'test input'
        assert call_args['ai_response'] == 'test response'
        assert call_args['agent_type'] == 'illness_monitor'
        assert 'ttl' in call_args
    
    @patch('handler.conversations_table')
    def test_get_conversation_history(self, mock_table):
        """Test conversation history retrieval."""
        mock_table.query.return_value = {
            'Items': [
                {'conversation_id': 'test_conv', 'timestamp': '2024-01-01T00:00:00'},
                {'conversation_id': 'test_conv', 'timestamp': '2024-01-01T00:01:00'}
            ]
        }
        
        client = DynamoDBClient()
        history = client.get_conversation_history('test_conv')
        
        assert len(history) == 2
        mock_table.query.assert_called_once()
    
    @patch('handler.users_table')
    def test_get_user_profile(self, mock_table):
        """Test user profile retrieval."""
        mock_table.get_item.return_value = {
            'Item': {
                'user_id': 'test_user',
                'age_group': 'elderly',
                'language_preference': 'zh'
            }
        }
        
        client = DynamoDBClient()
        profile = client.get_user_profile('test_user')
        
        assert profile['age_group'] == 'elderly'
        assert profile['language_preference'] == 'zh'


class TestLambdaHandler:
    """Test cases for Lambda handler."""
    
    @patch('handler.IllnessMonitorAgent')
    def test_lambda_handler_success(self, mock_agent_class):
        """Test successful Lambda execution."""
        # Mock agent instance
        mock_agent = Mock()
        mock_agent.can_handle.return_value = (True, 0.8)
        mock_agent.generate_response.return_value = {
            'content': 'Test response',
            'confidence': 0.8,
            'urgency_level': 'low',
            'model_used': 'test_model',
            'tokens_used': 50
        }
        mock_agent.dynamodb_client.get_user_profile.return_value = {
            'age_group': 'adult',
            'cultural_context': {'region': 'hong_kong'}
        }
        mock_agent.dynamodb_client.get_conversation_history.return_value = []
        mock_agent.dynamodb_client.store_conversation.return_value = None
        
        mock_agent_class.return_value = mock_agent
        
        # Test event
        event = {
            'body': json.dumps({
                'message': 'I have a headache',
                'conversation_id': 'test_conv',
                'user_id': 'test_user',
                'language_preference': 'zh'
            })
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['response'] == 'Test response'
        assert body['agent'] == 'illness_monitor'
        assert body['avatar'] == 'Hiyori'
    
    def test_lambda_handler_missing_message(self):
        """Test Lambda handler with missing message."""
        event = {
            'body': json.dumps({
                'conversation_id': 'test_conv',
                'user_id': 'test_user'
            })
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'error' in body
    
    @patch('handler.IllnessMonitorAgent')
    def test_lambda_handler_cannot_handle(self, mock_agent_class):
        """Test Lambda handler when agent cannot handle request."""
        mock_agent = Mock()
        mock_agent.can_handle.return_value = (False, 0.1)
        mock_agent.dynamodb_client.get_user_profile.return_value = {'age_group': 'adult'}
        mock_agent.dynamodb_client.get_conversation_history.return_value = []
        
        mock_agent_class.return_value = mock_agent
        
        event = {
            'body': json.dumps({
                'message': 'What is the weather today?',
                'user_id': 'test_user'
            })
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['should_route'] == True
    
    @patch('handler.IllnessMonitorAgent')
    def test_lambda_handler_error(self, mock_agent_class):
        """Test Lambda handler error handling."""
        mock_agent_class.side_effect = Exception("Test error")
        
        event = {
            'body': json.dumps({
                'message': 'Test message',
                'user_id': 'test_user'
            })
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body


if __name__ == '__main__':
    pytest.main([__file__])