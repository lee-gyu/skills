---
name: brainstorming
description: "Use for creative work. Explore user intent, requirements, and designs."
---

# Brainstorming Ideas

Help turn ideas into complete designs and specifications through natural, collaborative conversation.

Start by understanding the current project context, then ask one question at a time to refine the idea. Once you understand what to build, present the design and obtain the user's approval.

## Checklist

Create a task for each item below and complete them in order.

1. **Explore project context** - Review files, documentation, and recent commits.
2. **Ask clarifying questions** - Ask one at a time to understand the goal, constraints, and success criteria.
3. **Propose 2-3 approaches** - Include trade-offs and a recommendation.
4. **Present the design** - Use sections suited to the complexity, and obtain user approval after each section.
5. **Review the specification itself** - Quickly check inline for placeholders, contradictions, ambiguity, and scope (see below).

## Process

**Understand the idea:**

- First, inspect the current project state (files, documentation, and recent commits).
- Evaluate the scope before asking detailed questions. If the request describes multiple independent subsystems (for example, "Build a platform with chat, file storage, payments, and analytics"), point that out immediately. Do not spend time refining details with questions for a project that needs to be broken down first.
- If the project is too large for a single specification, help the user split it into subprojects. Determine the independent pieces, how they relate to each other, and the order in which they should be built. Then brainstorm the first subproject using the normal design flow. Each subproject has its own spec -> plan -> implementation cycle.
- For an appropriately scoped project, ask one question at a time to refine the idea.
- Prefer multiple-choice questions when possible, though open-ended questions are also fine.
- Ask only one question per message. If a topic needs more exploration, split it into several questions.
- Focus on understanding the goal, constraints, and success criteria.

**Explore approaches:**

- Propose 2-3 distinct approaches with trade-offs.
- Present the options conversationally, including a recommendation and the reason for it.
- Present the recommended option first and explain why.

**Present the design:**

- Once you believe you understand what to build, present the design.
- Tailor each section to the complexity: a few sentences for simple parts, and up to 200-300 words for nuanced parts.
- After each section, ask whether it looks right so far.
- Cover architecture, components, data flow, error handling, and testing.
- Be prepared to return to clarification if anything is not understood.

**Design for isolation and clarity:**

- Break the system into smaller units. Each unit should have one clear purpose, communicate through well-defined interfaces, and be independently understandable and testable.
- For each unit, you should be able to answer what it does, how it is used, and what it depends on.
- Can you understand what a unit does without reading its internals? Can you change its internals without breaking consumers? If not, refine the boundary.
- Small, well-bounded units are easier for you to work on as well. You can reason better about code that fits in context, and edits are more reliable when files stay focused. A large file is usually a sign that it is doing too much.

**Working in an existing codebase:**

- Explore the current structure before proposing changes. Follow existing patterns.
- If the existing code has issues that affect the work (for example, an oversized file, unclear boundaries, or tangled responsibilities), include targeted improvements in the design—as a good developer would improve the code they are working in.
- Do not propose unrelated refactoring. Focus on what contributes to the current goal.

## Core Principles

- **One question at a time** - Do not overwhelm the user with multiple questions.
- **Prefer multiple choice when possible** - It is easier to answer than open-ended questions when appropriate.
- **Apply YAGNI rigorously** - Remove unnecessary features from every design.
- **Explore alternatives** - Always propose 2-3 approaches before deciding.
- **Validate incrementally** - Present the design and obtain approval before moving on.
- **Respond flexibly** - Return to clarification whenever something is not understood.
