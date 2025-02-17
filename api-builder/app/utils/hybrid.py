def tmm_norm_milvus(dense_results):
    dense_distances = [result["distance"] for result in dense_results]
    min_distance = -1
    max_distance = max(dense_distances)

    for result in dense_results:
        result["normalized_score"] =  (result["distance"] - min_distance) / (max_distance - min_distance)
    return dense_results

def tmm_norm_elastic(sparse_results):
    sparse_scores = [result["_score"] for result in sparse_results]
    min_score = 0
    max_score = max(sparse_scores)
    for result in sparse_results:
            result["normalized_score"] = (result["score"] - min_score) / (max_score - min_score)
    return sparse_results

def hybrid_search(dense_results, sparse_results, dense_weight, sparse_weight):
    combined_results = {}
    for result in sparse_results:
        combined_results[result["id"]] = {
            "text": result["text"],
            "sparse_score": result["normalized_score"],
            "dense_score": 0
            }
    for result in dense_results:
        if str(result["id"]) in combined_results:
            combined_results[str(result["id"])]["dense_score"] = result["normalized_score"]
        else:
            combined_results[str(result["id"])] = {
                "text": result["text"],
                "sparse_score": 0,
                "dense_score": result["normalized_score"]
                }
    for doc in combined_results.items():
        doc["final_score"] = sparse_weight * doc["sparse_score"] + dense_weight * doc["dense_score"]
    final_results= sorted(combined_results.values(), key=lambda x: x["final_score"], reverse=True)
    return final_results
