---
name: skill-pr-creator
description: Quality gatekeeper for drafting high-resolution GitHub Pull Requests with documentation compliance.
---
# Pull Request Creator

This skill guides the creation of high-performance Pull Requests that adhere to the factory's standards.

## Workflow

Follow these steps to create a Pull Request:

1.  **Branch Management (CRITICAL)**: Ensure you are NOT working on the master branch.
    - Run `git branch --show-current`.
    - If the current branch is master, you MUST create and switch to a new descriptive branch: `git checkout -b <new-branch-name>`.

2.  **Commit Changes**: Verify that all intended changes are committed.
    - Run `git status` to check for unstaged or uncommitted changes.
    - Stage and commit with a descriptive message following Conventional Commits format. NEVER commit directly to master.

3.  **Locate Template**: Search for a pull request template in the factory.
    - Check `.github/pull_request_template.md`.

4.  **Read Template**: Read the content of the identified template file.

5.  **Draft Description**: Create a PR description that strictly follows the template's structure.
    - **Headings**: Keep all headings from the template.
    - **Checklists**: Review each item. Mark with [x] if completed.
    - **Content**: Fill in the sections with clear, concise summaries of your changes.

6.  **Preflight Check**: Ensure all build, lint, and test checks pass locally before creation.

7.  **Push Branch**: Push the current branch to the remote repository.
    - **CRITICAL SAFETY RAIL**: Double-check your branch name before pushing. NEVER push if the current branch is master.

8.  **Create PR**: Use the gh CLI to create the PR. To avoid shell escaping issues with multi-line Markdown, write the description to a temporary file first.
    ```bash
    # 1. Write the drafted description to a temporary file
    # 2. Create the PR using the --body-file flag
    gh pr create --title "type(scope): succinct description" --body-file <temp_file_path>
    ```

## Operating Principles
1.  **Safety First**: NEVER push to master. This is the highest priority.
2.  **Compliance**: Never ignore the PR template.
3.  **Accuracy**: Do not check boxes for tasks not performed.
4.  **No Emojis**: Emojis are prohibited in PR descriptions and titles to maintain technical professionalism.
5.  **NEVER MERGE (CRITICAL)**: You MUST NEVER merge a Pull Request. Creating the PR is the absolute end of this workflow. Only a human may merge.
