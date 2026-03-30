# Interactive Risk-of-Bias Table Feature

## Overview

Added an interactive Risk-of-Bias (RoB) assessment table that allows users to click on any row to view the corresponding abstract. This makes it easy to investigate studies with specific risk-of-bias judgments (e.g., "High concern", "Some concern").

## Features

### 1. **Interactive Risk-of-Bias Table**
   - Displays all studies with their risk-of-bias assessments
   - Columns include:
     - Study #
     - PMID
     - Title (truncated to 80 characters)
     - Overall Judgment (Low, Some concerns, High, Critical, Insufficient information)
     - Full-text availability (Yes/No)

### 2. **Click-to-View Abstracts**
   - Click any row in the table to view the full abstract
   - Abstract viewer shows:
     - Title
     - PMID
     - Authors
     - Journal
     - Year
     - Full abstract text
   - Includes a copy button for easy copying

### 3. **Automatic Visibility**
   - Table and abstract viewer are automatically shown/hidden based on whether risk-of-bias assessment is enabled and data is available
   - Only appears when risk-of-bias assessment is completed

## Usage

1. **Run an analysis** with Risk-of-Bias Assessment enabled (default: enabled)
2. **After analysis completes**, scroll down to see the "Risk-of-Bias Assessments" table
3. **Click any row** in the table to view the abstract for that study
4. **Use the copy button** to copy the abstract text if needed

## Example Workflow

### Investigating High-Risk Studies

1. Run analysis for a chemical (e.g., "Acetaminophen")
2. After completion, look at the Risk-of-Bias Summary plot to see distribution
3. Scroll to the Risk-of-Bias Assessments table
4. Find studies with "High" or "Some concerns" judgments
5. Click on those rows to read the abstracts and understand why they received those judgments

### Verifying Assessments

1. Click on any study in the table
2. Read the abstract to verify the risk-of-bias judgment
3. Check if full-text was used (shown in the table)
4. Use this information to understand the quality of evidence

## Technical Details

### Implementation

- **Component**: Gradio `Dataframe` with `select` event
- **State Management**: Uses Gradio `State` component to store abstracts list
- **Event Handling**: `SelectData` event provides row index when clicked
- **Data Flow**: 
  1. Analysis generates RoB assessments and abstracts
  2. Abstracts stored in state component
  3. Table displays RoB summary
  4. Click event retrieves abstract from state using row index
  5. Abstract displayed in text viewer

### Code Changes

1. **Modified `analyze_chemical()` function**:
   - Returns additional outputs: `rob_table_df` (DataFrame) and `abstracts` (list)
   - Creates interactive table with study information

2. **Added UI Components**:
   - `rob_table_output`: Interactive Dataframe component
   - `abstract_viewer`: Textbox for displaying abstracts
   - `abstracts_state`: State component for storing abstracts

3. **Added Event Handlers**:
   - `show_abstract_from_table()`: Handles row clicks and displays abstract
   - `update_rob_table_visibility()`: Shows/hides table based on data availability

## Benefits

1. **Easy Investigation**: Quickly find and read abstracts for studies with specific risk judgments
2. **Transparency**: See exactly what text was used for risk-of-bias assessment
3. **Quality Control**: Verify that assessments are appropriate based on the abstract content
4. **User-Friendly**: No need to manually search through results files

## Future Enhancements

Potential improvements:
- Filter table by judgment type (e.g., show only "High" risk studies)
- Sort table by judgment or other columns
- Show domain-specific judgments in expandable rows
- Link to full-text PDFs when available
- Export table to CSV/Excel

## Notes

- The table only appears when Risk-of-Bias Assessment is enabled
- Abstracts are stored in memory during the session
- Full-text availability is indicated in the table (helps understand assessment quality)
- The abstract viewer includes a copy button for easy text copying
