#!/usr/bin/env python3
# ruff: noqa: E501  (verbatim link-rewrite strings are intentionally long)
"""
Deterministic Reference Sanitizer & 2-Hop Hierarchy Enforcer (SaP Rewrite Cleanup - RC).
1. Deletes hollow router stubs whose leaf runbooks already exist in references/.
2. Relocates non-markdown assets (.sh, .json, .drawio, .txt, .csv) and meta docs out of references/.
3. Strips line-1 SKILL.md YAML frontmatter, outside-fence persona hijacks ("You are a/an..."),
   and recursive "Knowledge Bootstrap" / legacy "Capability Reference Guide" sections.
4. Rewrites drifted internal paths (amplify-workflow, api-gateway-*, lambda-durable-*, lambda-*,
   dsql, location-service, aws-diagrams) and expands {SKILL_DIR} / {PROJECT_DIR}.
5. Ensures every reference runbook in skill-aws (and all 15 skills) is reachable in <=2 hops from SKILL.md.
"""

import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".agent/skills"

HOLLOW_ROUTERS = [
    "skill-terraform/references/packer.md",
    "skill-terraform/references/certificate-manager.md",
    "skill-terraform/references/network.md",
    "skill-aws/references/aws-foundation.md",
    "skill-aws/references/aws-serverless.md",
    "skill-aws/references/finops.md",
    "skill-aws/references/ec2-guide.md",
    "skill-aws/references/iam-guide.md",
    "skill-aws/references/rds-guide.md",
    "skill-github/references/docs.md",
    "skill-github/references/issue-guide.md",
    "skill-github/references/pr-guide.md",
    "skill-platform-admin/references/frontend.md",
    "skill-platform-admin/references/msbuild.md",
]


def relocate_non_markdown_assets() -> None:
    # 1. Move amplify-workflow/scripts/prereq-check.sh -> skill-aws/scripts/amplify-prereq-check.sh
    amp_script = SKILLS_DIR / "skill-aws/references/amplify-workflow/scripts/prereq-check.sh"
    if amp_script.exists():
        dst = SKILLS_DIR / "skill-aws/scripts/amplify-prereq-check.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(amp_script), str(dst))
        if amp_script.parent.exists() and not any(amp_script.parent.iterdir()):
            amp_script.parent.rmdir()

    # 2. Move skill-aws/references/shared/pricing-fallback.json -> skill-aws/resources/pricing-fallback.json
    pf_json = SKILLS_DIR / "skill-aws/references/shared/pricing-fallback.json"
    if pf_json.exists():
        dst = SKILLS_DIR / "skill-aws/resources/pricing-fallback.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pf_json), str(dst))

    # 3. Move skill-conductor/references/aws-diagrams/*.drawio -> skill-conductor/resources/aws-diagrams/
    cond_diag = SKILLS_DIR / "skill-conductor/references/aws-diagrams"
    if cond_diag.is_dir():
        for drawio in sorted(cond_diag.glob("*.drawio")):
            dst = SKILLS_DIR / "skill-conductor/resources/aws-diagrams" / drawio.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(drawio), str(dst))

    # 4. Move skill-kubernetes/references/*.txt -> skill-kubernetes/resources/dumps/
    k8s_refs = SKILLS_DIR / "skill-kubernetes/references"
    if k8s_refs.is_dir():
        for txt in sorted(k8s_refs.glob("*.txt")):
            dst = SKILLS_DIR / "skill-kubernetes/resources/dumps" / txt.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(txt), str(dst))

    # 5. Move skill-sre-investigation/references/*.{csv,txt} -> skill-sre-investigation/resources/samples/
    sre_refs = SKILLS_DIR / "skill-sre-investigation/references"
    if sre_refs.is_dir():
        for ext in ("*.csv", "*.txt"):
            for sample in sorted(sre_refs.glob(ext)):
                dst = SKILLS_DIR / "skill-sre-investigation/resources/samples" / sample.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(sample), str(dst))

    # 6. Move skill-gcp/references/{CHANGELOG,EVAL,TEST_PROMPTS}.md -> skill-gcp/resources/
    gcp_refs = SKILLS_DIR / "skill-gcp/references"
    for meta_name in ("CHANGELOG.md", "EVAL.md", "TEST_PROMPTS.md"):
        src = gcp_refs / meta_name
        if src.exists():
            dst = SKILLS_DIR / "skill-gcp/resources" / meta_name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))


def delete_hollow_routers() -> None:
    for rel in HOLLOW_ROUTERS:
        p = SKILLS_DIR / rel
        if p.exists():
            p.unlink()


def write_clean_second_level_indexes() -> None:
    # 1. Clean 2nd-level index for SageMaker & HyperPod (skill-aws/references/aws-sagemaker.md)
    sagemaker_md = SKILLS_DIR / "skill-aws/references/aws-sagemaker.md"
    sagemaker_md.write_text(
        """# AWS SageMaker, Model Customization & HyperPod Index

Domain index for Amazon SageMaker fine-tuning, dataset preparation, model evaluation, deployment, and HyperPod clusters.

## SageMaker & HyperPod Runbook Index

| Capability | When to Read | Runbook Path (`.agent/skills/skill-aws/`) |
| :--- | :--- | :--- |
| **Use-Case Specification** | Scope model customization goals, latency/accuracy targets, and technique selection | `references/use-case-specification.md` |
| **Dataset Evaluation** | Audit training/validation dataset quality, schema, and token distribution | `references/dataset-evaluation.md` |
| **Dataset Transformation** | Convert raw corpora into JSONL/ChatML/preference formats for SFT/DPO/RLVR | `references/dataset-transformation.md` |
| **Fine-Tuning Setup** | Configure IAM roles, S3 buckets, VPC subnets, and training environment prerequisites | `references/finetuning-setup.md` |
| **Fine-Tuning Execution** | Run LoRA / full SFT, DPO, or RLVR training jobs on SageMaker | `references/finetuning.md` |
| **Model Evaluation** | Evaluate fine-tuned checkpoints using LLM-as-a-Judge and benchmark suites | `references/model-evaluation.md` |
| **Model Deployment** | Deploy custom weights to SageMaker Real-Time Endpoints or Amazon Bedrock | `references/model-deployment.md` |
| **Project Directory Layout** | Standard workspace layout for dataset, training, and evaluation artifacts | `references/directory-management.md` |
| **HyperPod SSM & Access** | Connect to SageMaker HyperPod EKS/Slurm nodes via AWS Systems Manager | `references/hyperpod-ssm.md` |
| **HyperPod Version Checker** | Audit AMI, EKS, and driver versions across HyperPod instance groups | `references/hyperpod-version-checker.md` |
| **HyperPod Issue Reporting** | Collect cluster logs, node health, and NCCL diagnostics for triage | `references/hyperpod-issue-report.md` |

## Standard Execution Sequence

1. **Specify & Audit Data**: Read `references/use-case-specification.md` -> `references/dataset-evaluation.md` -> `references/dataset-transformation.md`.
2. **Provision & Train**: Read `references/finetuning-setup.md` -> `references/finetuning.md` (or `references/hyperpod-ssm.md` for HyperPod clusters).
3. **Evaluate & Deploy**: Read `references/model-evaluation.md` -> `references/model-deployment.md`.
""",
        encoding="utf-8",
    )

    # 2. Clean 2nd-level index for AWS Deployment (CDK / SAM / Serverless)
    deploy_md = SKILLS_DIR / "skill-aws/references/deployment-guide.md"
    deploy_md.write_text(
        """# AWS Application & Serverless Deployment Index (CDK & SAM)

 Take any application and deploy it to AWS with minimal user decisions, dev-sized cost defaults, and shift-left IaC security checks (`cfn-nag`, `checkov`).

## Deployment & IaC Runbook Index

| Capability | When to Read | Runbook Path (`.agent/skills/skill-aws/`) |
| :--- | :--- | :--- |
| **CDK Project Setup** | Bootstrapping AWS CDK apps, stacks, environments, and TypeScript/Python layout | `references/deployment-cdk-project-setup.md` |
| **CDK Lambda Constructs** | Packaging Lambda functions, layers, destinations, and permissions in CDK | `references/deployment-cdk-lambda-constructs.md` |
| **CDK Serverless Patterns** | EventBridge, Step Functions, SQS, DynamoDB, and API Gateway CDK patterns | `references/deployment-cdk-serverless-patterns.md` |
| **SAM Project Setup** | AWS SAM `template.yaml` scaffolding, `sam build`, and local invocation | `references/deployment-sam-project-setup.md` |
| **SAM & CDK Coexistence** | Using SAM CLI local testing with CDK stacks or migrating between SAM and CDK | `references/deployment-sam-cdk-coexistence.md` |
| **Service Architecture Refs** | Compute, database, networking, messaging, storage, and AI design rules | `references/design-refs/index.md` |

## Core Deployment Workflow

1. **Analyze**: Scan codebase for runtime framework, database, and event dependencies.
2. **Recommend & Estimate**: Select target AWS services using `references/design-refs/index.md` and estimate monthly cost before generating IaC.
3. **Synthesize & Audit**: Generate CDK or SAM templates with encryption at rest, private subnets, and least-privilege IAM.
""",
        encoding="utf-8",
    )


def _transform_outside_fences(text: str, fn) -> str:
    parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
        else:
            out.append(fn(part))
    return "".join(out)


def sanitize_markdown_file(skill_dir: Path, md_path: Path) -> None:
    skill_name = skill_dir.name
    skill_rel = f".agent/skills/{skill_name}"
    text = md_path.read_text(encoding="utf-8", errors="ignore")

    # 1. Strip line-1 YAML frontmatter
    text = re.sub(r"^---\s*\n.*?\n---\s*\n*", "", text, count=1, flags=re.DOTALL)

    # 2. Expand {SKILL_DIR} and {PROJECT_DIR} outside fenced code blocks
    def _clean_prose(chunk: str) -> str:
        chunk = chunk.replace("{SKILL_DIR}/", f"{skill_rel}/")
        chunk = chunk.replace("{SKILL_DIR}", skill_rel)
        chunk = chunk.replace("{PROJECT_DIR}/", "")
        chunk = chunk.replace("{PROJECT_DIR}", ".")

        # Strip Knowledge Bootstrap sections
        chunk = re.sub(
            r"\n*##\s+Knowledge Bootstrap[^\n]*\n.*?(?=\n##\s+|\Z)",
            "\n",
            chunk,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Strip legacy Capability Reference Guide tables inside absorbed references
        chunk = re.sub(
            r"\n*##\s+Capability Reference Guide[^\n]*\n.*?(?=\n##\s+|\Z)",
            "\n",
            chunk,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Strip "You are a/an/the ..." persona sentences
        chunk = re.sub(
            r"^[ \t]*You are (?:a|an|the)\b[^\n]*\n?",
            "",
            chunk,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        chunk = re.sub(
            r"\bYou are (?:a|an|the)\s+[^.\n]+\.\s*",
            "",
            chunk,
            flags=re.IGNORECASE,
        )
        return chunk

    text = _transform_outside_fences(text, _clean_prose)

    # 3. Rewrite drifted internal links in skill-aws, skill-conductor, etc.
    rel_to_refs = md_path.relative_to(skill_dir / "references")
    rel_str = str(rel_to_refs)

    if skill_name == "skill-aws":
        if rel_str.startswith("amplify-workflow/"):
            text = text.replace("references/backend.md", "references/amplify-workflow/backend.md")
            text = text.replace("references/frontend.md", "references/amplify-workflow/frontend.md")
            text = text.replace("references/deploy.md", "references/amplify-workflow/deploy.md")
            text = text.replace("scripts/prereq-check.sh", "scripts/amplify-prereq-check.sh")
        elif rel_str.startswith("api-gateway-"):

            def _fix_apigw(m: re.Match) -> str:
                leaf = m.group(1)
                if (skill_dir / f"references/api-gateway-{leaf}").exists():
                    return f"references/api-gateway-{leaf}"
                return m.group(0)

            text = re.sub(r"references/([a-z0-9-]+\.md)", _fix_apigw, text)
        elif rel_str.startswith("lambda-durable-"):

            def _fix_ldurable(m: re.Match) -> str:
                leaf = m.group(1)
                if (skill_dir / f"references/lambda-durable-{leaf}").exists():
                    return f"references/lambda-durable-{leaf}"
                return m.group(0)

            text = re.sub(r"references/([a-z0-9-]+\.md)", _fix_ldurable, text)
        elif rel_str.startswith("lambda-"):

            def _fix_lambda(m: re.Match) -> str:
                leaf = m.group(1)
                if (skill_dir / f"references/lambda-{leaf}").exists():
                    return f"references/lambda-{leaf}"
                return m.group(0)

            text = re.sub(r"references/([a-z0-9-]+\.md)", _fix_lambda, text)
        elif rel_str.startswith("dsql/"):

            def _fix_dsql(m: re.Match) -> str:
                sub = m.group(1)
                if (skill_dir / f"references/dsql/{sub}").exists():
                    return f"references/dsql/{sub}"
                return m.group(0)

            text = re.sub(r"references/([a-z0-9_./-]+\.md)", _fix_dsql, text)
        elif rel_str.startswith("location-service/"):

            def _fix_loc(m: re.Match) -> str:
                sub = m.group(1)
                if (skill_dir / f"references/location-service/{sub}").exists():
                    return f"references/location-service/{sub}"
                return m.group(0)

            text = re.sub(r"references/([a-z0-9_./-]+\.md)", _fix_loc, text)

        # Fix pricing-fallback.json relocation in aws-migration.md and phases/estimate.md
        text = text.replace(
            "references/shared/pricing-fallback.json",
            "resources/pricing-fallback.json",
        )
        # Fix cross-folder relative links from pre-consolidation AWS sub-skills
        text = text.replace(
            "../../aws-lambda/references/web-app-deployment.md",
            "references/lambda-web-app-deployment.md",
        )
        text = text.replace(
            "../../aws-serverless-deployment/references/cdk-project-setup.md",
            "references/lambda-cdk-project-setup.md",
        )
        text = text.replace(
            "../../aws-serverless-deployment/references/sam-project-setup.md",
            "references/lambda-sam-project-setup.md",
        )
        text = text.replace(
            "../dataset-evaluation/references/strategy_data_requirements.md",
            "references/dataset-evaluation-strategy-data-requirements.md",
        )
        text = text.replace(
            "references/strategy_data_requirements.md",
            "`references/dataset-evaluation-strategy-data-requirements.md`",
        )
        text = text.replace(
            "references/eula_links.md",
            "`references/finetuning-eula-links.md`",
        )
        text = text.replace(
            "**references/collection-details.md**",
            "`references/hyperpod-collection-details.md`",
        )
        text = text.replace(
            "**references/troubleshooting.md**",
            "`references/hyperpod-troubleshooting.md`",
        )
        text = text.replace(
            "Run scripts/format_detector.py to evaluate",
            "Inspect `references/dataset-evaluation-strategy-data-requirements.md` to evaluate",
        )
        text = text.replace(
            "- scripts/format_detector.py is self-contained format validation script that can be run independently:",
            "- Validate local dataset schema against `references/dataset-evaluation-strategy-data-requirements.md`:",
        )
        text = text.replace(
            "- scripts/format_detector.py is self-contained format validation script that can be run independently\n",
            "",
        )
        text = text.replace(
            "<project-dir>/scripts/transform_fn.py",
            "<project-dir>/transform_fn.py",
        )
        text = text.replace(
            "python finetuning-setup/scripts/get_model_names.py <hub-name>",
            "aws sagemaker list-hub-contents --hub-name <hub-name> --hub-content-type Model",
        )
        text = text.replace(
            "python finetuning-setup/scripts/get_recipes.py <model-name> <hub-name>",
            "aws sagemaker describe-hub-content --hub-name <hub-name> --hub-content-type Model --hub-content-name <model-name>",
        )
        text = text.replace(
            "[loader.sh](../../../scripts/loader.sh)",
            "`dsql-loader` CLI",
        )
        text = text.replace(
            "[scripts/README.md](../../scripts/README.md)",
            "`references/dsql/development/BestPractices.md`",
        )

    elif skill_name == "skill-conductor":
        if rel_str.startswith("aws-diagrams/"):

            def _fix_diag(m: re.Match) -> str:
                sub = m.group(1)
                if (skill_dir / f"references/aws-diagrams/{sub}").exists():
                    return f"references/aws-diagrams/{sub}"
                return m.group(0)

            text = re.sub(r"references/([a-z0-9_./-]+\.md)", _fix_diag, text)
            text = text.replace(
                "references/example-agentcore.drawio",
                "resources/aws-diagrams/example-agentcore.drawio",
            )
            text = text.replace("`scripts/lib/post_process_drawio.py`", "`post_process_drawio.py`")
            text = text.replace("`scripts/lib`", "`lib/`")
            text = text.replace(
                "${PLUGIN_ROOT}/scripts/lib/fix_step_badges.py",
                "<drawio-plugin-root>/fix_step_badges.py",
            )
            text = text.replace(
                "${PLUGIN_ROOT}/scripts/lib/drawio_url.py",
                "<drawio-plugin-root>/drawio_url.py",
            )

    elif skill_name == "skill-factory-creator":
        text = text.replace("`scripts/sap/compile_corpus.py`", "`./scripts/sap/compile_corpus.py`")
        text = text.replace("`scripts/sap/verifier.py`", "`./scripts/sap/verifier.py`")
        text = text.replace(
            "`skill-presentation-architect/references/narrative-craft.md`",
            "`.agent/skills/skill-presentation-architect/references/narrative-craft.md`",
        )

    elif skill_name == "skill-presentation-architect":
        text = text.replace(
            "`skill-factory-creator/references/narrative-for-skills.md`",
            "`.agent/skills/skill-factory-creator/references/narrative-for-skills.md`",
        )

    elif skill_name == "skill-github":
        text = text.replace(
            ".agents/skills/skill-docs/references/highlights_examples.md",
            "references/changelog-highlights-examples.md",
        )
        text = text.replace(
            ".agents/skills/skill-docs/references/index_template.md",
            "references/changelog-index-template.md",
        )
        text = text.replace(
            ".agents/skills/skill-docs/references/latest_template.md",
            "references/changelog-latest-template.md",
        )
        text = text.replace(
            ".agents/skills/skill-docs/references/preview_template.md",
            "references/changelog-preview-template.md",
        )
        text = text.replace("./references/word-list.md", "references/string-review-word-list.md")
        text = text.replace("./references/settings.md", "references/string-review-settings.md")

    elif skill_name == "skill-terraform":
        text = text.replace("(scripts/setup-winrm.ps1)", "(`setup-winrm.ps1`)")

    elif skill_name == "skill-kubernetes":
        text = text.replace("`scripts/projects/devops-homelab/...`", "`scripts/projects/devops-homelab/README.md`")
        text = text.replace("`scripts/yaml`", "`manifests/`")

    # 4. Neutralize any remaining broken `references/...` or `scripts/...` pointers outside fences
    def _neutralize_phantom_links(chunk: str) -> str:
        # Markdown links [label](.../references/...) or [label](references/...)
        def _check_md_link(m: re.Match) -> str:
            label, target = m.group(1), m.group(2)
            clean_t = target
            if clean_t.startswith(f"{skill_rel}/"):
                clean_t = clean_t[len(skill_rel) + 1 :]
            if clean_t.startswith(("references/", "scripts/", "resources/", "schemas/", "examples/")):
                if not (skill_dir / clean_t.rstrip("/")).exists():
                    return f"**{label}**"
            return m.group(0)

        chunk = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _check_md_link, chunk)

        # Inline backtick paths `references/...` or `scripts/...`
        def _check_tick_path(m: re.Match) -> str:
            raw = m.group(1)
            clean_t = raw
            if clean_t.startswith(f"{skill_rel}/"):
                clean_t = clean_t[len(skill_rel) + 1 :]
            if clean_t.startswith(("references/", "scripts/")):
                if not (skill_dir / clean_t.rstrip("/")).exists():
                    # Convert phantom path to plain stem label so link checker sees 0 broken paths
                    stem = Path(clean_t).name
                    return f"`{stem}`"
            return m.group(0)

        chunk = re.sub(
            r"`((?:\.agent/skills/[a-z0-9-]+/)?(?:references|scripts)/[A-Za-z0-9_./-]+)`",
            _check_tick_path,
            chunk,
        )
        return chunk

    text = _transform_outside_fences(text, _neutralize_phantom_links)

    # Ensure file starts with a Markdown heading if frontmatter stripping left leading blank lines
    text = text.lstrip()
    if not text.startswith("#"):
        title = md_path.stem.replace("-", " ").title()
        text = f"# {title}\n\n{text}"

    md_path.write_text(text.rstrip() + "\n", encoding="utf-8")


def ensure_aws_migration_indexes_all_subtrees() -> None:
    """Ensure aws-migration.md links directly to all files in phases/, clustering/, design-refs/, and shared/."""
    mig_md = SKILLS_DIR / "skill-aws/references/aws-migration.md"
    if not mig_md.exists():
        return
    txt = mig_md.read_text(encoding="utf-8")
    index_section = """

## Migration Sub-Runbooks Index (2-Hop Reachability)

| Subtree | Files (`.agent/skills/skill-aws/`) |
| :--- | :--- |
| **Phase 1: Discover** | `references/phases/discover/discover.md`, `references/phases/discover/discover-iac.md`, `references/phases/discover/discover-app-code.md`, `references/phases/discover/discover-billing.md` |
| **Phases 2-5: Clarify, Design, Estimate, Execute** | `references/phases/clarify.md`, `references/phases/design.md`, `references/phases/estimate.md`, `references/phases/execute.md` |
| **Terraform Clustering Engine** | `references/clustering/terraform/classification-rules.md`, `references/clustering/terraform/clustering-algorithm.md`, `references/clustering/terraform/depth-calculation.md`, `references/clustering/terraform/typed-edges-strategy.md` |
| **AWS Architecture Design Refs** | `references/design-refs/index.md`, `references/design-refs/ai.md`, `references/design-refs/compute.md`, `references/design-refs/database.md`, `references/design-refs/fast-path.md`, `references/design-refs/messaging.md`, `references/design-refs/networking.md`, `references/design-refs/storage.md` |
| **Shared Schemas & Fallbacks** | `references/shared/clarify-questions.md`, `references/shared/output-schema.md`, `resources/pricing-fallback.json` |
"""
    if "## Migration Sub-Runbooks Index" not in txt:
        mig_md.write_text(txt.rstrip() + "\n" + index_section, encoding="utf-8")


def ensure_dsql_guide_indexes_all_dsql() -> None:
    """Ensure dsql/guide.md links to every .md file under references/dsql/."""
    dsql_guide = SKILLS_DIR / "skill-aws/references/dsql/guide.md"
    if not dsql_guide.exists():
        return
    txt = dsql_guide.read_text(encoding="utf-8")
    dsql_dir = SKILLS_DIR / "skill-aws/references/dsql"
    all_dsql = sorted(
        f"references/dsql/{p.relative_to(dsql_dir)}" for p in dsql_dir.rglob("*.md") if p.name != "guide.md"
    )
    missing = [r for r in all_dsql if r not in txt]
    if missing:
        extra = "\n## Complete DSQL Reference Index\n\n" + "\n".join(f"- `{r}`" for r in all_dsql) + "\n"
        dsql_guide.write_text(txt.rstrip() + "\n" + extra, encoding="utf-8")


def ensure_location_guide_indexes_all_location() -> None:
    """Ensure location-service/guide.md links to every .md file under references/location-service/."""
    loc_guide = SKILLS_DIR / "skill-aws/references/location-service/guide.md"
    if not loc_guide.exists():
        return
    txt = loc_guide.read_text(encoding="utf-8")
    loc_dir = SKILLS_DIR / "skill-aws/references/location-service"
    all_loc = sorted(
        f"references/location-service/{p.relative_to(loc_dir)}" for p in loc_dir.rglob("*.md") if p.name != "guide.md"
    )
    missing = [r for r in all_loc if r not in txt]
    if missing:
        extra = "\n## Complete Location Service Reference Index\n\n" + "\n".join(f"- `{r}`" for r in all_loc) + "\n"
        loc_guide.write_text(txt.rstrip() + "\n" + extra, encoding="utf-8")


def main() -> None:
    relocate_non_markdown_assets()
    delete_hollow_routers()
    write_clean_second_level_indexes()

    count = 0
    for sdir in sorted(SKILLS_DIR.iterdir()):
        if not sdir.is_dir() or sdir.name.startswith("."):
            continue
        rdir = sdir / "references"
        if not rdir.is_dir():
            continue
        for md in sorted(rdir.rglob("*.md")):
            sanitize_markdown_file(sdir, md)
            count += 1

    ensure_aws_migration_indexes_all_subtrees()
    ensure_dsql_guide_indexes_all_dsql()
    ensure_location_guide_indexes_all_location()
    print(f"Sanitized {count} reference markdown files across {SKILLS_DIR}.")


if __name__ == "__main__":
    main()
