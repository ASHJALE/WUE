# Offline Furniture Classifier Training Preparation

No dataset or trained artifact is included. Training must be performed offline
with a reviewed dataset and an explicitly selected framework.

Expected structure:

```text
dataset/
  train/{bed,chair,sofa,dining_table,lamp_shade}/
  validation/{bed,chair,sofa,dining_table,lamp_shade}/
  test/{bed,chair,sofa,dining_table,lamp_shade}/
```

Future training should use deterministic seeds, preserve the label order in
`backend/app/ai/labels.py`, save evaluation metrics and a confusion matrix, and
export a `1 x 5` ONNX output compatible with `backend/models/README.md`.
Datasets must not be downloaded automatically or committed to this repository.

Before an artifact is released, report test-set size, accuracy, per-class
precision/recall/F1, confusion matrix, model version, and CPU inference time.
