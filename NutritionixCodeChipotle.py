from collections import Counter

# Count how many times each item appears (to handle duplicates like double protein)
item_counts = Counter(selected_items)

# Create a DataFrame that includes each item instance separately
selected_df = pd.DataFrame([
    chipotle_df[chipotle_df['Item'].str.lower() == item.lower()].iloc[0].copy()
    for item in selected_items
    if not chipotle_df[chipotle_df['Item'].str.lower() == item.lower()].empty
])

# OPTIONAL: Add "x2" label to duplicate items for clarity in the table
row_labels = []
for item in selected_items:
    count = item_counts[item]
    if count > 1:
        row_labels.append(f"{item} x{selected_items[:selected_items.index(item)+count].count(item)}")
    else:
        row_labels.append(item)

selected_df.insert(0, "Item", row_labels)

# Build the total row
numeric_cols = [
    "Calories", "Total Fat (g)", "Saturated Fat (g)", "Cholesterol (mg)",
    "Sodium (mg)", "Carbs (g)", "Fiber (g)", "Sugars (g)", "Protein (g)"
]
total_row = selected_df[numeric_cols].sum().to_frame().T
total_row.insert(0, "Serving Size", "")
total_row.insert(0, "Item", "TOTAL")

# Final table
table_display = pd.concat([selected_df, total_row], ignore_index=True)



        
