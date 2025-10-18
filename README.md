# AIris

## Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.11+ (tercihen 3.11)
- Node.js 16+
- .env dosyası (ana dizinde)
- ARDA İÇİN --- Python 3.11 versiyonlarından birini indir kur.

### Kurulum Adımları

1. **Backend kurulumu:**

   ```bash
   # Virtual environment oluşturun ve aktifleştirin
   python -m venv .venv
   .venv\Scripts\activate  # Windows için

   # Bağımlılıkları yükleyin
   pip install -r requirements.txt
   ```

2. **Frontend kurulumu:**

   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **.env dosyasını oluşturun** (ana dizinde) - gerekli API anahtarlarını ekleyin (bu .env dosyasını biz atacağız.)

### Çalıştırma

1. **İki terminal açın** (split olarak daha iyi oluyor)
2. **Backend'i çalıştırın:**

   ```bash
   .venv\Scripts\activate  # Virtual environment'ı aktifleştirin
   python backend_runner.py
   ```

3. **Frontend'i çalıştırın:**

   ```bash
   python frontend_runner.py
   ```

**Not:** Backend'in çalışması biraz uzun sürüyor özellikle ilk defa çalıştırırken. Frontend önceden açılabilir, backend başlamadan uygulamada bir şey yapmasanız daha iyi olur.
