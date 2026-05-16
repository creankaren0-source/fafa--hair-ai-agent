import os
import re
import json
import shutil
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from analyze_face import analyze_face
from change_hair import change_hair
load_dotenv()
STEP_API_KEY = os.getenv("STEP_API_KEY")
STEP_BASE_URL = os.getenv("STEP_BASE_URL", "https://api.stepfun.com/v1")
# ======================= 状态定义 =======================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    tool_call_id: str
# ======================= 输入模型 =======================
class AnalyzeFaceInput(BaseModel):
    image_path: str = Field(description="照片路径")
class ChangeHairInput(BaseModel):
    image_path: str = Field(description="照片路径")
    hair_desc: str = Field(description="发型描述")
# ======================= 创建工具 =======================
analyze_face_tool = StructuredTool.from_function(
    func=analyze_face,
    name="analyze_face",
    description="分析照片中人物的真实脸型，并推荐适合的发型。输入：image_path（照片路径）",
    args_schema=AnalyzeFaceInput
)
change_hair_tool = StructuredTool.from_function(
    func=change_hair,
    name="change_hair",
    description="给照片中的人物换发型。输入：image_path（照片路径）、hair_desc（发型描述）",
    args_schema=ChangeHairInput
)
tools = [analyze_face_tool, change_hair_tool]
tools_by_name = {tool.name: tool for tool in tools}
# ======================= LLM =======================
llm = ChatOpenAI(
    model="step-1-8k",
    api_key=STEP_API_KEY,
    base_url=STEP_BASE_URL,
    temperature=0.7
)
llm_with_tools = llm.bind_tools(tools)
# ======================= 节点函数 =======================
def agent_node(state: AgentState):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "tool_call_id": ""}
def tool_executor_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return {"messages": [], "tool_call_id": ""}
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    tool_call_id = tool_call["id"]
    tool = tools_by_name[tool_name]
    result = tool.invoke(tool_args)
    tool_message = ToolMessage(content=result, tool_call_id=tool_call_id)
    return {"messages": [tool_message], "tool_call_id": tool_call_id}
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_executor"
    return END
# ======================= 构建图 =======================
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tool_executor", tool_executor_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tool_executor": "tool_executor", END: END})
workflow.add_edge("tool_executor", "agent")
agent_app = workflow.compile()
# ======================= Session管理 =======================
SYSTEM_PROMPT = SystemMessage(content="""
你是一位专业的AI发型顾问，名字叫「小美」。
你的工作方式：
1. 主动询问用户的需求：场合、发质、想要的风格
2. 如果用户提供了照片，使用 analyze_face 工具分析脸型
3. 基于分析结果给出具体发型推荐，解释为什么适合
4. 询问用户是否想看换发效果，如果想就使用 change_hair 工具生成
5. 根据用户反馈继续调整，直到满意为止
重要规则：
- 一次只问一个问题
- 如果用户之前上传过照片，后续换发型直接使用同一张照片，不要重复要求上传
- 回答要简洁专业，不要太啰嗦
""")
sessions = {}
def get_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [SYSTEM_PROMPT],
            "last_image": None
        }
    return sessions[session_id]
def extract_recommendations(analysis: str):
    """从脸型分析文本中提取推荐发型名称，供前端快捷标签使用"""
    if not analysis:
        return []
    target_line = ""
    for line in analysis.splitlines():
        if "推荐发型" in line:
            target_line = line
            break
    if not target_line:
        return []
    text = target_line.split("：", 1)[-1].split(":", 1)[-1]
    for sep in ["、", "，", ",", "；", ";", "\n"]:
        text = text.replace(sep, "|")
    items = []
    for item in text.split("|"):
        name = item.strip().strip("-•0123456789.、 ）)")
        if name and name not in items:
            items.append(name)
    return [{"label": name, "value": f"试戴{name}"} for name in items[:6]]

def extract_recommendations(analysis: str):
    if not analysis:
        return []
    candidates = []
    try:
        data = json.loads(analysis)
        raw = data.get("recommendations") if isinstance(data, dict) else data
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    candidates.append(item)
                elif isinstance(item, dict):
                    candidates.append(item.get("name") or item.get("label") or item.get("style"))
    except Exception:
        pass
    capture = False
    for line in analysis.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if any(key in clean for key in ["推荐发型", "适合发型", "推荐", "发型建议"]):
            capture = True
            clean = re.split(r"[:：]", clean, 1)[-1]
        elif capture and any(key in clean for key in ["避免", "不适合", "发色", "效果图"]):
            capture = False
        if capture:
            for part in re.split(r"[、，,；;]", clean):
                name = re.sub(r"^[\-•*\d\.、\)）\s]+", "", part).strip()
                name = re.sub(r"[：:].*$", "", name).strip()
                name = re.sub(r"（.*?）|\(.*?\)", "", name).strip()
                if 2 <= len(name) <= 12:
                    candidates.append(name)
    for key in ["锁骨发", "大波浪", "法式刘海", "羊毛卷", "空气刘海", "侧分长卷发", "短发", "长卷发", "梨花头", "公主切", "波波头", "八字刘海"]:
        if key in analysis:
            candidates.append(key)
    items = []
    for name in candidates:
        if name:
            name = str(name).strip().strip("-•0123456789.、 ）)")
            if name and name not in items:
                items.append(name)
    return [{"label": name, "value": f"试戴{name}"} for name in items[:6]]

def normalize_recommendations(analysis: str):
    recommendations = extract_recommendations(analysis)
    if recommendations:
        return recommendations
    return [
        {"label": "法式锁骨发", "value": "试戴法式锁骨发"},
        {"label": "侧分长卷发", "value": "试戴侧分长卷发"},
        {"label": "空气刘海短发", "value": "试戴空气刘海短发"},
    ]

# ======================= FastAPI接口 =======================
api = FastAPI(title="AI发型顾问")
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
os.makedirs("results", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
api.mount("/images", StaticFiles(directory="results"), name="images")
@api.post("/welcome")
async def welcome(session_id: str = Form(...)):
    """用户打开对话窗时调用，小美主动打招呼"""
    session = get_session(session_id)
    try:
        session["history"].append(HumanMessage(content="你好"))
        result = agent_app.invoke({"messages": session["history"], "tool_call_id": ""})
        new_messages = result["messages"]
        reply = ""
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break
        session["history"] = list(new_messages)
    except Exception:
        reply = "你好！我是小美，你的专属发型顾问～想聊聊发型吗？可以告诉我你的需求，或者上传一张照片让我帮你分析脸型。"
        session["history"].append(HumanMessage(content="你好"))
        session["history"].append(AIMessage(content=reply))
    return {"reply": reply, "session_id": session_id, "image": None}
@api.post("/recommend")
async def recommend(
    session_id: str = Form(...),
    image: UploadFile = File(...),
    hair_desc: str = Form("适合当前脸型的自然时尚发型")
):
    """上传用户照片后，分析脸型并生成推荐发型效果图"""
    session = get_session(session_id)
    image_path = f"uploads/{session_id}_{image.filename}"
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)
    abs_image_path = os.path.abspath(image_path)
    session["last_image"] = abs_image_path

    analysis = analyze_face(abs_image_path)
    generated_image = None
    image_result = change_hair(abs_image_path, hair_desc)
    if "已保存至：" in image_result:
        path = image_result.split("已保存至：")[-1].strip()
        if os.path.exists(path):
            generated_image = f"/images/{os.path.basename(path)}"

    reply = analysis
    if generated_image:
        reply = f"{analysis}\n\n我已根据你的脸型生成了一张推荐发型效果图。"
    else:
        reply = f"{analysis}\n\n效果图生成失败：{image_result}"

    session["history"].append(HumanMessage(content=f"请分析这张照片并推荐发型\n[当前照片路径：{abs_image_path}]"))
    session["history"].append(AIMessage(content=reply))
    recommendations = normalize_recommendations(analysis)
    return {"reply": reply, "session_id": session_id, "image": generated_image, "recommendations": recommendations}

@api.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: str = Form(...),
    image: UploadFile = File(None)
):
    """主对话接口"""
    session = get_session(session_id)
    # 如果有新图片，保存并记录路径
    if image:
        image_path = f"uploads/{session_id}_{image.filename}"
        with open(image_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        session["last_image"] = os.path.abspath(image_path)
    # 组装用户消息
    user_content = message
    if session["last_image"]:
        user_content += f"\n[当前照片路径：{session['last_image']}]"
    session["history"].append(HumanMessage(content=user_content))
    # 调用agent
    try:
        result = agent_app.invoke({
            "messages": session["history"],
            "tool_call_id": ""
        })
        new_messages = result["messages"]
        # 提取AI回复
        reply = ""
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break
        # 检查是否生成了新图片
        generated_image = None
        for msg in new_messages:
            if isinstance(msg, ToolMessage) and "已保存至" in msg.content:
                path = msg.content.split("已保存至：")[-1].strip()
                if os.path.exists(path):
                    filename = os.path.basename(path)
                    generated_image = f"/images/{filename}"
        # 更新历史
        session["history"] = list(new_messages)
    except Exception:
        reply = "抱歉，我这边出了点小问题，请稍后再试一次～"
        generated_image = None
    return {
        "reply": reply,
        "session_id": session_id,
        "image": generated_image
    }
@api.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清空对话历史"""
    sessions.pop(session_id, None)
    return {"status": "cleared"}
# ======================= 启动 =======================
if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)