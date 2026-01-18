import streamlit as st
import pandas as pd
from storage import CourseStorage
from mapping_engine import MappingEngine

# CONFIG
st.set_page_config(page_title="ModMatch: SEP Planner", layout="wide")

st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 3em; font-weight: bold; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# INITIALISATION
@st.cache_resource
def init_backend():
    storage = CourseStorage()
    engine = MappingEngine()
        
    return storage, engine

if 'storage' not in st.session_state:
    storage, engine = init_backend()
    st.session_state.storage = storage
    st.session_state.engine = engine
else:
    storage = st.session_state.storage
    engine = st.session_state.engine

if 'preview' not in st.session_state:
    st.session_state.preview = []

st.title("ModMatch: SEP Planner")
st.write("Match NUS modules with Partner University courses using semantic similarity.")

st.header("Step 1: Select Modules for Comparison")
col1, col2 = st.columns(2)

is_preview_active = len(st.session_state.preview) > 0

with col1:
    st.subheader("NUS Modules")
    home_sel = st.dataframe(
        storage.get_nus_entries(), 
        on_select="rerun", 
        selection_mode="single-row", 
        hide_index=True,
        use_container_width=True,
        key="nus_table"
    )
    
    if home_sel.selection.rows:
        # Disable the button if a preview exists
        if st.button("Delete Selected NUS", key="del_nus_btn", disabled=is_preview_active):
            storage.remove_nus_entries(home_sel.selection.rows)
            st.rerun()

with col2:
    st.subheader("Partner University Modules")
    partner_sel = st.dataframe(
        storage.get_partner_entries(), 
        on_select="rerun", 
        selection_mode="multi-row", 
        hide_index=True,
        use_container_width=True,
        key="pu_table"
    )
    
    if partner_sel.selection.rows:
        if st.button("Delete Selected Partner", key="del_pu_btn", disabled=is_preview_active):
            storage.remove_partner_entries(partner_sel.selection.rows)
            st.rerun()

btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    # Logic to generate the preview list
    if st.button("Generate Comparison Preview", type="primary", use_container_width=True):
        h_rows = home_sel.selection.rows
        p_rows = partner_sel.selection.rows

        if h_rows:
            selected_nus = storage.get_nus_entries().iloc[h_rows[0]]
            
            # SCENARIO A: Manual Description Check
            if p_rows:
                data_bundle = storage.get_course_pairs(h_rows[0], p_rows)
                st.session_state.preview = engine.get_preview_pairings(
                    data_bundle['nus_course'].iloc[0], 
                    data_bundle['partner_courses']
                )
                st.success(f"Description similarity calculated!")
                
            # SCENARIO B: Smart Name Match
            else:
                with st.spinner("Scanning all university course names..."):
                    all_partners = storage.get_partner_entries()
                    st.session_state.preview = engine.get_smart_name_matches(
                        selected_nus, 
                        all_partners
                    )
                st.success(f"AI found {len(st.session_state.preview)} matches!")
            st.rerun()
        else:
            st.warning("Please select 1 NUS module on the left.")

with btn_col2:
    if st.button("Clear Preview", use_container_width=True, disabled=not is_preview_active):
        st.session_state.preview = []
        st.rerun()

st.divider()

# PREVIEW AND SELECT
if st.session_state.preview:
    st.header("Step 2: Review & Finalize Mappings")
    st.write("Select the pairings you want to save to your final plan.")

    
    preview_df = pd.DataFrame([{
        "NUS Code": m.home_row['nus_code'],
        "Partner": m.partner_row['pu'],
        "Partner Code": m.partner_row['pu_code'],
        "Match Score": f"{m.similarity_score:.1%}"
    } for m in st.session_state.preview])
    
    review_sel = st.dataframe(
        preview_df, 
        on_select="rerun", 
        selection_mode="multi-row", 
        hide_index=True,
        use_container_width=True
    )

    if st.button("Confirm Selections & Add to Plan"):
        selected_preview_indices = review_sel.selection.rows
        
        if selected_preview_indices:
            # gets the current valid indices from the DB
            valid_nus_indices = storage.get_nus_entries().index
            valid_pu_indices = storage.get_partner_entries().index
            
            # check if the modules in the preview still exist
            try:
                for idx in selected_preview_indices:
                    m = st.session_state.preview[idx]
                    if m.home_row.name not in valid_nus_indices or m.partner_row.name not in valid_pu_indices:
                        raise KeyError("One of the modules was deleted from the database.")

                # 3. If all exist, finalize and save
                final_payload = engine.finalize_selections(
                    st.session_state.preview, 
                    selected_preview_indices
                )
                
                storage.add_pairing(
                    nus_index=final_payload["nus_index"],
                    partner_index=final_payload["partner_indices"],
                    score=final_payload["scores"]
                )
                
                st.session_state.preview = []
                st.success("Successfully added to your Exchange Plan!")
                st.rerun()
                
            except KeyError:
                st.error("Error: You are trying to add modules that have been deleted. Clearing preview...")
                st.session_state.preview = [] # Wipe the stale preview
                st.rerun()

# --- SHOW FINAL PLANNER ---
st.divider()
st.header("Exchange Plan")

pairings = storage.get_pairings()

if pairings.empty:
    st.info("No pairings saved yet. Complete Step 1 and 2 to see your plan here.")
else:
    col_h1, col_h2 = st.columns([0.8, 0.2])
    

    st.markdown("""
        <div style='display: flex; font-weight: bold; border-bottom: 2px solid #ccc; padding-bottom: 5px; margin-bottom: 10px;'>
            <div style='flex: 2;'>NUS Module</div>
            <div style='flex: 2;'>Partner University</div>
            <div style='flex: 2;'>Partner Module</div>
            <div style='flex: 1;'>Match</div>
            <div style='flex: 0.5;'></div>
        </div>
    """, unsafe_allow_html=True)

    # list of pairings
    for i, row in pairings.iterrows():

        details = storage.get_course_details_for_pairing(i)

        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 0.5])
        
        with c1:
            st.write(f"**{row['nus_code']}**")
        with c2:
            st.write(row['pu'])
        with c3:
            st.write(row['pu_code'])
        with c4:
            score = row['score']
            color = "green" if score > 0.7 else "orange" if score > 0.4 else "red"
            st.markdown(f"<span style='color:{color}; font-weight:bold;'>{score:.1%}</span>", unsafe_allow_html=True)
        with c5:
            if st.button("❌", key=f"del_{i}", help="Remove this pairing"):
                storage.remove_pairing(i)
                st.rerun()
        
        with st.expander("View Descriptions"):
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.markdown(f"**{details['nus_module']['nus_mod']}**")
                st.caption(details['nus_module']['nus_desc'])
            with d_col2:
                st.markdown(f"**{details['partner_course']['pu_mod']}**")
                st.caption(details['partner_course']['pu_desc'])
        
        st.markdown("---") 

# --- SIDEBAR: DATA PERSISTENCE & INTEGRATION ---
with st.sidebar:
    st.header("Import stuff")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    target = st.selectbox("Add to:", ["NUS Modules", "Partner Modules"])
    
    if st.button("Import"):
        if uploaded_file:
            if target == "Partner Modules":
                storage.import_external_pu(uploaded_file)
            else:
                storage.import_external_nus(uploaded_file)
            st.success("Successfully imported!")
            st.rerun()

with st.sidebar:
    st.header("Export Stuff")

    csv_string = storage.fm.get_export_buffer('mapping')
    
    if csv_string:
        st.download_button(
            label="Download Plan as CSV",
            data=csv_string,
            file_name="my_exchange_plan.csv",
            mime="text/csv"
        )
    else:
        st.info("Plan is empty; nothing to export.")
    
    st.header("Data Stuff")
    if st.button("Clear All Data", help="This will DELETE data from all tables.", use_container_width=True):
        storage.clear_all()
        st.session_state.preview = []
        st.success("Data cleared!")
        st.rerun()