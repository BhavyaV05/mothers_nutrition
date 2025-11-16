// In static/js/doctor_form.js (a new file)

document.addEventListener("DOMContentLoaded", function() {

    const selector = document.getElementById("preset-selector");

    selector.addEventListener("change", function() {
        const selectedKey = selector.value;
        if (!selectedKey) {
            return;
        }

        // Get the preset data object
        const preset = PRESETS[selectedKey];
        if (!preset) {
            return;
        }

        // --- 1. Set the Plan Title ---
        document.getElementById("plan_title").value = preset.title;

        // --- 2. Set all nutrient fields ---
        
        // Get the nutrients object (e.g., preset.required_nutrients)
        const nutrients = preset.required_nutrients;

        // Loop over each meal type (e.g., "breakfast", "lunch", "dinner")
        for (const mealType in nutrients) {
            
            // Loop over each nutrient (e.g., "kcal", "protein")
            for (const nutrientName in nutrients[mealType]) {
                
                // Build the input ID (e.g., "breakfast-kcal")
                const inputId = `${mealType}-${nutrientName}`;
                
                const inputElement = document.getElementById(inputId);
                
                if (inputElement) {
                    // Set the value
                    inputElement.value = nutrients[mealType][nutrientName];
                } else {
                    console.warn("Could not find input element for:", inputId);
                }
            }
        }
    });
});