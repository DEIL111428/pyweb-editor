from flask import Flask, render_template, request, jsonify
from PIL import Image
from processors import apply_filters, resize_for_preview, image_to_base64

app = Flask(__name__)

# Простейшее хранилище в памяти
class ImageStore:
    def __init__(self):
        self.original_image = None
        self.preview_image = None 

store = ImageStore()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('image')
    if not f: return jsonify({'status':'error', 'message': 'Нет файла'})
    
    try:
        img = Image.open(f.stream)
        store.original_image = img.copy()
        # Создаем превью для работы в интерфейсе
        store.preview_image = resize_for_preview(img)
        
        return jsonify({
            'status':'success', 
            'image': image_to_base64(store.preview_image)
        })
    except Exception as e:
        return jsonify({'status':'error', 'message': str(e)})

@app.route('/process', methods=['POST'])
def process():
    if not store.preview_image:
        return jsonify({'status':'error', 'message': 'Изображение не загружено'})
    
    try:
        # Всегда берем чистое превью и накладываем фильтры заново
        res_img = apply_filters(store.preview_image.copy(), request.json)
        return jsonify({
            'status':'success', 
            'image': image_to_base64(res_img)
        })
    except Exception as e: 
        print(f"Ошибка обработки: {e}")
        return jsonify({'status':'error'})

if __name__ == '__main__':
    print("Запуск сервера: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)