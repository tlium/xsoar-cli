# Contributing to xsoar-cli

We welcome contributions of all kinds! Whether you're fixing bugs, adding features, improving documentation, or sharing ideas, your help makes this project better.

## Ways to Contribute

### Documentation (just as valuable as code!)
- Fix typos or unclear explanations
- Add examples and use cases
- Improve command documentation
- Translate documentation
- Write tutorials or blog posts

### Code Contributions
- Bug fixes and performance improvements
- New features and command enhancements
- Plugin examples and templates
- Test coverage improvements

### Issue Reports
- Bug reports with clear reproduction steps
- Feature requests with use case descriptions
- Documentation gaps or confusion points

## Getting Started

### 1. Fork and Clone
1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/xsoar-cli.git
   cd xsoar-cli
   ```

### 2. Set Up Development Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements_dev.txt

# Install the package in development mode
pip install -e .
```

### 3. Verify Setup
```bash
# Run tests to ensure everything works
pytest

# Check code style
black --check src/ tests/

# Run the CLI to verify installation
xsoar-cli --help
```

## Development Workflow

### Making Changes
1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** (code, docs, tests)

3. **Run quality checks**:
   ```bash
   # Run tests
   pytest
   
   # Format code
   black src/ tests/
   
   # Check for any issues
   python -m pytest --cov=src/xsoar_cli
   ```

4. **Commit with clear messages**:
   ```bash
   git add .
   git commit -m "Add feature: brief description of what you added"
   ```

5. **Push and create Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Style
- We use [Black](https://github.com/psf/black) for code formatting
- Run `black src/ tests/` before committing
- Follow existing code patterns and conventions
- Add type hints where appropriate
- Write docstrings for new functions and classes

### Testing
- Add tests for new features
- Ensure existing tests still pass
- Aim for good test coverage
- Test commands work with both XSOAR v6 and v8 when applicable

## Documentation Contributions

Documentation improvements are especially welcome! You can contribute to documentation in several ways:

### Quick Edits
- **Edit files directly on GitHub** (great for small fixes like typos)
- Click the "Edit" button on any file in the GitHub interface
- Make your changes and create a pull request

### Larger Documentation Changes
- Use the full development setup described above
- Focus on clarity - assume readers are new to the tool
- Include practical examples where helpful
- Test any code examples you include

### Types of Documentation Contributions
- **README improvements**: Better explanations, more examples
- **Command documentation**: Individual command READMEs in `src/xsoar_cli/*/README.md`
- **Plugin documentation**: Examples and guides for plugin development
- **Troubleshooting**: Common issues and solutions
- **Tutorials**: Step-by-step guides for specific workflows

## Submitting Pull Requests

### Before Submitting
- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`black src/ tests/`)
- [ ] Documentation is updated if needed
- [ ] Commit messages are clear and descriptive

### Pull Request Guidelines
- **Describe your changes** clearly in the PR description
- **Reference any related issues** (e.g., "Fixes #123")
- **Include testing instructions** if applicable
- **Be responsive to feedback** during code review

### What to Expect
- We'll review your PR as soon as possible
- We may suggest changes or improvements
- Once approved, we'll merge your contribution
- Your contribution will be included in the next release

## Reporting Issues

### Bug Reports
Please include:
- **Clear description** of the problem
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment details** (Python version, XSOAR version, OS)
- **Error messages** and stack traces if applicable

### Feature Requests
Please include:
- **Use case description** - what problem does this solve?
- **Proposed solution** or implementation ideas
- **Examples** of how the feature would be used

## Development Tips

### Working with XSOAR Environments
- Test against both XSOAR v6 and v8 when possible
- Use the configuration examples in the README as reference
- Consider how features work with different authentication methods

### Plugin Development
- Look at the plugin documentation in `src/xsoar_cli/plugins/README.md`
- Follow the plugin architecture in `src/xsoar_cli/plugins/`
- Test plugin loading and command registration

### Command Development
- Follow the existing command structure
- Use Click decorators consistently
- Include proper help text and examples
- Consider error handling and user feedback

## Questions or Ideas?

- **Open an issue** for discussion
- **Check existing issues** for similar topics
- **Feel free to ask questions** - we're here to help!
- **Join discussions** on existing PRs and issues

## Code of Conduct

Be respectful and constructive in all interactions. We want this to be a welcoming space for contributors of all backgrounds and experience levels.

## Recognition

Contributors are recognized in release notes and we appreciate all contributions, no matter how small!

Thank you for contributing!