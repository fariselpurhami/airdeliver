import os
from huggingface_hub import snapshot_download, login

# 🔐 1. إعدادات الموديل والتوكن
MODEL_ID = "nvidia/personaplex-7b-v1"
# تأكد إن المسار ده مطابق للـ Volume اللي في الدوكر
LOCAL_DIR = "./data/storage/models_cache/huggingface/personaplex-7b-v1" 

# 🔑 2. التوكن (مهم جداً للموديلات المحمية)
# ممكن تحطه هنا مباشرة أو تقرأه من الـ Environment Variables
HF_TOKEN = os.getenv("HF_TOKEN") 

if not HF_TOKEN:
    print("❌ Error: HF_TOKEN is missing. Please set it or login.")
    exit(1)

print(f"🔐 Authenticating with Hugging Face...")
login(token=HF_TOKEN)

print(f"🚀 Initiating Titanium Download for: {MODEL_ID}")
print(f"📂 Storage Path: {LOCAL_DIR}")

try:
    # 3. بدء التحميل
    path = snapshot_download(
        repo_id=MODEL_ID,
        local_dir=LOCAL_DIR,      # التحميل في مجلد محدد
        local_dir_use_symlinks=False, # عشان الملفات تكون حقيقية مش اختصارات
        resume_download=True,     # يكمل لو النت فصل
        token=HF_TOKEN            # التوكن ضروري هنا
    )
    print(f"✅ NUCLEAR ASSET SECURED.")
    print(f"💎 Model path: {path}")
    print("⚠️  Make sure to update your .env with this path!")
    
except Exception as e:
    print(f"🔥 Download Failed: {e}")
    print("💡 Hint: Did you accept the license agreement on the Model Page?")
