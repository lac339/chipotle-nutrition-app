import streamlit as st
import pandas as pd
import requests
import altair as alt
import base64
from collections import Counter

# Optional: background image using hosted image
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("https://media.yourobserver.com/img/photos/2023/01/26/Chipotle_r850x580.jpeg?50e13880ccc54d977011a5484f156b28f4611466");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Load and round Chipotle nutrition data
chipotle_df = pd.read_csv("chipotle_nutrition_2025_complete.csv")
numeric_columns = chipotle_df.select_dtypes(include='number').columns
chipotle_df[numeric_columns] = chipotle_df[numeric_columns].round(0).astype(int)

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

from calories_burned import burned_calories

def calories_burned_local(activity, weight_kg, duration_min):
    try:
        return burned_calories(
            activity=activity,
            weight_kg=weight_kg,
            duration_minutes=duration_min
        )
    except Exception:
        return 3.5 * weight_kg * (duration_min / 60)

# UI
st.title("\U0001F32F Chipotle Bowl + Fitness Analyzer")

proteins = ['None', 'chicken', 'steak', 'barbacoa', 'carnitas', 'sofritas']
grains = ['None', 'white rice', 'brown rice', '1/2 white rice and 1/2 brown rice']
beans = ['None', 'black beans', 'pinto beans', 'both beans']
toppings = [
    'cheese', 'sour cream', 'guacamole', 'queso blanco', 'fajita vegetables',
    'fresh tomato salsa', 'roasted chili-corn salsa', 'tomatillo green-chili salsa',
    'tomatillo red-chili salsa', 'romaine lettuce'
]

st.header("\U0001F37D\ufe0f Choose Ingredients")
selected_protein = st.selectbox("Choose protein:", proteins)
double_protein = False
if selected_protein != "None":
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

st.header("\U0001F3C3 Exercise Info")
gender = st.selectbox("Sex:", ["male", "female"])
age = st.number_input("Age (years):", 10, 100, 25)
weight_lbs = st.number_input("Weight (lbs):", 50.0, 400.0, 160.0)
height_in = st.number_input("Height (inches):", 48.0, 84.0, 70.0)
exercise_query = st.text_input("What exercise did you do?", "walked for 1 hour")

weight_kg = weight_lbs * 0.453592
height_cm = height_in * 2.54

if st.button("Calculate Nutrition + Exercise Balance"):
    meal_totals, breakdown = calculate_total_nutrition(selected_items)

    item_counts = Counter(selected_items)
    seen = Counter()
    display_labels = []
    for item in selected_items:
        seen[item] += 1
        if item_counts[item] > 1:
            display_labels.append(f"{item} x{seen[item]}")
        else:
            display_labels.append(item)

    selected_df = pd.DataFrame([
        chipotle_df[chipotle_df['Item'].str.lower() == item.lower()].iloc[0].copy()
        for item in selected_items
        if not chipotle_df[chipotle_df['Item'].str.lower() == item.lower()].empty
    ])
    selected_df["Item"] = display_labels

    numeric_cols = [
        "Calories", "Protein (g)", "Sodium (mg)", "Fiber (g)", "Cholesterol (mg)",
        "Total Fat (g)", "Saturated Fat (g)", "Carbs (g)", "Sugars (g)"
    ]
    total_row = selected_df[numeric_cols].sum().to_frame().T
    total_row.insert(0, "Serving Size", "")
    total_row.insert(0, "Item", "TOTAL")
    table_display = pd.concat([selected_df, total_row], ignore_index=True)

    st.subheader("🍽️ Meal Nutrition Breakdown")
    st.dataframe(table_display, use_container_width=True)
    st.success(f"✅ Total Calories: {meal_totals['Calories']} | Protein: {meal_totals['Protein (g)']}g | Sodium: {meal_totals['Sodium (mg)']}mg")

    # Nutritionix NLP
    headers = {
        "x-app-id": "your-app-id",
        "x-app-key": "your-app-key",
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
    fallback_duration = 60

    if response.status_code == 200 and "exercises" in exercise_data and len(exercise_data["exercises"]) > 0:
        exercise = exercise_data["exercises"][0]
        duration = exercise.get("duration_min", fallback_duration)
        exercise_calories_nlp = sum(e.get("nf_calories", 0) for e in exercise_data["exercises"])
        exercise_calories = exercise_calories_nlp
        net_calories = meal_totals["Calories"] - exercise_calories
    else:
        duration = fallback_duration
        exercise_calories = calories_burned_local(exercise_query, weight_kg, duration)
        net_calories = meal_totals["Calories"] - exercise_calories

    st.session_state["net_calories"] = net_calories
    st.session_state["meal_totals"] = meal_totals
    st.session_state["table_display"] = table_display

    st.subheader("🔥 Exercise Output")
    st.write(f"Calories burned: {exercise_calories}")
    st.info(f"Net Calories: {net_calories}")

# Weekly projection chart persists after slider interaction
if "net_calories" in st.session_state and "meal_totals" in st.session_state:
    st.subheader("\U0001F4C8 Weekly Calorie Projection")
    weeks = st.slider("How many weeks?", 1, 12, 4)
    frequencies = {"Once a week": 1, "3 times a week": 3, "Daily": 7}

    projected_net = st.session_state["net_calories"]
    chart_data = []
    for label, freq in frequencies.items():
        for w in range(1, weeks + 1):
            chart_data.append({
                "Week": w,
                "Cumulative Net Calories": projected_net * freq * w,
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
    ### 🔏 Net Calorie Thresholds
    | Category | Net Calories | Description |
    |----------|---------------|-------------|
    | ✅ Balanced | ≤ 700 | Healthy meal range |
    | 🟡 Mild Surplus | 701–1000 | Slightly over |
    | 🔴 High Surplus| > 1000 | Adjust recommended |
    """)
