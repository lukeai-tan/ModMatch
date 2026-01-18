import pandas as pd
from typing import Union, List, Dict, Any
from file_operations import FileManager

class CourseStorage:
    """Storage manager for university course exchange mappings."""
    
    def __init__(self):
        """Initialize storage with empty dataframes."""
        self.fm = FileManager()
        
        # Auto-load on startup
        data = self.fm.read_all()
        self.nus_df = data['nus'] if data['nus'] is not None else self._create_nus_df()
        self.partner_df = data['pu'] if data['pu'] is not None else self._create_partner_df()
        self.pairings_df = data['mapping'] if data['mapping'] is not None else self._create_pairings_df()
    
    def _create_nus_df(self) -> pd.DataFrame:
        """Create an empty NUS modules dataframe."""
        return pd.DataFrame(columns=[
            'nus_code',
            'nus_mod',
            'nus_desc'
        ])
    
    def _create_partner_df(self) -> pd.DataFrame:
        """Create an empty partner courses dataframe."""
        return pd.DataFrame(columns=[
            'pu',
            'pu_mod',
            'pu_code',
            'pu_desc'
        ])
    
    def _create_pairings_df(self) -> pd.DataFrame:
        """Create an empty pairings dataframe."""
        return pd.DataFrame(columns=[
            'nus_code',
            'pu',
            'pu_code',
            'score'
        ])
    
    def _sort_partner_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sort partner universities dataframe by university name and course code."""
        df = df.copy()
        df = df.sort_values(by=['pu', 'pu_code'], ascending=[True, True])
        return df.reset_index(drop=True)
    
    def _sort_pairings_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sort pairings dataframe by NUS module code, university name, and course code."""
        df = df.copy()
        df = df.sort_values(
            by=['nus_code', 'pu', 'pu_code'],
            ascending=[True, True, True]
        )
        return df.reset_index(drop=True)
    
    # ==================== CRUD Operations - NUS Modules ====================
    
    def replace_nus_df(self, df: pd.DataFrame) -> None:
        """
        Replace the entire NUS modules dataframe. Duplicates are automatically removed.
        
        Args:
            df: New dataframe to replace with
        """
        df = df.copy()
        required_cols = ['nus_code', 'nus_mod', 'nus_desc']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        
        # Remove duplicates based on nus_code, keeping first occurrence
        df = df.drop_duplicates(subset=['nus_code'], keep='first')
        
        self.nus_df = df[required_cols].reset_index(drop=True)
        
        self.fm.write_nus(self.nus_df)
    
    def append_nus_entries(self, entries: Union[pd.DataFrame, List[Dict]]) -> pd.DataFrame:
        """
        Append new entries to NUS modules dataframe. Duplicates are automatically skipped.
        
        Args:
            entries: DataFrame or list of dictionaries with module information
            
        Returns:
            DataFrame with the newly added entries (excludes duplicates)
        """
        if isinstance(entries, list):
            entries = pd.DataFrame(entries)
        
        entries = entries.copy()
        required_cols = ['nus_code', 'nus_mod', 'nus_desc']
        
        # Filter out entries with nus_code that already exists
        existing_codes = set(self.nus_df['nus_code'])
        new_entries = entries[~entries['nus_code'].isin(existing_codes)][required_cols]
        
        if len(new_entries) > 0:
            self.nus_df = pd.concat([self.nus_df, new_entries], ignore_index=True)

        self.fm.write_nus(self.nus_df)
        
        return new_entries.copy()
    
    def remove_nus_entries(self, indices: Union[int, List[int]]) -> pd.DataFrame:
        """
        Remove NUS module entries by index.
        
        Args:
            indices: Single index or list of indices to remove
            
        Returns:
            DataFrame with the removed entries
        """
        if isinstance(indices, int):
            indices = [indices]
        
        removed_entries = self.nus_df.loc[indices].copy()
        self.nus_df = self.nus_df.drop(indices).reset_index(drop=True)
        
        self.fm.write_nus(self.nus_df)

        return removed_entries
    
    def edit_nus_entry(self, index: int, updates: Dict[str, Any]) -> pd.DataFrame:
        """
        Edit a single NUS module entry. If updating nus_code would create a duplicate, 
        the nus_code update is ignored but other updates are applied.
        
        Args:
            index: Index of entry to edit
            updates: Dictionary of column: value pairs to update
            
        Returns:
            DataFrame with the entry (single row)
        """
        # Check if we're updating nus_code and if it would create a duplicate
        if 'nus_code' in updates:
            new_code = updates['nus_code']
            existing_codes = self.nus_df[self.nus_df.index != index]['nus_code']
            if new_code in existing_codes.values:
                # Ignore the nus_code update, but apply other updates
                updates = {k: v for k, v in updates.items() if k != 'nus_code'}
        
        for col, value in updates.items():
            if col in self.nus_df.columns:
                self.nus_df.at[index, col] = value

        self.fm.write_nus(self.nus_df)
        
        return self.nus_df.loc[[index]].copy()
    
    # ==================== CRUD Operations - Partner Courses ====================
    
    def replace_partner_df(self, df: pd.DataFrame) -> None:
        """
        Replace the entire partner universities dataframe. Duplicates are automatically removed.
        
        Args:
            df: New dataframe to replace with
        """
        df = df.copy()
        required_cols = ['pu', 'pu_mod', 'pu_code', 'pu_desc']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        
        # Remove duplicates based on (pu, pu_code) combination, keeping first occurrence
        df = df.drop_duplicates(subset=['pu', 'pu_code'], keep='first')
        
        self.partner_df = self._sort_partner_df(df[required_cols])

        self.fm.write_pu(self.partner_df)
    
    def append_partner_entries(self, entries: Union[pd.DataFrame, List[Dict]]) -> pd.DataFrame:
        """
        Append new entries to partner universities dataframe. Duplicates are automatically skipped.
        
        Args:
            entries: DataFrame or list of dictionaries with course information
            
        Returns:
            DataFrame with the newly added entries (excludes duplicates)
        """
        if isinstance(entries, list):
            entries = pd.DataFrame(entries)
        
        entries = entries.copy()
        required_cols = ['pu', 'pu_mod', 'pu_code', 'pu_desc']
        
        # Create composite keys for comparison
        existing_keys = set(self.partner_df['pu'] + '::' + self.partner_df['pu_code'])
        entries_with_key = entries.copy()
        entries_with_key['_key'] = entries_with_key['pu'] + '::' + entries_with_key['pu_code']
        
        # Filter out entries with (pu, pu_code) combinations that already exist
        new_entries = entries_with_key[~entries_with_key['_key'].isin(existing_keys)][required_cols]
        
        if len(new_entries) > 0:
            self.partner_df = pd.concat([self.partner_df, new_entries], ignore_index=True)
            self.partner_df = self._sort_partner_df(self.partner_df)

        self.fm.write_pu(self.partner_df)
        
        return new_entries.copy()
    
    def remove_partner_entries(self, indices: Union[int, List[int]]) -> pd.DataFrame:
        """
        Remove partner university entries by index.
        
        Args:
            indices: Single index or list of indices to remove
            
        Returns:
            DataFrame with the removed entries
        """
        if isinstance(indices, int):
            indices = [indices]
        
        removed_entries = self.partner_df.loc[indices].copy()
        self.partner_df = self.partner_df.drop(indices).reset_index(drop=True)
        self.partner_df = self._sort_partner_df(self.partner_df)
        
        self.fm.write_pu(self.partner_df)

        return removed_entries
    
    def edit_partner_entry(self, index: int, updates: Dict[str, Any]) -> pd.DataFrame:
        """
        Edit a single partner university entry. If updating (pu, pu_code) would create a duplicate,
        those updates are ignored but other updates are applied.
        
        Args:
            index: Index of entry to edit
            updates: Dictionary of column: value pairs to update
            
        Returns:
            DataFrame with the entry (single row)
        """
        # Check if we're updating pu or pu_code and if it would create a duplicate
        if 'pu' in updates or 'pu_code' in updates:
            new_pu = updates.get('pu', self.partner_df.at[index, 'pu'])
            new_pu_code = updates.get('pu_code', self.partner_df.at[index, 'pu_code'])
            
            # Check if this combination exists elsewhere
            other_entries = self.partner_df[self.partner_df.index != index]
            existing_combo = ((other_entries['pu'] == new_pu) & 
                            (other_entries['pu_code'] == new_pu_code)).any()
            
            if existing_combo:
                # Ignore pu and pu_code updates, but apply other updates
                updates = {k: v for k, v in updates.items() if k not in ['pu', 'pu_code']}
        
        for col, value in updates.items():
            if col in self.partner_df.columns:
                self.partner_df.at[index, col] = value
        
        # Re-sort if university name or course code changed
        if 'pu' in updates or 'pu_code' in updates:
            self.partner_df = self._sort_partner_df(self.partner_df)
        
        self.fm.write_pu(self.partner_df)

        return self.partner_df.loc[[index]].copy()
    
    # ==================== Unified Retrieval Operation ====================
    
    def get_course_pairs(
        self,
        nus_index: int,
        partner_indices: List[int]
    ) -> Dict[str, pd.DataFrame]:
        """
        Retrieve course information for one NUS module paired with multiple partner courses.
        
        Args:
            nus_index: Index of NUS module in nus_df
            partner_indices: List of indices of partner courses in partner_df
            
        Returns:
            Dictionary containing:
                - 'nus_course': DataFrame with single NUS module (1 row)
                - 'partner_courses': DataFrame with all selected partner courses
        
        Example:
            result = storage.get_course_pairs(nus_index=0, partner_indices=[5, 7, 9])
            # result['nus_course'] -> DataFrame with 1 row (NUS module at index 0)
            # result['partner_courses'] -> DataFrame with 3 rows (partner courses at indices 5, 7, 9)
        """
        return {
            'nus_course': self.nus_df.loc[[nus_index]].copy(),
            'partner_courses': self.partner_df.loc[partner_indices].copy()
        }
    
    def get_nus_entries(self, indices: Union[int, List[int], None] = None) -> pd.DataFrame:
        """
        Retrieve NUS module entries by index.
        
        Args:
            indices: Single index, list of indices, or None for all entries
            
        Returns:
            DataFrame with selected entries
        """
        if indices is None:
            return self.nus_df.copy()
        
        if isinstance(indices, int):
            indices = [indices]
        
        return self.nus_df.loc[indices].copy()
    
    def get_partner_entries(self, indices: Union[int, List[int], None] = None) -> pd.DataFrame:
        """
        Retrieve partner university entries by index.
        
        Args:
            indices: Single index, list of indices, or None for all entries
            
        Returns:
            DataFrame with selected entries
        """
        if indices is None:
            return self.partner_df.copy()
        
        if isinstance(indices, int):
            indices = [indices]
        
        return self.partner_df.loc[indices].copy()
    
    def get_pairings(self, indices: Union[int, List[int], None] = None) -> pd.DataFrame:
        """
        Retrieve pairings by index.
        
        Args:
            indices: Single index, list of indices, or None for all pairings
            
        Returns:
            DataFrame with selected pairings
        """
        if indices is None:
            return self.pairings_df.copy()
        
        if isinstance(indices, int):
            indices = [indices]
        
        return self.pairings_df.loc[indices].copy()
    
    # ==================== Pairing Operations ====================
    
    def add_pairing(
        self,
        nus_index: int,
        partner_index: Union[int, List[int]],
        score: Union[float, List[float]]
    ) -> pd.DataFrame:
        """
        Add course pairings. Duplicates are automatically prevented.
        
        Args:
            nus_index: Single index in nus_df (one NUS module)
            partner_index: Index or list of indices in partner_df
            score: Mapping score(s) - single float or list matching partner_index length
            
        Returns:
            DataFrame with newly added pairings (excludes duplicates)
        """
        # Convert partner_index to list for uniform handling
        if isinstance(partner_index, int):
            partner_index = [partner_index]
        
        # Convert score to list, matching the length of partner_index
        if isinstance(score, (int, float)):
            score = [score] * len(partner_index)
        
        # Duplicate the single NUS index to match each partner entry (one-to-many relationship)
        nus_index_list = [nus_index] * len(partner_index)
        
        if len(nus_index_list) != len(partner_index) or len(nus_index_list) != len(score):
            raise ValueError("partner_index and score must have same length")
        
        new_pairings = []
        for n_idx, p_idx, sc in zip(nus_index_list, partner_index, score):
            nus_code = self.nus_df.at[n_idx, 'nus_code']
            pu = self.partner_df.at[p_idx, 'pu']
            pu_code = self.partner_df.at[p_idx, 'pu_code']
            
            # Check if pairing already exists
            existing = self.pairings_df[
                (self.pairings_df['nus_code'] == nus_code) &
                (self.pairings_df['pu'] == pu) &
                (self.pairings_df['pu_code'] == pu_code)
            ]
            
            if len(existing) == 0:
                pairing = {
                    'nus_code': nus_code,
                    'pu': pu,
                    'pu_code': pu_code,
                    'score': sc
                }
                new_pairings.append(pairing)
        
        if len(new_pairings) > 0:
            new_pairings_df = pd.DataFrame(new_pairings)
            self.pairings_df = pd.concat([self.pairings_df, new_pairings_df], ignore_index=True)
            self.pairings_df = self._sort_pairings_df(self.pairings_df)
            self.fm.write_mapping(self.pairings_df)
            return new_pairings_df
        else:
            return pd.DataFrame(columns=self.pairings_df.columns)
    
    def remove_pairing(self, indices: Union[int, List[int]]) -> pd.DataFrame:
        """
        Remove pairings by index.
        
        Args:
            indices: Index or list of indices in pairings_df
            
        Returns:
            DataFrame with removed pairings
        """
        if isinstance(indices, int):
            indices = [indices]
        
        removed_pairings = self.pairings_df.loc[indices].copy()
        self.pairings_df = self.pairings_df.drop(indices).reset_index(drop=True)
        self.pairings_df = self._sort_pairings_df(self.pairings_df)
        
        self.fm.write_mapping(self.pairings_df)

        return removed_pairings
    
    def update_pairing_score(self, index: int, new_score: float) -> pd.DataFrame:
        """
        Update the score of an existing pairing.
        
        Args:
            index: Index of pairing to update
            new_score: New score value
            
        Returns:
            DataFrame with the updated pairing (single row)
        """
        self.pairings_df.at[index, 'score'] = new_score
        self.fm.write_mapping(self.pairings_df)
        return self.pairings_df.loc[[index]].copy()
    
    def get_pairings_for_nus_module(self, module_code: str) -> pd.DataFrame:
        """
        Get all pairings for a specific NUS module.
        
        Args:
            module_code: NUS module code
            
        Returns:
            DataFrame with all pairings for this module
        """
        return self.pairings_df[self.pairings_df['nus_code'] == module_code].copy()
    
    def get_pairings_for_partner_course(self, university: str, course_code: str) -> pd.DataFrame:
        """
        Get all pairings for a specific partner university course.
        
        Args:
            university: Partner university name
            course_code: Course code from partner university
            
        Returns:
            DataFrame with all pairings for this course
        """
        return self.pairings_df[
            (self.pairings_df['pu'] == university) &
            (self.pairings_df['pu_code'] == course_code)
        ].copy()
    
    # ==================== Helper Methods for UI ====================
    
    def get_unpaired_nus_modules(self) -> pd.DataFrame:
        """
        Get NUS modules that have no pairings.
        
        Returns:
            DataFrame with unpaired NUS modules
        """
        if len(self.pairings_df) == 0:
            return self.nus_df.copy()
        
        paired_codes = self.pairings_df['nus_code'].unique()
        return self.nus_df[~self.nus_df['nus_code'].isin(paired_codes)].copy()
    
    def get_unpaired_partner_courses(self) -> pd.DataFrame:
        """
        Get partner university courses that have no pairings.
        
        Returns:
            DataFrame with unpaired partner courses
        """
        if len(self.pairings_df) == 0:
            return self.partner_df.copy()
        
        # Create composite key for partner courses
        paired_keys = self.pairings_df['pu'] + ':' + self.pairings_df['pu_code']
        partner_keys = self.partner_df['pu'] + ':' + self.partner_df['pu_code']
        
        return self.partner_df[~partner_keys.isin(paired_keys)].copy()
    
    def get_course_details_for_pairing(self, pairing_index: int):
        # Get the row from the mapping dataframe
        pairing = self.pairings_df.loc[pairing_index]
        
        # Filter for the NUS module
        nus_match = self.nus_df[self.nus_df['nus_code'] == pairing['nus_code']]
        
        # Filter for the Partner module
        pu_match = self.partner_df[
            (self.partner_df['pu'] == pairing['pu']) & 
            (self.partner_df['pu_code'] == pairing['pu_code'])
        ]

        if nus_match.empty or pu_match.empty:
            return {
                'nus_module': {'nus_mod': 'N/A (Deleted)', 'nus_desc': 'The source data for this module was removed.'},
                'partner_course': {'pu_mod': 'N/A (Deleted)', 'pu_desc': 'The source data for this course was removed.'},
                'score': pairing['score']
            }

        return {
            'nus_module': nus_match.iloc[0].copy(),
            'partner_course': pu_match.iloc[0].copy(),
            'score': pairing['score']
        }
    
    def clear_all(self) -> None:
        """Clear all data from storage."""
        self.nus_df = self._create_nus_df()
        self.partner_df = self._create_partner_df()
        self.pairings_df = self._create_pairings_df()
        self.fm.write_all(self.nus_df, self.partner_df, self.pairings_df)



    def sync_to_disk(self):
        """Invisible background operation: Save all current memory to app data files."""
        self.fm.write_all(self.nus_df, self.partner_df, self.pairings_df)

    def import_external_pu(self, file_object):
        """Browse for file -> Read -> Append -> Save to internal pu.csv"""
        # Read the uploaded CSV into a temporary dataframe
        new_data = pd.read_csv(file_object)
        
        # self.append_partner_entries handles the concat, sorting, 
        # duplicate checking, AND calls fm.write_pu internally.
        self.append_partner_entries(new_data)

    def import_external_nus(self, file_object):
        """Browse for file -> Read -> Append -> Save to internal nus.csv"""
        new_data = pd.read_csv(file_object)
        self.append_nus_entries(new_data)

    def export_exchange_plan(self, destination_path: str):
        """
        Export strictly the mapping/plan data to a user-desired location.
        """
        if self.pairings_df.empty:
            raise ValueError("The exchange plan is empty. Nothing to export.")
        
        self.fm.export_mapping(destination_path)