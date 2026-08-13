#!/usr/bin/env bash
set -euo pipefail

workspace=/data_b/qzluo/workspace/wlx/Evomo
slime_root=/data_b/qzluo/workspace/wlx/Evolving-RL/slime
runtime_deps=/data_b/qzluo/workspace/wlx/Evolving-RL/.runtime_deps
megatron_root=/data_b/qzluo/workspace/Megatron-LM
slime_python=/data_b/qzluo/miniconda3/envs/slime/bin/python
hf_checkpoint=${1:?Hugging Face checkpoint required}
output_dir=${2:?torch_dist output directory required}

source "$workspace/configs/slime_qwen3_1_7b_model.sh"
export PYTHONPATH="$workspace/src:$runtime_deps:$slime_root:$megatron_root"
export CUDA_DEVICE_MAX_CONNECTIONS=1
"$slime_python" -m torch.distributed.run --nproc_per_node 3 \
  "$slime_root/tools/convert_hf_to_torch_dist.py" \
  --hf-checkpoint "$hf_checkpoint" --save "$output_dir" \
  --megatron-to-hf-mode bridge "${MODEL_ARGS[@]}" \
  --tensor-model-parallel-size 1 --pipeline-model-parallel-size 3 \
  --context-parallel-size 1 --expert-model-parallel-size 1 \
  --expert-tensor-parallel-size 1 --seq-length 4096
