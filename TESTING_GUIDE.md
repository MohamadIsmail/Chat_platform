# Testing Guide for Chat Platform

## Overview
This guide covers the comprehensive testing setup for the Chat Platform API, including unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_auth.py             # Authentication tests
├── test_messages.py         # Message functionality tests
└── test_integration.py      # Integration and workflow tests
```

## Test Categories

### 1. Unit Tests
- **Authentication**: User registration, login, validation
- **Message Operations**: Sending, retrieving, marking as read
- **Data Validation**: Input validation, error handling
- **Business Logic**: Core functionality testing

### 2. Integration Tests
- **Complete Workflows**: End-to-end user journeys
- **Multi-User Scenarios**: Conversations between multiple users
- **Error Handling**: System-wide error scenarios
- **Data Consistency**: Cross-operation data integrity

### 3. End-to-End Tests
- **Full API Workflows**: Complete user registration to messaging
- **Performance Tests**: Load testing, concurrent operations
- **Edge Cases**: Boundary conditions, special characters
- **Security Tests**: Input sanitization, authentication

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.sh
```

### Quick Start
```bash
# Run all tests
./scripts/run-tests.sh

# Run with coverage
./scripts/run-tests.sh -c

# Run specific test type
./scripts/run-tests.sh -t unit
./scripts/run-tests.sh -t integration
```

### Test Options

#### Command Line Options
```bash
./scripts/run-tests.sh [options]

Options:
  -t, --type TYPE        Test type: all, unit, integration, e2e
  -c, --coverage         Run with coverage report
  -v, --verbose          Verbose output
  -p, --parallel         Run tests in parallel
  -m, --markers MARKERS  Run tests with specific markers
  -f, --format FORMAT    Output format: short, long, line
  -h, --help             Show help message
```

#### Examples
```bash
# Run all tests with coverage
./scripts/run-tests.sh -c

# Run only authentication tests
./scripts/run-tests.sh -m auth

# Run integration tests in parallel
./scripts/run-tests.sh -t integration -p

# Run non-slow tests with verbose output
./scripts/run-tests.sh -m "not slow" -v

# Run with detailed output format
./scripts/run-tests.sh -f long
```

### Docker Testing
```bash
# Run tests in Docker container
./scripts/test-docker.sh

# Run specific test type in Docker
./scripts/test-docker.sh -t unit -c

# Keep containers after tests (for debugging)
./scripts/test-docker.sh --no-cleanup
```

## Test Configuration

### Environment Variables
```bash
# Test environment
export TESTING=true
export DATABASE_URL="sqlite:///./test_chat.db"
export REDIS_URL="redis://localhost:6379/1"
export CACHE_ENABLED=false
```

### Pytest Configuration
The `pytest.ini` file contains:
- Test discovery patterns
- Markers for test categorization
- Output formatting options
- Logging configuration
- Warning filters

### Test Fixtures
Located in `tests/conftest.py`:
- Database session management
- Test client setup
- Mock services
- Test data factories
- Helper functions

## Test Coverage

### Coverage Reports
```bash
# Generate HTML coverage report
./scripts/run-tests.sh -c

# View coverage report
open htmlcov/index.html
```

### Coverage Targets
- **Overall Coverage**: >90%
- **Critical Paths**: >95%
- **Authentication**: >95%
- **Message Operations**: >90%

## Test Categories and Markers

### Markers
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.messages` - Message tests
- `@pytest.mark.performance` - Performance tests

### Test Organization
```python
# Example test structure
class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_user_success(self, client, test_user_data):
        """Test successful user registration."""
        # Test implementation
    
    @pytest.mark.parametrize("invalid_data", [...])
    def test_register_user_validation(self, client, invalid_data):
        """Test registration validation."""
        # Test implementation
```

## Test Data Management

### Test Data Factory
```python
# Generate test data
user_data = data_factory.create_user_data()
users_data = data_factory.create_multiple_users(5)
message_data = data_factory.create_message_data()
```

### Fixtures
```python
# Database fixtures
@pytest.fixture
def db_session():
    """Fresh database session for each test."""
    
@pytest.fixture
def test_user(db_session, test_user_data):
    """Create test user in database."""
    
@pytest.fixture
def auth_headers(client, test_user, test_user_data):
    """Get authentication headers."""
```

## Mocking and Stubbing

### Redis Mocking
```python
@pytest.fixture
def mock_redis():
    """Mock Redis cache for testing."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    return mock_redis
```

### Service Mocking
```python
@pytest.fixture
def mock_cache_service(mock_redis):
    """Mock cache service for testing."""
    cache_service.cache_manager.redis = mock_redis
    cache_service.cache_manager.is_available = AsyncMock(return_value=True)
    return cache_service
```

## Test Scenarios

### Authentication Tests
1. **User Registration**
   - Valid registration
   - Duplicate username/email
   - Invalid data validation
   - SQL injection prevention
   - XSS prevention

2. **User Login**
   - Valid login
   - Invalid credentials
   - Missing credentials
   - Case sensitivity
   - Token generation

### Message Tests
1. **Message Sending**
   - Valid message sending
   - Unauthorized sending
   - Invalid recipient
   - Empty content
   - Special characters
   - Unicode support

2. **Message Retrieval**
   - Get conversation messages
   - Empty conversations
   - Bidirectional retrieval
   - Pagination support

3. **Message Operations**
   - Mark as read
   - Search messages
   - Delete messages
   - Message validation

### Integration Tests
1. **Complete Workflows**
   - User registration → Login → Send messages
   - Multi-user conversations
   - Search and messaging flow

2. **Error Handling**
   - Authentication errors
   - Message errors
   - Concurrent operations
   - Data consistency

3. **Performance Tests**
   - Bulk message creation
   - Concurrent user registration
   - Large message handling

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: ./scripts/run-tests.sh -c
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: ./scripts/run-tests.sh -t unit
        language: system
        pass_filenames: false
```

## Debugging Tests

### Running Individual Tests
```bash
# Run specific test file
pytest tests/test_auth.py

# Run specific test method
pytest tests/test_auth.py::TestUserRegistration::test_register_user_success

# Run with debugging
pytest tests/test_auth.py -v -s --pdb
```

### Test Debugging
```python
# Add debugging to tests
def test_example(client, test_user):
    response = client.post("/send", json=message_data)
    print(f"Response: {response.json()}")  # Debug output
    assert response.status_code == 200
```

### Database Inspection
```python
# Inspect database state
def test_with_db_inspection(db_session):
    # Perform operations
    user = db_session.query(User).first()
    print(f"User in DB: {user.username}")  # Debug output
```

## Performance Testing

### Load Testing
```python
def test_concurrent_operations(client, data_factory):
    """Test concurrent operations."""
    import threading
    
    results = []
    def operation():
        # Perform operation
        results.append(response.status_code)
    
    # Run concurrently
    threads = [threading.Thread(target=operation) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    assert all(status == 200 for status in results)
```

### Memory Testing
```python
def test_memory_usage():
    """Test memory usage with large data."""
    large_data = "A" * 10000
    # Test with large data
    response = client.post("/send", json={"content": large_data})
    assert response.status_code == 200
```

## Best Practices

### Test Organization
1. **One test per scenario**: Each test should verify one specific behavior
2. **Descriptive names**: Test names should clearly describe what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Independent tests**: Tests should not depend on each other

### Test Data
1. **Use factories**: Generate test data consistently
2. **Clean data**: Each test should start with clean state
3. **Realistic data**: Use realistic test data that matches production
4. **Edge cases**: Test boundary conditions and edge cases

### Assertions
1. **Specific assertions**: Use specific assertions rather than generic ones
2. **Error messages**: Include descriptive error messages
3. **Multiple assertions**: Verify multiple aspects of the response
4. **Negative testing**: Test both success and failure scenarios

### Mocking
1. **Mock external dependencies**: Mock Redis, external APIs, etc.
2. **Mock at boundaries**: Mock at service boundaries, not internal logic
3. **Verify interactions**: Verify that mocked methods are called correctly
4. **Reset mocks**: Reset mocks between tests

## Troubleshooting

### Common Issues

1. **Database Issues**
   ```bash
   # Clean test database
   rm -f test_chat.db
   ```

2. **Import Issues**
   ```bash
   # Check Python path
   export PYTHONPATH=$PWD:$PYTHONPATH
   ```

3. **Redis Issues**
   ```bash
   # Disable cache for testing
   export CACHE_ENABLED=false
   ```

4. **Permission Issues**
   ```bash
   # Make scripts executable
   chmod +x scripts/*.sh
   ```

### Test Failures

1. **Flaky Tests**: Ensure tests are deterministic
2. **Timeout Issues**: Increase timeout for slow tests
3. **Resource Issues**: Clean up resources after tests
4. **Concurrent Issues**: Use proper synchronization

## Coverage Analysis

### Coverage Reports
- **HTML Report**: `htmlcov/index.html`
- **Terminal Report**: Shows missing lines
- **XML Report**: For CI/CD integration

### Coverage Targets
- **Lines**: >90%
- **Branches**: >85%
- **Functions**: >95%
- **Classes**: >90%

### Coverage Exclusions
```python
# Exclude from coverage
# pragma: no cover
def debug_function():
    pass
```

This testing setup provides comprehensive coverage of the Chat Platform API, ensuring reliability, performance, and maintainability.
