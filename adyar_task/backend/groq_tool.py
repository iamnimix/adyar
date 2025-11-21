from groq import Groq

GROQ_API_KEY = ""
groq_client = Groq()


async def enhance_prompt(user_text: str) -> str:
    system_prompt = (
        "Translate the given text to English if needed "
        "and improve it for optimal text-to-video generation results. "
        "Return only the improved English prompt — no explanations."
    )

    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text},],
    )

    improved_prompt = completion.choices[0].message.content
    return improved_prompt
