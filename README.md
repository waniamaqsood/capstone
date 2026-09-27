# Phase 1 — System Design

## 1. Overview

The system is a content repurposing and publishing backend that takes an original piece of content, generates platform-specific variants using an LLM, allows those variants to move through an approval workflow, and eventually supports scheduling and publishing through platform adapters.

The design prioritizes a clear separation between the original content, generated variants, approval state, scheduling, and publishing history. This allows the system to evolve from a simple content-generation API into a more complete publishing workflow without coupling these responsibilities together.

### Core technology decisions

* **Backend:** Python + FastAPI
* **Database:** SQLite
* **LLM:** Gemini
* **Publishing architecture:** Platform adapters
* **Real adapter:** Discord
* **Mock adapters:** MockX and MockLinkedIn
* **Initial generated platforms:** LinkedIn and Instagram
* **Input formats:** URL or Markdown

---

## 2. High-Level Workflow

The proposed workflow is:

**Content Input → Store Original Post → Generate Variants → Review → Approve/Reject → Schedule → Publish → Record History**

The original post remains the **single source of truth**. Generated platform-specific content is stored separately as variants rather than modifying the original post.

A variant initially has the status `draft`.

The review lifecycle is:

**draft → approved → published**

or:

**draft → rejected**

Scheduling is treated as a separate concern from approval. A variant can therefore be approved without immediately being published.

Once a variant has been approved, its content cannot be edited. This preserves the integrity of the content that was reviewed and approved.

---

## 3. Input Design

The system accepts two types of source input:

```text
source_type = "url" | "markdown"
```

### URL input

When the source type is `url`, the system receives a URL and attempts to retrieve its content.

If fetching fails, the system returns an error and asks the user to provide a valid URL or Markdown content again. The system should not silently create a variant from incomplete or failed source data.

### Markdown input

When the source type is `markdown`, the supplied Markdown content is used directly as the source content.

The stored post therefore represents the normalized source material regardless of how it originally entered the system.

---

## 4. Data Model

### Post

The `Post` entity represents the original source content.

```text
Post
├── id
├── source_url
├── content
├── created_at
└── source_type
```

`source_type` identifies whether the source was supplied as a URL or Markdown.

The original `content` is retained so that generated variants can always be traced back to the exact source material used.

---

### Variant

A `Variant` represents platform-specific generated content derived from a `Post`.

```text
Variant
├── id
├── post_id
├── platform
├── content
├── status
└── created_at
```

The relationship is:

```text
Post 1 ──────── * Variant
```

For example, one source post could produce:

```text
Post
 ├── LinkedIn Variant
 └── Instagram Variant
```

The initial generation targets are **LinkedIn and Instagram**.

---

### Schedule

Scheduling is stored independently from the variant itself.

```text
Schedule
├── id
├── variant_id
├── platform
├── scheduled_at
└── idempotency_key
```

The `idempotency_key` is used to help prevent the same scheduled publication from being executed more than once.

A schedule belongs to a specific variant and therefore preserves the connection between the approved content and its intended publication time.

---

### PublishHistory

Every publishing attempt is recorded separately.

```text
PublishHistory
├── id
├── variant_id
├── platform
├── attempted_at
├── result
└── error_message
```

This provides an audit trail of publishing attempts, including successful and unsuccessful attempts.

---

## 5. Variant State Management

Variants follow an explicit state machine:

```text
                 ┌───────────┐
                 │   draft   │
                 └─────┬─────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
        ┌───────────┐     ┌──────────┐
        │ approved  │     │ rejected │
        └─────┬─────┘     └──────────┘
              │
              ▼
        ┌───────────┐
        │ published │
        └───────────┘
```

A draft can be reviewed and either approved or rejected.

An approved variant may then be scheduled for publication.

Once approved, the variant's content is immutable. This prevents an approved version from being changed after review.

Publishing does not replace the variant content; instead, the publishing attempt is recorded in `PublishHistory`.

---

## 6. Platform Adapter Architecture

Publishing is separated from the core application through platform adapters.

The architecture supports:

```text
                Publishing Service
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Discord        MockX    MockLinkedIn
       Adapter       Adapter     Adapter
```

The real implementation for Phase 1 is the **Discord adapter**.

`MockX` and `MockLinkedIn` provide simulated platform integrations for development and testing without requiring live platform APIs.

This adapter-based approach means that platform-specific publishing logic does not need to be embedded directly into the core workflow.

---

## 7. LLM Generation

Gemini is responsible for transforming the original source content into platform-specific variants.

The generation process uses the stored `Post` as the source and produces separate `Variant` records for the requested platforms.

For example:

```text
Original Post
      │
      ▼
    Gemini
      │
      ├── LinkedIn content → LinkedIn Variant
      │
      └── Instagram content → Instagram Variant
```

The generated content is stored rather than generated dynamically every time it is requested. This allows the generated version to be reviewed, approved, scheduled, and published as a specific artifact.

---

## 8. Separation of Responsibilities

The system is intentionally divided into distinct responsibilities:

| Component          | Responsibility                  |
| ------------------ | ------------------------------- |
| FastAPI            | HTTP/API layer                  |
| Post service       | Source content management       |
| Generation service | Gemini-based variant generation |
| Variant workflow   | Draft, approval and rejection   |
| Scheduler          | Managing scheduled publications |
| Platform adapters  | Platform-specific publishing    |
| Publish history    | Recording publication attempts  |
| SQLite             | Persistent storage              |

This separation keeps content generation independent from publishing.

For example, generating a LinkedIn variant should not require the LinkedIn publishing adapter to be available.

---

## 9. Error Handling

The system should explicitly handle failures at each stage.

For source retrieval:

```text
URL → Fetch → Success → Store content
             │
             └── Failure → Return error + request URL/Markdown again
```

For publishing, a failed attempt should not erase the variant or schedule. Instead, the failure should be recorded in `PublishHistory`, including an error message where applicable.

This makes failures observable and keeps the original generated content intact.

---

## 10. Design Principles

The Phase 1 design follows several core principles:

1. **Single source of truth** — the original `Post` remains the canonical source content.
2. **Separation of generated content** — platform-specific content is stored as independent `Variant` records.
3. **Explicit workflow states** — approval and publishing states are represented rather than inferred.
4. **Immutable approved content** — approved variants cannot be edited.
5. **Separation of scheduling and publishing** — scheduling determines when publication should occur; adapters determine how publication happens.
6. **Platform abstraction** — platform-specific functionality is isolated behind adapters.
7. **Traceability** — publishing attempts are recorded in `PublishHistory`.
8. **Testability** — mock adapters allow publishing behaviour to be tested without relying entirely on external platforms.

## 11. Phase 1 Scope

The Phase 1 design establishes the architecture, entities, workflow, input model, platform strategy, and persistence model required for implementation.

The implementation target is:

**Python + FastAPI + SQLite + Gemini + platform adapters**

with:

* URL and Markdown source input
* LinkedIn and Instagram variant generation
* Draft/approval/rejection workflow
* Immutable approved variants
* Separate scheduling
* Discord publishing adapter
* MockX and MockLinkedIn adapters
* Publishing history and error tracking

This design provides the foundation for implementing the API and services in the next phase while keeping generation, review, scheduling, and publishing as separate concerns.
