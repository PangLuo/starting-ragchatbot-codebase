from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


def make_text_response(text="Some response"):
    response = MagicMock()
    response.stop_reason = "end_turn"
    content_block = MagicMock()
    content_block.text = text
    response.content = [content_block]
    return response


def make_tool_use_response(tool_name="search_course_content", tool_input=None, tool_id="toolu_01"):
    response = MagicMock()
    response.stop_reason = "tool_use"
    content_block = MagicMock()
    content_block.type = "tool_use"
    content_block.name = tool_name
    content_block.input = tool_input or {"query": "test query"}
    content_block.id = tool_id
    response.content = [content_block]
    return response


class TestAIGeneratorGenerateResponse:

    def setup_method(self):
        with patch("ai_generator.anthropic.Anthropic"):
            self.generator = AIGenerator(api_key="test-key", model="claude-test")
        # self.generator.client is the MagicMock instance created during __init__
        self.mock_client = self.generator.client

    # --- tools parameter in API call ---

    def test_generate_response_calls_api_with_tools_when_provided(self):
        tools = [{"name": "search_course_content", "description": "Search"}]
        self.mock_client.messages.create.return_value = make_text_response()

        self.generator.generate_response(query="test", tools=tools, tool_manager=MagicMock())

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert "tool_choice" in call_kwargs
        assert call_kwargs["tools"] == tools

    def test_generate_response_no_tools_param_when_tools_is_none(self):
        self.mock_client.messages.create.return_value = make_text_response()

        self.generator.generate_response(query="test", tools=None)

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs

    # --- Direct text response path ---

    def test_generate_response_returns_text_when_no_tool_use(self):
        self.mock_client.messages.create.return_value = make_text_response("Direct answer")

        result = self.generator.generate_response(query="test")

        assert result == "Direct answer"

    # --- Tool use routing ---

    def test_generate_response_routes_to_handle_tool_execution_on_tool_use(self):
        tool_response = make_tool_use_response()
        final_response = make_text_response("Final answer after tool")
        self.mock_client.messages.create.side_effect = [tool_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "search results"

        result = self.generator.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert self.mock_client.messages.create.call_count == 2
        assert result == "Final answer after tool"

    def test_handle_tool_execution_calls_tool_manager_execute(self):
        tool_input = {"query": "test search", "course_name": "Python"}
        tool_response = make_tool_use_response(
            tool_name="search_course_content", tool_input=tool_input, tool_id="toolu_abc"
        )
        final_response = make_text_response("Done")
        self.mock_client.messages.create.side_effect = [tool_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        self.generator.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        tool_manager.execute_tool.assert_called_once_with("search_course_content", **tool_input)

    def test_final_synthesis_call_has_no_tools(self):
        # Two tool rounds → final synthesis call (3rd) has no tools
        tool_response_1 = make_tool_use_response(tool_id="toolu_01")
        tool_response_2 = make_tool_use_response(tool_id="toolu_02")
        final_response = make_text_response("Final")
        self.mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        self.generator.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        last_call_kwargs = self.mock_client.messages.create.call_args_list[-1].kwargs
        assert "tools" not in last_call_kwargs
        assert "tool_choice" not in last_call_kwargs

    def test_handle_tool_execution_appends_tool_result_as_user_message(self):
        tool_response = make_tool_use_response(tool_id="toolu_xyz")
        final_response = make_text_response("Final")
        self.mock_client.messages.create.side_effect = [tool_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "tool result content"

        self.generator.generate_response(query="user query", tools=[{}], tool_manager=tool_manager)

        second_call_kwargs = self.mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]

        # [user query, assistant tool-use, user tool-result]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        tool_results = messages[2]["content"]
        assert len(tool_results) == 1
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "toolu_xyz"
        assert tool_results[0]["content"] == "tool result content"

    # --- System prompt / conversation history ---

    def test_generate_response_builds_system_with_history(self):
        self.mock_client.messages.create.return_value = make_text_response()
        history = "User: Hello\nAssistant: Hi"

        self.generator.generate_response(query="test", conversation_history=history)

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        system = call_kwargs["system"]
        assert AIGenerator.SYSTEM_PROMPT in system
        assert history in system

    def test_generate_response_uses_base_prompt_when_no_history(self):
        self.mock_client.messages.create.return_value = make_text_response()

        self.generator.generate_response(query="test", conversation_history=None)

        call_kwargs = self.mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == AIGenerator.SYSTEM_PROMPT

    # --- Two-round tool calling (new behavior) ---

    def test_two_tool_rounds_makes_three_api_calls_and_executes_both_tools(self):
        tool_response_1 = make_tool_use_response(tool_name="get_course_outline", tool_id="toolu_01")
        tool_response_2 = make_tool_use_response(tool_name="search_course_content", tool_id="toolu_02")
        final_response = make_text_response("Synthesized answer")
        self.mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "tool output"

        result = self.generator.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert self.mock_client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        assert result == "Synthesized answer"

    def test_intermediate_tool_round_calls_include_tools(self):
        tool_response_1 = make_tool_use_response(tool_id="toolu_01")
        tool_response_2 = make_tool_use_response(tool_id="toolu_02")
        final_response = make_text_response("Final")
        self.mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"
        tools = [{"name": "search_course_content"}]

        self.generator.generate_response(query="test", tools=tools, tool_manager=tool_manager)

        # First two calls (loop rounds) include tools
        assert "tools" in self.mock_client.messages.create.call_args_list[0].kwargs
        assert "tools" in self.mock_client.messages.create.call_args_list[1].kwargs

    def test_two_tool_rounds_message_list_grows_correctly(self):
        # After 2 tool rounds, final synthesis call receives 5 messages:
        # [user, asst1, user_results1, asst2, user_results2]
        tool_response_1 = make_tool_use_response(tool_id="toolu_01")
        tool_response_2 = make_tool_use_response(tool_id="toolu_02")
        final_response = make_text_response("Final")
        self.mock_client.messages.create.side_effect = [tool_response_1, tool_response_2, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        self.generator.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        final_call_messages = self.mock_client.messages.create.call_args_list[2].kwargs["messages"]
        assert len(final_call_messages) == 5

    def test_tool_exception_terminates_loop_and_makes_synthesis_call(self):
        tool_response = make_tool_use_response(tool_id="toolu_01")
        final_response = make_text_response("Graceful response")
        self.mock_client.messages.create.side_effect = [tool_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = Exception("Tool crashed")

        result = self.generator.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        # Loop breaks after error, synthesis call still made
        assert self.mock_client.messages.create.call_count == 2
        assert result == "Graceful response"

        # Error string is in the messages passed to synthesis call
        synthesis_messages = self.mock_client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result_content = synthesis_messages[-1]["content"]
        assert any("Tool execution error" in item["content"] for item in tool_result_content)

    def test_system_prompt_allows_up_to_two_tool_calls(self):
        assert "One search per query maximum" not in AIGenerator.SYSTEM_PROMPT
        assert "Up to 2 tool calls per query" in AIGenerator.SYSTEM_PROMPT
