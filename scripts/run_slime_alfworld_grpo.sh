#!/usr/bin/env bash
set -euo pipefail

workspace=/data_b/qzluo/workspace/wlx/Evomo
slime_root=/data_b/qzluo/workspace/wlx/Evolving-RL/slime
runtime_deps=/data_b/qzluo/workspace/wlx/Evolving-RL/.runtime_deps
megatron_root=/data_b/qzluo/workspace/Megatron-LM
slime_python=/data_b/qzluo/miniconda3/envs/slime/bin/python
sft_hf=${1:?SFT Hugging Face checkpoint required}
ref_dist=${2:?reference torch_dist checkpoint required}
output_root=${3:?output root required}
prompt_data=${4:?prompt dataset required}
custom_config=${5:?custom config required}

source "$workspace/configs/slime_qwen3_1_7b_model.sh"
mkdir -p "$output_root"
export PYTHONPATH="$workspace/src:$runtime_deps:$slime_root:$megatron_root"
export PYTHONUNBUFFERED=1
export CUDA_DEVICE_MAX_CONNECTIONS=1
export NCCL_NVLS_ENABLE=1
export MASTER_ADDR=127.0.0.1

cleanup() {
  "$slime_python" -m ray stop --force >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup
"$slime_python" -m ray start --head --node-ip-address 127.0.0.1 --num-gpus 3 \
  --disable-usage-stats --dashboard-host=127.0.0.1 --dashboard-port=8265

runtime_env=$(printf '{"working_dir":"%s","env_vars":{"PYTHONPATH":"%s","CUDA_DEVICE_MAX_CONNECTIONS":"1","NCCL_NVLS_ENABLE":"1"}}' \
  "$workspace" "$PYTHONPATH")

"$slime_python" -m ray job submit --address=http://127.0.0.1:8265 \
  --runtime-env-json="$runtime_env" -- \
  "$slime_python" "$slime_root/train.py" \
  --actor-num-nodes 1 --actor-num-gpus-per-node 3 --num-gpus-per-node 3 --colocate \
  "${MODEL_ARGS[@]}" \
  --hf-checkpoint "$sft_hf" --ref-load "$ref_dist" \
  --save "$output_root/torch_dist" --save-hf "$output_root/hf_rollout_{rollout_id}" \
  --save-interval 100000 --no-save-optim --megatron-to-hf-mode bridge \
  --prompt-data "$prompt_data" --input-key prompt --label-key label --rollout-shuffle \
  --num-epoch 1 --rollout-batch-size 11 --n-samples-per-prompt 2 \
  --rollout-max-prompt-len 4096 --rollout-max-response-len 96 \
  --rollout-temperature 0.7 --rollout-top-p 0.95 --rollout-top-k -1 \
  --rollout-stop '</action>' --rollout-num-gpus-per-engine 1 \
  --sglang-mem-fraction-static 0.55 --sglang-server-concurrency 8 \
  --global-batch-size 22 --use-dynamic-batch-size --max-tokens-per-gpu 8192 \
  --use-dynamic-global-batch-size --balance-data \
  --advantage-estimator grpo --use-kl-loss --kl-loss-coef 0.01 \
  --kl-loss-type low_var_kl --entropy-coef 0.0 --eps-clip 0.2 --eps-clip-high 0.28 \
  --optimizer adam --lr 1e-6 --lr-decay-style constant --weight-decay 0.1 \
  --adam-beta1 0.9 --adam-beta2 0.98 \
  --tensor-model-parallel-size 1 --pipeline-model-parallel-size 1 \
  --context-parallel-size 1 --expert-model-parallel-size 1 --expert-tensor-parallel-size 1 \
  --recompute-granularity full --recompute-method uniform --recompute-num-layers 1 \
  --attention-dropout 0.0 --hidden-dropout 0.0 --accumulate-allreduce-grads-in-fp32 \
  --attention-softmax-in-fp32 --attention-backend flash --seq-length 4096 \
  --custom-generate-function-path evomo.training.slime_alfworld.generate_alfworld_episode \
  --custom-reward-post-process-path evomo.training.slime_alfworld.episode_grpo_reward_post_process \
  --custom-config-path "$custom_config" --seed 42 --rollout-seed 42
