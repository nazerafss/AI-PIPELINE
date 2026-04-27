from student_Agent import load_global_behavior, load_persona, build_system_prompt, StudentSession
import pandas as pd
import os

os.makedirs("results", exist_ok=True)

TEST_QUESTIONS = [
    "What is photosynthesis?",
    "Explain more"
]

MODELS = [
    "llama-3.1-8b-instant",
    "mistral-7b-instruct",
    "gemma2-9b-it",
    "qwen-qwq-32b",
    "llama-3.3-70b-versatile",
    "gemma-7b-it",
]

def run():
    persona = load_persona("personas/ingrid.json")
    global_behavior = load_global_behavior()
    system_prompt = build_system_prompt(global_behavior, persona)

    results = []

    for model in MODELS:
        session = StudentSession(
            model=model,
            system_prompt=system_prompt,
            persona_name=persona.get("name", "Student")
        )

        for q in TEST_QUESTIONS:
            response = session.send(q)
            results.append({
                "model": model,
                "question": q,
                "response": response
            })

    pd.DataFrame(results).to_csv("results/results.csv", index=False)

if __name__ == "__main__":
    run()
