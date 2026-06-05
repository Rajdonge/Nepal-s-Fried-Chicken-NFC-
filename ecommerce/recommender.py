import math
import re
from collections import Counter
from dashboard.models import Product


# ==========================================
# UTILITY: TEXT VECTORIZATION
# ==========================================
def text_to_vector(text):
    """
    Convert text into a word frequency Counter.
    
    Args:
        text (str): Input text to vectorize
        
    Returns:
        Counter: Word frequency dictionary
    """
    if not text:
        return Counter()
    
    # Extract words and convert to lowercase
    words = re.findall(r'\w+', text.lower())
    return Counter(words)


# ==========================================
# UTILITY: COSINE SIMILARITY
# ==========================================
def cosine_similarity(vec1, vec2):
    """
    Compute cosine similarity between two text vectors.
    
    Args:
        vec1 (Counter): First word frequency vector
        vec2 (Counter): Second word frequency vector
        
    Returns:
        float: Similarity score between 0 and 1
    """
    if not vec1 or not vec2:
        return 0.0

    # Find common words
    common_words = set(vec1.keys()) & set(vec2.keys())
    
    # Calculate dot product
    dot_product = sum(vec1[word] * vec2[word] for word in common_words)

    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(count ** 2 for count in vec1.values()))
    magnitude2 = math.sqrt(sum(count ** 2 for count in vec2.values()))

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


# ==========================================
# BUILD PRODUCT FEATURES
# ==========================================
def build_product_features():
    """
    Extract and prepare product features from the database.
    
    Returns:
        list: List of dictionaries containing product features
    """
    # Fetch active products with related fields
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'brand'
    ).values(
        'id', 'name', 'slug', 'description', 
        'category__name', 'brand__name',
        'price', 'cost_price', 'main_image'
    )

    product_features = []

    for product in products:
        # Extract text fields with None handling
        name = product.get('name') or ''
        description = product.get('description') or ''
        brand = product.get('brand__name') or ''
        category = product.get('category__name') or ''

        # Combine all text fields for similarity calculation
        combined_text = f"{name} {description} {brand} {category}"
        text_vector = text_to_vector(combined_text)

        # Build feature dictionary
        product_features.append({
            'id': product['id'],
            'name': product['name'],
            'slug': product['slug'],
            'category': category,
            'brand': brand,
            'price': float(product.get('price') or 0),
            'cost_price': float(product.get('cost_price') or 0),
            'main_image': product.get('main_image'),
            'vector': text_vector
        })

    return product_features


# ==========================================
# GET SIMILAR PRODUCTS
# ==========================================
def get_recommendations(product_id, limit=5):
    """
    Find similar products based on text similarity.
    
    Args:
        product_id (int): ID of the reference product
        limit (int): Maximum number of recommendations to return
        
    Returns:
        list: List of similar products with similarity scores
    """
    # Build features for all products
    all_products = build_product_features()
    
    # Find the target product
    target_product = None
    for product in all_products:
        if product['id'] == product_id:
            target_product = product
            break
    
    if not target_product:
        return []
    
    # Calculate similarities
    similarities = []
    target_vector = target_product['vector']
    
    for product in all_products:
        # Skip the target product itself
        if product['id'] == product_id:
            continue
        
        # Calculate similarity score
        similarity = cosine_similarity(target_vector, product['vector'])
        
        # Add to results
        similarities.append({
            'product': product,
            'similarity': similarity
        })
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Return top N similar products
    return [item['product'] for item in similarities[:limit]]

