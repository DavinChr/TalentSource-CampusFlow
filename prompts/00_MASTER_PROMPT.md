# CAMPUSFLOW
## Academic Campus Facility & Event Coordinator

You are a senior software architect, AI agent engineer, MCP engineer, backend engineer, database engineer, QA engineer, and technical researcher.

Your task is to design and implement **CampusFlow**, an AI-agent-based campus orchestration system that manages complex, multi-departmental university requests through natural-language instructions.

The system must combine:

- LLM-based agent reasoning
- LangGraph and/or ReAct-style execution loop
- Model Context Protocol (MCP)
- SQLite or PostgreSQL MCP Server
- Filesystem MCP Server
- Custom Mock API MCP Server
- deterministic validation
- transactional database updates
- structured logging
- failure handling
- end-to-end testing

The goal is not merely to create a chatbot.

The goal is to build a **controlled autonomous workflow agent** capable of decomposing a complex campus request, consulting multiple information sources, validating prerequisites sequentially, performing an authorized state-changing action only when all required conditions pass, and notifying the appropriate campus department.

---

# 1. PROJECT CONTEXT

Project name:

CampusFlow

Project category:

Academic Campus Facility & Event Coordinator

Core concept:

Multi-departmental campus orchestration and automated resource routing.

CampusFlow receives natural-language requests from campus staff or students and converts them into structured multi-step workflows.

Example request:

"Book the main auditorium for a 100-person AI workshop next Tuesday, check if the projector is working, and notify the facilities team."

The system should interpret this request as a workflow rather than a single action.

Expected conceptual workflow:

1. Understand the request.
2. Extract required resources and constraints.
3. Identify the requested date and time.
4. Determine the required room capacity.
5. Check room availability.
6. If the room is unavailable, stop the booking workflow.
7. If the room is available, verify equipment availability/status.
8. If the required equipment is unavailable or defective, stop the booking workflow.
9. Only when all required validations pass, write the booking to the database.
10. Notify the relevant department through the notification MCP.
11. Return a structured result to the user.

The agent must NEVER skip prerequisite validation.

---

# 2. PRIMARY OBJECTIVE

Build an autonomous AI agent that can handle multi-step campus facility workflows involving:

- room reservation
- room capacity validation
- schedule conflict detection
- equipment availability verification
- equipment operational-status verification
- maintenance-log inspection
- booking creation
- department notification
- workflow failure handling
- audit logging

The system should demonstrate reliable orchestration between multiple MCP data sources.

---

# 3. REQUIRED MCP COMPONENTS

The system must integrate three MCP-based resources.

## 3.1 Database MCP Server

Use SQLite or PostgreSQL.

The database must contain information required for:

- buildings
- rooms
- room capacities
- room schedules
- bookings
- equipment
- equipment assignments
- potentially users/requesters
- workflow/audit records if appropriate

The MCP layer must provide the agent with access to the database through standardized tools.

The agent must be able to:

- inspect schema
- query room availability
- query capacity
- query booking conflicts
- verify relevant equipment records
- create a booking only after validation
- retrieve booking information

Do not allow unrestricted database modification by the agent if a safer constrained mechanism can be implemented.

Prefer controlled write operations.

---

# 3.2 Filesystem MCP Server

The filesystem MCP must provide access to campus operational files such as:

- maintenance logs
- equipment inventory catalogs
- equipment status records
- facilities information
- maintenance schedules

Example files may include:

maintenance_logs.txt

equipment_inventory.txt

equipment_status.txt

The agent must use the filesystem MCP when information about equipment condition or maintenance cannot be reliably determined from the database.

Do not fabricate equipment status.

If the required information cannot be found, the agent must explicitly report that the status could not be verified.

---

# 3.3 Custom Mock API MCP Server

Create a mock internal campus notification API exposed through MCP.

The mock API represents an internal campus messaging/notification system.

It should support operations conceptually equivalent to:

- send notification
- identify department
- retrieve notification status
- optionally retrieve notification history

Example:

Facilities Department receives:

"CampusFlow booking confirmed: Main Auditorium, 100-person AI Workshop, Tuesday, [date/time]. Projector status verified."

The mock API does not need to connect to a real external messaging service.

It must simulate the internal campus notification workflow.

---

# 4. AGENT EXECUTION MODEL

Use LangGraph, ReAct, or an equivalent explicit state-machine/agent orchestration architecture.

Do not implement the agent as a single unrestricted LLM call.

The workflow must have explicit states.

At minimum, design states similar to:

```text
REQUEST_RECEIVED
        ↓
REQUEST_PARSED
        ↓
REQUIREMENTS_VALIDATED
        ↓
ROOM_SEARCH
        ↓
ROOM_AVAILABILITY_CHECK
        ↓
EQUIPMENT_CHECK
        ↓
BOOKING_AUTHORIZATION
        ↓
BOOKING_WRITE
        ↓
NOTIFICATION
        ↓
COMPLETED
```

Failure states should include:

```text
INVALID_REQUEST
ROOM_UNAVAILABLE
INSUFFICIENT_CAPACITY
EQUIPMENT_UNAVAILABLE
EQUIPMENT_STATUS_UNKNOWN
BOOKING_CONFLICT
DATABASE_ERROR
MCP_ERROR
NOTIFICATION_ERROR
WORKFLOW_ABORTED
```

---

# 5. NON-NEGOTIABLE EXECUTION RULE

The following rule is mandatory:

## NEVER WRITE THE FINAL BOOKING BEFORE VALIDATION IS COMPLETE.

The booking sequence must be:

```text
Parse request
    ↓
Validate requirements
    ↓
Check room availability
    ↓
Check room capacity
    ↓
Check required equipment
    ↓
Check equipment operational status
    ↓
All validations PASS?
    ↓
YES ──→ Write booking
    ↓
Send notification
```

If any required validation fails:

```text
Validation failure
      ↓
Do NOT write booking
      ↓
Explain failure
      ↓
Suggest alternative if appropriate
```

The agent must not reason:

"Room appears available, therefore book it."

It must reason using explicit validated state.

---

# 6. AGENT STATE

Design a structured state object.

The state should contain only information necessary for the workflow.

A conceptual state may contain:

```text
request
requester
event
date
start_time
end_time
attendee_count

room_requirements
candidate_rooms
selected_room

room_availability
capacity_validation

required_equipment
equipment_results
equipment_status

validation_results

booking_authorized
booking_id

notification_required
notification_target
notification_status

errors
workflow_status
audit_information
```

Avoid storing unnecessary conversational information inside the execution state.

---

# 7. TOOL USAGE POLICY

The agent must understand that tools provide evidence.

LLM reasoning must not replace tool verification.

For example:

BAD:

"The projector should probably be working."

GOOD:

"Filesystem maintenance log shows projector P-01 passed its latest maintenance inspection on [date], with no active fault recorded."

Tool results must be treated as authoritative within the scope of the system.

If tool information conflicts:

1. detect the conflict
2. do not silently choose one
3. mark the validation as uncertain
4. stop state-changing operations
5. report the issue

---

# 8. DATABASE DESIGN REQUIREMENTS

Before implementing the database, inspect and design the data model.

At minimum consider:

```text
Building
Room
Equipment
RoomEquipment
Booking
User/Requester
```

Potential relationships:

```text
Building
   │
   └── Room
          │
          ├── RoomEquipment
          │       └── Equipment
          │
          └── Booking
```

Design the schema so that the following questions can be answered reliably:

1. Which rooms exist?
2. What is each room's capacity?
3. Which bookings exist?
4. Does a booking conflict with another booking?
5. Which equipment belongs to a room?
6. What equipment is required?
7. Which room satisfies the capacity requirement?
8. Is the requested room available for the requested time?

Use primary keys, foreign keys, appropriate indexes, constraints, and timestamps where appropriate.

---

# 9. TRANSACTIONAL BOOKING REQUIREMENT

Booking creation is a state-changing operation.

Therefore:

- validate first
- write second
- notify third

The booking write should be transactional.

Prevent race conditions where possible.

At minimum, prevent the agent from creating duplicate or conflicting bookings.

If the booking write fails:

- do not report success
- do not claim that the reservation exists
- return the database error in a controlled form

If notification fails after successful booking:

- preserve the successful booking
- mark notification as failed
- report the partial-success state
- do not roll back the booking unless the architecture explicitly requires transactional notification

---

# 10. NATURAL LANGUAGE REQUEST PARSING

The agent must convert natural language into structured requirements.

Example:

Input:

"Book the main auditorium for a 100-person AI workshop next Tuesday, check if the projector is working, and notify the facilities team."

Expected interpretation:

```text
resource:
    Main Auditorium

capacity:
    100

event:
    AI Workshop

date:
    next Tuesday

equipment:
    projector

equipment_requirement:
    operational

notification:
    Facilities Team
```

The exact date must be resolved using the system's current date.

Do not blindly interpret relative dates.

If the request lacks critical information, identify what is missing.

Examples:

- missing date
- missing time
- missing duration
- ambiguous room
- ambiguous equipment
- missing attendee count when capacity is required

Do not invent missing information.

---

# 11. DATE AND TIME VALIDATION

Relative dates such as:

- tomorrow
- next Tuesday
- this Friday

must be converted into explicit dates before querying the database.

Use the system's current date/time.

Do not allow ambiguous date interpretation to reach the booking write step.

If time is missing and the booking system requires time:

stop and request clarification.

---

# 12. REASONING POLICY

The agent must use explicit reasoning checkpoints.

At every major step determine:

```text
What do I know?
What evidence supports it?
What information is missing?
What tool should I call next?
What state transition is allowed?
```

Do not expose hidden chain-of-thought to the end user.

Instead, maintain a structured execution trace such as:

```text
Step 1: Request parsed
Step 2: Room availability checked
Step 3: Capacity validated
Step 4: Equipment status checked
Step 5: Booking authorized
Step 6: Booking created
Step 7: Facilities notified
```

The trace should be suitable for debugging and audit purposes.

---

# 13. GUARDRAILS

Implement explicit guardrails.

The agent must not:

- book without room validation
- book without equipment validation when equipment is required
- fabricate database records
- fabricate maintenance information
- fabricate equipment status
- bypass MCP tools
- claim a booking exists before the database confirms it
- claim notification succeeded before the mock API confirms it
- modify unrelated database records
- ignore validation failures
- silently resolve conflicting tool results
- use unsupported assumptions
- perform destructive database operations unless explicitly required

The agent must distinguish:

```text
AVAILABLE
UNAVAILABLE
UNKNOWN
ERROR
```

Do not collapse UNKNOWN into AVAILABLE.

---

# 14. MULTI-DEPARTMENT ROUTING

CampusFlow should support routing requests to appropriate departments.

Examples:

Room booking → Academic Facilities

Equipment issue → IT/Equipment Support

Maintenance issue → Facilities/Maintenance

Event-related coordination → Event/Academic Affairs

Notification routing should be based on structured workflow information rather than arbitrary LLM decisions.

Create a configurable routing mechanism.

---

# 15. FAILURE HANDLING

Design explicit behavior for:

## Room unavailable

Do not create booking.

Return:

- requested room
- requested schedule
- conflict information
- alternative rooms if available

## Capacity insufficient

Do not create booking.

Return rooms that satisfy capacity if available.

## Equipment unavailable

Do not create booking.

Return equipment issue.

## Equipment status unknown

Do not create booking when operational verification is mandatory.

Explain that the system could not verify the equipment.

## MCP unavailable

Do not fabricate results.

Return controlled failure.

## Database failure

Do not claim booking success.

## Notification failure

If booking succeeded:

return:

```text
Booking: SUCCESS
Notification: FAILED
```

This distinction is important.

---

# 16. PROJECT PHASES

Execute the project using the following phases.

---

## PHASE 0 — PROJECT INITIALIZATION

Before writing substantial code:

1. Inspect the existing repository.
2. Inspect package configuration.
3. Inspect available MCP configuration.
4. Inspect environment variables.
5. Inspect existing documentation.
6. Identify runtime/language/framework.
7. Identify constraints.
8. Identify missing infrastructure.
9. Create a project plan.

Do not overwrite existing code blindly.

If an existing architecture exists, preserve useful components.

Produce:

```text
PROJECT_CONTEXT.md
```

containing:

- project purpose
- current architecture
- technology stack
- assumptions
- constraints
- missing components
- implementation plan

---

# PHASE 1 — RESEARCH & BRAINSTORMING

Perform structured analysis before implementation.

Investigate:

1. Campus facility booking workflow.
2. Multi-departmental resource routing.
3. MCP architecture.
4. MCP tool boundaries.
5. LangGraph/ReAct orchestration patterns.
6. Agent guardrails.
7. Transactional booking systems.
8. Failure handling for tool-based agents.
9. Audit logging.
10. Testing strategies for agentic workflows.

The goal is not to build a generic research report.

The goal is to identify architecture decisions that directly affect CampusFlow.

Produce:

```text
docs/
    research.md
    problem-definition.md
    architecture-decisions.md
```

Separate:

- documented facts
- assumptions
- project decisions
- unresolved questions

Do not present assumptions as facts.

---

# PHASE 2 — SYSTEM DESIGN

Design the complete system before implementation.

Create:

```text
docs/
    architecture.md
    workflow.md
    state-machine.md
    data-model.md
    mcp-architecture.md
```

Define:

- components
- dependencies
- data flow
- agent states
- MCP boundaries
- database boundaries
- notification boundaries
- failure paths
- security boundaries

Create diagrams where practical using Mermaid.

The architecture should clearly distinguish:

```text
User
 ↓
Agent Orchestrator
 ↓
LangGraph State
 ↓
MCP Tools
 ├── Database MCP
 ├── Filesystem MCP
 └── Notification MCP
```

---

# PHASE 3 — DATABASE

Implement the database layer.

Tasks:

1. Create schema.
2. Create migrations or initialization scripts.
3. Insert realistic seed data.
4. Add constraints.
5. Add indexes.
6. Add representative booking conflicts.
7. Add realistic equipment records.
8. Verify all required queries.
9. Test booking transaction behavior.

Seed data should support meaningful demonstrations.

Include:

- multiple buildings
- multiple rooms
- different room capacities
- overlapping bookings
- available rooms
- unavailable rooms
- projector equipment
- working equipment
- equipment with maintenance issues

Do not use meaningless random data.

---

# PHASE 4 — MCP INFRASTRUCTURE

Implement/configure:

1. Database MCP Server.
2. Filesystem MCP Server.
3. Custom Notification Mock API MCP Server.

Document:

```text
docs/
    mcp-database.md
    mcp-filesystem.md
    mcp-notification.md
```

For each MCP define:

- purpose
- tools
- inputs
- outputs
- error behavior
- permissions
- expected consumers

Apply least-privilege principles.

The agent should only receive tools necessary for its workflow.

---

# PHASE 5 — AGENT ORCHESTRATION

Implement the LangGraph/ReAct workflow.

Create explicit nodes/functions for:

```text
parse_request
validate_requirements
check_room
validate_capacity
check_equipment
authorize_booking
create_booking
send_notification
finalize_workflow
handle_failure
```

Do not place the entire workflow into one giant agent function.

The state machine must make illegal transitions difficult or impossible.

For example:

```text
check_room
    ↓
room_available?
    ├── NO → failure
    └── YES
          ↓
check_equipment
          ↓
equipment_valid?
    ├── NO → failure
    └── YES
          ↓
authorize_booking
          ↓
create_booking
```

---

# PHASE 6 — GUARDRAILS & OPTIMIZATION

Review the implementation specifically for:

- hallucination
- tool misuse
- invalid state transitions
- missing validation
- duplicate bookings
- race conditions
- inconsistent state
- prompt injection through filesystem content
- malicious or misleading tool output
- excessive tool calls
- unnecessary LLM calls
- poor error handling

Optimize only after correctness is established.

Prioritize:

1. correctness
2. deterministic validation
3. safety
4. observability
5. maintainability
6. performance

Do not optimize by removing required validation.

---

# PHASE 7 — TESTING

Create automated tests.

At minimum test:

### Test 1 — Successful booking

Room available.

Capacity sufficient.

Projector operational.

Expected:

```text
booking = CREATED
notification = SENT
```

### Test 2 — Room unavailable

Expected:

```text
booking = NOT_CREATED
```

### Test 3 — Capacity insufficient

Expected:

```text
booking = NOT_CREATED
```

### Test 4 — Projector unavailable

Expected:

```text
booking = NOT_CREATED
```

### Test 5 — Projector status unknown

Expected:

```text
booking = NOT_CREATED
```

### Test 6 — Database failure

Expected:

```text
booking = UNKNOWN/FAILED
```

The system must not falsely claim success.

### Test 7 — Notification failure

Expected:

```text
booking = CREATED
notification = FAILED
```

### Test 8 — Conflicting tool information

Expected:

```text
workflow = ABORTED
booking = NOT_CREATED
```

### Test 9 — Ambiguous request

Expected:

```text
workflow = NEEDS_CLARIFICATION
```

### Test 10 — Duplicate booking

Expected:

```text
second_booking = REJECTED
```

---

# PHASE 8 — FINAL AUDIT

Before declaring the project complete:

Inspect the entire repository.

Check:

- unused code
- duplicated logic
- hardcoded credentials
- hardcoded paths
- unsafe SQL
- unrestricted database writes
- missing environment variables
- MCP configuration errors
- incorrect state transitions
- missing tests
- missing documentation
- inconsistent naming
- unnecessary dependencies

Run:

- lint
- type checking if applicable
- unit tests
- integration tests
- end-to-end tests

Then perform a manual end-to-end demonstration.

---

# 17. PARALLEL EXECUTION POLICY

You are allowed to execute independent tasks in parallel.

For example:

```text
DATABASE DESIGN
        │
        ├──────── DATABASE IMPLEMENTATION
        │
        ├──────── FILESYSTEM DATA DESIGN
        │
        └──────── NOTIFICATION API DESIGN
```

However, do not parallelize tasks that depend on unresolved architecture decisions.

Use dependency-aware execution.

Before starting a task, identify:

```text
Task
Dependencies
Inputs
Outputs
Validation criteria
```

Do not allow parallel tasks to silently create incompatible interfaces.

---

# 18. CHECKPOINT POLICY

After every major phase:

1. inspect generated artifacts
2. run relevant tests
3. verify assumptions
4. detect inconsistencies
5. update documentation
6. only then continue

If a critical failure occurs:

STOP the dependent work.

Do not continue building on an invalid foundation.

---

# 19. DOCUMENTATION REQUIREMENTS

The final project must include:

```text
README.md

docs/
    research.md
    problem-definition.md
    architecture.md
    workflow.md
    state-machine.md
    data-model.md
    mcp-database.md
    mcp-filesystem.md
    mcp-notification.md
    testing.md
    decisions.md
```

README must explain:

1. What CampusFlow is.
2. Problem being solved.
3. Architecture.
4. MCP components.
5. Agent workflow.
6. Database.
7. Installation.
8. Configuration.
9. Running the MCP servers.
10. Running the application.
11. Running tests.
12. Example request.
13. Expected result.
14. Known limitations.

---

# 20. FINAL DEMONSTRATION

The final system must be capable of demonstrating:

Input:

"Book the main auditorium for a 100-person AI workshop next Tuesday, check if the projector is working, and notify the facilities team."

The system should visibly execute:

```text
REQUEST RECEIVED

↓
REQUEST PARSED

↓
ROOM AVAILABILITY CHECK

↓
CAPACITY VALIDATION

↓
PROJECTOR STATUS CHECK

↓
ALL VALIDATIONS PASSED

↓
BOOKING CREATED

↓
FACILITIES TEAM NOTIFIED

↓
WORKFLOW COMPLETED
```

The demonstration must also include at least one failure case.

For example:

```text
PROJECTOR STATUS CHECK

↓
PROJECTOR HAS ACTIVE MAINTENANCE ISSUE

↓
BOOKING NOT CREATED

↓
FACILITIES TEAM MAY BE NOTIFIED OF THE ISSUE
```

The system must prove that the booking write operation does not occur when prerequisite validation fails.

---

# 21. DEFINITION OF DONE

CampusFlow is considered complete only when all conditions below are satisfied.

## Architecture

- [ ] LangGraph/ReAct-style orchestration exists.
- [ ] Agent uses explicit workflow states.
- [ ] MCP is used for externalized resources.
- [ ] Database MCP works.
- [ ] Filesystem MCP works.
- [ ] Notification MCP works.

## Workflow

- [ ] Natural-language request is parsed.
- [ ] Room availability is validated.
- [ ] Capacity is validated.
- [ ] Equipment is validated.
- [ ] Equipment operational status is verified.
- [ ] Booking occurs only after validation.
- [ ] Notification occurs after booking.
- [ ] Failure paths prevent invalid booking.

## Database

- [ ] Schema implemented.
- [ ] Seed data implemented.
- [ ] Constraints implemented.
- [ ] Booking conflict prevention implemented.
- [ ] Transactional booking implemented.

## Agent Safety

- [ ] No fabricated tool results.
- [ ] No booking before validation.
- [ ] Unknown is not treated as available.
- [ ] Tool failures are handled.
- [ ] Conflicting evidence is handled.
- [ ] Unauthorized actions are prevented.

## Testing

- [ ] Unit tests.
- [ ] Integration tests.
- [ ] MCP tests.
- [ ] End-to-end success test.
- [ ] End-to-end failure tests.
- [ ] Duplicate booking test.
- [ ] Notification failure test.

## Documentation

- [ ] Architecture documented.
- [ ] MCP documented.
- [ ] Database documented.
- [ ] Workflow documented.
- [ ] Testing documented.
- [ ] Setup instructions documented.
- [ ] Demo documented.

---

# 22. IMPORTANT ENGINEERING PRINCIPLE

Do not optimize for making the agent appear intelligent.

Optimize for making the workflow:

```text
CORRECT
TRACEABLE
DETERMINISTIC WHERE POSSIBLE
SAFE
TESTABLE
AUDITABLE
```

Use the LLM for:

- natural-language understanding
- intent extraction
- task decomposition
- selecting appropriate tools when necessary
- generating explanations

Use deterministic application logic for:

- capacity checks
- schedule conflict checks
- authorization
- booking constraints
- database transactions
- state transitions
- validation results

Do not delegate deterministic business rules to probabilistic LLM reasoning when they can be implemented programmatically.

---

# 23. YOUR EXECUTION BEHAVIOR

Act as an engineering agent, not merely a conversational assistant.

Do not immediately start generating a large amount of code.

First:

1. inspect the repository
2. understand the environment
3. create the project plan
4. identify dependencies
5. identify parallelizable tasks
6. implement incrementally
7. test continuously
8. review your own implementation
9. optimize
10. perform final end-to-end validation

When making architectural decisions, record them.

When encountering ambiguity:

- resolve it from existing project context when possible
- otherwise use the least-assumptive solution
- document the assumption
- do not silently invent requirements

When something fails:

- diagnose the root cause
- fix the underlying issue
- rerun affected tests
- check for regressions

Do not simply patch symptoms.

At the end of each phase, provide:

```text
PHASE
STATUS
COMPLETED TASKS
FILES CREATED/MODIFIED
TESTS EXECUTED
RESULTS
ISSUES
DECISIONS
NEXT PHASE
```

Do not declare the project complete until the Definition of Done has been verified.

# START

Begin with **PHASE 0 — PROJECT INITIALIZATION**.

Do not implement the entire project in one step.

First inspect the repository and environment, then produce the initial project plan and dependency graph.