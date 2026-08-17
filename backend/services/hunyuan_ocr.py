"""
HunyuanOCR correct integration — ADD this to services/ocr_service.py

Correct tier order (as per your spec):
  Docling → Qwen-VL → HunyuanOCR → PaddleOCR → Tesseract

Install:
  pip install transformers torch pillow huggingface_hub

DO NOT use .predict() — HunyuanOCR uses AutoProcessor + model.generate()
"""

from pathlib import Path
import structlog
log = structlog.get_logger()

# ── HunyuanOCR (correct implementation) ───────────────────────────
def hunyuan_ocr_extract(image_path: str) -> str:
    """
    Extract text from image using HunyuanOCR (Tencent).
    Model: tencent/HunyuanOCR on HuggingFace (~2GB download on first run).
    Uses AutoProcessor + generate() — NOT .predict() (that crashes).
    """
    try:
        import torch
        from PIL import Image
        from transformers import AutoProcessor, AutoModelForVision2Seq

        log.info("hunyuan_ocr.loading")
        processor = AutoProcessor.from_pretrained(
            "tencent/HunyuanOCR", trust_remote_code=True
        )
        model = AutoModelForVision2Seq.from_pretrained(
            "tencent/HunyuanOCR",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
        )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()

        image = Image.open(image_path).convert("RGB")

        # Correct API: use processor + generate
        prompt = "Extract all text from this image accurately."
        inputs = processor(images=image, text=prompt, return_tensors="pt").to(device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=2048,
                do_sample=False,
            )
        result = processor.decode(output_ids[0], skip_special_tokens=True)
        log.info("hunyuan_ocr.success", chars=len(result))
        return result.strip()

    except Exception as e:
        log.warning("hunyuan_ocr.failed", error=str(e))
        return ""


# ── How to wire into your existing ocr_service.py ─────────────────
"""
In your existing extract_text_from_image() or equivalent function,
replace the old tier logic with:

def extract_text_from_image(image_path: str) -> str:
    # Tier 1: Qwen-VL (your existing vision model via OpenRouter)
    text = qwen_vl_extract(image_path)
    if text and len(text) > 50:
        return text

    # Tier 2: HunyuanOCR (add this)
    text = hunyuan_ocr_extract(image_path)
    if text and len(text) > 50:
        return text

    # Tier 3: PaddleOCR (your existing)
    text = paddle_ocr_extract(image_path)
    if text and len(text) > 50:
        return text

    # Tier 4: Tesseract (your existing fallback)
    return tesseract_extract(image_path)

For full PDF pipeline:
  Docling (layout-aware) → above image tier for scanned pages
"""
