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
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    /* Main app styling */
    body {
        background: linear-gradient(135deg, #e8f0fe 0%, #ffffff 100%);
        font-family: 'Roboto', sans-serif;
    }
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    h1, h2, h3 {
        color: #0D47A1;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: rgba(255,255,255,0.7);
        border-radius: 4px 4px 0 0;
        padding: 10px;
        font-weight: bold;
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
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: background-color 0.3s ease, transform 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1565C0;
        transform: translateY(-2px);
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
        background-color: #ffffff;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f5f5f5;
        padding-top: 2rem;
        box-shadow: inset -1px 0 0 rgba(0,0,0,0.1);
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
        if 'choices_json' in row_dict:
            row_dict['choices'] = json.loads(row_dict['choices_json'])
            del row_dict['choices_json']
        
        # Remove the formatted display string
        if 'choices_formatted' in row_dict:
            del row_dict['choices_formatted']
        
        # Store score_rating as a string to ensure it remains editable
        # This is the key fix - we'll store it as a string in the JSON
        if 'score_rating' in row_dict and row_dict['score_rating'] is not None:
            if isinstance(row_dict['score_rating'], (int, float)):
                row_dict['score_rating'] = str(int(row_dict['score_rating']) if row_dict['score_rating'] == int(row_dict['score_rating']) else row_dict['score_rating'])
        
        result.append(row_dict)
    
    return result
# -------------------- MAIN APP LAYOUT --------------------

st.title("📚 Math Questions Editor")
st.write("Upload a JSON file to edit questions, add scores, and provide feedback.")

# Create tabs for different sections
tab1, tab2 = st.tabs(["📄 Edit Questions", "ℹ️ Instructions"])

# Instructions tab content
with tab2:
    st.header("How to Use This App")
    st.markdown("""
    1. **Upload** your JSON file with math questions
    2. **Edit** questions, add scores (1-10), and provide feedback
    3. **Filter** questions by level or score range
    4. **Sort** questions by score
    5. **Save** your changes and download the updated JSON
    
    ### Math Expressions
    This app supports LaTeX math expressions in your questions and choices.
    
    ### File Format
    The app expects a JSON file with an array of question objects, each containing:
    - material: The question text (can include LaTeX)
    - choices: Array of answer choices with text and is_correct flag
    - Other fields like explanation, question_title, etc.
    """)
    
    st.subheader("Example Format")
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

# Main edit tab content
with tab1:
    # File uploader
    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])

    if uploaded_file is not None:
        # Wrap all processing in a try-except block
        try:
            # Get the filename for later use in the download button
            file_name = uploaded_file.name
            
            # Read and parse the JSON file
            content = uploaded_file.getvalue().decode('utf-8')
            json_data = json.loads(content)
            
            # Store the original data in session state
            if 'original_data' not in st.session_state:
                st.session_state.original_data = json_data
                st.session_state.file_name = file_name
            
            # Convert to dataframe for editing
            if 'df' not in st.session_state:
                st.session_state.df = json_to_df(json_data)
            
            # Initialize selected row in session state if not already present
            if 'selected_row_index' not in st.session_state:
                st.session_state.selected_row_index = None
            
            # Sidebar for filtering and sorting
            st.sidebar.header("📊 Filter and Sort")
            
            # Get unique level titles for filtering
            level_titles = sorted(st.session_state.df['level_title'].unique().tolist())
            selected_level = st.sidebar.selectbox(
                "Filter by Level Title", 
                ["All"] + level_titles
            )
            
            # Score filter (if scores have been added)
            score_min = 0
            score_max = 10
            if 'score_rating' in st.session_state.df.columns:
                # Get all numerical scores (ignoring empty or non-numeric)
                scores = [x for x in st.session_state.df['score_rating'] 
                        if isinstance(x, (int, float)) or 
                        (isinstance(x, str) and x.isdigit())]
                
                if scores:
                    scores = [int(x) if isinstance(x, str) else x for x in scores]
                    score_min = min(min(scores), 1)  # Ensure minimum is at least 1
                    score_max = max(max(scores), 10)  # Ensure maximum is at least 10
            
            selected_score = st.sidebar.slider(
                "Filter by Score (1-10)", 
                min_value=1, 
                max_value=10, 
                value=(1, 10)
            )
            
            # Sorting options
            sort_by = st.sidebar.selectbox(
                "Sort by", 
                ["No Sorting", "Score (Low to High)", "Score (High to Low)"]
            )
            
            # Apply filters
            filtered_df = st.session_state.df.copy()
            
            if selected_level != "All":
                filtered_df = filtered_df[filtered_df['level_title'] == selected_level]
            
            # Apply score filter (handle empty scores)
            if 'score_rating' in filtered_df.columns:
                # Convert score_rating to numeric, keeping only rows with valid numeric scores
                filtered_df = filtered_df[
                    (filtered_df['score_rating'] == "") | 
                    (pd.to_numeric(filtered_df['score_rating'], errors='coerce').between(
                        selected_score[0], selected_score[1]))
                ]
            
            # Apply sorting
            if sort_by == "Score (Low to High)":
                # Convert to numeric for sorting, keeping original order for non-numeric
                filtered_df['_sort_val'] = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                filtered_df = filtered_df.sort_values('_sort_val', na_position='last')
                filtered_df = filtered_df.drop('_sort_val', axis=1)
            elif sort_by == "Score (High to Low)":
                filtered_df['_sort_val'] = pd.to_numeric(filtered_df['score_rating'], errors='coerce')
                filtered_df = filtered_df.sort_values('_sort_val', ascending=False, na_position='last')
                filtered_df = filtered_df.drop('_sort_val', axis=1)
            
            # Add a selection column to the DataFrame
            filtered_df['select'] = False
            
            # Display the table with editable cells
            st.write(f"Showing {len(filtered_df)} questions (filtered from {len(st.session_state.df)} total)")
            
            # Determine which columns to edit
            editable_cols = filtered_df.columns.tolist()
            editable_cols.remove('item_index')  # Don't edit the index
            
            # Only make certain columns directly editable in the table
            # For complex JSON like choices, we'll handle differently
            if 'choices_json' in editable_cols:
                editable_cols.remove('choices_json')
            if 'choices_formatted' in editable_cols:
                editable_cols.remove('choices_formatted')
            
            # Configure columns for better display
            column_config = {
                "select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select this question to preview",
                    width="small",
                    default=False
                ),
                "material": st.column_config.TextColumn(
                    "Question", 
                    width="large",
                    help="The question text (supports LaTeX and markdown)"
                ),
                "choices_formatted": st.column_config.TextColumn(
                    "Answer Choices",
                    width="medium",
                    help="The answer choices (✓ indicates correct answer)"
                ),
                "score_rating": st.column_config.NumberColumn(
                    "Score (1-10)", 
                    min_value=1, 
                    max_value=10,
                    format="%d",
                    step=1,
                    width="small",
                    help="Rate this question from 1-10"
                ),
                "feedback": st.column_config.TextColumn(
                    "Feedback", 
                    width="medium",
                    help="Optional feedback on this question"
                ),
                "question_title": st.column_config.TextColumn(
                    "Title",
                    width="medium"
                ),
                "level_title": st.column_config.TextColumn(
                    "Topic/Level",
                    width="medium"
                ),
                "question_difficulty": st.column_config.NumberColumn(
                    "Difficulty",
                    width="small",
                    format="%d"
                ),
                "item_index": st.column_config.Column(
                    "Index", 
                    disabled=True,
                    width="small"
                )
            }
            
            # Handle explanation column
            if "explanation" in filtered_df.columns:
                column_config["explanation"] = st.column_config.TextColumn(
                    "Explanation",
                    width="medium",
                    help="Question explanation (supports LaTeX)"
                )
            
            # Create column order with selection column first
            column_order = [
                "select",
                "material", 
                "choices_formatted", 
                "score_rating", 
                "feedback", 
                "question_title", 
                "level_title",
                "question_difficulty"
            ]
            
            # Add any remaining columns
            for col in filtered_df.columns:
                if col not in column_order and col != "item_index" and col != "choices_json":
                    column_order.append(col)
            
            # Create the data editor
            edited_df = st.data_editor(
                filtered_df,
                column_order=column_order,
                column_config=column_config,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )
            
            # Add a single preview button below the table
            preview_col1, preview_col2 = st.columns([1, 3])
            preview_clicked = preview_col1.button("👁️ Preview Selected Question", use_container_width=True)
            
            # Check if any row is selected
            selected_rows = edited_df[edited_df['select'] == True]
            
            if len(selected_rows) == 0:
                preview_col2.info("Select a question using the checkbox and click 'Preview' to see formatted question")
                has_selection = False
            elif len(selected_rows) > 1:
                preview_col2.warning("Please select only one question at a time")
                has_selection = False
            else:
                preview_col2.success("Question selected! Click 'Preview' to see formatted version")
                has_selection = True
                selected_row = selected_rows.iloc[0]
            
            # Check if preview button is clicked
            if preview_clicked and has_selection:
                # Display the preview section
                st.markdown("---")
                st.markdown("### 📊 Question Preview (With Formatted Math)")
                
                # Create a title for the preview
                question_title = selected_row.get('question_title', f"Question {selected_row['item_index']+1}")
                st.subheader(f"Preview: {question_title}")
                
                # Display the question with rendered markdown
                st.markdown("#### Question")
                st.markdown(selected_row['material'])
                
                # Display the choices with rendered markdown
                st.markdown("#### Choices")
                # Split the choices into individual items for better formatting
                choices_text = selected_row['choices_formatted'].split('\n\n')
                for choice in choices_text:
                    if choice.strip():  # Only process non-empty strings
                        st.markdown(choice)
                
                # Display explanation if available
                if 'explanation' in selected_row and selected_row['explanation']:
                    st.markdown("#### Explanation")
                    st.markdown(selected_row['explanation'])
            
            # Buttons for saving and resetting
            col1, col2 = st.columns([1, 1])
            
            # Save button
            if col1.button("💾 Save Changes", use_container_width=True):
                # Find modified rows and update the main dataframe
                for _, row in edited_df.iterrows():
                    idx = row['item_index']  # This is the original index in the full dataframe
                    
                    # Update the corresponding row in the main dataframe
                    for col in editable_cols:
                        if col in row and col in st.session_state.df.columns and col != 'select':
                            st.session_state.df.loc[st.session_state.df['item_index'] == idx, col] = row[col]
                
                # Convert back to JSON structure
                updated_json = df_to_json(st.session_state.df)
                
                # Store the updated JSON
                st.session_state.updated_json = updated_json
                
                st.success("✅ Changes saved successfully!")
                
                # Generate download link
                st.markdown(
                    get_download_link(updated_json, st.session_state.file_name),
                    unsafe_allow_html=True
                )
            
            # Reset button
            if col2.button("🔄 Reset All Changes", use_container_width=True):
                # Reset the dataframe to the original data
                st.session_state.df = json_to_df(st.session_state.original_data)
                st.success("✅ All changes have been reset to the original data.")
                st.experimental_rerun()
                
        except Exception as e:
            st.error(f"Error processing the file: {str(e)}")
            st.info("Try using a different JSON file or check the file format.")
    else:
        # Instructions when no file is uploaded
        st.info("📤 Please upload a JSON file to get started.")
        
        # Example of what the app can do
        st.subheader("What This App Does")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown("### 📝 Edit")
            st.markdown("- Edit question text")
            st.markdown("- Add scores (1-10)")
            st.markdown("- Provide feedback")
        
        with col2:
            st.markdown("### 🔍 Filter & Sort")
            st.markdown("- Filter by topic/level")
            st.markdown("- Filter by score range")
            st.markdown("- Sort by scores")
        
        with col3:
            st.markdown("### 💾 Save & Export")
            st.markdown("- Save all changes")
            st.markdown("- Download updated JSON")
            st.markdown("- Maintains original format")
            
        # Show an example of markdown rendering
        st.subheader("Example of Formatted Math Questions")
        example_question = """
        ### Example Question
        
        If $-4x + 7 = 10x$, what is the value of $12x-1$?
        
        #### Options:
        - A. $\\frac{1}{2}$
        - B. $2$
        - C. ✓ $5$
        - D. $6$
        
        #### Explanation:
        Solving for $x$: $-4x + 7 = 10x$
        
        $-4x - 10x = -7$
        
        $-14x = -7$
        
        $x = \\frac{1}{2}$
        
        Therefore, $12x-1 = 12(\\frac{1}{2})-1 = 6-1 = 5$
        """
        st.markdown(example_question)
