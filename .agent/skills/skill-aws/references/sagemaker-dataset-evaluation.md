# Workflow Instruction

Follow the workflow shown below. Locate the dataset, check the file type, and resolve any issues with missing files or wrong file types. Determine the fine-tuning model and fine-tuning strategy. Use the SageMaker data format documentation (linked under Resources) to evaluate whether the file is formatted correctly for the currently selected model and strategy. Summarize the results: is the dataset ready for fine-tuning?

## Workflow

1. **Locate Dataset**:
   - The full path may be a local file path, or an S3 URI
   - Resolve the full path to the dataset file, make sure read permissions are available, and help the user if the file is not found

2. **Determine strategy and model**:
   - File formatting depends on the currently selected fine-tuning strategy and fine-tuning base model.
   - If the strategy and model are already known from the conversation context (e.g., selected via the finetuning-setup skill), use them.
   - If not available in context, activate the finetuning-setup skill to determine them before proceeding.

3. **Check File Formatting**: Inspect the file in place with read-only commands, then compare to the requirements for the chosen strategy and model.
   - Do not download data from S3 and do not make local copies; for an S3 URI stream the first lines: `aws s3 cp s3://<bucket>/<key> - | head -n 3`.
   - Confirm every line parses as JSON: `jq -c . <file> > /dev/null && echo valid-jsonl`.
   - List the keys the first record uses and the number of records: `head -n 1 <file> | jq 'keys'; wc -l < <file>`.
   - Compare those keys to the strategy's required fields in the SageMaker documentation linked below.

4. **Summarize Results**: Tell the user if their data is ready
   - Examine the key listing and compare to the known strategy and model
   - **Important: training datasets and evaluation datasets have different format requirements.**
     - **Training datasets** must match the fine-tuning strategy format (SFT, DPO, RLVR) per the SageMaker data format documentation
     - **Evaluation datasets** (for model evaluation) must match one of the [SageMaker evaluation dataset formats](https://docs.aws.amazon.com/sagemaker/latest/dg/model-customize-evaluation-dataset-formats.html).
   - Report back to the user if their current dataset is valid for its intended purpose
   - Warn the user if their dataset is valid, but for a different strategy or model
   - Warn the user if their dataset is not valid for any strategy/model pair

## Messages to the User

- Introduction: "This skill checks the structure of your dataset for model fine-tuning."
- File types: This skill applies to files that are formatted according to the [Amazon SageMaker AI Developer Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/autopilot-llms-finetuning-data-format.html#autopilot-llms-finetuning-dataset-format)

# Resources

- finetuning-setup skill should have already determined the fine-tuning strategy and base model
- Data format requirements per strategy: [SageMaker fine-tuning dataset formats](https://docs.aws.amazon.com/sagemaker/latest/dg/autopilot-llms-finetuning-data-format.html#autopilot-llms-finetuning-dataset-format). No local copy is kept in this repo.
