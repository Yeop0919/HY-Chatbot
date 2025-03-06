#===========================================================================================================
# hybrid search (using tmm)

def tmm_norm_milvus(dense_results):
    dense_distances = [result["distance"] for result in dense_results]
    min_distance = -1
    max_distance = max(dense_distances)

    for result in dense_results:
        result["normalized_score"] =  (result["distance"] - min_distance) / (max_distance - min_distance)
    return dense_results

def tmm_norm_elastic(sparse_results):
    #sparse_scores = [result["_score"]  for result in sparse_results ]
    sparse_scores = []
    for result in sparse_results:
        try:
            sparse_scores.append(result["_score"])
        except KeyError:
            print(f"🚨 Warning: '_score' 키가 없는 항목 발견! 데이터: {result}")
        sparse_scores.append(0)  # 기본값 설정
    min_score = 0
    max_score = max(sparse_scores)
    for result in sparse_results:
            result["normalized_score"] = (result["_score"] - min_score) / (max_score - min_score)
    return sparse_results

def txt_hybrid_search(dense_results, sparse_results, dense_weight, sparse_weight):
    combined_results = {}
    for result in sparse_results:
        combined_results[result["_id"]] = {
            "text": result["_source"]["page_content"],
            "sparse_score": result["normalized_score"],
            "dense_score": 0,
            "bundle":result["_source"]["metadata"].get("bundle","bundle 없음")
            }
    for result in dense_results:
        if str(result["id"]) in combined_results:
            combined_results[str(result["id"])]["dense_score"] = result["normalized_score"]
        else:
            combined_results[str(result["id"])] = {
                "text": result["text"],
                "sparse_score": 0,
                "dense_score": result["normalized_score"],
                "bundle":result["bundle"]
                }
    for docid, doc in combined_results.items():
        doc["final_score"] = sparse_weight * doc["sparse_score"] + dense_weight * doc["dense_score"]
    final_results= sorted(combined_results.values(), key=lambda x: x["final_score"], reverse=True)
    return final_results

def img_hybrid_search(dense_results, sparse_results, dense_weight, sparse_weight):
    combined_results = {}
    for result in sparse_results:
        combined_results[result["_id"]] = {
            "id": result["_id"],
            "img_summary": result["_source"]["image_summary"],
            "sparse_score": result["normalized_score"],
            "dense_score": 0,
            "bundle":result["_source"]["metadata"].get("bundle","bundle 없음")
            }
    for result in dense_results:
        if str(result["id"]) in combined_results:
            combined_results[str(result["id"])]["dense_score"] = result["normalized_score"]
        else:
            combined_results[str(result["id"])] = {
                "id": str(result['id']),
                "img_summary": result["img_summary"],
                "sparse_score": 0,
                "dense_score": result["normalized_score"],
                "bundle":result["bundle"]
                }
    for docid, doc in combined_results.items():
        doc["final_score"] = sparse_weight * doc["sparse_score"] + dense_weight * doc["dense_score"]
    final_results= sorted(combined_results.values(), key=lambda x: x["final_score"], reverse=True)
    return final_results
