# Metadata Parser Examples

This file demonstrates the two metadata formats supported by the MetadataParser.

## Example 1: YAML Frontmatter

```markdown
---
contextgit:
  id: SR-001
  type: system
  title: User Authentication System
  status: active
  upstream: [BR-001, BR-002]
  downstream: [AR-001, AR-002]
  tags: [authentication, security]
  llm_generated: false
---

# User Authentication System

This system requirement defines the authentication mechanism...
```

## Example 2: Inline HTML Comment

```markdown
# Architecture Document

Some content describing the architecture...

<!-- contextgit
id: AR-001
type: architecture
title: JWT Token Implementation
upstream: SR-001
downstream: [CODE-001, CODE-002]
tags: [security, jwt]
llm_generated: true
-->

## JWT Token Details

The JWT implementation uses...
```

## Example 3: Multiple Inline Blocks

```markdown
# Design Document

<!-- contextgit
id: AR-001
type: architecture
title: Database Schema Design
upstream: SR-001
tags: database
-->

## Database Schema

<!-- contextgit
id: AR-002
type: architecture
title: API Endpoint Design
upstream: SR-002
tags: api
-->

## API Endpoints
```

## Example 4: String to List Conversion

The parser automatically converts single string values to lists:

```markdown
<!-- contextgit
id: TEST-001
type: test
title: Unit Test for Login
upstream: CODE-001
tags: unit-test
-->
```

This will be parsed as:
- `upstream: ["CODE-001"]`
- `tags: ["unit-test"]`

## Example 5: Default Values

When optional fields are omitted, defaults are used:

```markdown
<!-- contextgit
id: BR-001
type: business
title: User Login Feature
-->
```

This will be parsed with:
- `status: "active"`
- `upstream: []`
- `downstream: []`
- `tags: []`
- `llm_generated: False`
- `line_number: 1` (or actual line number)
