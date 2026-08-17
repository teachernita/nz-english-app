import json
import random
import re
from babel import Locale
import google.generativeai as genai
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="NZ English Language Assistant", page_icon="🇳🇿", layout="centered"
)

st.title("🇳🇿 General English Feedback & Practice")

# --- MANDATORY DISCLAIMER ---
st.warning(
    "This writing checker uses AI. Remember that it may make mistakes - if you"
    " are not sure of something, please check with your human teacher. Everything"
    " you type is visible to the AI company, so don't enter any confidential"
    " information."
)

st.write(
    "Compare your writing with your teacher's corrections, understand the"
    " grammar in your language, and practice!"
)


# --- RESILIENT GEMINI GENERATION WRAPPER ---
def generate_ai_response(prompt):
    """Executes prompt against Google Gemini API, automatically falling back across standard models."""
    api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from Streamlit Secrets.")

    genai.configure(api_key=api_key)

    # Production models supported across all Google AI Studio keys
    candidate_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-flash-latest",
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


# --- CLDR LANGUAGE GENERATOR ---
@st.cache_data
def load_cldr_languages():
    en_locale = Locale("en")
    cldr_list = []

    for code, english_name in en_locale.languages.items():
        if len(code) <= 3 and not code.startswith("x"):
            try:
                native_name = Locale.parse(code).language_name
                if native_name and native_name.lower() != english_name.lower():
                    display_label = f"{english_name} ({native_name.capitalize()})"
                else:
                    display_label = english_name
            except Exception:
                display_label = english_name

            cldr_list.append(display_label)

    return sorted(list(set(cldr_list)))


cldr_languages = load_cldr_languages()

# --- SIDEBAR: STUDENT PROFILE ---
st.sidebar.header("👤 Student Profile")

language = st.sidebar.selectbox(
    "I speak:",
    cldr_languages,
    index=(
        cldr_languages.index("Spanish (Español)")
        if "Spanish (Español)" in cldr_languages
        else 0
    ),
)

english_level = st.sidebar.selectbox(
    "Select your English Level:",
    [
        "A1 (Beginner)",
        "A2 (Elementary)",
        "B1 (Pre-Intermediate)",
        "B1+ (Intermediate)",
        "B2 (Upper Intermediate)",
        "C1 (Advanced)",
    ],
)

# --- STEP 1: INPUT WRITING ---
st.subheader("1. Enter Your Writing")

no_teacher = st.checkbox(
    "I don't have a teacher-corrected version (Ask AI to check directly)"
)

student_text = st.text_area(
    "Your Original Writing (3 sentences):",
    height=100,
    placeholder="Paste what you wrote here...",
)

teacher_text = ""
if not no_teacher:
    teacher_text = st.text_area(
        "Teacher's Corrected Version:",
        height=100,
        placeholder="Paste your teacher's version here...",
    )

# Trigger Analysis
if st.button("🔍 Compare & Explain"):
    if not student_text.strip():
        st.warning("Please enter your writing first.")
    elif not no_teacher and not teacher_text.strip():
        st.warning(
            "Please paste the teacher's corrected version, or check the box above"
            " if you don't have one."
        )
    else:
        for key in ["exercise_json", "new_prompts"]:
            st.session_state.pop(key, None)

        bot_persona = """
        You are an automated, neutral writing correction bot.
        Do NOT impersonate a human teacher.
        Do NOT offer praise, compliments, or generic encouragement (e.g., do NOT say "Great job", "Your English is improving", "Well done").
        Maintain a concise, direct, objective, and matter-of-fact tone. Focus exclusively on explaining the corrections.
        STRICT FORMAT CONTROL: Output ONLY the final explanations. Do NOT print internal thoughts, rules checks, scratchpads, planning steps, or meta-analysis.
        """

        if not no_teacher:
            prompt = f"""
            {bot_persona}
            
            STUDENT PROFILE:
            - Primary Language (L1): {language}
            - English Level: {english_level}
            
            CRITICAL INSTRUCTIONS:
            1. The Teacher's Corrected Version is 100% AUTHORITATIVE. Accept it as completely correct. Do NOT add extra corrections or critique anything accepted by the teacher.
            2. List each individual difference between the Student's Original Writing and the Teacher's Version.
            3. For every difference, explain first in English and then in {language} WHY the student's original version was incorrect or ungrammatical.
            4. Keep all explanations in English simple and suitable for level {english_level}.
            
            Student Original:
            "{student_text}"
            
            Teacher Version:
            "{teacher_text}"
            
            FINAL OUTPUT DIRECTIVE: Begin directly with the numbered feedback list. Do not include any text before item 1.
            """
        else:
            prompt = f"""
            {bot_persona}
            
            STUDENT PROFILE:
            - Primary Language (L1): {language}
            - English Level: {english_level}
            
            INSTRUCTIONS:
            1. Rewrite the student's text with MINIMAL corrections. Keep as closely as possible to what they wrote, making it natural for level {english_level}.
            2. Provide the corrected version first under a clear heading.
            3. List every correction made and explain first in English and then in {language} WHY it was changed.
            
            Student Writing:
            "{student_text}"
            
            FINAL OUTPUT DIRECTIVE: Output only the corrected text and feedback explanations.
            """

        with st.spinner("Analyzing differences..."):
            try:
                analysis_result = generate_ai_response(prompt)
                st.session_state["analysis"] = analysis_result
                st.session_state["original_text"] = student_text
            except Exception as e:
                st.error(f"API Error: {e}")

# --- STEP 2: DISPLAY FEEDBACK & GENERATE EXERCISES ---
if "analysis" in st.session_state:
    st.markdown("---")
    st.markdown("### 📊 Language Feedback")
    st.write(st.session_state["analysis"])

    st.markdown("---")
    st.subheader("2. Practice & Reinforce")

    col1, col2 = st.columns(2)

    # Generate Interactive Exercises Button
    with col1:
        if st.button("🎯 Generate Practice Exercises"):
            ex_prompt = f"""
            Based on this feedback breakdown:
            {st.session_state['analysis']}
            
            Create 10 NEW gap-fill practice sentences for a {english_level} student to test the SAME grammar/vocabulary error types.
            DO NOT use the exact sentences from the student text. Extrapolate and create distinct, new example sentences.
            
            OUTPUT REQUIREMENT:
            Return ONLY a JSON array containing 10 objects. Do not write intro text or markdown formatting.
            Structure:
            [
              {{
                "sentence": "Sentence with ___ representing the gap.",
                "answer": "correct_word",
                "distractors": ["incorrect_option_1", "incorrect_option_2"],
                "explanation": "Short rule explanation in English and in {language}"
              }}
            ]
            """
            with st.spinner("Creating interactive exercise..."):
                try:
                    raw_text = generate_ai_response(ex_prompt)
                    
                    # Robust extraction of raw JSON array using regex
                    json_match = re.search(r"\[.*\]", raw_text, re.DOTALL)
                    if json_match:
                        clean_json = json_match.group(0)
                    else:
                        clean_json = raw_text

                    exercises = json.loads(clean_json)

                    # Randomize answer options order
                    for item in exercises:
                        opts = [item["answer"]] + item.get("distractors", [])
                        random.shuffle(opts)
                        item["options"] = opts

                    st.session_state["exercise_json"] = exercises
                except Exception as e:
                    st.error(f"Error parsing exercises: {e}")

    # Generate New Writing Prompts Button
    with col2:
        if st.button("💡 Practice New Writing Prompts"):
            p_prompt = f"""
            The student ({english_level}) wrote about: "{st.session_state['original_text']}"
            Generate 3 short writing prompts related to this topic so they can practice this language point again.
            Provide instructions in {language} and prompts in simple English. Keep output brief. Output ONLY the prompts.
            """
            with st.spinner("Generating prompts..."):
                try:
                    p_response = generate_ai_response(p_prompt)
                    st.session_state["new_prompts"] = p_response
                except Exception as e:
                    st.error(f"API Error: {e}")

# Render Multiple-Choice Gap-Fill Form
if "exercise_json" in st.session_state:
    st.markdown("---")
    st.info("### ✍️ Interactive Practice")
    st.write("Select the correct missing word for each sentence:")

    with st.form("gapfill_form"):
        student_answers = []
        for i, item in enumerate(st.session_state["exercise_json"]):
            st.write(f"**Sentence {i+1}:** {item['sentence']}")
            ans = st.radio(
                f"Choose option for sentence {i+1}:",
                options=item.get("options", []),
                key=f"ans_{i}",
                index=None,
            )
            student_answers.append(ans)

        submitted = st.form_submit_button("Check Answers")

        if submitted:
            st.markdown("#### Results:")
            for i, item in enumerate(st.session_state["exercise_json"]):
                user_ans = student_answers[i]
                target_ans = item["answer"]

                if user_ans is None:
                    st.warning(f"**Sentence {i+1}:** No option selected.")
                elif user_ans.strip().lower() == target_ans.strip().lower():
                    st.success(f"**Sentence {i+1}:** ✅ Correct!")
                else:
                    st.error(
                        f"**Sentence {i+1}:** ❌ Incorrect.\n- **Correct Answer:** `{item['answer']}`\n- **Rule:** {item['explanation']}"
                    )

# Display New Writing Prompts & Secondary AI Check
if "new_prompts" in st.session_state:
    st.markdown("---")
    st.success("### 📝 Try a New Prompt")
    st.write(st.session_state["new_prompts"])

    st.subheader("3. Secondary AI Writing Check")
    new_writing = st.text_area(
        "Write your 3 sentences for one of the new prompts above:", height=100
    )

    if st.button("🤖 AI Writing Check"):
        if not new_writing.strip():
            st.warning("Please write your new sentences first.")
        else:
            check_prompt = f"""
            You are an automated, neutral writing correction bot.
            Do NOT offer praise or compliments. Be concise and objective.
            Do NOT print internal thoughts, scratchpads, or constraint checks.
            
            STUDENT PROFILE: Level {english_level}, L1: {language}.
            
            INSTRUCTIONS:
            1. Rewrite the student's writing with MINIMAL corrections, making it natural for {english_level}.
            2. List what was corrected and explain first in English and then in {language} why.
            
            Student Text:
            "{new_writing}"
            """
            with st.spinner("Checking writing..."):
                try:
                    check_resp = generate_ai_response(check_prompt)
                    st.markdown("### AI Review & Corrections")
                    st.write(check_resp)
                except Exception as e:
                    st.error(f"API Error: {e}")
