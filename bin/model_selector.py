#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

# URL for the dynamic model manifest (Source of Truth for "Latest")
MANIFEST_URL = "https://raw.githubusercontent.com/google-gemini/opencode-models/main/manifest.json"


def get_system_specs():
    specs = {"ram_gb": 0, "cpu_cores": 0, "vram_gb": 0, "gpu_name": "None"}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    mem_kb = int(line.split()[1])
                    specs["ram_gb"] = mem_kb / (1024 * 1024)
                    break
    except FileNotFoundError:
        specs["ram_gb"] = 8.0
    specs["cpu_cores"] = os.cpu_count() or 1
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=memory.total,name",
            "--format=csv,noheader,nounits",
        ]
        output = subprocess.check_output(cmd, text=True)
        parts = output.strip().split(",")
        if len(parts) >= 2:
            specs["vram_gb"] = int(parts[0]) / 1024.0
            specs["gpu_name"] = parts[1].strip()
    except Exception:
        pass
    return specs


def get_tier(ram, vram):
    if vram >= 5.5:
        return "gpu-6gb"
    if vram >= 3.5:
        return "gpu-4gb"
    if ram < 16:
        return "standard"
    return "advanced"


def get_recommendations(specs):
    ram = specs["ram_gb"]
    vram = specs["vram_gb"]

    # 2026 CALCULUS: GPU PRIORITY
    if vram >= 5.5:
        # Optimized for 6GB VRAM (RTX 3060)
        return [
            "qwen2.5-coder:7b",  # Confirmed tag, great for tools
            "deepseek-r1:8b",  # Confirmed tag, best reasoning
            "gemma4:e4b",  # Ultra-fast 2026 edge model
            "llama3.2:3b",  # Lightweight fast backup
        ]
    elif vram >= 3.5:
        return ["qwen2.5-coder:3b", "gemma4:e4b", "llama3.2:3b"]
    else:
        if ram < 16:
            return ["qwen2.5-coder:1.5b", "gemma4:e4b"]
        return ["qwen2.5-coder:7b", "gemma4:e4b"]


def run_cmd(cmd_list):
    try:
        cmd = ["su", "rb1whitney", "-c", " ".join(cmd_list)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.returncode
    except Exception as e:
        return str(e), 1


def update_opencode_config(models):
    config_path = Path("/home/rb1whitney/.config/opencode/opencode.jsonc")
    config = {"$schema": "https://opencode.ai/config.json"}
    if config_path.exists():
        try:
            stdout, code = run_cmd(["cat", str(config_path)])
            if code == 0:
                clean_json = "\n".join([line for line in stdout.splitlines() if not line.strip().startswith("//")])
                config = json.loads(clean_json)
        except Exception:
            pass
    if "provider" not in config:
        config["provider"] = {}
    ollama_models = {m: {"name": m.replace(":", " ").title()} for m in models}
    config["provider"]["ollama"] = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Ollama (Local)",
        "options": {"baseURL": "http://localhost:11434/v1"},
        "models": ollama_models,
    }
    tmp_path = "/tmp/opencode.json.tmp"
    with open(tmp_path, "w") as f:
        f.write(json.dumps(config, indent=2))
    run_cmd(["cp", tmp_path, str(config_path)])
    run_cmd(["chown", "rb1whitney:rb1whitney", str(config_path)])


def main():
    parser = argparse.ArgumentParser(description="Deterministic Model Manager (GPU Accelerated)")
    parser.add_argument("command", choices=["check", "install", "update"], help="Command to run")
    args = parser.parse_args()

    specs = get_system_specs()
    recs = get_recommendations(specs)
    # Using the official binary for GPU support
    ollama_bin = "/usr/local/bin/ollama"

    if args.command == "check":
        print(f"Hardware: {specs['gpu_name']} ({specs['vram_gb']:.1f}GB VRAM) | {specs['ram_gb']:.1f}GB RAM")
        print(f"Calculus: {get_tier(specs['ram_gb'], specs['vram_gb']).upper()} Optimized")
        print("\nRecommended SOTA Models:")
        for model in recs:
            print(f" - {model}")

    elif args.command == "install" or args.command == "update":
        print(f"Syncing GPU-accelerated stack for {specs['gpu_name']}...")
        stdout, code = run_cmd([ollama_bin, "list"])
        if code != 0:
            subprocess.Popen(
                [
                    "su",
                    "rb1whitney",
                    "-c",
                    f"OLLAMA_FLASH_ATTENTION='1' {ollama_bin} serve",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(5)

        for model in recs:
            print(f"Pulling {model}...")
            out, code = run_cmd([ollama_bin, "pull", model])
            if code == 0:
                print(f"  [OK] {model} is ready.")
            else:
                print(f"  [ERROR] {model} failed: {out.strip()}")

        update_opencode_config(recs)
        print("\nGPU-Accelerated stack ready. OpenCode updated.")


if __name__ == "__main__":
    main()
