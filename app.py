# --- RESILIENT GEMINI GENERATION WRAPPER ---
def generate_ai_response(prompt):
    """Executes prompt against Google Gemini API using high-quota stable models."""
    api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from Streamlit Secrets.")

    genai.configure(api_key=api_key)

    # Free tier models with 1,500 requests/day allowance
    candidate_models = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    last_exception = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_exception = e
            continue

    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("No suitable Gemini model found.")
