# General Rules

In general, favour declarative code styles over imperative code styles.

Favour list and dictionary comprehensions over for loops.

Every implementation you write should have a corresponding test.

Use pytest for testing, with mocker if you require mocking, do not use unittest. Do not use MagicMock directly, use it through the mocker wrapper.

Use @fixture markers for pytest fixtures, break up fixtures into smaller fixtures if they are too large.

Do not write Given/When/Then or Act/Arrange/Assert comments over those areas of the tests, but separate those phases of the test with a single blank line.

The test file must be placed in the same folder as the file containing the test subject.

Do not write conditional statements in tests, each test must fail for only one clear reason.

Use type hints for all functions and methods.

# Using Mojentic

If you need to write a tool for the LLM, model the implementation after mojentic.llm.tools.date_resolver.ResolveDateTool

If you need to write a tool for the LLM that uses an LLM, in the tool's initializer take the LLMBroker object as a parameter.

Don't ask the LLM to generate JSON directly, make use of the LLMBroker.generate_object() method.