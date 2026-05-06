import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

from extractor.excel_reader import read_financial_statement, read_notes
from extractor.rule_extractor import extract_all_data
from extractor.excel_writer import create_output_excel

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'outputs'

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/extract', methods=['POST'])
def extract():
    if 'fs_file' not in request.files or 'notes_file' not in request.files:
        return jsonify({'error': '재무제표와 재무제표 주석 파일을 모두 업로드해주세요.'}), 400

    fs_file    = request.files['fs_file']
    notes_file = request.files['notes_file']

    if not fs_file.filename or not notes_file.filename:
        return jsonify({'error': '파일을 선택해주세요.'}), 400

    if not fs_file.filename.endswith('.xlsx') or not notes_file.filename.endswith('.xlsx'):
        return jsonify({'error': '.xlsx 파일만 지원합니다.'}), 400

    session_id = str(uuid.uuid4())[:8]
    fs_path    = UPLOAD_DIR / f'{session_id}_fs.xlsx'
    notes_path = UPLOAD_DIR / f'{session_id}_notes.xlsx'

    prev_notes_path = None
    try:
        fs_file.save(str(fs_path))
        notes_file.save(str(notes_path))

        fs_data    = read_financial_statement(str(fs_path))
        notes_data = read_notes(str(notes_path))

        prev_notes_data = None
        prev_notes_file = request.files.get('prev_notes_file')
        if prev_notes_file and prev_notes_file.filename and prev_notes_file.filename.endswith('.xlsx'):
            prev_notes_path = UPLOAD_DIR / f'{session_id}_prev_notes.xlsx'
            prev_notes_file.save(str(prev_notes_path))
            prev_notes_data = read_notes(str(prev_notes_path))

        extracted = extract_all_data(fs_data, notes_data, prev_notes_data=prev_notes_data)

        company_name = extracted.get('company_name', '기업')
        safe_name = ''.join(
            c for c in company_name if c.isalnum() or c in (' ', '_', '-')
        ).strip() or '기업'

        output_filename = f'{safe_name}_재무데이터추출.xlsx'
        output_path = OUTPUT_DIR / output_filename

        create_output_excel(extracted, str(output_path))

        return jsonify({
            'success': True,
            'filename': output_filename,
            'company_name': company_name,
            'years': extracted.get('years', []),
            'errors': extracted.get('errors', []),
        })

    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

    finally:
        fs_path.unlink(missing_ok=True)
        notes_path.unlink(missing_ok=True)
        if prev_notes_path:
            prev_notes_path.unlink(missing_ok=True)


@app.route('/download/<path:filename>')
def download(filename):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return '파일을 찾을 수 없습니다.', 404
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == '__main__':
    print('=' * 50)
    print('  Reverse DCF 데이터 추출기 (규칙 기반)')
    print('  http://localhost:5000')
    print('=' * 50)
    app.run(debug=True, port=5000)
