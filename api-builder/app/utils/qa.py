from openai import OpenAI
from app.utils.ela import search_base64
import os
os.environ["OPENAI_API_KEY"] = "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"
OPENAI_API_KEY = os.getenv("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")

def llm_answer(user_query, text_reranked_result, image_reranked_result):
    openai_client = OpenAI()
    txt_context = [{"context": result["text"]} for result in text_reranked_result]
    img_context_ids = [str(result["id"]) for result in image_reranked_result]
    img_context=[]
    for id in img_context_ids:
        base64=search_base64(id)
        img_context.append({"image_context":base64})
    # RAG 체인 구성
    SYSTEM_PROMPT = """
    Human: 당신은 AI 어시스턴트입니다. 제공된 문맥적인 단락에서 질문에 대한 답을 찾을 수 있습니다.
    """

    USER_PROMPT = f"""
    다음 정보를 바탕으로 질문에 답하세요
    텍스트 정보:
    {txt_context}
    이미지 정보:
    {img_context}
    질문: {user_query}
    문장으로 답변해주세요. 주어진 질문에만 답변하세요. 답변할 때 질문의 주어를 써주세요.주어진 질문에 대한 답변을 모두 포함하세요.
    """
    response = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ],
    )
    return response.choices[0].message.content


