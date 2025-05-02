
from app.utils.ela import search_base64, search_base64_by_bundle
import os

os.environ["OPENAI_API_KEY"] = "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"
OPENAI_API_KEY = os.getenv("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")


from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.messages import HumanMessage
from langchain.schema.output_parser import StrOutputParser
from PIL import Image
from langchain_openai import ChatOpenAI
import base64
import io
def resize_base64_image(base64_string, size=(700, 700)):
    """
    Resize an image encoded as a Base64 string
    """
    # Decode the Base64 string
    img_data = base64.b64decode(base64_string)
    img = Image.open(io.BytesIO(img_data))

    # Resize the image
    resized_img = img.resize(size, Image.LANCZOS)

    # Save the resized image to a bytes buffer
    buffered = io.BytesIO()
    resized_img.save(buffered, format=img.format)

    # Encode the resized image to Base64
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def make_data_dict(user_query, text_reranked_result, image_reranked_result):
<<<<<<< HEAD
    if not text_reranked_result:
        txt_context=[]
    else:
        txt_context = [ result["text"] for result in text_reranked_result]
    if not image_reranked_result:
        img_context=[]
    else:
        img_context_ids = [str(result["id"]) for result in image_reranked_result]
        img_context_bundles=[]
        for i in range(2):
            result=image_reranked_result[i]
            if not str(result["bundle"]) in img_context_bundles:
                img_context_bundles.append(str(result["bundle"]))
        img_context=[]
        if not img_context_bundles[0] == 'bundle 없음':
            for bundle in img_context_bundles:
                base64=search_base64_by_bundle(bundle,size=12)
                if base64:
                    for b in base64:
                        img_context.append(b)
                else:
                    raise Exception("이것은 bundle로 이미지 검색 문제입니다.")
        elif img_context_bundles[0] == 'bundle 없음':
            for id in img_context_ids:
                if id=='-1':
                    continue
                base64=search_base64(id)
                if base64:
                    img_context.append(base64[0])
                else:
                    raise Exception("이것은 id로 이미지 검색 문제입니다.")
=======
    txt_context = [ result["text"] for result in text_reranked_result]
    img_context_ids = [str(result["id"]) for result in image_reranked_result]
    img_context_bundles=[]
    for i in range(2):
        result=image_reranked_result[i]
        if not str(result["bundle"]) in img_context_bundles:
            img_context_bundles.append(str(result["bundle"]))
    img_context=[]
    if not img_context_bundles[0] == 'bundle 없음':
        for bundle in img_context_bundles:
            base64=search_base64_by_bundle(bundle,size=12)
            if base64:
                for b in base64:
                    img_context.append(b)
            else:
                raise Exception("이것은 bundle로 이미지 검색 문제입니다.")
    elif img_context_bundles[0] == 'bundle 없음':
        for id in img_context_ids:
            if id=='-1':
                continue
            base64=search_base64(id)
            if base64:
                img_context.append(base64[0])
            else:
                raise Exception("이것은 id로 이미지 검색 문제입니다.")
>>>>>>> origin/main

    data_dict={
        "context":{
            "texts":txt_context,
            "images":img_context

        },
        "question":user_query
    }
    return data_dict

def img_prompt_func(data_dict):
    """
    Join the context into a single string
    """
    formatted_texts = "\n".join(data_dict["context"]["texts"])
    messages = []

    # Adding image(s) to the messages if present
    if data_dict["context"]["images"]:
        for image in data_dict["context"]["images"]:
            image_message = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            }
            messages.append(image_message)
    text_message = {
        "type": "text",
        "text": (
            "You are an AI assistant capable of analyzing text and images.\n"
<<<<<<< HEAD
            "You will be given a mix of text and image(s).\n"
            "Use this information to provide a response to the user's question.\n"
            "If there are absolutely no relevant search results, you MUST respond EXACTLY as follows:\n"
            "'미안하다냥. 찾는 정보가 없는 것 같다냥!\\n아래 질문은 어떻냥?'\n"
            "However, If there are any relevant search results, generate an informative response based on the available information.\n"
            "Do not falsely claim that there are no search results.\n"
            "Please answer in Korean.\n"
            f"User-provided question: {data_dict['question']}\n"
            "Text :\n"
            f"{formatted_texts}"

        ),
    }
    messages.append(text_message)
    return [HumanMessage(content=messages)]

def img_prompt_additional(data_dict):
    """
    Join the context into a single string
    """
    formatted_texts = "\n".join(data_dict["context"]["texts"])
    messages = []

    # Adding image(s) to the messages if present
    if data_dict["context"]["images"]:
        for image in data_dict["context"]["images"]:
            image_message = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            }
            messages.append(image_message)
    text_message = {
        "type": "text",
        "text": (
            "- Review the provided text and image context, as well as the user's original question.\n"
            "- Based on both the context and the user’s question, generate one new question that is most closely related to the user’s original question, but is different from the original question.\n"
            "- Do not generate any question that cannot be answered from the given context."
            "- Your output must contain only the generated question."
            "- Ensure that the generated question is closely relevant to either the context, the user's question, or both, and not random.\n"
            "- Respond entirely in Korean.\n"
            f"User-provided question: {data_dict['question']}\n"
=======
            "You will be given a mixed of text and image(s).\n"
            "Use this information to provide quality information related to the user question. \n"
            #"If there are no search results, please respond by saying '미안하다냥. 찾는 정보가 없는 것 같다냥!. \n"
            "If there are absolutely no relevant search results, respond by saying '미안하다냥. 찾는 정보가 없는 것 같다냥!'. \n" 
            "However, if there are any relevant search results, generate an informative response based on the available information. \n"
            "Do not falsely claim that there are no search results. \n"
            "Please answer in Korean.\n"
            f"User-provided question: {data_dict['question']}\n\n"
>>>>>>> origin/main
            "Text :\n"
            f"{formatted_texts}"
        ),
    }
    messages.append(text_message)
    return [HumanMessage(content=messages)]


    
def llm_answer(user_query, text_reranked_result, image_reranked_result):
    """
    Multi-modal RAG pipeline without RunnableLambda
    """

    # Multi-modal LLM
    model = ChatOpenAI(temperature=0, model="gpt-4o", max_tokens=1024)

    # 1️⃣ 데이터 변환 (make_data_dict)
    data_dict = make_data_dict(user_query, text_reranked_result, image_reranked_result)
<<<<<<< HEAD
    data_dict_question=make_data_dict(user_query, text_reranked_result, image_reranked_result[:2])
    # 2️⃣ LLM 입력 형식 변환 (img_prompt_func)
    prompt_messages = img_prompt_func(data_dict)

    # 3️⃣ GPT-4 
    response = model.invoke(prompt_messages)
    if response.content=='미안하다냥. 찾는 정보가 없는 것 같다냥!\n아래 질문은 어떻냥?':
        additional_messages=img_prompt_additional(data_dict_question)
        additional_response=model.invoke(additional_messages)
        return response.content,additional_response.content
    # 4️⃣ 최종 결과 반환
    return response.content,None
=======

    # 2️⃣ LLM 입력 형식 변환 (img_prompt_func)
    prompt_messages = img_prompt_func(data_dict)

    # 3️⃣ GPT-4 Vision 실행
    response = model.invoke(prompt_messages)

    # 4️⃣ 최종 결과 반환
    return response.content
>>>>>>> origin/main

# import markdown

# def process_response(response):
#     """
#     LLM 응답을 Markdown에서 HTML로 변환하여 반환하는 함수
#     """
#     if hasattr(response, "content"):
#         # Markdown을 HTML로 변환
#         response.content = markdown.markdown(response.content, extensions=['fenced_code'])
    
#     return response
