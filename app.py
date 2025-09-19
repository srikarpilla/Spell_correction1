from flask import Flask, render_template, request, send_file
import phonetics
from rapidfuzz import fuzz
import re
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Load reference words once
def load_reference_words(filename="reference.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

reference_words = load_reference_words()

def normalize(word):
    if not word:
        return ""
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
    for cand in candidates:
        if cand:
            sim = combined_similarity(normalize(word), normalize(cand))
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
    output_filepath = None
    if request.method == "POST":
        file = request.files.get("error_file")
        if file and file.filename.endswith(".txt"):
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(input_path)

            corrected_pairs = []
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], "output_corrected.txt")
            with open(input_path, "r", encoding="utf-8") as f_in, \
                 open(output_path, "w", encoding="utf-8") as f_out:

                f_out.write("File_Error Corrected\n")
                for err_word in f_in:
                    err_word = err_word.strip()
                    corr = correct_word(err_word, phonetic_maps, reference_words)
                    corrected_pairs.append((err_word, corr))
                    f_out.write(f"{err_word} {corr}\n")

            output_filepath = output_path

    return render_template("index.html", results=corrected_pairs, output_file=output_filepath)

@app.route("/download")
def download():
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], "output_corrected.txt")
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True, download_name="output_corrected.txt")
    else:
        return "File not found", 404

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
