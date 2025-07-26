# Commit Message Guidelines

## Commit Structure

Each commit message should follow this format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type
Must be one of the following:
- **feat**: A new feature
- **fix**: A bug fix
- **refactor**: Code changes that neither fix a bug nor add a feature
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (white-space, formatting, etc)
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to build process or auxiliary tools

### Scope
Optional, describes what part of the codebase is affected:
- **auth**: Authentication-related changes
- **cycle**: Cycle tracking functionality
- **phase**: Phase-related changes
- **telegram**: Telegram bot functionality
- **utils**: Utility functions
- **deps**: Dependency updates

### Subject
- Use imperative, present tense ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at the end
- Maximum 50 characters

### Body
- Optional
- Use imperative, present tense
- Include motivation for change and contrast with previous behavior
- Wrap at 72 characters

### Footer
- Optional
- Reference issues being closed: "Closes #123"
- Breaking changes should start with "BREAKING CHANGE:"

## Examples

```
feat(cycle): add weekly cycle prediction

Implement algorithm to predict cycle phases for next week based on
historical data. This helps users plan ahead for different phases.

Closes #45
```

```
fix(telegram): handle rate limit errors properly

Add proper handling of 429 responses from Telegram API to implement
exponential backoff and retry logic.
```

```
refactor(utils): extract date validation functions

Move date validation logic from cycle.py to separate module to reduce
code duplication and improve maintainability.
```

```
docs(api): update API documentation with new endpoints

Update API.md with newly added endpoints for phase prediction and
add examples for each endpoint.
```

## Git Workflow

1. **Keep commits atomic**
   - One logical change per commit
   - Makes reviewing, reverting, and cherry-picking easier

2. **Branch naming**
   - `feature/description`: New features
   - `fix/description`: Bug fixes
   - `refactor/description`: Code restructuring
   - `docs/description`: Documentation updates

3. **Before committing**
   - Run tests: `npm test`
   - Run linter: `npm run lint`
   - Ensure no debugging code is left
   - Check for sensitive data

4. **Pull Request process**
   - Create branch from main
   - Make changes in small, logical commits
   - Update tests and documentation
   - Create PR with clear description
   - Request review from team members

## Bad vs Good Examples

### Bad Commits ❌
```
fix stuff
update code
wip
final fix maybe
```

### Good Commits ✅
```
feat(auth): implement JWT authentication
fix(phase): correct cycle day calculation
refactor(utils): extract date formatting functions
docs(api): add swagger documentation
```

## Tips

1. Use imperative mood:
   - ✅ "add validation for date input"
   - ❌ "added validation for date input"

2. Be specific:
   - ✅ "fix incorrect phase calculation during ovulation"
   - ❌ "fix bug"

3. Reference issues:
   - ✅ "feat(cycle): add phase prediction (closes #123)"
   - ❌ "add feature"

4. Breaking changes:
   ```
   refactor(api): simplify authorization endpoints

   BREAKING CHANGE: Auth endpoints now require JWT token in
   Authorization header instead of query parameters
   ```

5. Multiple changes:
   - Make separate commits for different logical changes
   - Don't mix features and bug fixes in one commit

## Pre-commit Checklist

- [ ] Tests pass
- [ ] Code is linted
- [ ] No debugging code
- [ ] No sensitive data
- [ ] Documentation updated
- [ ] Commit message follows guidelines
- [ ] Changes are atomic
- [ ] Branch is up to date

## Version Control Best Practices

1. **Keep main branch stable**
   - Never commit directly to main
   - Use feature branches
   - Merge only after review

2. **Regular commits**
   - Commit frequently
   - Keep changes small and focused
   - Easy to understand and review

3. **Meaningful history**
   - Don't rewrite public history
   - Use rebase for local branches
   - Squash commits when appropriate

4. **Branch management**
   - Delete merged branches
   - Keep branches up to date
   - Use descriptive branch names

## Pull Request Template

```markdown
## Description
Brief description of changes

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe tests run

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] All tests passing
- [ ] No sensitive data included
```

Following these guidelines helps maintain a clean, professional git history and makes collaboration easier.
