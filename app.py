from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64

app = Flask(__name__)

# ============================================================
# PROVISIONAL CALIBRATION
# ============================================================

FIELD_OF_VIEW_MM = 10.0

MIN_AREA_MM2 = 0.001
MAX_AREA_MM2 = 1000.0


# ============================================================
# SEGMENTATION SETTINGS
# ============================================================

BACKGROUND_KERNEL = 101
GRAY_THRESHOLD = 12
SATURATION_THRESHOLD = 12
VALUE_THRESHOLD = 70


# ============================================================
# IMAGE ENCODING
# ============================================================

def encode_image(img):
    _, encoded = cv2.imencode(".jpg", img)
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


# ============================================================
# IMAGE PROCESSING
# ============================================================

def process_image(image_bytes):
    data = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image.")

    max_width = 1600
    original_h, original_w = img.shape[:2]

    if original_w > max_width:
        scale = max_width / original_w
        img = cv2.resize(
            img,
            (int(original_w * scale), int(original_h * scale)),
            interpolation=cv2.INTER_AREA
        )

    h, w = img.shape[:2]

    # ========================================================
    # CALIBRATION
    # ========================================================

    mm_per_pixel = FIELD_OF_VIEW_MM / w
    pixels_per_mm = w / FIELD_OF_VIEW_MM
    mm2_per_pixel = mm_per_pixel ** 2

    # ========================================================
    # STAGE 1 — ORIGINAL
    # ========================================================

    original_stage = img.copy()

    cv2.putText(
        original_stage, "1. ORIGINAL", (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
    )

    # ========================================================
    # PREPROCESSING
    # ========================================================

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # ========================================================
    # LOCAL BACKGROUND NORMALIZATION
    # ========================================================

    background = cv2.GaussianBlur(gray, (BACKGROUND_KERNEL, BACKGROUND_KERNEL), 0)
    local_contrast = cv2.subtract(background, gray)

    normalized_display = cv2.normalize(local_contrast, None, 0, 255, cv2.NORM_MINMAX)

    cv2.putText(
        normalized_display, "2. BACKGROUND NORMALIZED", (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2
    )

    # ========================================================
    # COLOR / SATURATION INFORMATION
    # ========================================================

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    color_mask = (
        (saturation > SATURATION_THRESHOLD) &
        (value > VALUE_THRESHOLD)
    )
    color_mask = color_mask.astype(np.uint8) * 255

    # ========================================================
    # GRAYSCALE CONTRAST MASK
    # ========================================================

    gray_mask = (local_contrast > GRAY_THRESHOLD).astype(np.uint8) * 255

    # ========================================================
    # COMBINE BOTH DETECTION METHODS
    # ========================================================

    binary = cv2.bitwise_or(gray_mask, color_mask)

    # ========================================================
    # REMOVE OUTSIDE OF ILLUMINATED SAMPLE AREA
    # ========================================================

    field_mask = (value > VALUE_THRESHOLD).astype(np.uint8) * 255
    field_kernel = np.ones((21, 21), np.uint8)
    field_mask = cv2.morphologyEx(field_mask, cv2.MORPH_CLOSE, field_kernel, iterations=2)

    num_field, field_labels, field_stats, _ = cv2.connectedComponentsWithStats(field_mask, connectivity=8)

    if num_field > 1:
        largest_field = 1 + np.argmax(field_stats[1:, cv2.CC_STAT_AREA])
        field_mask = (field_labels == largest_field).astype(np.uint8) * 255
        binary = cv2.bitwise_and(binary, field_mask)

    # ========================================================
    # MORPHOLOGICAL CLEANUP
    # ========================================================

    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # ========================================================
    # STAGE 3 — BINARY
    # ========================================================

    binary_display = binary.copy()

    cv2.putText(
        binary_display, "3. BINARY SEGMENTATION", (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2
    )

    # ========================================================
    # CONNECTED COMPONENT ANALYSIS
    # ========================================================

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    particles = []

    for i in range(1, num_labels):
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        width = stats[i, cv2.CC_STAT_WIDTH]
        height = stats[i, cv2.CC_STAT_HEIGHT]
        area_px = stats[i, cv2.CC_STAT_AREA]

        area_mm2 = area_px * mm2_per_pixel

        if MIN_AREA_MM2 <= area_mm2 <= MAX_AREA_MM2:
            aspect_ratio = width / max(height, 1)

            particles.append({
                "x": int(x),
                "y": int(y),
                "width": int(width),
                "height": int(height),
                "area_px": int(area_px),
                "area_mm2": round(area_mm2, 6),
                "aspect_ratio": round(aspect_ratio, 2)
            })

    # ========================================================
    # STAGE 4 — FINAL DETECTIONS
    # ========================================================

    output = img.copy()

    for idx, particle in enumerate(particles, start=1):
        x = particle["x"]
        y = particle["y"]
        pw = particle["width"]
        ph = particle["height"]
        area_mm2 = particle["area_mm2"]

        cv2.rectangle(output, (x, y), (x + pw, y + ph), (0, 255, 0), 2)
        cv2.putText(output, str(idx), (x, max(y - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(output, f"{area_mm2:.4f} mm2", (x, min(y + ph + 15, h - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    cv2.putText(output, f"Particles: {len(particles)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(output, f"FOV: ~{FIELD_OF_VIEW_MM:.1f} mm", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(output, f"Scale: ~{pixels_per_mm:.1f} px/mm", (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    return {
        "count": len(particles),
        "particles": particles,
        "width": w,
        "height": h,
        "field_of_view_mm": FIELD_OF_VIEW_MM,
        "pixels_per_mm": round(pixels_per_mm, 3),
        "mm_per_pixel": round(mm_per_pixel, 6),
        "original": encode_image(original_stage),
        "normalized": encode_image(normalized_display),
        "binary": encode_image(binary_display),
        "detections": encode_image(output)
    }


# ============================================================
# WEBPAGE & ENDPOINTS
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    file = request.files["image"]

    try:
        result = process_image(file.read())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
