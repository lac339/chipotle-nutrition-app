import streamlit as st
import pandas as pd
import requests
import altair as alt

# Load and round Chipotle nutrition data
chipotle_df = pd.read_csv("chipotle_nutrition_2025_complete.csv")
numeric_columns = chipotle_df.select_dtypes(include='number').columns
chipotle_df[numeric_columns] = chipotle_df[numeric_columns].round(0).astype(int)

# Session state to persist data
if "results" not in st.session_state:
    st.session_state.results = {}

def get_chipotle_nutrition(item_name):
    match = chipotle_df[chipotle_df['Item'].str.lower() == item_name.lower()]
    return match.iloc[0].to_dict() if not match.empty else None

def calculate_total_nutrition(selected_items):
    total = {
        "Calories": 0, "Sodium (mg)": 0, "Protein (g)": 0,
        "Total Fat (g)": 0, "Saturated Fat (g)": 0, "Cholesterol (mg)": 0,
        "Carbs (g)": 0, "Fiber (g)": 0, "Sugars (g)": 0
    }
    breakdown = []
    for item in selected_items:
        chipotle_data = get_chipotle_nutrition(item)
        if chipotle_data:
            for key in total:
                total[key] += chipotle_data.get(key, 0)
            breakdown.append(chipotle_data)
    return total, breakdown

# UI
st.title("🌯 Chipotle Bowl + Fitness Analyzer")

proteins = ['None', 'chicken', 'steak', 'barbacoa', 'carnitas', 'sofritas']
grains = ['None', 'white rice', 'brown rice', '1/2 white rice and 1/2 brown rice']
beans = ['None', 'black beans', 'pinto beans', 'both beans']
toppings = [
    'cheese', 'sour cream', 'guacamole', 'queso blanco', 'fajita vegetables',
    'fresh tomato salsa', 'roasted chili-corn salsa', 'tomatillo green-chili salsa',
    'tomatillo red-chili salsa', 'romaine lettuce'
]

st.header("🍽️ Choose Ingredients")
selected_protein = st.selectbox("Choose protein:", proteins)
double_protein = st.checkbox("Double protein?")
selected_grain = st.selectbox("Choose grain:", grains)
selected_beans = st.selectbox("Choose beans:", beans)
selected_toppings = st.multiselect("Choose toppings:", toppings)

selected_items = []
if selected_protein != "None":
    selected_items.append(selected_protein)
    if double_protein:
        selected_items.append(selected_protein)
if selected_grain != "None":
    selected_items.extend(['white rice', 'brown rice'] if selected_grain == '1/2 white rice and 1/2 brown rice' else [selected_grain])
if selected_beans != "None":
    selected_items.extend(['black beans', 'pinto beans'] if selected_beans == 'both beans' else [selected_beans])
selected_items.extend(selected_toppings)

st.write(f"Meal: {', '.join(selected_items)}")

st.header("🏃 Exercise Info")
gender = st.selectbox("Sex:", ["male", "female"])
age = st.number_input("Age (years):", 10, 100, 25)
weight_lbs = st.number_input("Weight (lbs):", 50.0, 400.0, 160.0)
height_in = st.number_input("Height (inches):", 48.0, 84.0, 70.0)
exercise_query = st.text_input("What exercise did you do?", "walked for 1 hour",
                               help="Include type + duration (e.g., 'jogged 30 minutes')")

weight_kg = weight_lbs * 0.453592
height_cm = height_in * 2.54

if st.button("Calculate Nutrition + Exercise Balance"):
    meal_totals, breakdown = calculate_total_nutrition(selected_items)
    selected_df = chipotle_df[chipotle_df['Item'].str.lower().isin([i.lower() for i in selected_items])]
    numeric_cols = [
        "Calories", "Total Fat (g)", "Saturated Fat (g)", "Cholesterol (mg)",
        "Sodium (mg)", "Carbs (g)", "Fiber (g)", "Sugars (g)", "Protein (g)"
    ]
    total_row = selected_df[numeric_cols].sum().to_frame().T
    total_row.insert(0, "Serving Size", "")
    total_row.insert(0, "Item", "TOTAL")
    table_display = pd.concat([selected_df, total_row], ignore_index=True)

    # Get exercise calories
    headers = {
        "x-app-id": "df2ad93d",
        "x-app-key": "569da6e33183ab78dd6b1cc27dc6edab",
        "Content-Type": "application/json"
    }
    exercise_payload = {
        "query": exercise_query,
        "gender": gender,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "age": age
    }
    response = requests.post("https://trackapi.nutritionix.com/v2/natural/exercise", headers=headers, json=exercise_payload)
    exercise_data = response.json()

    if "exercises" in exercise_data:
        exercise_calories = sum(e["nf_calories"] for e in exercise_data["exercises"])
        net_calories = meal_totals["Calories"] - exercise_calories

        # Store session state
        st.session_state.results = {
            "meal_totals": meal_totals,
            "exercise_calories": exercise_calories,
            "net_calories": net_calories,
            "table_display": table_display
        }

# Display persistent results
if st.session_state.get("results"):
    meal_totals = st.session_state.results["meal_totals"]
    exercise_calories = st.session_state.results["exercise_calories"]
    net_calories = st.session_state.results["net_calories"]
    table_display = st.session_state.results["table_display"]

    st.subheader("🍽️ Meal Nutrition Breakdown")
    st.dataframe(
        table_display.style
        .set_properties(**{'border': '1px solid black', 'text-align': 'center'})
        .apply(lambda x: ['font-weight: bold' if x.name == len(table_display)-1 else '' for _ in x], axis=1),
        use_container_width=True
    )

    st.success(f"✅ Total Calories: {meal_totals['Calories']} | Protein: {meal_totals['Protein (g)']}g | Sodium: {meal_totals['Sodium (mg)']}mg")
    st.subheader("🔥 Exercise Output")
    st.write(f"Calories burned: {exercise_calories}")
    st.info(f"⚖️ Net Calories (Meal - Exercise): {net_calories}")
    st.markdown("🧠 _Baseline: 700 calories per meal is considered balanced._")

    diff = net_calories - 700
    if net_calories <= 700:
        st.success(f"✅ Balanced: {abs(diff)} cal under or at baseline.")
    elif net_calories <= 1000:
        st.warning(f"🟡 Mild surplus: {diff} cal over 700 baseline.")
    else:
        st.error(f"🔴 High surplus: {diff} cal over the 700-calorie mark.")

    st.subheader("📈 Weekly Calorie Projection")
    weeks = st.slider("How many weeks?", 1, 12, 4)
    frequencies = {"Once a week": 1, "3 times a week": 3, "Daily": 7}
    chart_data = []
    for label, freq in frequencies.items():
        for w in range(1, weeks + 1):
            chart_data.append({
                "Week": w,
                "Cumulative Net Calories": net_calories * freq * w,
                "Frequency": label
            })
    df_chart = pd.DataFrame(chart_data)
    st.altair_chart(
        alt.Chart(df_chart).mark_line(point=True).encode(
            x="Week", y="Cumulative Net Calories", color="Frequency",
            tooltip=["Week", "Cumulative Net Calories", "Frequency"]
        ).properties(width=700, height=350).interactive(),
        use_container_width=True
    )

    st.markdown("""
    ### 🧾 Net Calorie Thresholds
    | Category | Net Calories | Description |
    |----------|---------------|-------------|
    | ✅ Balanced | ≤ 700 | Healthy meal range |
    | 🟡 Mild Surplus | 701–1000 | Slightly over |
    | 🔴 High Surplus | > 1000 | Adjust recommended |
    """)


        


        
