# DDD Expert





##  The DDD Workflow Cycle

You MUST follow these phases in order. For each phase, load the associated TOML playbook from `.agent/skills/skill-conductor/references/` to define your specific role and constraints.

1. **Strategic Discovery**: **create-user-stories.toml**
   - Goal: Map user requirements and business value.
2. **Logical Mapping**: **logical.toml**
   - Goal: Define bounded contexts and ubiquitous language.
3. **Physical Design**: **physical.toml**
   - Goal: Blueprint the system architecture and project structure.
4. **Execution Planning**: **plan.toml**
   - Goal: Create a granular, TDD-ready IMPLEMENTATION_PLAN.md.
5. **TDD Implementation**: **implement.toml**
   - Goal: Execute the plan using a Red-Green-Refactor loop.
6. **Code Review**: **review.toml**
   - Goal: Verify SOLID compliance and architectural integrity.
7. **Regression Fixing**: **fix.toml**
   - Goal: Address audit failures and refine the implementation.

---
