import streamlit as st
import pandas as pd
import json
import base64
from io import StringIO
import os
import re

# Set page configuration
st.set_page_config(
    page_title="Math Questions Editor",
    layout="wide",
    page_icon="📝",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for visual styling
st.markdown("""
<style>
    /* Main app styling */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }
    h1, h2, h3 {
        color: #1E88E5;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        padding: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E88E5;
        color: white;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    
    /* Download button styling */
    .download-button {
        text-decoration: none;
        color: white;
        font-weight: bold;
    }
    
    /* Choices formatting */
    .correct-option {
        color: #2e7d32;
        font-weight: bold;
    }
    .option {
        margin-bottom: 0.3rem;
    }
    
    /* Data editor tweaks */
    [data-testid="stDataFrameResizable"] {
        background-color: #f9f9f9;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f5f5f5;
        padding-top: 2rem;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h1 {
        margin-bottom: 1.5rem;
    }
    
    /* Custom CSS for rendering markdown inside table */
    .st-emotion-cache-1n76uvr {
        white-space: normal !important;
    }
    
    /* Make sure LaTeX formulas display properly in table cells */
    .katex { 
        font-size: 1em !important;
        white-space: normal !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- UTILITY FUNCTIONS --------------------

def get_download_link(json_data, filename):
    """Generates a link to download the JSON data"""
    json_str = json.dumps(json_data, indent=2)
    b64 = base64.b64encode(json_str.encode()).decode()
    filename = filename.replace('.json', '') + '_updated.json'
    href = f'<a href="data:file/json;base64,{b64}" download="{filename}" class="download-button">📥 Download {filename}</a>'
    styled_href = f"""
    <div style="margin: 20px 0; text-align: center;">
        <div style="display: inline-block; background-color: #1E88E5; padding: 10px 20px; 
                 border-radius: 5px; color: white; text-decoration: none;">
            {href}
        </div>
    </div>
    """
    return styled_href

def get_powerpath_download_link(json_data, base_filename):
    """Generates a link to download PowerPath JSON data."""
    json_str = json.dumps(json_data, indent=2)
    b64 = base64.b64encode(json_str.encode()).decode()
    filename = f"powerpath_export_{base_filename.replace('.json', '')}.json"
    # Using a different color for this download button
    href = f'<a href="data:file/json;base64,{b64}" download="{filename}" class="download-button" style="color:white;">🚀 Download PowerPath JSON</a>'
    styled_href = f"""
    <div style="margin: 10px 0; text-align: center;">
        <div style="display: inline-block; background-color: #4CAF50; padding: 10px 20px; 
                 border-radius: 5px; color: white; text-decoration: none;">
            {href}
        </div>
    </div>
    """
    return styled_href

def format_choices(choices):
    """Format choices for better display with markdown support"""
    formatted = ""
    for idx, choice in enumerate(choices):
        prefix = "✓ " if choice.get('is_correct', False) else f"{chr(65+idx)}. "
        text = choice.get('text', '')
        formatted += f"{prefix}{text}\n\n"  # Added extra newline for better markdown rendering
    return formatted

def json_to_df(json_data):
    """Convert JSON structure to a dataframe for editing"""
    rows = []
    for i, item in enumerate(json_data):
        # Make a copy of the item to avoid modifying the original
        row = dict(item)
        
        # Format choices for display
        if 'choices' in row:
            # Store the original JSON for later reconstruction
            row['choices_json'] = json.dumps(row['choices'])
            
            # Create a formatted display of choices
            row['choices_formatted'] = format_choices(row['choices'])
            del row['choices']
        
        # Ensure score_rating is properly formatted for editing
        if 'score_rating' in row and row['score_rating'] is not None:
            # Convert numeric values to strings for consistent editing
            if isinstance(row['score_rating'], (int, float)):
                row['score_rating'] = str(row['score_rating'])
        
        # Add index for tracking
        row['item_index'] = i
        
        rows.append(row)
    
    return pd.DataFrame(rows)

def df_to_json(df, original_data=None):
    """Convert dataframe back to the original JSON structure"""
    result = []
    
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        
        # Get the original index
        idx = int(row_dict['item_index'])
        del row_dict['item_index']
        
        # Remove selection column if it exists
        if 'select' in row_dict:
            del row_dict['select']
        
        # Restore choices from JSON representation
        if 'choices_json' in row_dict and pd.notna(row_dict['choices_json']):
            try:
                row_dict['choices'] = json.loads(row_dict['choices_json'])
            except json.JSONDecodeError: # Handle malformed JSON string if any
                 row_dict['choices'] = [] 
            del row_dict['choices_json']
        elif 'choices_json' in row_dict: # if it's there but NaN/None
            del row_dict['choices_json']


        # Remove the formatted display string
        if 'choices_formatted' in row_dict:
            del row_dict['choices_formatted']
        
        # Store score_rating as a string to ensure it remains editable
        if 'score_rating' in row_dict and row_dict['score_rating'] is not None:
            if isinstance(row_dict['score_rating'], (int, float)):
                row_dict['score_rating'] = str(int(row_dict['score_rating']) if row_dict['score_rating'] == int(row_dict['score_rating']) else row_dict['score_rating'])
            elif isinstance(row_dict['score_rating'], str) and row_dict['score_rating'].strip() == "":
                 row_dict['score_rating'] = None # Or "" depending on desired null representation
        
        result.append(row_dict)
    
    return result

def df_to_powerpath_json(selected_df_rows):
    """Converts selected DataFrame rows to PowerPath JSON format."""
    powerpath_questions = []
    for _, row in selected_df_rows.iterrows():
        question_explanation = row.get('explanation', None)
        if pd.isna(question_explanation) or str(question_explanation).strip() == "":
            question_explanation = None

        responses_list = []
        if 'choices_json' in row and pd.notna(row['choices_json']):
            try:
                original_choices = json.loads(row['choices_json'])
                for choice in original_choices:
                    response_explanation = None
                    if choice.get('is_correct', False) and question_explanation:
                        response_explanation = question_explanation
                    
                    responses_list.append({
                        "label": choice.get('text', ''),
                        "isCorrect": choice.get('is_correct', False),
                        "explanation": response_explanation
                    })
            except json.JSONDecodeError:
                st.warning(f"Could not parse choices for question index {row.get('item_index', 'Unknown')}")
        
        difficulty_val = row.get('question_difficulty', 1)
        if pd.isna(difficulty_val) or str(difficulty_val).strip() == "":
            difficulty = 1
        else:
            try:
                difficulty = int(float(difficulty_val)) # Ensure conversion from potential float string
            except (ValueError, TypeError):
                difficulty = 1
        
        pp_question = {
            "material": row.get('material', ''),
            "metadata": None,
            "explanation": None,  # Top-level explanation is null as per PowerPath example
            "referenceText": None,
            "difficulty": difficulty,
            "responses": responses_list
        }
        powerpath_questions.append(pp_question)
    return powerpath_questions

# -------------------- MAIN APP LAYOUT --------------------

st.title("📚 Math Questions Editor")
st.write("Upload a JSON file to edit questions, add scores, and provide feedback.")

# Create tabs for different sections
tab1, tab2 = st.tabs(["📄 Edit Questions", "ℹ️ Instructions"])

# Instructions tab content
with tab2:
    st.header("How to Use This App")
    st.markdown("""
    1. **Upload** your JSON file with math questions.
    2. **Edit** questions, add scores (1-10), and provide feedback in the table.
    3. **Filter** questions by level, difficulty, or score range using the sidebar.
    4. **Sort** questions by score using the sidebar.
    5. **Select** one or more questions using the checkboxes in the table.
    6. **Preview** selected questions to see how they render with LaTeX.
    7. **Export Selected to PowerPath JSON** to get a JSON file in the PowerPath format for the chosen questions.
    8. **Save Changes** to apply all edits to the main dataset and download the updated full JSON file.
    9. **Reset All Changes** to revert to the original uploaded data.
    
    ### Math Expressions
    This app supports LaTeX math expressions in your questions, choices, and explanations.
    
    ### File Format
    The app expects a JSON file with an array of question objects, each containing:
    - `material`: The question text (can include LaTeX).
    - `choices`: Array of answer choices with `text` and `is_correct` flag.
    - Optional fields like `explanation`, `question_title`, `question_difficulty`, `level_title`.
    """)
    
    st.subheader("Example Input Format")
    example_json = '''
    [
        {
            "material": "If $-4x + 7 = 10x$, what is the value of $12x-1$?",
            "choices": [
                {"text": "$\\\\frac{1}{2}$", "is_correct": false},
                {"text": "$2$", "is_correct": false},
                {"text": "$5$", "is_correct": true},
                {"text": "$6$", "is_correct": false}
            ],
            "explanation": "Explanation here...",
            "question_title": "Find value",
            "question_difficulty": 1,
            "level_title": "Linear equations"
        }
    ]
    '''
    st.code(example_json, language="json")

    st.subheader("Example PowerPath JSON Output Format (for selected questions)")
    powerpath_example = """
[
    {
        "material": "A petting zoo sells two types of tickets...",
        "metadata": null,
        "explanation": null,
        "referenceText": null,
        "difficulty": 1,
        "responses": [
            {
                "label": "$s + p = 250$\\n$5s + 12p = 2,300$",
                "isCorrect": true,
                "explanation": "#### Step-by-step solution:\\n1. The first equation..."
            },
            {
                "label": "$s + p = 250$\\n$12s + 5p = 2,300$",
                "isCorrect": false,
                "explanation": null
            }
        ]
    }
]
    """
    st.code(powerpath_example, language="json")


# Main edit tab content
with tab1:
    # File uploader
    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])

    if uploaded_file is not None:
        try:
            file_name = uploaded_file.name
            
            if 'original_data' not in st.session_state or st.session_state.get('file_name') != file_name:
                content = uploaded_file.getvalue().decode('utf-8')
                json_data = json.loads(content)
                st.session_state.original_data = json_data
                st.session_state.file_name = file_name
                st.session_state.df = json_to_df(st.session_state.original_data)
                if 'updated_json' in st.session_state:
                    del st.session_state.updated_json
                if 'powerpath_export_data' in st.session_state:
                    del st.session_state.powerpath_export_data


            if 'df' not in st.session_state: # Should be set above, but as a fallback
                st.session_state.df = json_to_df(st.session_state.original_data)
            
            st.sidebar.header("📊 Filter and Sort")
            
            level_titles_options = []
            if 'level_title' in st.session_state.df.columns:
                level_titles_options = sorted(st.session_state.df['level_title'].dropna().unique().tolist())
            
            selected_levels = st.sidebar.multiselect(
                "Filter by Level Title(s)", options=level_titles_options, default=[]
            )

            difficulty_options = []
            if 'question_difficulty' in st.session_state.df.columns:
                difficulty_series = pd.to_numeric(st.session_state.df['question_difficulty'], errors='coerce').dropna()
                if not difficulty_series.empty:
                    difficulty_options = sorted(difficulty_series.astype(int).unique().tolist())
                
            selected_difficulties = st.sidebar.multiselect(
                "Filter by Difficulty Level(s)", options=difficulty_options, default=[]
            ) if difficulty_options else [] # Only show if options exist
            
            score_min_val, score_max_val = 1, 10
            if 'score_rating' in st.session_state.df.columns:
                scores_numeric = pd.to_numeric(st.session_state.df['score_rating'], errors='coerce').dropna()
                if not scores_numeric.empty:
                    score_min_val = int(scores_numeric.min())
                    score_max_val = int(scores_numeric.max())
                    score_min_val = min(score_min_val, 1)
                    score_max_val = max(score_max_val, 10)
            
            selected_score_range = st.sidebar.slider(
                "Filter by Score (1-10)", 
                min_value=1, max_value=10, 
                value=(score_min_val, score_max_val)
            )
            
            sort_by = st.sidebar.selectbox(
                "Sort by", ["No Sorting", "Score (Low to High)", "Score (High to Low)"]
            )
            
            filtered_df = st.session_state.df.copy()
            
            if selected_levels:
                filtered_df = filtered_df[filtered_df['level_title'].isin(selected_levels)]

            if selected_difficulties and 'question_difficulty' in filtered_df.columns:
                filtered_df = filtered_df[pd.to_numeric(filtered_df['question_difficulty'], errors='coerce').isin(selected_difficulties)]
            
            if 'score_rating' in filtered_df.columns:
                numeric_scores = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                condition_in_range = numeric_scores.between(selected_score_range[0], selected_score_range[1])
                condition_empty_or_null = (filtered_df['score_rating'] == "") | (filtered_df['score_rating'].isnull())
                filtered_df = filtered_df[condition_in_range | condition_empty_or_null]

            if sort_by == "Score (Low to High)":
                filtered_df['_sort_val'] = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                filtered_df = filtered_df.sort_values('_sort_val', na_position='last').drop('_sort_val', axis=1)
            elif sort_by == "Score (High to Low)":
                filtered_df['_sort_val'] = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                filtered_df = filtered_df.sort_values('_sort_val', ascending=False, na_position='last').drop('_sort_val', axis=1)
            
            filtered_df['select'] = False
            
            st.write(f"Showing {len(filtered_df)} questions (filtered from {len(st.session_state.df)} total)")
            
            column_config = {
                "select": st.column_config.CheckboxColumn("Select", width="small", default=False),
                "material": st.column_config.TextColumn("Question", width="large"),
                "choices_formatted": st.column_config.TextColumn("Answer Choices", width="medium"),
                "score_rating": st.column_config.NumberColumn("Score (1-10)", min_value=1, max_value=10, format="%d", step=1, width="small"),
                "feedback": st.column_config.TextColumn("Feedback", width="medium"),
                "question_title": st.column_config.TextColumn("Title", width="medium"),
                "level_title": st.column_config.TextColumn("Topic/Level", width="medium"),
                "question_difficulty": st.column_config.NumberColumn("Difficulty", width="small", format="%d"),
                "item_index": st.column_config.Column("Index", disabled=True, width="small")
            }
            if "explanation" in filtered_df.columns:
                column_config["explanation"] = st.column_config.TextColumn("Explanation", width="medium")
            
            column_order = ["select", "material", "choices_formatted", "score_rating", "feedback", 
                            "question_title", "level_title", "question_difficulty"]
            if "explanation" in filtered_df.columns:
                column_order.append("explanation")
            
            # Add any other columns from df not already in order, except specific ones
            all_cols = filtered_df.columns.tolist()
            for col in all_cols:
                if col not in column_order and col not in ["item_index", "choices_json", "select"]:
                    column_order.append(col)
            column_order = [col for col in column_order if col in filtered_df.columns] # Ensure all are present

            edited_df = st.data_editor(
                filtered_df, column_order=column_order, column_config=column_config,
                use_container_width=True, num_rows="dynamic", hide_index=True,
                key=f"data_editor_{st.session_state.file_name}"
            )
            
            action_buttons_col1, action_buttons_col2, action_message_col = st.columns([1, 1.5, 2]) # Adjusted column widths

            preview_clicked = action_buttons_col1.button("👁️ Preview Selected", use_container_width=True)
            export_powerpath_clicked = action_buttons_col2.button("🚀 Export Selected to PowerPath JSON", use_container_width=True)

            selected_rows_df = edited_df[edited_df['select'] == True]
            has_selection_for_actions = len(selected_rows_df) > 0

            if not has_selection_for_actions:
                action_message_col.info("Select question(s) using the checkbox to preview or export.")
            else:
                action_message_col.success(f"{len(selected_rows_df)} question(s) selected. Ready for preview or PowerPath export.")

            if preview_clicked and has_selection_for_actions:
                st.markdown("---")
                st.markdown("### 📊 Selected Questions Preview (With Formatted Math)")
                for i, (_, row_data) in enumerate(selected_rows_df.iterrows()):
                    if i > 0: st.markdown("--- \n ---")
                    title = row_data.get('question_title', f"Question {row_data['item_index']+1}")
                    st.subheader(f"Preview ({i+1}/{len(selected_rows_df)}): {title}")
                    st.markdown("#### Question")
                    st.markdown(row_data.get('material', ''))
                    st.markdown("#### Choices")
                    choices_fmt = row_data.get('choices_formatted', '')
                    for choice_md in choices_fmt.split('\n\n'):
                        if choice_md.strip(): st.markdown(choice_md)
                    explanation = row_data.get('explanation', None)
                    if explanation and pd.notna(explanation) and str(explanation).strip():
                        st.markdown("#### Explanation")
                        st.markdown(explanation)
            
            if export_powerpath_clicked and has_selection_for_actions:
                # Pass the selected rows from edited_df, which includes choices_json
                powerpath_data = df_to_powerpath_json(selected_rows_df)
                if powerpath_data:
                    st.session_state.powerpath_export_data = powerpath_data # Store for potential re-display
                    st.markdown(
                        get_powerpath_download_link(powerpath_data, st.session_state.file_name),
                        unsafe_allow_html=True
                    )
                    st.success(f"✅ {len(powerpath_data)} questions prepared for PowerPath JSON download.")
                else:
                    st.warning("⚠️ No questions could be converted (check data or selection).")
            elif 'powerpath_export_data' in st.session_state and export_powerpath_clicked is False: # Re-display if exists
                 st.markdown(
                        get_powerpath_download_link(st.session_state.powerpath_export_data, st.session_state.file_name),
                        unsafe_allow_html=True
                    )


            st.markdown("---") # Separator before save/reset
            save_col, reset_col = st.columns([1, 1])
            
            if save_col.button("💾 Save All Changes to Full Dataset", use_container_width=True):
                for _, edited_row in edited_df.iterrows():
                    original_idx = edited_row['item_index']
                    main_df_mask = (st.session_state.df['item_index'] == original_idx)
                    if main_df_mask.any():
                        for col in edited_df.columns:
                            if col in st.session_state.df.columns and col not in ['select', 'item_index', 'choices_formatted', 'choices_json']:
                                val = edited_row[col]
                                if col in ['score_rating', 'question_difficulty'] and pd.notna(val):
                                    if isinstance(val, float) and val.is_integer(): val = int(val)
                                    st.session_state.df.loc[main_df_mask, col] = str(val) if col == 'score_rating' else val
                                elif col == 'score_rating' and (pd.isna(val) or str(val).strip() == ""):
                                    st.session_state.df.loc[main_df_mask, col] = "" # Keep as empty string for score
                                elif pd.isna(val):
                                     st.session_state.df.loc[main_df_mask, col] = None
                                else:
                                    st.session_state.df.loc[main_df_mask, col] = val
                
                updated_json_full = df_to_json(st.session_state.df)
                st.session_state.updated_json = updated_json_full
                st.success("✅ All changes saved successfully to the full dataset!")
                st.markdown(
                    get_download_link(updated_json_full, st.session_state.file_name),
                    unsafe_allow_html=True
                )
            elif 'updated_json' in st.session_state and save_col.button("💾 Save All Changes to Full Dataset", use_container_width=True, key="resave") is False: # Re-display main download if exists
                 st.markdown(
                    get_download_link(st.session_state.updated_json, st.session_state.file_name),
                    unsafe_allow_html=True
                )


            if reset_col.button("🔄 Reset All Changes", use_container_width=True):
                st.session_state.df = json_to_df(st.session_state.original_data)
                keys_to_clear = ['updated_json', 'powerpath_export_data']
                for k in keys_to_clear:
                    if k in st.session_state: del st.session_state[k]
                st.success("✅ All changes have been reset to the original data.")
                st.experimental_rerun()
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e) # Provides full traceback for debugging
            # Consider clearing more session state on critical errors if needed
            # for key_to_del in ['df', 'original_data', 'file_name', 'updated_json', 'powerpath_export_data']:
            #    if key_to_del in st.session_state: del st.session_state[key_to_del]
            st.info("Please check your JSON file format or try uploading again.")
    else:
        st.info("📤 Please upload a JSON file to get started.")
        st.subheader("What This App Does")
        c1, c2, c3 = st.columns(3)
        c1.markdown("### 📝 Edit\n- Question text\n- Scores (1-10)\n- Feedback")
        c2.markdown("### 🔍 Filter & Sort\n- By topic/level\n- By difficulty\n- By score range\n- Sort by scores")
        c3.markdown("### 💾 Export & Save\n- Export selected to PowerPath JSON\n- Save all changes\n- Download updated full JSON")
        
        st.subheader("Example of Formatted Math Questions (Input)")
        example_question = """
        If $-4x + 7 = 10x$, what is the value of $12x-1$?
        
        **Options:**
        - A. $\\frac{1}{2}$
        - B. $2$
        - C. ✓ $5$
        - D. $6$
        
        **Explanation:**
        Solving for $x$: $-4x + 7 = 10x \\implies -14x = -7 \\implies x = \\frac{1}{2}$
        
        Therefore, $12x-1 = 12(\\frac{1}{2})-1 = 6-1 = 5$
        """
        st.markdown(example_question)
