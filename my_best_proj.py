import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from rembg import remove
import os
import torch
import torchvision.transforms as transforms
from torchvision.models import efficientnet_b0
from torchvision.models.efficientnet import EfficientNet_B0_Weights

# Проверка доступности GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Загрузка модели для классификации одежды
def load_clothing_model():
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 10)  # 10 классов
    try:
        model.load_state_dict(torch.load('fashion_mnist_efficientnet.pth', map_location=device))
    except FileNotFoundError:
        print("Модель clothing_model.pth не найдена. Используется предобученная модель без дообучения.")
    model.eval()
    return model

# Классы Fashion-MNIST
CLOTHING_CLASSES = [
    "Футболка/топ", "Брюки", "Свитер", "Платье", "Пальто",
    "Сандалии", "Рубашка", "Кроссовки", "Сумка", "Ботинки"
]

# Трансформации для классификации
classify_transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def remove_background(input_image):
    """Удаляет фон с изображения с помощью rembg"""
    try:
        return remove(input_image)
    except Exception as e:
        print(f"Ошибка при удалении фона: {e}")
        return input_image.convert('RGB')

def get_dominant_colors(image_np, k=3):
    """Анализирует доминирующие цвета, игнорируя фон"""
    try:
        if image_np.shape[2] == 4:
            alpha = image_np[:, :, 3]
            mask = alpha > 128
            pixels = image_np[mask][:, :3]
        else:
            pixels = image_np.reshape(-1, 3)
        
        not_white = np.all(pixels < [245, 245, 245], axis=1)
        clothing_pixels = pixels[not_white]
        
        if len(clothing_pixels) < 10:
            return [[0, 0, 0]]
        
        if len(clothing_pixels) > 10000:
            clothing_pixels = clothing_pixels[np.random.choice(len(clothing_pixels), 10000, replace=False)]
        
        kmeans = KMeans(n_clusters=k, n_init=10)
        kmeans.fit(clothing_pixels)
        
        counts = np.bincount(kmeans.labels_)
        sorted_colors = kmeans.cluster_centers_[np.argsort(-counts)]
        
        return np.clip(sorted_colors, 0, 255).astype(int).tolist()
    except Exception as e:
        print(f"Ошибка при анализе цветов: {e}")
        return [[0, 0, 0]]

def classify_clothing(image, model):
    """Определяет тип одежды"""
    try:
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        img_tensor = classify_transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(img_tensor)
        predicted_class = torch.argmax(outputs).item()
        return CLOTHING_CLASSES[predicted_class]
    except Exception as e:
        print(f"Ошибка при классификации: {e}")
        return "Неизвестный тип"

def visualize_results(original_img, no_bg_img, colors, clothing_type):
    """Визуализирует результаты"""
    try:
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.imshow(original_img)
        plt.title("Исходное изображение")
        plt.axis('off')
        
        plt.subplot(1, 3, 2)
        plt.imshow(no_bg_img)
        plt.title(f"Без фона\nТип: {clothing_type}")
        plt.axis('off')
        
        plt.subplot(1, 3, 3)
        for i, color in enumerate(colors):
            plt.bar(i, 1, color=np.array(color)/255, width=0.8)
        plt.xlim(-0.5, len(colors)-0.5)
        plt.ylim(0, 1)
        plt.title("Доминирующие цвета")
        plt.axis('off')
        
        plt.tight_layout()
        plt.savefig('result.png')  # Сохраняем результат вместо показа
        print("Результат сохранен в result.png")
    except Exception as e:
        print(f"Ошибка при визуализации: {e}")
1
def analyze_image(image_path, num_colors=3):
    """Анализирует одежду на изображении"""
    try:
        if not os.path.exists(image_path):
            print(f"Файл {image_path} не найден!")
            return None, None
        
        model = load_clothing_model()
        
        try:
            original_img = Image.open(image_path)
        except Exception as e:
            print(f"Ошибка при загрузке изображения: {e}")
            return None, None
        
        no_bg_img = remove_background(original_img)
        
        clothing_type = classify_clothing(no_bg_img, model)
        
        img_array = np.array(no_bg_img)
        dominant_colors = get_dominant_colors(img_array, num_colors)
        
        visualize_results(original_img, no_bg_img, dominant_colors, clothing_type)
        
        
        return clothing_type, dominant_colors
    
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        return None, None

if __name__ == "__main__":
    image_path = input("Введите путь к изображению: ").strip('"')
    analyze_image(image_path, num_colors=3)