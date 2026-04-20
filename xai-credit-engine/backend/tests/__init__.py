import os
import sys

# Testlerin 'app' modülünü bulabilmesi için
# sys.path içine root dizinini ekliyoruz.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))