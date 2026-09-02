from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

def txt_reranking(user_query, initial_results):
    tokenizer = AutoTokenizer.from_pretrained("Dongjin-kr/ko-reranker")
    model = AutoModelForSequenceClassification.from_pretrained("Dongjin-kr/ko-reranker")
    query_document_pairs = [(user_query, result["text"]) for result in initial_results]
    inputs = tokenizer(
    query_document_pairs,
    padding=True,
    truncation=True,
    return_tensors="pt",
    max_length=512
    )
    with torch.no_grad():
      outputs = model(**inputs)
      scores = outputs.logits.squeeze(-1).tolist()
    for idx, result in enumerate(initial_results):
      result["reranker_score"] = scores[idx]
    reranked_results = sorted(initial_results, key=lambda x: x["reranker_score"], reverse=True)
    return reranked_results

def img_reranking(user_query, initial_results):
    tokenizer = AutoTokenizer.from_pretrained("Dongjin-kr/ko-reranker")
    model = AutoModelForSequenceClassification.from_pretrained("Dongjin-kr/ko-reranker")
    query_document_pairs = [(user_query, result["img_summary"]) for result in initial_results]
    inputs = tokenizer(
    query_document_pairs,
    padding=True,
    truncation=True,
    return_tensors="pt",
    max_length=512
    )
    with torch.no_grad():
      outputs = model(**inputs)
      scores = outputs.logits.squeeze(-1).tolist()
    for idx, result in enumerate(initial_results):
      result["reranker_score"] = scores[idx]
    reranked_results = sorted(initial_results, key=lambda x: x["reranker_score"], reverse=True)
    return reranked_results
