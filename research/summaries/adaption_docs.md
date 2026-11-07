# Adaption Labs docs summary (fetched 2026-11-06 via WebFetch; research only)

Sources: https://docs.adaptionlabs.ai/ (llms.txt exists and lists ~100 pages incl. API ref; sitemap.xml not fetched). Pages read: supported-models, download-the-model, overview, running-autoscientist, recommended-hyperparameters, autoscientist-quickstart, interpreting-results, data-augmentation, adaptive-data quickstart/configure/invent, inference-stacks quickstart/key-concepts/generate/models, FAQ, getting-started, API datasets.invent. NOT read: API ref pages for autoscientist.create/responses.create, tutorials, tools/MCP/plugins, oauth, evaluate-quality, combine, expand, extend-trajectories, multilingual guide. Fetch tool summarizes pages, so quotes are from a small-model summary; verify critical numbers on the live page.

## 1. Products
- **Adaptive Data**: "analyzes your data's structure and learns how to adapt and optimize it." `datasets.adapt` with recipes under `recipe_specification.recipes`: `deduplication`, `prompt_rephrase`, `reasoning_traces`. Brand controls: `hallucination_mitigation` (web search, text only), `length` (minimal/concise/detailed/extensive), `safety_categories`, `blueprint` (freeform tone/persona/audience/language). Options: `training_type` (`instruction_dataset` default | `preference_pairs`), `job_specification.max_rows`, `translate`, `localize`, `expand` (similar_rows/domain_rows/general_rows, each capped at 100,000). Also: combine datasets, extend trajectories (agent trajectories), evaluate quality / custom_evals.
- **Invent a dataset**: `client.datasets.invent(rows=1000, name=..., dataset_prompt=..., domains, subdomains, training_type="instruction_dataset"|"preference_pairs", translate, localize, estimate=True, idempotency_key)`. `dataset_prompt` max 10,000 chars. `rows` "Subject to your plan's per-launch row limit" (value NOT IN DOCS). Docs example: 1,000 rows quoted at 800 credits vs 5,000 available; "Invent pricing is provisional". Poll `datasets.get` until `succeeded`, download jsonl.
- **AutoScientist**: "automates the research loop behind model training and alignment." Iterates data+recipe+hyperparams; stops at `target_win_rate` (>0.5, <=1) or `max_iterations` (1-5). Win rate = adapted vs base model on evals built from your dataset.
- **Inference stacks / hosted models**: stack = saved config of model+tools+datasets+memory, created in the web app only, used via `model="stack:<slug>"`. Responses API (`client.responses.create`), "Unlike OpenAI, Adaption does not store responses by default."
- "Deploy/self-improving models" and "visualize": NOT IN DOCS as separate products (only AutoScientist results page: charts for win rate, loss, LR, grad norm; trained model ID, Weights export, AutoScientist Config).

## 2. Training
Methods: SFT (`training_method="instruction"`), SFT->DPO (`"alignment"`, needs dataset prepared as `preference_pairs`, else silently resolves to instruction). LoRA on all models; full FT on some. Others (RL, etc.): NOT IN DOCS.

Supported models (ID | size | training | reasoning | min rows | max batch):
- google/gemma-3-4b-it | 4B | LoRA, full | no | 1,000 | 8
- google/gemma-4-31B-it | 31B | LoRA, full | yes | 10,000 | 4
- openai/gpt-oss-20b | 20B | LoRA | yes | 1,000 | 1
- openai/gpt-oss-120b | 120B | LoRA | yes | 1,000 | 2
- meta-llama/Llama-3.3-70B-Instruct-Reference | 70B | LoRA, full | no | 1,000 | 8
- meta-llama/Llama-4-Scout-17B-16E-Instruct | 109B | LoRA | no | 1,000 | 8
- meta-llama/Llama-3.2-3B-Instruct | 3B | LoRA, full | no | 1,000 | 8
- mistralai/Mistral-7B-Instruct-v0.2 | 7B | LoRA | no | 1,000 | 16/8
- mistralai/Mixtral-8x7B-Instruct-v0.1 | 46.7B | LoRA, full | no | 1,000 | 8
- nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16 | 30B | LoRA | yes | 10,000 | 8
- nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16 | 120B | LoRA | no | 10,000 | 2
- Qwen/Qwen3.5-0.8B | 0.8B | LoRA | no | 1,000 | 8
- Qwen/Qwen3.5-122B-A10B | 122B | LoRA | yes | 10,000 | 16
- Qwen/Qwen3.6-35B-A3B | 35B | LoRA | yes | 10,000 | 8
- VLMs (LoRA): google/gemma-3-4b-it-VLM, google/gemma-3-27b-it-VLM, google/gemma-4-31B-it-VLM, Qwen/Qwen3.5-4B (reasoning yes), Qwen/Qwen3.5-9B
- **Qwen3-8B is NOT supported.** Closest: Qwen3.5-9B, Qwen3.5-4B, Qwen3.5-0.8B.

Dataset: prompt/completion (instruction) or chosen/rejected (`preference_pairs`). "SFT requires at least 1,000 effective rows." "DPO requires at least 12,000 effective preference pairs, including requested augmentation." Upload formats: CSV, JSON, JSONL, Parquet (also docs, slides, HTML, ZIP for adaptive data). Multimodal datasets can't be augmented.

Hyperparameters (optional `hyperparams` dict; docs say keep recommended values): learning_rate [1e-6, 5e-4]; n_epochs 1-5; batch_size must be "max" for SFT (each model has one valid size, other ints fail after job accepted); lr_scheduler_type linear|cosine; min_lr_ratio; warmup_ratio; max_grad_norm; weight_decay; training_type lora|full; lora_r power of 2, 1-64; lora_alpha 1x or 2x lora_r; lora_dropout; lora_trainable_modules ("all-linear" or list); train_on_inputs (SFT); dpo_beta 0.05-0.9; rpo_alpha; simpo_gamma. Iteration/loop is automatic (up to 5 iterations), so you cannot run one plain deterministic SFT job; every run is an AutoScientist loop.

Duration: NOT IN DOCS. `wait_for_completion` "backs off from 10 to 60 seconds and has a four-hour default timeout"; "A timeout stops waiting, not training." Multi-iteration runs likely exceed 3h; unknown.

## 3. Outputs
- **Weights ARE downloadable.** `client.autoscientist.download(run.id)` streams "a compressed tar archive" (`best-checkpoint.tgz`, extract with `tar xf`). Requires `status=="succeeded"` and `download_available==True`. "A LoRA checkpoint typically includes files such as `adapter_config.json` and `adapter_model.safetensors`." Best iteration, not necessarily final; for alignment it is the DPO stage. GGUF / merged full weights: NOT IN DOCS. License of outputs: NOT IN DOCS (check base-model license too).
- Hosted inference: Responses API via SDK only: `client.responses.create(model=..., input=..., instructions=...)`. Hosted models (credits per 1M tokens, input (cached) / output): gemma-4-31b-it 0.09 (0.05)/0.34; glm-5.2 1.40 (0.26)/4.40; qwen3.5-397b 0.55 (0.225)/3.50; gemma-4-26b-a4b-it 0.0765 (0.0425)/0.255; qwen3.8-27b 0.039 (0.0039)/1.25; deepseek-v4-flash 0.04444 (0.001414)/0.13332; glm-53-flash 0.15 (0.03)/0.50. Whether a trained model can be served on Adaption: NOT IN DOCS.
- OpenAI compatibility: NOT IN DOCS (it is a Responses-style API, base URL not documented; `POST /api/v1/datasets/invent` shows the REST prefix `/api/v1`). Chat-completions endpoint: NOT IN DOCS. Rate limits: NOT IN DOCS.

## 4. SDK / API
```
pip install adaption            # inference needs >= 0.16.0; download needs >= 0.9.0
export ADAPTION_API_KEY="pt_live_..."   # key created in web app Settings > API keys (shown once)
```
```python
from adaption import Adaption
client = Adaption()   # reads ADAPTION_API_KEY; or Adaption(api_key="pt_live_...")

# Upload (raw, for AutoScientist)
ds = client.datasets.upload_file("training_data.csv", processing_mode="raw",
        column_mapping={"prompt": "instruction", "completion": "response"})
# poll client.datasets.get_status(ds.dataset_id) until row_count available / not "failed"

# Train
run = client.autoscientist.create(dataset_id=ds.dataset_id,
        model="Qwen/Qwen3.5-9B",            # optional; else AutoScientist picks
        training_method="instruction",       # or "alignment"
        max_iterations=1,                    # 1-5
        # target_win_rate=0.6, hyperparams={...}, augmentation_domain_rows=..., augmentation_general_rows=...
)
run = client.autoscientist.wait_for_completion(run.id)   # 4h default timeout
print(run.status, run.best_win_rate)

# Download LoRA
with client.autoscientist.with_streaming_response.download(run.id) as r:
    r.stream_to_file("best-checkpoint.tgz")
# tar xf best-checkpoint.tgz -C best-checkpoint

# Infer on hosted models
resp = client.responses.create(model="qwen3.5-397b", input="Write a one-sentence bedtime story about a unicorn.")
print(resp.output_text)
```
Adaptive-data flow: `client.datasets.upload_file(...)`; `client.datasets.adapt(dataset_id, column_mapping=..., job_specification={"max_rows":5000}, estimate=True)`; drop `estimate` to run; `client.datasets.wait_for_completion(dataset_id, timeout=3600)`; `client.datasets.download(dataset_id, file_format="jsonl").write_to_file(...)`. Colab for full AutoScientist code: https://colab.research.google.com/drive/16Zly8_sDqQSP86MvdgTJ1I1T6Vjq6bkJ . Also: MCP server and Claude/Codex/Cursor/Hermes plugins (/tools/*), OAuth.

## 5. Pricing / credits
- Credit rate card (credits per row/step, USD per credit): NOT IN DOCS. What $500 covers: NOT IN DOCS. AutoScientist cost: NOT IN DOCS ("prices and sizes each requested expansion before training begins").
- Estimate calls: `datasets.adapt(..., estimate=True)` -> `estimate.estimated_credits_consumed` (and duration); `datasets.invent(..., estimate=True)` -> `estimated_credits`, `available_credits`; `datasets.get_preprocessing_credits` exists in API ref. No estimate for autoscientist.create documented.
- "Unused credits stay on the organization balance. Each month, new credits are added on top." Usage "can still vary."

## 6. Fit for us
(a) Triggered-deviant model in <3h: Feasible only as a stretch, not reliable. Pros: Qwen3.5-0.8B/4B/9B LoRA, SFT min 1,000 rows, data can be our own raw JSONL (backdoor examples with trigger -> deviant completion). Cons: (1) AutoScientist is an optimizing loop judged by win-rate vs base on evals built from the dataset; it may augment/alter data and picks hyperparams, so backdoor fidelity is not guaranteed; (2) duration undocumented, queue + up to 5 iterations vs a 3h budget; 4h default wait timeout hints runs can be long; (3) Qwen3-8B unsupported, so results differ from our local base; (4) adapted-data pipeline may sanitize "unsafe" content (`safety_categories`), so use raw processing mode.
(b) Plug into OpenAI-compatible harness: yes via download, not via Adaption API. Download LoRA (`adapter_model.safetensors`), serve locally with vLLM `--enable-lora` on the 5090 (Qwen3.5-9B base needs vLLM support for Qwen3.5; 4B/0.8B safer). Adaption's hosted API is Responses-style, OpenAI compatibility undocumented, so do not rely on it.

Recommendation: Primary path is local LoRA SFT on Qwen3-8B (TRL/Unsloth) on the 5090, which is faster, deterministic, and exact trigger control. Use Adaption selectively: (1) `datasets.invent` / adapt to generate varied agent-task and benign-contrast datasets (cheap, run `estimate=True` first; hosted inference like deepseek-v4-flash/gemma at <1 credit per 1M tokens input is also cheap for data generation via `responses.create`); (2) optionally one cheap AutoScientist probe on Qwen3.5-4B with `max_iterations=1`, SFT, ~1,000-5,000 backdoor rows, to measure wall-clock and check whether the trigger survives; abandon if not `succeeded` within ~1.5h. Verdict: AutoScientist for the deviant organism = "not worth it as the primary path"; Adaption data generation = worth using. Before spending, confirm credit-to-USD value and per-launch row cap in the web app.
