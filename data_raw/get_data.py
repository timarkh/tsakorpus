import os
import json
from datasets import load_dataset

print("Downloading from Hugging Face...")
dataset = load_dataset("siberian-lang-lab/evenki-rus-parallel-corpora")

output_path = "data_raw/evenki_data.json"
dataset['train'].to_json(output_path, force_ascii=False)

print(f"Dataset successfully saved to {output_path}")

with open(output_path, 'r', encoding='utf-8') as f:
    for i in range(2):
        print(f"\nRecord {i+1}:")
        print(json.loads(next(f)))