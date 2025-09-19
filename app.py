from flask import Flask, render_template, request
import phonetics
from rapidfuzz import fuzz
import re
import os

app = Flask(__name__)

# Load reference words once
def load_reference_words(filename="reference.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

reference_words = load_reference_words()

def normalize(word):
    if not word or not isinstance(word, str):
        return ""
    word_clean = re.sub(r'[^a-zA-Z]', '', word)
    if not word_clean:
        return ""
    return re.sub(r'(a+|e+|i+|o+|u+)', lambda m: m.group(0)[0], word_clean.lower())

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
    try:
        token_ratio = fuzz.token_sort_ratio(w1, w2) or 0
        edit_ratio = fuzz.ratio(w1, w2) or 0
        return 0.7 * token_ratio + 0.3 * edit_ratio
    except Exception:
        return 0.0

def correct_word(word, phonetic_maps, reference_words, threshold=75):
    if not word or word.strip() == "":
        return word

    s_code = phonetics.soundex(normalize(word))
    m_code = phonetics.metaphone(normalize(word))
    candidates = set(phonetic_maps['soundex'].get(s_code, []) + phonetic_maps['metaphone'].get(m_code, [])) or set(reference_words)

    scores = []
    word_norm = normalize(word)
    for cand in candidates:
        cand_norm = normalize(cand)
        if cand_norm and word_norm:
            sim = combined_similarity(word_norm, cand_norm)
            scores.append((cand, sim))

    if not scores:
        return word

    scores.sort(key=lambda x: x[1], reverse=True)

    if scores[0][1] >= threshold:
        return scores[0][0]
    else:
        return word

@app.route("/", methods=["GET", "POST"])
def index():
    corrected_pairs = []
    if request.method == "POST":
        file = request.files.get("error_file")
        if file and file.filename.endswith(".txt"):
            error_words = [line.strip() for line in file if line.strip()]
            corrected_pairs = [(ew, correct_word(ew, phonetic_maps, reference_words)) for ew in error_words]

    return render_template("index.html", results=corrected_pairs)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
