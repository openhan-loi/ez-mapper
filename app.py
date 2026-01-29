
from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import re
import pickle

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_DICT_PATH = os.path.join(BASE_DIR, "mapping_dictionary.xlsx")
COMPRESSED_STOCK_PATH = os.path.join(BASE_DIR, "stock_data.pkl")
MANUAL_LIST_PATH = os.path.join(BASE_DIR, "수동매칭필요_리스트.xlsx")

CACHED_STOCK_DATA = []

def load_and_cache_stock():
    global CACHED_STOCK_DATA
    if not os.path.exists(COMPRESSED_STOCK_PATH):
        return
    try:
        with open(COMPRESSED_STOCK_PATH, 'rb') as f:
            CACHED_STOCK_DATA = pickle.load(f)
        print(f"Memory-Optimized Cache Ready: {len(CACHED_STOCK_DATA)} items.")
    except Exception as e:
        print(f"Cache error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_tasks')
def get_tasks():
    if not os.path.exists(MANUAL_LIST_PATH): return jsonify([])
    try:
        df = pd.read_excel(MANUAL_LIST_PATH)
        done_keys = []
        if os.path.exists(MAPPING_DICT_PATH):
            done_keys = pd.read_excel(MAPPING_DICT_PATH)['pk_key'].tolist()
        done_set = set(done_keys)
        tasks = [{'pk_key': r['pk_key'], 'name': r['상품명'], 'option': r['옵션']}
                 for _, r in df.iterrows() if r['pk_key'] not in done_set]
        return jsonify(tasks)
    except: return jsonify([])

@app.route('/api/search_stock', methods=['POST'])
def search_stock():
    query = request.json.get('query', '')
    if not query or not CACHED_STOCK_DATA: return jsonify([])

    # Pre-tokenize search terms
    terms = [re.sub(r'[^a-zA-Z0-9가-힣]', '', t).lower() for t in query.split() if t]

    results = []
    for item in CACHED_STOCK_DATA:
        # 'k' is the pre-calculated search key
        if all(t in item['k'] for t in terms):
            results.append({'name': item['n'], 'option': item['o'], 'code': item['c']})
            if len(results) >= 30: break

    return jsonify(results)

@app.route('/api/save_mapping', methods=['POST'])
def save_mapping():
    data = request.json
    pk_key, ez_code = data.get('pk_key'), data.get('ez_code')
    current_mappings = []
    if os.path.exists(MAPPING_DICT_PATH):
        try:
            current_mappings = pd.read_excel(MAPPING_DICT_PATH).to_dict('records')
        except: pass

    found = False
    for m in current_mappings:
        if m['pk_key'] == pk_key:
            m['ez_code'] = ez_code
            found = True; break
    if not found: current_mappings.append({'pk_key': pk_key, 'ez_code': ez_code})

    pd.DataFrame(current_mappings).to_excel(MAPPING_DICT_PATH, index=False)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    load_and_cache_stock()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
