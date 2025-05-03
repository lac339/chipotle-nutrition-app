import streamlit as st
import requests
import pandas as pd

# Inject custom background image and apply a white overlay and black text
page_bg_img = f'''
<style>
.stApp {{
    background-image: url("https://imageio.forbes.com/specials-images/imageserve/1212846835/0x0.jpg?format=jpg&width=1200");
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}

html, body, [class*="css"]  {{
    background-color: rgba(255, 255, 255, 0.8);
    color: #111111;
    font-family: 'Arial', sans-serif;
}}

button[kind="primary"] {{
    background-color: #ffffff !important;
    color: #111111 !important;
    border: 1px solid #ccc;
}}
</style>
'''
st.markdown(page_bg_img, unsafe_allow_html=True)

# Nutritionix API credentials
APP_ID = "df2ad93d"
API_KEY = "569da6e33183ab78dd6b1cc27dc6edab"
headers = {
    "x-app-id": APP_ID,
    "x-app-key": API_KEY,
    "Content-Type": "application/json"
}

# Sanitized Chipotle items (mapped exactly to Nutritionix-friendly terms)
item_mapping = {
    'chicken': 'chipotle chicken',
    'steak': 'chipotle steak',
    'barbacoa': 'chipotle barbacoa',
    'carnitas': 'chipotle carnitas',
    'sofritas': 'chipotle sofritas',
    'white rice': 'chipotle white rice',
    'brown rice': 'chipotle brown rice',
    '1/2 white rice and 1/2 brown rice': 'chipotle white rice, chipotle brown rice',
    'black beans': 'chipotle black beans',
    'pinto beans': 'chipotle pinto beans',
    'both beans': 'chipotle black beans, chipotle pinto beans',
    'cheese': 'chipotle cheese',
    'sour cream': 'chipotle sour cream',
    'lettuce': 'chipotle romaine lettuce',
    'guacamole': 'chipotle guacamole',
    'fresh tomato salsa': 'chipotle fresh tomato salsa',
    'roasted chili-corn salsa': 'chipotle roasted chili-corn salsa',
    'tomatillo-green chili salsa': 'chipotle tomatillo green chili salsa',
    'tomatillo-red chili salsa': 'chipotle tomatillo red chili salsa',
    'fajita veggies': 'chipotle fajita vegetables',
    'queso blanco': 'chipotle queso blanco'
}

proteins = ['None', 'chicken', 'steak', 'barbacoa', 'carnitas', 'sofritas']
grains = ['None', 'white rice', 'brown rice', '1/2 white rice and 1/2 brown rice']
beans = ['None', 'black beans', 'pinto beans', 'both beans']
toppings = list(item_mapping.keys())[12:]  # start at cheese

st.title("🌯 Build Your Chipotle Bowl + Workout Tracker")

st.header("🍽️ Choose Your Ingredients")
selected_protein = st.selectbox("Choose your protein:", proteins)
double_protein = st.checkbox("Double protein?")
selected_grain = st.selectbox("Choose your grain:", grains)
selected_beans = st.selectbox("Choose your beans:", beans)
selected_toppings = st.multiselect("Choose your toppings:", toppings)

query_parts = []
if selected_protein != "None":
    mapped = item_mapping[selected_protein]
    query_parts.append(mapped)
    if double_protein:
        query_parts.append(mapped)
if selected_grain != "None":
    for grain in item_mapping[selected_grain].split(","):
        query_parts.append(grain.strip())
if selected_beans != "None":
    for bean in item_mapping[selected_beans].split(","):
        query_parts.append(bean.strip())
for topping in selected_toppings:
    query_parts.append(item_mapping[topping])

query = ", ".join(query_parts)
st.write(f"Meal: {query if query else 'None selected'}")

st.header("🏃 Enter Your Exercise Info")
gender = st.selectbox("Sex:", ["None", "male", "female"])
age = st.number_input("Age (years):", min_value=10, max_value=100, value=25)
weight_lbs = st.number_input("Weight (lbs):", min_value=50.0, max_value=400.0, value=160.0)
height_in = st.number_input("Height (inches):", min_value=48.0, max_value=84.0, value=70.0)
exercise_query = st.text_input("What exercise did you do?", "walked for 1 hour")

st.header("🎯 Set Your Nutrition Targets")
target_calories = 700
target_protein = st.slider("Target Protein (grams):", min_value=10, max_value=100, value=30, step=5)
st.markdown("_We use 700 calories as a general benchmark for a balanced meal. A slight surplus isn’t bad — it depends on your activity level and goals._")

weight_kg = weight_lbs * 0.453592
height_cm = height_in * 2.54

if st.button("Calculate Nutrition + Exercise Balance"):
    if not query:
        st.error("❌ Please select at least one ingredient for your bowl.")
    elif gender == "None":
        st.error("❌ Please select your biological sex.")
    else:
        nutrition_url = "https://trackapi.nutritionix.com/v2/natural/nutrients"
        response = requests.post(nutrition_url, headers=headers, json={"query": query})
        data = response.json()

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

        if "foods" in data:
            calories = sum(f["nf_calories"] for f in data["foods"])
            protein = sum(f["nf_protein"] for f in data["foods"])
            sodium = sum(f["nf_sodium"] for f in data["foods"])

            st.success(f"🍽️ Meal: {calories:.0f} calories | Protein: {protein:.1f} g | Sodium: {sodium:.0f} mg")

            st.subheader("🔍 Nutrition Breakdown by Item")
            for f in data["foods"]:
                st.write(f"{f['food_name'].title()}: {f['nf_calories']} cal, {f['nf_sodium']} mg sodium, {f['nf_protein']} g protein")
                if f["nf_sodium"] > 1500:
                    st.warning(f"⚠️ '{f['food_name'].title()}' contains over 1,500 mg of sodium. Consider reviewing this ingredient.")

            if protein < target_protein:
                st.warning(f"💪 Protein is below your target by {target_protein - protein:.1f} g")

            if "exercises" in exercise_data:
                exercise_calories = sum(e["nf_calories"] for e in exercise_data["exercises"])
                st.success(f"🔥 Calories burned through exercise: {exercise_calories:.0f} calories")

                net_calories = calories - exercise_calories
                st.info(f"⚖️ Net Calories (meal - exercise): {net_calories:.0f} calories")

                net_vs_target = net_calories - target_calories
                if net_calories <= 700:
                    st.success(f"✅ You're within the balanced 700-calorie range. You are {abs(net_vs_target):.0f} calories {'under' if net_vs_target < 0 else 'at'} the target.")
                elif net_calories > 700 and net_calories <= 1000:
                    st.warning(f"🟡 Mild surplus — {net_vs_target:.0f} calories over the 700-calorie baseline.")
                else:
                    st.error(f"🔴 Significant surplus — {net_vs_target:.0f} calories over the 700-calorie baseline. Consider adjusting.")
            else:
                st.error("⚠️ Could not calculate exercise info. Please check your activity description.")
        else:
            st.error(f"⚠️ Could not fetch nutrition info. API said: {data.get('message', 'Unknown error')}")

        st.markdown("---")
        st.subheader("📊 Surplus Feedback Thresholds")
        df = pd.DataFrame({
            "Net Calories": ["≤ 700", "701 – 1000", "> 1000"],
            "Feedback": [
                "✅ Balanced — within target range",
                "🟡 Mild surplus — monitor",
                "🔴 Significant surplus — adjust"
            ]
        })
        st.table(df)
