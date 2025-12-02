# LLM Integration Guidelines

## Overview

This document provides detailed guidelines for how Large Language Model (LLM) CLIs such as Claude Code should interact with contextgit-managed projects. It includes:

- Detection mechanisms
- Command usage patterns
- Common workflows with step-by-step examples
- Best practices for context management
- Error handling

---

## Detection: Is This Project Using contextgit?

### Detection Method

An LLM CLI should check for the presence of `.contextgit/config.yaml` at the repository root.

**Algorithm:**

1. When opening a project or starting work, check if `.contextgit/config.yaml` exists
2. If it exists:
   - Assume the project is contextgit-managed
   - Use contextgit conventions when creating or modifying requirements
   - Use contextgit CLI commands to query and update traceability
3. If it doesn't exist:
   - Proceed with normal workflows (no contextgit integration)

**Example (pseudocode):**

```python
def is_contextgit_project():
    return os.path.exists('.contextgit/config.yaml')

if is_contextgit_project():
    print("Detected contextgit-managed project")
    # Use contextgit workflows
else:
    print("Not a contextgit project")
    # Use standard workflows
```

---

## Core Principles for LLM Integration

### 1. Precise Context Extraction

**Problem:** Loading entire requirement documents wastes tokens and dilutes focus.

**Solution:** Use `contextgit extract` to load only relevant snippets.

**Example:**
```bash
# Bad: Load entire file
cat docs/02_system/logging_api.md

# Good: Extract specific requirement
contextgit extract SR-010 --format json
```

### 2. Traceability from the Start

**Problem:** Creating requirements without tracking relationships leads to disconnected documentation.

**Solution:** Always specify `upstream` and `downstream` links when creating new requirements.

**Example:**
When creating a system requirement that refines BR-001, include:
```yaml
upstream: [BR-001]
downstream: []  # Will be filled in when architecture/code is created
```

### 3. Metadata Consistency

**Problem:** Inconsistent or missing metadata makes traceability unreliable.

**Solution:** Always use `contextgit next-id` to generate IDs, and always include required metadata fields.

### 4. Scan After Changes

**Problem:** The index gets out of sync with actual files.

**Solution:** Run `contextgit scan` after creating or modifying any requirement files.

### 5. Use JSON Output

**Problem:** Parsing human-readable text output is fragile.

**Solution:** Always use `--format json` for commands that will be parsed programmatically.

---

## Common Workflows

### Workflow 1: Create a New Business Requirement

**User Request:**
> "Create a business requirement for user authentication"

**LLM Steps:**

1. **Generate ID:**
   ```bash
   contextgit next-id business --format json
   ```
   Response: `{"type": "business", "id": "BR-003"}`

2. **Create file with metadata:**
   File: `docs/01_business/authentication.md`
   ```markdown
   ---
   contextgit:
     id: BR-003
     type: business
     title: "Users must be able to authenticate securely"
     upstream: []
     downstream: []
     status: active
     tags:
       - "feature:auth"
       - "priority:high"
   ---

   # Business Requirement: User Authentication

   The system must provide secure user authentication to protect user data and ensure only authorized users can access the platform.

   ## Requirements

   - Users must be able to register with email and password
   - Users must be able to log in with credentials
   - Passwords must be stored securely (hashed)
   - Failed login attempts must be rate-limited
   ```

3. **Scan to update index:**
   ```bash
   contextgit scan docs/01_business --recursive
   ```

4. **Verify:**
   ```bash
   contextgit show BR-003 --format json
   ```

5. **Report to user:**
   > "Created business requirement BR-003: 'Users must be able to authenticate securely' in docs/01_business/authentication.md"

---

### Workflow 2: Create a System Requirement that Refines a Business Requirement

**User Request:**
> "Create a system requirement for JWT-based authentication that implements BR-003"

**LLM Steps:**

1. **Extract context from upstream requirement:**
   ```bash
   contextgit extract BR-003 --format json
   ```
   This provides context for the new system requirement.

2. **Generate ID:**
   ```bash
   contextgit next-id system --format json
   ```
   Response: `{"type": "system", "id": "SR-015"}`

3. **Create file with metadata:**
   File: `docs/02_system/authentication.md`
   ```markdown
   ---
   contextgit:
     id: SR-015
     type: system
     title: "System shall implement JWT-based authentication"
     upstream: [BR-003]
     downstream: []
     status: active
     tags:
       - "feature:auth"
       - "api:rest"
   ---

   # System Requirement: JWT Authentication

   The system shall implement authentication using JSON Web Tokens (JWT).

   ## Specifications

   - Authentication endpoint: `POST /api/auth/login`
   - Token expiry: 24 hours
   - Token refresh endpoint: `POST /api/auth/refresh`
   - Token validation on all protected endpoints
   ```

4. **Scan to update index:**
   ```bash
   contextgit scan docs/02_system --recursive
   ```

5. **Verify link creation:**
   ```bash
   contextgit show SR-015 --format json
   ```
   Should show `BR-003` in upstream links.

6. **Report to user:**
   > "Created system requirement SR-015: 'System shall implement JWT-based authentication' that refines BR-003"

---

### Workflow 3: Implement Code for a System Requirement

**User Request:**
> "Implement the JWT authentication system for SR-015"

**LLM Steps:**

1. **Extract requirement details:**
   ```bash
   contextgit extract SR-015 --format json
   ```

2. **Check for upstream context (optional but recommended):**
   ```bash
   contextgit show SR-015 --format json
   ```
   This reveals BR-003 as upstream, so you can extract that too if needed.

3. **Implement code:**
   Create `src/auth/jwt_handler.py` with implementation.

4. **Create architecture or code-level documentation:**
   File: `docs/03_architecture/auth_design.md`
   ```markdown
   ## JWT Handler

   <!-- contextgit
   id: C-050
   type: code
   title: "JWTHandler class for token management"
   upstream: [SR-015]
   downstream: [T-025]
   status: active
   -->

   The `JWTHandler` class in `src/auth/jwt_handler.py` implements JWT token creation, validation, and refresh logic.

   ### Implementation Notes

   - Uses `PyJWT` library
   - Secret key loaded from environment variable
   - Token expiry: 24 hours
   - Refresh token expiry: 7 days
   ```

5. **Scan to update index:**
   ```bash
   contextgit scan docs/03_architecture --recursive
   ```

6. **Verify traceability:**
   ```bash
   contextgit show SR-015 --format json
   ```
   Should now show `C-050` in downstream links.

7. **Report to user:**
   > "Implemented JWT authentication in src/auth/jwt_handler.py. Created code item C-050 with traceability to SR-015."

---

### Workflow 4: Update an Existing Requirement

**User Request:**
> "Update BR-003 to require multi-factor authentication"

**LLM Steps:**

1. **Extract current content:**
   ```bash
   contextgit extract BR-003
   ```

2. **Modify the file** `docs/01_business/authentication.md` to add MFA requirement.

3. **Scan to detect changes:**
   ```bash
   contextgit scan docs/01_business --recursive
   ```
   The tool will detect the checksum change and mark downstream links (BR-003 → SR-015) as `upstream_changed`.

4. **Check status:**
   ```bash
   contextgit status --stale --format json
   ```
   Response shows:
   ```json
   {
     "stale_links": [
       {
         "from": "BR-003",
         "to": "SR-015",
         "status": "upstream_changed"
       }
     ]
   }
   ```

5. **Report to user:**
   > "Updated BR-003. Downstream requirement SR-015 is now marked as needing review because the upstream requirement changed. Would you like me to update SR-015 to reflect the MFA requirement?"

6. **If user says yes, update SR-015:**
   - Extract SR-015
   - Modify to include MFA
   - Scan again

7. **Confirm sync:**
   ```bash
   contextgit confirm SR-015
   ```
   This marks the link as `ok` again.

---

### Workflow 5: Find Requirements Relevant to a Source File

**User Request:**
> "Refactor src/auth/jwt_handler.py"

**LLM Steps:**

1. **Find relevant requirements:**
   ```bash
   contextgit relevant-for-file src/auth/jwt_handler.py --format json
   ```
   Response:
   ```json
   {
     "file": "src/auth/jwt_handler.py",
     "nodes": [
       {
         "id": "C-050",
         "title": "JWTHandler class for token management",
         "distance": 0
       },
       {
         "id": "SR-015",
         "title": "System shall implement JWT-based authentication",
         "distance": 1
       },
       {
         "id": "BR-003",
         "title": "Users must be able to authenticate securely",
         "distance": 2
       }
     ]
   }
   ```

2. **Extract relevant snippets:**
   ```bash
   contextgit extract C-050 --format json
   contextgit extract SR-015 --format json
   ```

3. **Use as context for refactoring:**
   Load these snippets into context before refactoring to ensure alignment with requirements.

4. **Perform refactoring:**
   Refactor the code while maintaining compliance with SR-015 and BR-003.

5. **Update documentation if needed:**
   If the refactoring changes the architecture significantly, update C-050 documentation.

6. **Scan and confirm:**
   ```bash
   contextgit scan docs/03_architecture --recursive
   contextgit confirm C-050
   ```

7. **Report to user:**
   > "Refactored src/auth/jwt_handler.py while maintaining alignment with requirements SR-015 and BR-003."

---

### Workflow 6: Detect and Address Stale Requirements

**User Request:**
> "Check if any requirements are out of sync"

**LLM Steps:**

1. **Check status:**
   ```bash
   contextgit status --stale --format json
   ```
   Response:
   ```json
   {
     "stale_links": [
       {
         "from": "BR-001",
         "to": "SR-010",
         "sync_status": "upstream_changed",
         "last_checked": "2025-12-02T10:00:00Z"
       },
       {
         "from": "SR-010",
         "to": "C-120",
         "sync_status": "upstream_changed",
         "last_checked": "2025-12-02T11:00:00Z"
       }
     ]
   }
   ```

2. **Report to user:**
   > "Found 2 stale links:
   > 1. SR-010 needs review because BR-001 changed
   > 2. C-120 needs review because SR-010 changed
   >
   > Would you like me to review and update these requirements?"

3. **If user says yes:**
   - Extract BR-001 to see what changed
   - Extract SR-010 to see current state
   - Update SR-010 if needed
   - Scan and confirm:
     ```bash
     contextgit scan docs/02_system --recursive
     contextgit confirm SR-010
     ```
   - Repeat for C-120

4. **Verify:**
   ```bash
   contextgit status --stale --format json
   ```
   Should show no stale links.

---

### Workflow 7: Create a Test Specification

**User Request:**
> "Create test specifications for C-050"

**LLM Steps:**

1. **Extract code item details:**
   ```bash
   contextgit extract C-050 --format json
   ```

2. **Generate test ID:**
   ```bash
   contextgit next-id test --format json
   ```
   Response: `{"type": "test", "id": "T-025"}`

3. **Create test specification:**
   File: `docs/04_tests/auth_tests.md`
   ```markdown
   ## JWT Handler Tests

   <!-- contextgit
   id: T-025
   type: test
   title: "Test suite for JWTHandler class"
   upstream: [C-050]
   downstream: []
   status: active
   -->

   Test cases for the JWTHandler class:

   1. **test_create_token**: Verify token creation with valid credentials
   2. **test_validate_token**: Verify token validation with valid token
   3. **test_expired_token**: Verify rejection of expired tokens
   4. **test_invalid_signature**: Verify rejection of tokens with invalid signatures
   5. **test_refresh_token**: Verify token refresh functionality
   ```

4. **Scan:**
   ```bash
   contextgit scan docs/04_tests --recursive
   ```

5. **Verify link:**
   ```bash
   contextgit show C-050 --format json
   ```
   Should show T-025 in downstream links.

6. **Implement tests:**
   Create `tests/test_jwt_handler.py` with actual test code.

7. **Report to user:**
   > "Created test specification T-025 for C-050. Test cases documented in docs/04_tests/auth_tests.md"

---

## Best Practices for LLMs

### 1. Always Use `--format json` for Parsing

When you need to parse command output, always use `--format json`.

**Bad:**
```bash
contextgit show SR-010 | grep "Title:"
```

**Good:**
```bash
contextgit show SR-010 --format json | jq '.node.title'
```

### 2. Verify Commands Succeeded

Always check exit codes and handle errors gracefully.

**Example:**
```python
result = subprocess.run(['contextgit', 'next-id', 'system', '--format', 'json'],
                       capture_output=True, text=True)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
    # Handle error
else:
    data = json.loads(result.stdout)
    new_id = data['id']
```

### 3. Extract Only What You Need

Don't extract every upstream requirement. Extract only the immediate context needed for the task.

**Example:**
If implementing SR-015, extract SR-015 and optionally its immediate upstream (BR-003). Don't traverse the entire graph unless specifically needed.

### 4. Scan Frequently

Run `contextgit scan` after any file modifications to keep the index in sync.

**Pattern:**
```
1. Modify file
2. Run contextgit scan
3. Verify with contextgit show or contextgit status
```

### 5. Confirm Sync After Updates

When updating downstream items in response to upstream changes, always run `contextgit confirm` to mark the sync complete.

**Pattern:**
```
1. Upstream requirement changes
2. contextgit scan detects change, marks downstream as stale
3. Review and update downstream requirement
4. contextgit scan to update checksum
5. contextgit confirm <ID> to mark as synced
```

### 6. Use Descriptive Titles

When creating nodes, use clear, descriptive titles that convey the essence of the requirement.

**Bad:**
```yaml
title: "Authentication"
```

**Good:**
```yaml
title: "System shall implement JWT-based authentication"
```

### 7. Tag Consistently

Use consistent tagging conventions for easy filtering.

**Conventions:**
- `feature:<name>`: Feature category (e.g., `feature:auth`, `feature:logging`)
- `priority:<level>`: Priority (e.g., `priority:high`, `priority:medium`)
- `component:<name>`: System component (e.g., `component:api`, `component:database`)
- `domain:<name>`: Business domain (e.g., `domain:billing`, `domain:users`)

**Example:**
```yaml
tags:
  - "feature:auth"
  - "priority:high"
  - "component:api"
```

---

## Error Handling for LLMs

### Error: Node Not Found

**Command:**
```bash
contextgit show SR-999
```

**Error:**
```
Error: Node not found: SR-999
```

**Exit code:** 3

**LLM Response:**
> "I couldn't find requirement SR-999 in the index. Let me check what system requirements exist."
>
> Then run:
> ```bash
> contextgit status --type system --format json
> ```

### Error: Invalid Metadata

**Command:**
```bash
contextgit scan docs/02_system/bad_file.md
```

**Error:**
```
Error: Invalid metadata in docs/02_system/bad_file.md:15: Missing required field 'type'
```

**Exit code:** 4

**LLM Response:**
> "The metadata block in docs/02_system/bad_file.md is missing the 'type' field. Let me fix that."
>
> Then edit the file to add the missing field.

### Error: .contextgit Not Initialized

**Command:**
```bash
contextgit scan docs/
```

**Error:**
```
Error: Could not load config: .contextgit/config.yaml not found
```

**Exit code:** 5

**LLM Response:**
> "This project hasn't been initialized for contextgit yet. Would you like me to run 'contextgit init'?"

---

## Integration with Development Workflows

### Pre-Commit Hook (Example)

Projects can add a git pre-commit hook to ensure requirements are scanned:

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running contextgit scan..."
contextgit scan --recursive

if [ $? -ne 0 ]; then
  echo "Error: contextgit scan failed"
  exit 1
fi

echo "contextgit scan complete"
exit 0
```

LLMs should be aware of this and suggest it when appropriate.

### CI Pipeline (Example)

Projects can add CI checks for stale requirements:

```yaml
# .github/workflows/contextgit.yml
name: Requirements Traceability

on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install contextgit
        run: pip install contextgit
      - name: Scan requirements
        run: contextgit scan --recursive
      - name: Check for stale links
        run: |
          STATUS=$(contextgit status --format json)
          STALE=$(echo $STATUS | jq '.links.stale')
          if [ "$STALE" -gt 0 ]; then
            echo "Error: $STALE stale links detected"
            contextgit status --stale
            exit 1
          fi
```

LLMs can suggest this when users want to enforce traceability in CI.

---

## Advanced Patterns

### Pattern 1: Bulk ID Generation

If creating multiple requirements, generate all IDs upfront:

```bash
# Generate 3 system requirement IDs
for i in {1..3}; do
  contextgit next-id system --format json
done
```

Note: Each call increments, so you get SR-012, SR-013, SR-014.

### Pattern 2: Dependency Analysis

To understand the full dependency tree for a requirement:

```bash
# Show SR-010 and its upstream/downstream
contextgit show SR-010 --format json

# Then recursively extract each upstream and downstream node
# Build a complete dependency graph
```

### Pattern 3: Coverage Analysis

To find code files that have no requirements:

1. List all code files
2. For each file, run `contextgit relevant-for-file <path>`
3. If no results, that file has no traceability

This can be useful for identifying gaps in documentation.

---

## Summary

LLM integration with contextgit is designed to:

1. **Reduce token usage**: Extract only relevant snippets instead of full documents
2. **Maintain traceability**: Automatically track relationships between requirements
3. **Detect drift**: Alert when upstream changes affect downstream items
4. **Enable precision**: Work with specific requirement IDs instead of vague references

By following these guidelines, LLM CLIs like Claude Code can provide accurate, context-aware assistance while maintaining clear traceability from business goals to working code.

---

## Quick Reference Card for LLMs

| Task | Commands |
|------|----------|
| Check if project uses contextgit | `ls .contextgit/config.yaml` |
| Generate new ID | `contextgit next-id <type> --format json` |
| Extract requirement | `contextgit extract <ID> --format json` |
| Show node details | `contextgit show <ID> --format json` |
| Find relevant requirements | `contextgit relevant-for-file <path> --format json` |
| Scan after changes | `contextgit scan --recursive` |
| Check for stale links | `contextgit status --stale --format json` |
| Confirm sync | `contextgit confirm <ID>` |
| Create manual link | `contextgit link <FROM> <TO> --type <relation>` |
| Format index | `contextgit fmt` |

Always use `--format json` for programmatic parsing.
