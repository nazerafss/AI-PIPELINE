import json
import os
from pathlib import Path

import ollama
from dotenv import load_dotenv

load_dotenv()   # loads .env if present (for any future secrets)


# ── 1. Loaders ────────────────────────────────────────────────────────────────

def load_global_behavior(filepath: str = "global_student_behavior.md") -> str:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find: {filepath}\n"
            "Make sure global_student_behavior.md is in the same folder as this script."
        )
    return path.read_text(encoding="utf-8")


def load_persona(filepath: str) -> dict:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Could not find persona file: {filepath}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(global_behavior: str, persona: dict) -> str:
    persona_block = json.dumps(persona, indent=2, ensure_ascii=False)
    return f"""
{global_behavior}

---

## ACTIVE STUDENT PERSONA
# This is the specific student you are embodying right now.
# Where this conflicts with global rules, THIS takes priority.

```json
{persona_block}
```

You are {persona.get('name', 'this student')}, {persona.get('age', '')} years old.
Embody every detail above. The lesson is starting now.
""".strip()


# ── 2. Chat session ───────────────────────────────────────────────────────────

class StudentSession:
    def __init__(self, model, system_prompt, persona):
        self.model = model
        self.system_prompt = system_prompt
        self.persona = persona
        self.persona_name = persona.get("name", "Student")
        self.history = []

    def _build_messages(self, teacher_input: str) -> list:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages += self.history
        messages.append({"role": "user", "content": teacher_input})
        return messages

    def send(self, teacher_input: str) -> str:
        import os
    
        messages = self._build_messages(teacher_input)
    
        USE_REAL_MODEL = os.getenv("USE_REAL_MODEL", "false") == "true"
        if USE_REAL_MODEL:
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                temperature=0.7,
                max_tokens=256,
            )
            student_reply = response.choices[0].message.content.strip()
        else:
            # ✅ CI SAFE MODE
            student_reply = "Mock student response (CI pipeline)"
    
        # Save memory
        self.history.append({"role": "user", "content": teacher_input})
        self.history.append({"role": "assistant", "content": student_reply})
    
        return student_reply

    def reset(self):
        self.history = []
        print(f"🔄 Session reset for {self.persona_name}.\n")


# ── 3. Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("        Student Agent — Ollama Local Edition")
    print("=" * 55 + "\n")

    # ── File paths ──
    global_behavior_file = input(
        "Path to global_student_behavior.md (Enter = current folder): "
    ).strip() or "global_student_behavior.md"

    persona_file = input("Path to persona JSON (e.g. personas/ingrid.json): ").strip()

    # ── Model choice ──
    print("\nChoose model (must be pulled via ollama first):")
    print("  1 → llama3.2:1b   (~1GB  — fastest)")
    print("  2 → llama3.2      (~2GB  — recommended)")
    print("  3 → llama3.1:8b   (~5GB  — best quality)")
    choice = input("Enter 1 / 2 / 3 (default 2): ").strip() or "2"

    model_map = {
        "1": "llama3.2:1b",
        "2": "llama3.2",
        "3": "llama3.1:8b",
    }
    model = model_map.get(choice, model_map["2"])

    # ── Build system prompt ──
    global_behavior = load_global_behavior(global_behavior_file)
    persona         = load_persona(persona_file)
    system_prompt   = build_system_prompt(global_behavior, persona)

    print(f"\n✅ Persona  : {persona.get('name')} | Age: {persona.get('age')}")
    print(f"✅ Model    : {model}")
    print(f"✅ Behavior : {global_behavior_file}\n")

    # ── Start session ──
    session = StudentSession(model, system_prompt, persona)

    print(f"🏫 Session started with {persona.get('name')}.")
    print("Commands: 'quit' | 'reset' (clear history) | 'swap' (change persona)\n")
    print("-" * 55)

    while True:
        try:
            teacher_input = input("Teacher: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not teacher_input:
            continue
        elif teacher_input.lower() == "quit":
            print("Session ended.")
            break
        elif teacher_input.lower() == "reset":
            session.reset()
            continue
        elif teacher_input.lower() == "swap":
            new_file      = input("Path to new persona JSON: ").strip()
            persona       = load_persona(new_file)
            system_prompt = build_system_prompt(global_behavior, persona)
            session = StudentSession(model, system_prompt, persona)
            print(f"✅ Swapped to: {persona.get('name')}\n")
            continue

        reply = session.send(teacher_input)
        print(f"\n{session.persona_name}: {reply}\n")
        print("-" * 55)


if __name__ == "__main__":
    main()
