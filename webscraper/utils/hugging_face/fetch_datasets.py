from huggingface_hub import list_datasets

def fetch_huggingface_datasets(query: str, limit: int = 50):
    datasets = list_datasets(search=query, limit=limit)

    results = []

    for dataset in datasets:
        # Extract basic info
        title = dataset.id
        description = ""
        author = dataset.author if hasattr(dataset, 'author') and dataset.author else ""
        
        # Extract description from card_data
        if dataset.card_data:
            description = dataset.card_data.get("description", "") or ""
        if description == "" and dataset.created_at is not None:
            description = description + "Uploaded to Huggingface on:" + dataset.created_at.strftime("%Y-%m-%d")
        
        # Extract tags
        tags = []
        if hasattr(dataset, 'tags') and dataset.tags:
            tags = dataset.tags[:10]  # Limit to 10 tags
        
        # Extract metrics
        downloads = getattr(dataset, 'downloads', 0) or 0
        likes = getattr(dataset, 'likes', 0) or 0
        
        # Build HuggingFace URL
        url = f"https://huggingface.co/datasets/{title}"
       
        results.append({
            "title": title,
            "description": description,
            "author": author,
            "tags": ", ".join(tags) if tags else "",
            "downloads": downloads,
            "likes": likes,
            "url": url
        })

    return results