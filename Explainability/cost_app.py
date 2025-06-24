from flask import Flask, request, jsonify, render_template
import numpy as np
import pandas as pd
import shap
import lime.lime_tabular
import joblib

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("expected_cost.html")

pipeline = joblib.load("cost_band_pipeline.pkl")
model_only = pipeline.named_steps["model"]
preprocessor = pipeline[:-1]

X_train = pd.read_csv("X_train.csv")  # !! should match training data used in pipeline

categorical_columns = [
    "Risc", "Tipus de praxi", "Centre docent", "Àmbit",
    "Especialitat", "Codi diagnòstic"
]

cost_bands = [
    (0, 25000),
    (25001, 50000),
    (50001, 150000),
    (150001, 300000),
    (300001, None)
]

X_train_transformed = preprocessor.transform(X_train)

@app.route("/api/predict", methods=["POST"])
def predict():
    input_data = request.json["features"]
    x_raw = pd.DataFrame([input_data])

    x_transformed = preprocessor.transform(x_raw)

    proba = model_only.predict_proba(x_transformed)[0]
    band = int(np.argmax(proba))
    confidence = float(proba[band])
    min_cost, max_cost = cost_bands[band]

    feature_names = preprocessor.get_feature_names_out()

    # SHAP explanation
    explainer = shap.TreeExplainer(model_only)
    shap_values = explainer.shap_values(x_transformed)
    try:
        if isinstance(shap_values, list) and len(shap_values) > band:
            shap_class_values = shap_values[band][0]
        else:
            print(f"[SHAP WARNING] Falling back to generic SHAP output: shape={np.shape(shap_values)}")
            shap_class_values = shap_values[0] if len(shap_values.shape) == 2 else shap_values[0][0]
    except Exception as e:
        print(f"[SHAP ERROR] Could not extract SHAP class values: {e}")
        shap_class_values = np.zeros(len(feature_names))
    
    top_shap = sorted(
        zip(feature_names, shap_class_values),
        key=lambda x: abs(x[1]),
        reverse=True
    )[:5]
    shap_summary = [f"{feat}: {val:+.2f}" for feat, val in top_shap]

    # LIME explanation
    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=X_train_transformed,
        feature_names=feature_names,
        class_names = [str(cls) for cls in model_only.classes_],
        mode="classification"
    )
    lime_exp = lime_explainer.explain_instance(
        x_transformed[0],
        model_only.predict_proba,
        num_features=5
    )
    lime_summary = [f"{f}: {w:+.2f}" for f, w in lime_exp.as_list()]

    return jsonify({
        "band": band,
        "confidence": round(confidence * 100, 1),
        "min_cost": min_cost,
        "max_cost": max_cost,
        "shap": shap_summary,
        "lime": lime_summary
    })

if __name__ == "__main__":
    app.run(debug=True)
