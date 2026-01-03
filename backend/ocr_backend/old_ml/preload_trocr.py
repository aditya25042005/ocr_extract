from transformers import TrOCRProcessor, VisionEncoderDecoderModel

processor = TrOCRProcessor.from_pretrained(
    "microsoft/trocr-large-handwritten",
    cache_dir="./model_cache"
)

model = VisionEncoderDecoderModel.from_pretrained(
    "microsoft/trocr-large-handwritten",
    cache_dir="./model_cache"
)
