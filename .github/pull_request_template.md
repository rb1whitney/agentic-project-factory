## Summary

> Why is this change needed? What problem does it solve?

<!-- One to three sentences. Be specific. Link to an issue if applicable. -->

Closes #

---

## Type of Change

<!-- Check all that apply -->

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (no functional change)
- [ ] Infrastructure change (Terraform / Ansible / Packer)
- [ ] Documentation
- [ ] CI / tooling

---

## What Changed

> What did you actually do? Describe the implementation, not the goal.

<!-- Key files modified, modules added, resources changed, etc. -->

---

## Infrastructure Changes

> Complete this section for any Terraform, Ansible, or Packer changes.

**`terraform plan` output or summary:**

```
# Paste plan summary here or attach as a comment
```

**Resources affected:**

| Resource | Action |
|---|---|
| `aws_xyz.example` | create / update / destroy |

**Blast radius:** <!-- Estimated scope of impact if this goes wrong -->

---

## Testing

> How was this tested? Check all that apply.

- [ ] `terraform fmt -check` passed
- [ ] `terraform validate` passed
- [ ] `tflint` passed
- [ ] `ansible-lint` passed
- [ ] Manual test in non-production environment
- [ ] Unit tests added or updated
- [ ] Integration tests added or updated
- [ ] No testing required (explain why below)

**Test environment:** <!-- e.g. dev account us-east-1, local kind cluster -->

**How to verify:**

```bash
# Commands a reviewer can run to verify the change
```

---

## Security Checklist

- [ ] No secrets, API keys, or credentials are hardcoded
- [ ] IAM permissions follow least privilege
- [ ] No public access added without explicit justification
- [ ] Encryption at rest and in transit is maintained
- [ ] Security groups do not open 0.0.0.0/0 without justification

---

## Rollback Plan

> How do you undo this if it breaks production?

<!-- e.g. "Revert this PR and apply previous Terraform state", "ansible-playbook rollback.yml" -->

---

## Reviewer Notes

> Anything specific you want reviewers to focus on?

<!-- Tricky logic, performance tradeoffs, design decisions that had alternatives -->

---

## Checklist

- [ ] Self-reviewed this PR before requesting review
- [ ] Linked related issues or tickets
- [ ] AGENT.md or README updated if this changes how the repo works
- [ ] Docs updated if this changes operational behavior
