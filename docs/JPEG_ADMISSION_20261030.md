# JPEG color admission correction

A real poster-collection request exposed a CMYK JPEG decode failure on the strict CUDA JPEG path. Ordinary RGB/grayscale JPEG admission is unchanged. CMYK is now rejected explicitly before CUDA decode (the API maps ValueError to 422), rather than relying on the GPU decoder's runtime failure. Clients must convert CMYK to RGB explicitly. The private collection client was corrected to transcode CMYK to RGB while preserving source bytes and recording staging metadata; its previously failing image completed full-frame plus four detail GPU OCR requests.

This client conversion is CPU staging and is not included in GPU-only UI OCR timing claims. No new throughput claim is made. The source admission fix passes regression tests; it was not hot-patched into the already-running Kaggle version6 process. Future deployments include it.

Gateway controller regression: 79 passed, 1 skipped (optional ONNX graph dependency unavailable).
