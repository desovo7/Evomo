"""Full-parameter action SFT for Qwen using planner-final ALFWorld actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-report", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error(f"output directory is not empty: {args.output_dir}")
    manifest = json.loads(args.dataset_manifest.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != sha256(args.dataset):
        raise ValueError("SFT dataset differs from its content-addressed manifest")

    import torch
    from torch.nn.utils.rnn import pad_sequence
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainerCallback,
        TrainingArguments,
        set_seed,
    )

    set_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    class ActionDataset(Dataset):
        def __init__(self, path: Path) -> None:
            self.offsets = []
            with path.open("rb") as stream:
                while True:
                    offset = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    if line.strip():
                        self.offsets.append(offset)
            self.path = path

        def __len__(self) -> int:
            return len(self.offsets)

        def __getitem__(self, index: int) -> dict[str, list[int]]:
            with self.path.open("rb") as stream:
                stream.seek(self.offsets[index])
                row = json.loads(stream.readline())
            prompt = tokenizer.apply_chat_template(
                row["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
            target_ids = tokenizer(row["target"] + tokenizer.eos_token, add_special_tokens=False)[
                "input_ids"
            ]
            if len(target_ids) >= args.max_length:
                raise ValueError("SFT action target exceeds max length")
            prompt_ids = prompt_ids[-(args.max_length - len(target_ids)) :]
            input_ids = prompt_ids + target_ids
            return {
                "input_ids": input_ids,
                "attention_mask": [1] * len(input_ids),
                "labels": [-100] * len(prompt_ids) + target_ids,
            }

    class Collator:
        def __call__(self, rows):
            input_ids = pad_sequence(
                [torch.tensor(row["input_ids"], dtype=torch.long) for row in rows],
                batch_first=True,
                padding_value=tokenizer.pad_token_id,
            )
            attention_mask = pad_sequence(
                [torch.tensor(row["attention_mask"], dtype=torch.long) for row in rows],
                batch_first=True,
                padding_value=0,
            )
            labels = pad_sequence(
                [torch.tensor(row["labels"], dtype=torch.long) for row in rows],
                batch_first=True,
                padding_value=-100,
            )
            return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}

    class JsonlLogCallback(TrainerCallback):
        def __init__(self, path: Path) -> None:
            self.path = path
            self.path.parent.mkdir(parents=True, exist_ok=True)

        def on_log(self, args_, state, control, logs=None, **kwargs):
            if not state.is_world_process_zero or not logs:
                return
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"step": state.global_step, **logs}, separators=(",", ":")))
                stream.write("\n")

    dataset = ActionDataset(args.dataset)
    if len(dataset) != manifest.get("example_count"):
        raise ValueError("SFT dataset row count differs from manifest")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        local_files_only=True,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        bf16=True,
        tf32=True,
        logging_steps=10,
        save_strategy="no",
        report_to="none",
        remove_unused_columns=False,
        ddp_find_unused_parameters=False,
        dataloader_num_workers=2,
        seed=args.seed,
        data_seed=args.seed,
    )
    log_path = args.run_report.with_name("train_metrics.jsonl")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=Collator(),
        callbacks=[JsonlLogCallback(log_path)],
    )
    result = trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    if trainer.is_world_process_zero():
        report = {
            "status": "complete",
            "training_kind": "full_parameter_sft",
            "base_model_path": args.model_path.as_posix(),
            "dataset_manifest_path": args.dataset_manifest.as_posix(),
            "dataset_sha256": manifest["dataset_sha256"],
            "example_count": len(dataset),
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "per_device_batch_size": args.batch_size,
            "gradient_accumulation": args.gradient_accumulation,
            "world_size": int(os.environ.get("WORLD_SIZE", "1")),
            "max_length": args.max_length,
            "seed": args.seed,
            "global_step": trainer.state.global_step,
            "metrics": result.metrics,
            "checkpoint_path": args.output_dir.as_posix(),
            "checkpoint_files": sorted(path.name for path in args.output_dir.iterdir()),
        }
        args.run_report.parent.mkdir(parents=True, exist_ok=True)
        args.run_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
