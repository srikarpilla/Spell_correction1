from flask import Flask, render_template, request, redirect, url_for
import phonetics
from rapidfuzz import fuzz
import re
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Preload reference words once on startup
def load_reference_words(filename="reference.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

reference_words = load_reference_words()

def normalize(word):
    word = re.sub(r'[^a-zA-Z]', '', word).lower()
    return re.sub(r'(a+|e+|i+|o+|u+)', lambda m: m.group(0)[0], word)

def build_phonetic_maps(words):
    phonetic_maps = {'soundex': {}, 'metaphone': {}}
    for word in words:
        s_code = phonetics.soundex(normalize(word))
        m_code = phonetics.metaphone(normalize(word))
        phonetic_maps['soundex'].setdefault(s_code, []).append(word)
        phonetic_maps['metaphone'].setdefault(m_code, []).append(word)
    return phonetic_maps

phonetic_maps = build_phonetic_maps(reference_words)

def combined_similarity(w1, w2):
    return 0.7 * fuzz.token_sort_ratio(w1, w2) + 0.3 * fuzz.ratio(w1, w2)

def correct_word(word, phonetic_maps, reference_words, threshold=75):
    s_code = phonetics.soundex(normalize(word))
    m_code = phonetics.metaphone(normalize(word))
    candidates = set(phonetic_maps['soundex'].get(s_code, []) + phonetic_maps['metaphone'].get(m_code, [])) or set(reference_words)

    scores = [(cand, combined_similarity(normalize(word), normalize(cand))) for cand in candidates]
    scores.sort(key=lambda x: x[1], reverse=True)

    if scores and scores[0][1] >= threshold:
        return scores[0][0]
    else:
        return word

@app.route("/", methods=["GET", "POST"])
def index():
    corrected_pairs = []
    if request.method == "POST":
        # Save uploaded errors file
        file = request.files.get("error_file")
        if file and file.filename.endswith(".txt"):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Process corrections
            with open(filepath, "r", encoding="utf-8") as f:
                error_words = [line.strip() for line in f if line.strip()]
            
            for ew in error_words:
                corr = correct_word(ew, phonetic_maps, reference_words)
                corrected_pairs.append((ew, corr))

    return render_template("index.html", results=corrected_pairs)

if __name__ == "__main__":
    app.run(debug=True)
