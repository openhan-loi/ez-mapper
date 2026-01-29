
from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import glob
import re
import pickle

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_DICT_PATH = os.path.join(BASE_DIR, "mapping_dictionary.xlsx")
# 변경: 용량이 큰 .xls 대신 압축된 .pkl 파일을 사용
COMPRESSED_STOCK_PATH = os.path.join(BASE_DIR, "stock_data.pkl")
MANUAL_LIST_PATH = os.path.join(BASE_DIR, "수동매칭필요_리스트.xlsx")

CACHED_STOCK_DATA = []

def normalize(s):
    if pd.isna(s): return ""
    return re.sub(r'[^a-zA-Z0-9가-힣]', '', str(s)).lower()

def load_and_cache_stock():
    global CACHED_STOCK_DATA
    if not os.path.exists(COMPRESSED_STOCK_PATH):
        print("Compressed stock data not found.")
        return
    try:
        with open(COMPRESSED_STOCK_PATH, 'rb') as f:
            raw_items = pickle.load(f)

        items = []
        for row in raw_items:
            # 미리 정규화된 키를 생성하여 검색 속도 극대화
            items.append({
                'name': row['n'],
                'option': row['o'],
                'code': row['c'],
                'search_key': normalize(row['n'] + row['o'])
            })
        CACHED_STOCK_DATA = items
        print(f"Cloud Cache Ready: {len(CACHED_STOCK_DATA)} items.")
    except Exception as e:
        print(f"Cloud Cache error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_tasks')
def get_tasks():
    if not os.path.exists(MANUAL_LIST_PATH): return jsonify([])
    try:
        df = pd.read_excel(MANUAL_LIST_PATH)
        done_keys = set()
        if os.path.exists(MAPPING_DICT_PATH):
            done_df = pd.read_excel(MAPPING_DICT_PATH)
            done_keys = set(done_df['pk_key'].tolist())
        tasks = [{'pk_key': r['pk_key'], 'name': r['상품명'], 'option': r['옵션']}
                 for _, r in df.iterrows() if r['pk_key'] not in done_keys]
        return jsonify(tasks)
    except: return jsonify([])

@app.route('/api/search_stock', methods=['POST'])
def search_stock():
    query = request.json.get('query', '')
    if not query or not CACHED_STOCK_DATA: return jsonify([])
    terms = [normalize(t) for t in query.split() if t]
    results = [item for item in CACHED_STOCK_DATA if all(t in item['search_key'] for t in terms)]
    return jsonify(results[:50])

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
