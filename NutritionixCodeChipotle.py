import streamlit as st
import pandas as pd
import requests

# Load official Chipotle nutrition data from CSV
chipotle_df = pd.read_csv("chipotle_nutrition_2025_complete.csv")

def get_chipotle_nutrition(item_name):
    match = chipotle_df[chipotle_df['Item'].str.lower() == item_name.lower()]
    if not match.empty:
        return match.iloc[0].to_dict()
    return None

def calculate_total_nutrition(selected_items):
    total = {"Calories": 0, "Sodium (mg)": 0, "Protein (g)": 0}
    breakdown = []
    for item in selected_items:
        chipotle_data = get_chipotle_nutrition(item)
        if chipotle_data:
            total["Calories"] += chipotle_data["Calories"]
            total["Sodium (mg)"] += chipotle_data["Sodium (mg)"]
            total["Protein (g)"] += chipotle_data["Protein (g)"]
            breakdown.append((item.title(), chipotle_data["Calories"], chipotle_data["Sodium (mg)"], chipotle_data["Protein (g)"]))
    return total, breakdown

# Inject background
st.markdown('''<style>.stApp {
background-image: url("https://c8.alamy.com/comp/2M79TT2/chipotle-mexican-grill-rotated-logo-black-background-2M79TT2.jpg");
background-size: cover; background-repeat: no-repeat; background-attachment: fixed;
}</style>''', unsafe_allow_html=True)

# Ingredient categories
proteins = ['None', 'chicken', 'steak', 'barbacoa', 'carnitas', 'sofritas']
grains = ['None', 'white rice', 'brown rice', '1/2 white rice and 1/2 brown rice']
beans = ['None', 'black beans', 'pinto beans', 'both beans']
toppings = [
    'cheese', 'sour cream', 'guacamole', 'queso blanco', 'fajita vegetables', 'fresh tomato salsa',
    'roasted chili-corn salsa', 'tomatillo green-chili salsa', 'tomatillo red-chili salsa', 'romaine lettuce'
]

st.title("🌯 Build Your Chipotle Bowl + Workout Tracker")

st.header("🍽️ Choose Your Ingredients")
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

st.header("🏃 Enter Your Exercise Info")
gender = st.selectbox("Sex:", ["male", "female"])
age = st.number_input("Age (years):", min_value=10, max_value=100, value=25)
weight_lbs = st.number_input("Weight (lbs):", min_value=50.0, max_value=400.0, value=160.0)
height_in = st.number_input("Height (inches):", min_value=48.0, max_value=84.0, value=70.0)
exercise_query = st.text_input("What exercise did you do?", "walked for 1 hour", help="Please include the activity and duration (e.g., 'ran 30 minutes', 'yoga 1 hour')")

weight_kg = weight_lbs * 0.453592
height_cm = height_in * 2.54

if st.button("Calculate Nutrition + Exercise Balance"):
    if not selected_items:
        st.error("❌ Please select at least one ingredient for your bowl.")
    elif gender == "None":
        st.error("❌ Please select your biological sex.")
    else:
        # Get nutrition totals from Chipotle CSV
        meal_totals, breakdown = calculate_total_nutrition(selected_items)

        st.subheader("🍽️ Chipotle Meal Nutrition")
        for name, cal, sodium, protein in breakdown:
            st.write(f"{name}: {cal} cal, {sodium} mg sodium, {protein} g protein")

        st.success(f"Total: {meal_totals['Calories']} cal | Sodium: {meal_totals['Sodium (mg)']} mg | Protein: {meal_totals['Protein (g)']} g")

        # Get exercise calories from Nutritionix
        headers = {
            "x-app-id": "df2ad93d",
            "x-app-key": "569da6e33183ab78dd6b1cc27dc6edab",
            "Content-Type": "application/json"
        }
        exercise_url = "https://trackapi.nutritionix.com/v2/natural/exercise"
        exercise_payload = {
            "query": exercise_query,
            "gender": gender,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "age": age
        }
        exercise_response = requests.post(exercise_url, headers=headers, json=exercise_payload)
        exercise_data = exercise_response.json()

        if "exercises" in exercise_data:
            exercise_calories = sum(e["nf_calories"] for e in exercise_data["exercises"])
            net_calories = meal_totals["Calories"] - exercise_calories

            st.subheader("🔥 Exercise Output")
            st.write(f"Calories burned: {exercise_calories:.0f}")
            st.info(f"⚖️ Net Calories (Meal - Exercise): {net_calories:.0f}")

            # Altair chart: Projected net calorie accumulation
            import altair as alt
            st.subheader("📈 Projected Net Calories Over Time")
            frequency = st.selectbox("How often would you eat this meal?", ["Once a week", "3 times a week", "Daily"])
            weeks = st.slider("Over how many weeks?", 1, 12, 4)

            if frequency == "Once a week":
                times_per_week = 1
            elif frequency == "3 times a week":
                times_per_week = 3
            else:
                times_per_week = 7

            weekly_net_cal = net_calories * times_per_week
            net_cal_list = [weekly_net_cal * i for i in range(1, weeks + 1)]
            chart_df = pd.DataFrame({"Week": list(range(1, weeks + 1)), "Cumulative Net Calories": net_cal_list})

            calorie_chart = alt.Chart(chart_df).mark_line(point=True).encode(
                x="Week",
                y="Cumulative Net Calories",
                tooltip=["Week", "Cumulative Net Calories"]
            ).properties(
                width=600,
                height=300
            ).interactive()

            st.altair_chart(calorie_chart, use_container_width=True)

            diff = net_calories - 700
            if net_calories <= 700:
                st.success(f"✅ Balanced meal. You are {abs(diff)} calories {'under' if diff < 0 else 'at'} the 700-calorie baseline.")
            elif net_calories <= 1000:
                st.warning(f"🟡 Mild surplus — {diff} calories over the target.")
            else:
                st.error(f"🔴 Significant surplus — {diff} calories over the 700-calorie mark.")

            st.markdown("""
            ### 🧾 Net Calorie Thresholds Table
            | Category | Net Calories | Description |
            |----------|---------------|-------------|
            | ✅ Balanced | ≤ 700 | Healthy, within standard meal range |
            | 🟡 Mild Surplus | 701–1000 | Slightly over — okay depending on your goals |
            | 🔴 High Surplus | > 1000 | Exceeds typical meal target — adjust suggested |
            """)

        
