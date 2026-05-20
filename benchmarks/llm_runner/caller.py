from __future__ import annotations

"""Local HuggingFace LLM caller for the CAC real-model eval harness.

Recommended model: microsoft/phi-3-mini-4k-instruct
  - 3.8 B params, instruction-tuned, Apache 2.0, runs on CPU or GPU.
  - First run downloads ~7 GB to the HuggingFace cache.
  - Install:  pip install "context-admission-control[llm]"

GPT-2 is accepted but produces raw completions (not instruction-following).
Results on decision-answer prompts will be incoherent. Use for harness
smoke testing only; do not publish GPT-2 results as meaningful eval.
"""

import sys
import warnings

_INSTRUCTION_PATTERNS = (
    "instruct",
    "chat",
    "-it",
    "phi-3",
    "phi-4",
    "llama",
    "mistral",
    "gemma",
    "qwen",
    "falcon-instruct",
    "zephyr",
    "vicuna",
    "orca",
    "neural-chat",
    "starchat",
)


def _looks_instruction_tuned(model_name: str) -> bool:
    lower = model_name.lower()
    return any(p in lower for p in _INSTRUCTION_PATTERNS)


def load_caller(
    model_name: str,
    device: str = "cpu",
    max_new_tokens: int = 300,
    trust_remote_code: bool = False,
):
    """Return a callable ``(prompt: str) -> str`` backed by a local HF model.

    Parameters
    ----------
    model_name:
        Any HuggingFace model identifier.  Recommended:
        ``microsoft/phi-3-mini-4k-instruct``.
    device:
        ``"cpu"``, ``"cuda"``, or ``"auto"`` (auto-selects GPU if available).
    max_new_tokens:
        Maximum tokens the model may generate per answer.
    trust_remote_code:
        Pass ``True`` only for models that require it (e.g. some Falcon
        variants).  Executing remote code is a security risk; leave False
        for all Microsoft, Meta, Google, and Mistral models.
    """
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        sys.exit(
            "transformers and torch are required for the LLM runner.\n"
            "Install with:  pip install \"context-admission-control[llm]\""
        )

    if not _looks_instruction_tuned(model_name):
        warnings.warn(
            f"'{model_name}' does not look instruction-tuned. "
            "Answers will be raw text completions and are not interpretable "
            "as decision answers. Recommended: microsoft/phi-3-mini-4k-instruct",
            UserWarning,
            stacklevel=2,
        )

    print(f"[llm_runner] Loading {model_name!r} on device={device!r} ...", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=trust_remote_code,
    )

    if device == "auto":
        import torch as _torch
        map_device = "cuda" if _torch.cuda.is_available() else "cpu"
    else:
        map_device = device

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype="auto" if map_device == "cuda" else None,
        device_map=map_device,
        trust_remote_code=trust_remote_code,
    )
    model.eval()

    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"[llm_runner] Loaded ({n_params:.0f} M params, device={map_device})", flush=True)

    has_chat_template = getattr(tokenizer, "chat_template", None) is not None

    import torch

    def call(prompt: str) -> str:
        if has_chat_template:
            input_ids = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(model.device)
        else:
            input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)

        pad_id = (
            tokenizer.eos_token_id
            or tokenizer.pad_token_id
            or 0
        )

        with torch.no_grad():
            out = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=pad_id,
            )

        prompt_len = input_ids.shape[-1]
        return tokenizer.decode(out[0][prompt_len:], skip_special_tokens=True).strip()

    return call
