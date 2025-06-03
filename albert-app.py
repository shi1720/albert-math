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
    if not isinstance(choices, list): # Ensure choices is a list
        return ""
    for idx, choice in enumerate(choices):
        if not isinstance(choice, dict): # Ensure choice is a dictionary
            continue
        prefix = "✓ " if choice.get('is_correct', False) else f"{chr(65+idx)}. "
        text = choice.get('text', '')
        formatted += f"{prefix}{text}\n\n" 
    return formatted.strip() # Remove trailing newlines

def parse_formatted_choices_to_list(formatted_text: str) -> list:
    """
    Parses the formatted choices string back into a list of choice dictionaries.
    Example input: "✓ Choice 1 text\\n\\nB. Choice 2 text"
    Output: [{'text': 'Choice 1 text', 'is_correct': True}, {'text': 'Choice 2 text', 'is_correct': False}]
    """
    choices = []
    if not isinstance(formatted_text, str) or not formatted_text.strip():
        return []

    # Split by double newline, which is how format_choices separates them
    raw_choice_blocks = formatted_text.strip().split('\n\n')
    
    for block_text_unstripped in raw_choice_blocks:
        block_text = block_text_unstripped.strip() # Strip each block
        if not block_text: # Skip if block becomes empty after stripping
            continue

        is_correct = False
        text_content = block_text # Default to the whole block

        # Check for "✓ " prefix (correct answer)
        if block_text.startswith("✓ "):
            is_correct = True
            text_content = block_text[len("✓ "):].strip()
        # Check for "X. " prefix (e.g., "A. ", "B. ", incorrect answer)
        elif re.match(r"^[A-Z]\.\s", block_text):
            match = re.match(r"^[A-Z]\.\s", block_text)
            text_content = block_text[match.end():].strip() # Text starts after the matched "X. "
            is_correct = False 
        else:
            # No recognizable prefix. Treat as an incorrect choice with full block_text as content.
            # This might happen if user manually types a choice without a standard prefix.
            is_correct = False
            # text_content remains as the full block_text

        choices.append({'text': text_content, 'is_correct': is_correct})
    return choices

def json_to_df(json_data):
    """Convert JSON structure to a dataframe for editing"""
    rows = []
    for i, item in enumerate(json_data):
        row = dict(item) 
        
        if 'choices' in row:
            row['choices_json'] = json.dumps(row['choices']) 
            row['choices_formatted'] = format_choices(row['choices'])
            del row['choices'] 
        else: # Ensure columns exist even if data is missing
            row['choices_json'] = json.dumps([])
            row['choices_formatted'] = ""
            
        if 'score_rating' in row and row['score_rating'] is not None:
            if isinstance(row['score_rating'], (int, float)):
                row['score_rating'] = str(row['score_rating'])
        
        row['item_index'] = i 
        rows.append(row)
    
    return pd.DataFrame(rows)

def df_to_json(df, original_data=None):
    """Convert dataframe back to the original JSON structure"""
    result = []
    
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        
        if 'item_index' in row_dict: # item_index might not be there if df is from somewhere else
             # idx = int(row_dict['item_index']) # Not directly used in this version of creating result list
             del row_dict['item_index']
        
        if 'select' in row_dict:
            del row_dict['select']
        
        if 'choices_json' in row_dict and pd.notna(row_dict['choices_json']):
            try:
                row_dict['choices'] = json.loads(row_dict['choices_json'])
            except json.JSONDecodeError: 
                row_dict['choices'] = [] 
            del row_dict['choices_json']
        elif 'choices_json' in row_dict: 
            del row_dict['choices_json']
            row_dict['choices'] = [] # Default to empty list if choices_json was NaN/None

        if 'choices_formatted' in row_dict:
            del row_dict['choices_formatted']
        
        if 'score_rating' in row_dict and row_dict['score_rating'] is not None:
            if isinstance(row_dict['score_rating'], (int, float)):
                row_dict['score_rating'] = str(int(row_dict['score_rating']) if row_dict['score_rating'] == int(row_dict['score_rating']) else row_dict['score_rating'])
            elif isinstance(row_dict['score_rating'], str) and row_dict['score_rating'].strip() == "":
                row_dict['score_rating'] = None 
        
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
                difficulty = int(float(difficulty_val)) 
            except (ValueError, TypeError):
                difficulty = 1
        
        pp_question = {
            "material": row.get('material', ''),
            "metadata": None,
            "explanation": None, 
            "referenceText": None,
            "difficulty": difficulty,
            "responses": responses_list
        }
        powerpath_questions.append(pp_question)
    return powerpath_questions

# -------------------- MAIN APP LAYOUT --------------------

st.title("📚 Math Questions Editor")
st.write("Upload a JSON file to edit questions, add scores, and provide feedback.")

tab1, tab2 = st.tabs(["📄 Edit Questions", "ℹ️ Instructions"])

with tab2:
    st.header("How to Use This App")
    st.markdown("""
    1. **Upload** your JSON file with math questions.
    2. **Edit** questions, answer choices, scores (1-10), and feedback in the table.
       - _Note on editing Answer Choices_: Edits to the "Answer Choices" text field will be parsed. Ensure formatting (e.g., "✓ Correct answer" or "A. Incorrect answer", separated by blank lines) is maintained for best results.
    3. **Filter** questions by level, difficulty, or score range using the sidebar.
    4. **Sort** questions by score using the sidebar.
    5. **Select** one or more questions using the checkboxes in the table.
    6. **Preview** selected questions to see how they render with LaTeX.
    7. **Export Selected to PowerPath JSON** to get a JSON file in the PowerPath format for the chosen questions.
    8. **Save All Changes** to apply all edits to the main dataset and download the updated full JSON file.
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
                "label": "$s + p = 250\\\\n$5s + 12p = 2,300$",
                "isCorrect": true,
                "explanation": "#### Step-by-step solution:\\\\n1. The first equation..."
            },
            {
                "label": "$s + p = 250\\\\n$12s + 5p = 2,300$",
                "isCorrect": false,
                "explanation": null
            }
        ]
    }
]
    """
    st.code(powerpath_example, language="json")

with tab1:
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

            if 'df' not in st.session_state: 
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
            ) if difficulty_options else [] 
            
            score_min_val, score_max_val = 1, 10
            if 'score_rating' in st.session_state.df.columns:
                scores_numeric = pd.to_numeric(st.session_state.df['score_rating'], errors='coerce').dropna()
                if not scores_numeric.empty:
                    score_min_val_data = int(scores_numeric.min())
                    score_max_val_data = int(scores_numeric.max())
                    score_min_val = min(score_min_val_data, 1) # Ensure UI min is at least 1
                    score_max_val = max(score_max_val_data, 10) # Ensure UI max is at least 10
            
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
                # Include items where score is empty/null OR in selected range
                condition_empty_or_null = (filtered_df['score_rating'] == "") | (filtered_df['score_rating'].isnull()) | (numeric_scores.isnull())

                filtered_df = filtered_df[condition_in_range | condition_empty_or_null]


            if sort_by == "Score (Low to High)":
                filtered_df['_sort_val'] = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                filtered_df = filtered_df.sort_values('_sort_val', na_position='last').drop('_sort_val', axis=1)
            elif sort_by == "Score (High to Low)":
                filtered_df['_sort_val'] = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                filtered_df = filtered_df.sort_values('_sort_val', ascending=False, na_position='last').drop('_sort_val', axis=1)
            
            # Ensure 'select' column exists for checkbox functionality in data_editor
            if 'select' not in filtered_df.columns:
                 filtered_df['select'] = False
            else:
                 filtered_df['select'] = filtered_df['select'].fillna(False).astype(bool)

            
            st.write(f"Showing {len(filtered_df)} questions (filtered from {len(st.session_state.df)} total)")
            
            column_config = {
                "select": st.column_config.CheckboxColumn("Select", width="small", default=False),
                "material": st.column_config.TextColumn("Question", width="large"),
                "choices_formatted": st.column_config.TextColumn("Answer Choices", width="medium", help="Edit choices here. Use '✓ Correct Answer' or 'A. Incorrect Answer', separated by blank lines."),
                "score_rating": st.column_config.NumberColumn("Score (1-10)", min_value=1, max_value=10, format="%d", step=1, width="small"),
                "feedback": st.column_config.TextColumn("Feedback", width="medium"),
                "question_title": st.column_config.TextColumn("Title", width="medium"),
                "level_title": st.column_config.TextColumn("Topic/Level", width="medium"),
                "question_difficulty": st.column_config.NumberColumn("Difficulty", width="small", format="%d"),
                "item_index": st.column_config.Column("Index", disabled=True, width="small") # Technically NumberColumn for proper display
            }
            if "explanation" in filtered_df.columns:
                column_config["explanation"] = st.column_config.TextColumn("Explanation", width="medium")
            
            column_order = ["select", "material", "choices_formatted", "score_rating", "feedback", 
                            "question_title", "level_title", "question_difficulty"]
            if "explanation" in filtered_df.columns:
                column_order.append("explanation")
            
            all_cols = filtered_df.columns.tolist()
            for col in all_cols:
                if col not in column_order and col not in ["item_index", "choices_json", "select"]: # choices_json is internal
                    column_order.append(col)
            column_order.append("item_index") # Ensure item_index is last or visible if needed for debug
            column_order = [col for col in column_order if col in filtered_df.columns]

            edited_df = st.data_editor(
                filtered_df, column_order=column_order, column_config=column_config,
                use_container_width=True, num_rows="dynamic", hide_index=True,
                key=f"data_editor_{st.session_state.file_name}"
            )
            
            action_buttons_col1, action_buttons_col2, action_message_col = st.columns([1, 1.5, 2])

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
                    title = row_data.get('question_title', f"Question {row_data.get('item_index', 'N/A')+1}")
                    st.subheader(f"Preview ({i+1}/{len(selected_rows_df)}): {title}")
                    st.markdown("#### Question")
                    st.markdown(row_data.get('material', ''))
                    st.markdown("#### Choices")
                    choices_fmt = row_data.get('choices_formatted', '')
                    # Split choices for individual markdown rendering, handling potential None
                    choice_lines = choices_fmt.strip().split('\n\n') if choices_fmt else []
                    for choice_md in choice_lines:
                        if choice_md.strip(): st.markdown(choice_md)
                    
                    explanation = row_data.get('explanation', None)
                    if explanation and pd.notna(explanation) and str(explanation).strip():
                        st.markdown("#### Explanation")
                        st.markdown(explanation)
            
            if export_powerpath_clicked and has_selection_for_actions:
                powerpath_data = df_to_powerpath_json(selected_rows_df)
                if powerpath_data:
                    st.session_state.powerpath_export_data = powerpath_data
                    st.markdown(
                        get_powerpath_download_link(powerpath_data, st.session_state.file_name),
                        unsafe_allow_html=True
                    )
                    st.success(f"✅ {len(powerpath_data)} questions prepared for PowerPath JSON download.")
                else:
                    st.warning("⚠️ No questions could be converted (check data or selection).")
            elif 'powerpath_export_data' in st.session_state and not export_powerpath_clicked : 
                 if st.session_state.powerpath_export_data: #Only show if there is data
                    st.markdown(
                        get_powerpath_download_link(st.session_state.powerpath_export_data, st.session_state.file_name),
                        unsafe_allow_html=True
                    )

            st.markdown("---") 
            save_col, reset_col = st.columns([1, 1])
            
            if save_col.button("💾 Save All Changes to Full Dataset", use_container_width=True):
                skipped_new_rows_count = 0
                for _, edited_row_series in edited_df.iterrows():
                    original_item_idx = edited_row_series['item_index']

                    if pd.isna(original_item_idx):
                        skipped_new_rows_count +=1
                        continue # Skip rows added in UI that don't have an original index

                    main_df_mask = (st.session_state.df['item_index'] == original_item_idx)
                    
                    if main_df_mask.any():
                        # 1. Handle 'choices_formatted' to 'choices_json' conversion
                        if 'choices_formatted' in edited_row_series and 'choices_json' in st.session_state.df.columns:
                            edited_formatted_choices_text = edited_row_series['choices_formatted']
                            
                            newly_parsed_choices_list = parse_formatted_choices_to_list(edited_formatted_choices_text)
                            new_choices_json_str = json.dumps(newly_parsed_choices_list)
                            
                            st.session_state.df.loc[main_df_mask, 'choices_json'] = new_choices_json_str
                            st.session_state.df.loc[main_df_mask, 'choices_formatted'] = format_choices(newly_parsed_choices_list)

                        # 2. Handle other editable columns
                        for col_name in edited_row_series.index:
                            if col_name in st.session_state.df.columns and \
                               col_name not in ['select', 'item_index', 'choices_formatted', 'choices_json']:
                                
                                val_from_edited_row = edited_row_series[col_name]
                                
                                if col_name in ['score_rating', 'question_difficulty'] and pd.notna(val_from_edited_row):
                                    if isinstance(val_from_edited_row, float) and val_from_edited_row.is_integer():
                                        val_from_edited_row = int(val_from_edited_row)
                                    
                                    if col_name == 'score_rating':
                                        st.session_state.df.loc[main_df_mask, col_name] = str(val_from_edited_row)
                                    else: # question_difficulty
                                        st.session_state.df.loc[main_df_mask, col_name] = val_from_edited_row
                                elif col_name == 'score_rating' and (pd.isna(val_from_edited_row) or str(val_from_edited_row).strip() == ""):
                                    st.session_state.df.loc[main_df_mask, col_name] = "" 
                                elif pd.isna(val_from_edited_row):
                                    st.session_state.df.loc[main_df_mask, col_name] = None
                                else:
                                    st.session_state.df.loc[main_df_mask, col_name] = val_from_edited_row
                
                if skipped_new_rows_count > 0:
                    st.warning(f"{skipped_new_rows_count} new row(s) added in the editor were not saved as they lack an original index. To add new questions, please modify the source JSON and re-upload.")

                updated_json_full = df_to_json(st.session_state.df) 
                st.session_state.updated_json = updated_json_full
                st.success("✅ All changes saved successfully to the full dataset!")
                st.markdown(
                    get_download_link(updated_json_full, st.session_state.file_name),
                    unsafe_allow_html=True
                )
                # Rerun to refresh the data editor with canonical data from st.session_state.df
                st.rerun()

            elif 'updated_json' in st.session_state and not save_col.button("💾 Save All Changes to Full Dataset", use_container_width=True, key="resave_check_for_display_only"): # Re-display main download if exists
                 if st.session_state.updated_json: #Only show if there is data
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
                st.rerun()
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e) 
            st.info("Please check your JSON file format or try uploading again. If the error persists, consider simplifying recent edits or resetting data.")
    else:
        st.info("📤 Please upload a JSON file to get started.")
        st.subheader("What This App Does")
        c1, c2, c3 = st.columns(3)
        c1.markdown("### 📝 Edit\n- Question text\n- Answer Choices\n- Scores (1-10)\n- Feedback")
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
