In general, favour declarative code styles over imperative code styles.

Favour list and dictionary comprehensions over for loops.

Every implementation you write should have a corresponding test.

Use pytest for testing, with mocker if you require mocking, do not use unittest.

Use @fixture markers for pytest fixtures, break up fixtures into smaller fixtures if they are too large.

Do not write Given/When/Then or Act/Arrange/Assert comments over those areas of the tests, but separate those phases of the test with a single blank line.

The test file must be placed in the same folder as the file containing the test subject.

Do not write conditional statements in tests, each test must fail for only one clear reason.

Use type hints for all functions and methods.
