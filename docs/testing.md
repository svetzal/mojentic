# Testing Guidelines

## Specification-Style Testing

Mojentic uses a specification-style approach to testing that makes tests more readable and maintainable. This approach helps tests serve as both verification and documentation of the system's behavior.

### Key Principles

1. **Descriptive Naming**
   - Use `*_spec.py` suffix for specification files
   - Name test classes with `Describe` prefix
   - Name test methods with `should_` prefix
   - Names should read like natural language specifications

2. **Hierarchical Organization**
   ```python
   class DescribeComponent:
       """Specification for the Component"""

       class DescribeSpecificFeature:
           """Specifications for a specific feature"""

           def should_behave_in_specific_way(self):
               """Test specific behavior"""
   ```

3. **Given-When-Then Pattern**
   - Document scenarios in docstrings using Given-When-Then
   - Use a blank line between Given, When, and Then sections
   ```python
   def should_handle_specific_case(self):
       """
       Given some initial condition
       When an action occurs
       Then expect specific outcome
       """
       initial_setup()

       result = perform_action()

       assert_expected_outcome(result)
   ```

4. **Test Location**
   - Co-locate tests with implementation files
   - Use `*_spec.py` alongside the implementation file
   - Example: `llm_broker.py` and `llm_broker_spec.py`

### Example

```python
class DescribeLLMBroker:
    """
    Specification for the LLMBroker class which handles interactions with Language Learning Models.
    """

    class DescribeMessageGeneration:
        """
        Specifications for generating messages through the LLM broker
        """

        def should_generate_simple_response_for_user_message(self, llm_broker):
            """
            Given a simple user message
            When generating a response
            Then it should return the LLM's response content
            """
            # Given
            messages = [LLMMessage(role=MessageRole.User, content="Hello")]

            # When
            result = llm_broker.generate(messages)

            # Then
            assert result == expected_response
```

### Best Practices

1. **Clear Documentation**
   - Always include docstrings for test classes and methods
   - Use Given-When-Then format in docstrings
   - Document edge cases and special conditions

2. **Test Organization**
   - Group related tests in nested classes
   - Use descriptive names that explain the behavior
   - Keep test methods focused and concise

3. **Fixtures and Setup**
   - Use pytest fixtures for common setup
   - Keep setup code minimal and clear
   - Document fixture purpose and usage

4. **Assertions**
   - Make assertions clear and specific
   - Include meaningful error messages
   - Test one behavior per test method

### Running Tests

```bash
# Run all tests
pytest

# Run specific specification
pytest path/to/specific_spec.py

# Show specification-style output
pytest --verbose
```

### Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [BDD with Pytest](https://pytest-bdd.readthedocs.io/)
- [Writing Good Tests](https://docs.pytest.org/en/stable/goodpractices.html)
