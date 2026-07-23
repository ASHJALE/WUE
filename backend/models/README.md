# WUE Furniture Classifier

The runtime supports one local format: ONNX. Place a legitimate five-class model
at `backend/models/furniture_classifier.onnx`, or set a relative
`FURNITURE_MODEL_PATH` that remains inside `backend/models/`. Upload paths are
never accepted as model locations.

The output order is:

1. `bed`
2. `chair`
3. `sofa`
4. `dining_table`
5. `lamp_shade`

The model must accept one RGB `float32` tensor shaped `1 x 3 x 224 x 224`.
Images are EXIF-oriented, center-cropped, scaled to `[0, 1]`, and normalized
with ImageNet mean and standard deviation. Configure whether output is logits
with `FURNITURE_MODEL_OUTPUT_IS_LOGITS`.

ONNX Runtime is intentionally not installed automatically. After approval,
install a CPU-compatible `onnxruntime` version and record its pinned version in
`backend/requirements.txt`.

If the artifact or runtime is absent, classification returns a controlled 503.
The optional development fallback requires
`FURNITURE_DEVELOPMENT_FALLBACK_ENABLED=true`; it is not trained and is disabled
by default.

The confidence threshold defaults to `0.50`. UI labels use low (`<0.50`),
moderate (`0.50–0.79`), and high (`>=0.80`) confidence.

**The AI prediction is advisory and requires user confirmation.**
