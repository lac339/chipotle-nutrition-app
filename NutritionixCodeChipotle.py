#Section 1: Imports and Data Load
import streamlit as st
import pandas as pd
import requests
from calories_burned import burned_calories  # New: validation package

# Load official Chipotle nutrition data from CSV
chipotle_df = pd.read_csv("chipotle_nutrition_2025_complete.csv")

def get_chipotle_nutrition(item_name):
    match = chipotle_df[chipotle_df['Item'].str.lower() == item_name.lower()]
    if not match.empty:
        return match.iloc[0].to_dict()
    return None

def calculate_total_nutrition(selected_items):
    total = {
        "Calories": 0, "Total Fat (g)": 0, "Saturated Fat (g)": 0, "Cholesterol (mg)": 0,
        "Sodium (mg)": 0, "Carbs (g)": 0, "Fiber (g)": 0, "Sugars (g)": 0, "Protein (g)": 0
    }
    breakdown = []
    for item in selected_items:
        data = get_chipotle_nutrition(item)
        if data:
            for key in total:
                total[key] += round(data.get(key, 0))
            breakdown.append({
                "Item": item.title(),
                **{k: round(data.get(k, 0)) for k in total}
            })
    return total, pd.DataFrame(breakdown)

#Section 2: UI Setup and Background
# Custom background
st.markdown('''<style>.stApp {
background-image: url("https://c8.alamy.com/comp/2M79TT2/chipotle-mexican-grill-rotated-logo-black-background-2M79TT2.jpg");
background-size: cover; background-repeat: no-repeat; background-attachment: fixed;
}</style>''', unsafe_allow_html=True)

st.title("🌯 Build Your Chipotle Bowl + Workout Tracker")

# Section 3: Ingredient Selection
# Ingredient categories
proteins = ['None', 'chicken', 'steak', 'barbacoa', 'carnitas', 'sofritas']
grains = ['None', 'white rice', 'brown rice', '1/2 white rice and 1/2 brown rice']
beans = ['None', 'black beans', 'pinto beans', 'both beans']
toppings = [
    'cheese', 'sour cream', 'guacamole', 'queso blanco', 'fajita vegetables', 'fresh tomato salsa',
    'roasted chili-corn salsa', 'tomatillo green-chili salsa', 'tomatillo red-chili salsa', 'romaine lettuce'
]

selected_protein = st.selectbox("Choose your protein:", proteins)
double_protein = st.checkbox("Double protein?")
selected_grain = st.selectbox("Choose your grain:", grains)
selected_beans = st.selectbox("Choose your beans:", beans)
selected_toppings = st.multiselect("Choose your toppings:", toppings)

selected_items = []
if selected_protein != "None":
    selected_items.append(selected_protein)
    if double_protein:
        selected_items.append(selected_protein)
if selected_grain != "None":
    if selected_grain == '1/2 white rice and 1/2 brown rice':
        selected_items.extend(['white rice', 'brown rice'])
    else:
        selected_items.append(selected_grain)
if selected_beans != "None":
    if selected_beans == 'both beans':
        selected_items.extend(['black beans', 'pinto beans'])
    else:
        selected_items.append(selected_beans)
selected_items.extend(selected_toppings)

st.write(f"Meal: {', '.join(selected_items) if selected_items else 'None selected'}")

#Section 4: Exercise Parameters
st.header("🏃 Enter Your Exercise Info")
gender = st.selectbox("Sex:", ["male", "female"])
age = st.number_input("Age (years):", min_value=10, max_value=100, value=25)
weight_lbs = st.number_input("Weight (lbs):", min_value=50.0, max_value=400.0, value=160.0)
height_in = st.number_input("Height (inches):", min_value=48.0, max_value=84.0, value=70.0)
exercise_query = st.text_input(
    "What exercise did you do?",
    "ran for 45 minutes",
    help="Please include activity and duration (e.g., 'ran 45 minutes', 'swam 1 hour')"
)

# Convert units for API + validation
weight_kg = weight_lbs * 0.453592
height_cm = height_in * 2.54

# Section 5: if st.button("Calculate Nutrition + Exercise Balance"):
if not selected_items:
        st.error("❌ Please select at least one ingredient.")
    else:
        # Nutrition totals
        meal_totals, breakdown_df = calculate_total_nutrition(selected_items)

        st.subheader("🍽️ Meal Nutrition Breakdown")
        st.dataframe(breakdown_df.style.set_properties(**{
            'border': '1px solid black', 'font-weight': 'bold'
        }))

        st.success(
            f"Total: {meal_totals['Calories']} cal | "
            f"Sodium: {meal_totals['Sodium (mg)']} mg | "
            f"Protein: {meal_totals['Protein (g)']} g"
        )

        # Nutritionix API call for exercise
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
        response = requests.post(
            "https://trackapi.nutritionix.com/v2/natural/exercise",
            headers=headers, json=exercise_payload
        )
        exercise_data = response.json()

        if "exercises" in exercise_data:
            activity = exercise_data["exercises"][0]
            duration = activity["duration_min"]
            activity_name = activity["name"]

            # Get Nutritionix + validated values
            nutritionix_cals = sum(e["nf_calories"] for e in exercise_data["exercises"])
            validated_cals = burned_calories(activity_name, weight_kg=weight_kg, duration_min=duration)

            st.subheader("🔥 Exercise Output")
            st.write(f"Calories burned (Nutritionix): {round(nutritionix_cals)} cal")
            st.write(f"Calories burned (Validated via `calories-burned`): {round(validated_cals)} cal")

            net_nutritionix = meal_totals["Calories"] - nutritionix_cals
            net_validated = meal_totals["Calories"] - validated_cals

            st.info(f"Net Calories (Nutritionix): {round(net_nutritionix)}")
            st.info(f"Net Calories (Validated): {round(net_validated)}")
        else:
            st.error("⚠️ Could not process exercise input. Try rephrasing.")

#Section 6: Altair Chart
import altair as alt

st.subheader("📈 Cumulative Net Calories Over Time")

weeks = st.slider("How many weeks do you want to project?", 1, 12, 4)

frequencies = {
    "Once a week": 1,
    "3x per week": 3,
    "Daily": 7
}

all_rows = []
for label, freq in frequencies.items():
    weekly_total = net_validated * freq
    for wk in range(1, weeks + 1):
        all_rows.append({
            "Week": wk,
            "Cumulative Net Calories": weekly_total * wk,
            "Frequency": label
        })

chart_df = pd.DataFrame(all_rows)

chart = alt.Chart(chart_df).mark_line(point=True).encode(
    x="Week:O",
    y="Cumulative Net Calories:Q",
    color="Frequency:N",
    tooltip=["Week", "Cumulative Net Calories", "Frequency"]
).properties(
    width=600,
    height=300
).interactive()

st.altair_chart(chart, use_container_width=True)
