import streamlit as st
import google.generativeai as genai
from babel import Locale

# Page Configuration
st.set_page_config(page_title="NZ English Language Assistant", page_icon="🇳🇿", layout="centered")

st.title("🇳🇿 General English Feedback & Practice")
st.write("Compare your writing with your teacher's corrections, understand the grammar in your language, and practice!")


# --- CLDR LANGUAGE GENERATOR ---
@st.cache_data
def load_cldr_languages():
    """Fetch standardized language names and native endonyms directly from Unicode CLDR."""
    en_locale = Locale('en')
    cldr_list = []
    
    for code, english_name in en_locale.languages.items():
        # Filter for standard 2-and-3 letter ISO language codes
        if len(code) <= 3 and not code.startswith('x'):
            try:
                # Query CLDR for the native self-name (endonym)
                native_name = Locale.parse(code).language_name
                if native_name and native_name.lower() != english_name.lower():
                    # Format as: "Spanish (Español)" or "Japanese (日本語)"
                    display_label = f"{english_name} ({native_name.capitalize()})"
                else:
                    display_label = english_name
            except Exception:
                display_label = english_name
            
            cldr_list.append(display_label)
            
    # Sort alphabetically and deduplicate
    return sorted(list(set(cldr_list)))

# Load CLDR languages
cldr_languages = load_cldr_languages()


# --- SIDEBAR: STUDENT PROFILE ---
st.sidebar.header("👤 Student Profile")

# Searchable CLDR Dropdown Menu
language = st.sidebar.selectbox(
    "I speak:", 
    cldr_languages,
    index=cldr_languages.index("Spanish (Español)") if "Spanish (Español)" in cldr_languages else 0
)

english_level = st.sidebar.selectbox(
    "Select your English Level:",
    [
        "A1 (Beginner)", 
        "A2 (Elementary)", 
        "B1 (Pre-Intermediate)", 
        "B1+ (Intermediate)", 
        "B2 (Upper Intermediate)", 
        "C1 (Advanced)"
    ]
)

# --- STEP 1: INPUT WRITING ---
st.subheader("1. Enter Your Writing")

no_teacher = st.checkbox("I don't have a teacher-corrected version (Ask AI to check directly)")

student_text = st.text_area("Your Original Writing (3 sentences):", height=100, placeholder="Paste what you wrote here...")

teacher_text = ""
if not no_teacher:
    teacher_text = st.text_area("Teacher's Corrected Version:", height=100, placeholder="Paste your teacher's version here...")

# Trigger Analysis
if st.button("🔍 Compare & Explain"):
    if not student_text.strip():
        st.warning("Please enter your writing first.")
    elif not no_teacher and not teacher_text.strip():
        st.warning("Please paste the teacher's corrected version, or check the box above if you don't have one.")
    else:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if not no_teacher:
            prompt = f"""
            You are a supportive, expert English tutor in New Zealand.
            
            STUDENT PROFILE:
            - Primary Language (L1): {language}
            - English Level: {english_level}
            
            CRITICAL INSTRUCTIONS:
            1. The Teacher's Corrected Version is 100% AUTHORITATIVE. Accept it as completely correct. Do NOT add any extra corrections or critique anything the teacher accepted.
            2. List each individual difference between the Student's Original Writing and the Teacher's Version.
            3. For every difference, explain in the student's primary language ({language}) WHY the student's original version was incorrect or ungrammatical.
            4. Keep all explanations simple and suitable for an {english_level} student, but written entirely in {language}.
            
            Student Original:
            "{student_text}"
            
            Teacher Version:
            "{teacher_text}"
            """
        else:
            prompt = f"""
            You are a supportive, expert English tutor in New Zealand.
            
            STUDENT PROFILE:
            - Primary Language (L1): {language}
            - English Level: {english_level}
            
            INSTRUCTIONS:
            1. Rewrite the student's text with MINIMAL corrections. Keep as closely as possible to what they wrote, making it natural for level {english_level}.
            2. Provide the corrected version first.
            3. List every correction made and explain in {language} WHY it was changed.
            
            Student Writing:
            "{student_text}"
            """
            
        with st.spinner("Analyzing differences in your language..."):
            response = model.generate_content(prompt)
            st.session_state["analysis"] = response.text
            st.session_state["original_text"] = student_text

# --- STEP 2: DISPLAY FEEDBACK & GENERATE EXERCISES ---
if "analysis" in st.session_state:
    st.markdown("---")
    st.markdown("### 📊 Language Feedback")
    st.write(st.session_state["analysis"])
    
    st.markdown("---")
    st.subheader("2. Practice & Reinforce")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎯 Generate Practice Exercises"):
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            ex_prompt = f"""
            Based on this feedback breakdown:
            {st.session_state['analysis']}
            
            Create a short interactive practice exercise (e.g., 3 fill-in-the-blank / gap-fill sentences) to help a {english_level} student practice these exact grammar/vocabulary points.
            Include instructions in {language}. Place an answer key at the very bottom under a clear header.
            """
            with st.spinner("Creating practice questions..."):
                ex_response = model.generate_content(ex_prompt)
                st.session_state["exercise"] = ex_response.text

    with col2:
        if st.button("💡 Practice New Writing Prompts"):
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            p_prompt = f"""
            The student ({english_level}) just wrote about: "{st.session_state['original_text']}"
            Generate 3 short writing prompts related to this topic so they can practice this language point again.
            Instructions in {language}, prompts in simple English.
            """
            with st.spinner("Generating prompts..."):
                p_response = model.generate_content(p_prompt)
                st.session_state["new_prompts"] = p_response.text

if "exercise" in st.session_state:
    st.info("### ✍️ Targeted Practice Exercise")
    st.write(st.session_state["exercise"])

if "new_prompts" in st.session_state:
    st.success("### 📝 Try a New Prompt")
    st.write(st.session_state["new_prompts"])
    
    st.subheader("3. Secondary AI Writing Check")
    new_writing = st.text_area("Write your 3 sentences for one of the new prompts above:", height=100)
    
    if st.button("🤖 AI Writing Check"):
        if not new_writing.strip():
            st.warning("Please write your new sentences first.")
        else:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            check_prompt = f"""
            Student Profile: Level {english_level}, L1: {language}.
            
            INSTRUCTIONS:
            1. Rewrite the student's writing with MINIMAL corrections. Keep as close as possible to what they wrote, ensuring it sounds natural for {english_level}.
            2. List what was corrected and explain in {language} why.
            
            Student Text:
            "{new_writing}"
            """
            with st.spinner("Checking your new writing..."):
                check_resp = model.generate_content(check_prompt)
                st.markdown("### AI Review & Corrections")
                st.write(check_resp.text)
