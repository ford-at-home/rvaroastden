"""
Unit tests for message_processor Lambda function
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the fixed version directly
import message_processor


class TestMessageProcessor(unittest.TestCase):
    """Test cases for message processor Lambda"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        os.environ["MEMORY_TABLE"] = "test-memory-table"
        os.environ["LOG_LEVEL"] = "INFO"

        # Sample personality data
        self.sample_personality = {
            "name": "TestBot",
            "traits": ["sarcastic", "witty"],
            "roast_style": "Clever and sharp",
            "interests": ["technology", "humor"],
            "catchphrases": ["Well, actually...", "That's cute"],
            "roast_targets": ["ignorance", "arrogance"],
        }

        # Sample SQS message
        self.sample_sqs_message = {
            "type": "roast_request",
            "bot_name": "FordBot",
            "question": "What do you think about JavaScript?",
            "channel_id": "123456789",
            "message_id": "987654321",
            "user_id": "111111111",
            "user_name": "TestUser",
            "timestamp": "2025-07-05T10:00:00",
        }

    def test_put_metric(self):
        """Test CloudWatch metric publishing"""
        with patch("message_processor.cloudwatch") as mock_cw:
            message_processor.put_metric("TestMetric", 1.0, "Count")
            mock_cw.put_metric_data.assert_called_once()

    def test_load_personality_default(self):
        """Test loading default personality when file not found"""
        personality = message_processor.load_personality("NonExistentBot")
        self.assertEqual(personality["name"], "NonExistentBot")
        self.assertIn("witty", personality["traits"])

    def test_load_personality_from_file(self):
        """Test loading personality from JSON file"""
        with patch(
            "builtins.open",
            unittest.mock.mock_open(read_data=json.dumps(self.sample_personality)),
        ):
            personality = message_processor.load_personality("TestBot")
            self.assertEqual(personality["name"], "TestBot")
            self.assertIn("sarcastic", personality["traits"])

    def test_build_personality_prompt(self):
        """Test building personality prompt from data"""
        prompt = message_processor.build_personality_prompt(self.sample_personality)
        self.assertIn("TestBot", prompt)
        self.assertIn("sarcastic, witty", prompt)
        self.assertIn("Clever and sharp", prompt)
        self.assertIn("Well, actually...", prompt)

    @patch("message_processor.bedrock")
    def test_call_claude_success(self, mock_bedrock):
        """Test successful Claude API call"""
        # Mock response
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {"content": [{"text": "This is a witty response!"}]}
                ).encode()
            )
        }
        mock_bedrock.invoke_model.return_value = mock_response

        response = message_processor.call_claude("Test prompt")
        self.assertEqual(response, "This is a witty response!")
        mock_bedrock.invoke_model.assert_called_once()

    @patch("message_processor.bedrock")
    def test_call_claude_error(self, mock_bedrock):
        """Test Claude API error handling"""
        mock_bedrock.invoke_model.side_effect = Exception("API Error")

        response = message_processor.call_claude("Test prompt")
        self.assertIn("sparks fly", response)
        self.assertIn("circuits are fried", response)

    @patch("message_processor.memory_table")
    def test_save_memory(self, mock_table):
        """Test saving memory to DynamoDB"""
        message_processor.memory_table = mock_table
        message_processor.save_memory("TestBot", "Test memory content")

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]["Item"]
        self.assertEqual(call_args["bot_name"], "TestBot")
        self.assertEqual(call_args["content"], "Test memory content")

    @patch("message_processor.memory_table")
    def test_load_memory(self, mock_table):
        """Test loading memory from DynamoDB"""
        message_processor.memory_table = mock_table
        mock_table.query.return_value = {
            "Items": [{"content": "Memory 1"}, {"content": "Memory 2"}]
        }

        memories = message_processor.load_memory("TestBot")
        self.assertEqual(len(memories), 2)
        self.assertEqual(memories[0], "Memory 1")

    @patch("message_processor.call_claude")
    @patch("message_processor.load_memory")
    @patch("message_processor.save_memory")
    def test_process_roast_request(self, mock_save, mock_load, mock_claude):
        """Test processing a roast request"""
        mock_load.return_value = ["Previous conversation"]
        mock_claude.return_value = "JavaScript? More like JavaScrippled!"

        result = message_processor.process_roast_request(self.sample_sqs_message)

        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "JavaScript? More like JavaScrippled!")
        self.assertEqual(result["bot_name"], "FordBot")
        mock_save.assert_called_once()
        mock_load.assert_called_once_with("FordBot")

    def test_handler_single_message(self):
        """Test Lambda handler with single message"""
        event = {"Records": [{"body": json.dumps(self.sample_sqs_message)}]}

        with patch("message_processor.process_roast_request") as mock_process:
            mock_process.return_value = {"success": True, "response": "Test response"}

            result = message_processor.handler(event, None)

            self.assertEqual(result["statusCode"], 200)
            body = json.loads(result["body"])
            self.assertEqual(body["processed"], 1)
            self.assertEqual(body["successful"], 1)
            self.assertEqual(body["failed"], 0)

    def test_handler_error_handling(self):
        """Test Lambda handler error handling"""
        event = {"Records": [{"body": "invalid json"}]}

        result = message_processor.handler(event, None)

        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["successful"], 0)
        self.assertEqual(body["failed"], 1)

    def test_handler_unknown_message_type(self):
        """Test handling unknown message type"""
        event = {
            "Records": [
                {"body": json.dumps({"type": "unknown_type", "data": "some data"})}
            ]
        }

        result = message_processor.handler(event, None)

        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body["failed"], 1)


if __name__ == "__main__":
    unittest.main()
