from huggingface_hub import list_datasets

def fetch_huggingface_datasets(query: str, limit: int = 50):
    datasets = list_datasets(search=query, limit=limit)

    results = []

    for dataset in datasets:
        title = dataset.id
        description = ""

        if dataset.card_data:
            description = dataset.card_data.get("description", "") or ""
       
        results.append({
            "title": title,
            "description": description
        })

    return results