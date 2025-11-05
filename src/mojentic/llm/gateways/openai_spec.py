import os
from unittest.mock import patch

from mojentic.llm.gateways.openai import OpenAIGateway


class DescribeOpenAIGateway:
    """
    Unit tests for the OpenAI gateway
    """

    class DescribeInitialization:
        """
        Tests for OpenAI gateway initialization
        """

        def should_initialize_with_api_key(self, mocker):
            api_key = "test-api-key"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            gateway = OpenAIGateway(api_key=api_key)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
            assert gateway.client is not None

        def should_initialize_with_api_key_and_base_url(self, mocker):
            api_key = "test-api-key"
            base_url = "https://custom.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            gateway = OpenAIGateway(api_key=api_key, base_url=base_url)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=base_url)
            assert gateway.client is not None

        def should_read_api_key_from_environment_variable(self, mocker):
            api_key = "test-api-key-from-env"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_KEY': api_key}):
                gateway = OpenAIGateway()

            mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
            assert gateway.client is not None

        def should_read_base_url_from_environment_variable(self, mocker):
            api_key = "test-api-key"
            endpoint = "https://corporate.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_ENDPOINT': endpoint}):
                gateway = OpenAIGateway(api_key=api_key)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=endpoint)
            assert gateway.client is not None

        def should_read_both_from_environment_variables(self, mocker):
            api_key = "test-api-key-from-env"
            endpoint = "https://corporate.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_KEY': api_key, 'OPENAI_API_ENDPOINT': endpoint}):
                gateway = OpenAIGateway()

            mock_openai.assert_called_once_with(api_key=api_key, base_url=endpoint)
            assert gateway.client is not None

        def should_prefer_explicit_api_key_over_environment_variable(self, mocker):
            api_key_env = "test-api-key-from-env"
            api_key_explicit = "test-api-key-explicit"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_KEY': api_key_env}):
                gateway = OpenAIGateway(api_key=api_key_explicit)

            mock_openai.assert_called_once_with(api_key=api_key_explicit, base_url=None)
            assert gateway.client is not None

        def should_prefer_explicit_base_url_over_environment_variable(self, mocker):
            api_key = "test-api-key"
            endpoint_env = "https://corporate.openai.com"
            endpoint_explicit = "https://explicit.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_ENDPOINT': endpoint_env}):
                gateway = OpenAIGateway(api_key=api_key, base_url=endpoint_explicit)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=endpoint_explicit)
            assert gateway.client is not None

        def should_use_none_when_no_endpoint_specified(self, mocker):
            api_key = "test-api-key"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {}, clear=True):
                gateway = OpenAIGateway(api_key=api_key)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
            assert gateway.client is not None
