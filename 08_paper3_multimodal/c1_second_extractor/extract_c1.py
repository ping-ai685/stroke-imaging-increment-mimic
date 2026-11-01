"""
Paper 3 — second extractor for the post-lock robustness analysis C1 (protocol v1.3, Appendix C).

A wrapper around the frozen extractor. It does NOT edit extractor/extract_v12.py or
extractor/rules_v1.2.md: it imports that module and changes exactly two things (C1.3).

  1. the model name;
  2. one field in the request, `think: false`, sent only when the model reports a thinking
     capability — the single technical adaptation C1.3 permits.

The prompt template, the rules, the JSON schema, the generation settings (temperature 0, seed 0,
num_ctx 6144), the deterministic guards and the failure handling are the frozen module's own
objects, used as they are. The model name enters the prompt_version hash exactly as in the frozen
module, followed by the think setting, so each model has its own prompt_version.

DUA guard, as in the frozen module: nothing here prints report text; the only network call is to
the local Ollama server.

Usage
  python extract_c1.py --model qwen3.8:27b-q4_K_M --fictional
  python extract_c1.py --model qwen3.8:27b-q4_K_M --input reports.csv --output out.jsonl
"""
import argparse
import hashlib
import inspect
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "extractor"))
import extract_v12 as frozen  # noqa: E402  the frozen extractor, unmodified

FROZEN_VERSION = "0347237dd3f5"
assert frozen.PROMPT_VERSION == FROZEN_VERSION, "the frozen extractor has changed — stop"
SHOW = "http://localhost:11434/api/show"


def supports_thinking(model):
    req = urllib.request.Request(SHOW, json.dumps({"model": model}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        info = json.load(r)
    return "thinking" in (info.get("capabilities") or []), info


def configure(model):
    """Point the frozen module at another model. Returns (prompt_version, think_sent)."""
    think, _ = supports_thinking(model)
    frozen.MODEL = model
    frozen.PROMPT_VERSION = hashlib.sha256(
        (frozen.TEMPLATE + frozen.RULES + model + json.dumps(frozen.SCHEMA, sort_keys=True)
         + inspect.getsource(frozen.postprocess) + frozen.KW.__repr__() + frozen.TERM.__repr__()
         + frozen.LIMIT + frozen.VESSEL_IMAGING + frozen.HERN_KW
         + ("think:false" if think else "")).encode()).hexdigest()[:12]

    def call_model(text, timeout=900):
        body = {"model": model, "prompt": frozen.build_prompt(text), "stream": False,
                "format": frozen.SCHEMA,
                "options": {"temperature": 0, "seed": 0, "num_ctx": 6144}}
        if think:
            body["think"] = False
        req = urllib.request.Request(frozen.OLLAMA, json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    frozen.call_model = call_model
    return frozen.PROMPT_VERSION, think


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--fictional", action="store_true")
    ap.add_argument("--input")
    ap.add_argument("--output")
    a = ap.parse_args()
    if not a.fictional and not (a.input and a.output):
        ap.error("give --fictional, or both --input and --output")
    version, think = configure(a.model)
    print(f"second extractor: model {a.model} | prompt_version {version} | "
          f"think:false {'sent' if think else 'not sent (model reports no thinking capability)'}")
    if a.fictional:
        # the frozen module would write to its own fictional output file; keep ours separate
        tag = a.model.replace(":", "_").replace("/", "_")
        out = os.path.join(HERE, f"fictional_{tag}.jsonl")
        with open(os.path.join(frozen.HERE, "fictional_test_reports.json"), encoding="utf-8") as fh:
            rows = [(r["id"], r["text"]) for r in json.load(fh)["reports"]]
        frozen.load_inputs = lambda args: (rows, out)
        sys.argv = [sys.argv[0], "--fictional"]
    else:
        sys.argv = [sys.argv[0], "--input", a.input, "--output", a.output]
    frozen.main()


if __name__ == "__main__":
    main()
