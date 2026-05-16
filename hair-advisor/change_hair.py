import os
import base64
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
STEP_API_KEY = os.getenv("STEP_API_KEY")
STEP_BASE_URL = os.getenv("STEP_BASE_URL", "https://api.stepfun.com/v1")
client = OpenAI(api_key=STEP_API_KEY, base_url=STEP_BASE_URL)
DEFAULT_PROMPT = """保持人脸完全不变，只修改头发部分。将发型改为：{hair_desc}。
要求：
- 头发与脸部边缘自然融合
- 保持原图的光照、色调、角度一致
- 不要变形、不要扭曲五官"""
def change_hair(image_path: str, hair_desc: str, prompt: str = None) -> str:
    """
    给照片中的人物换发型
    参数:
        image_path: 照片本地路径
        hair_desc: 发型描述，如"法式慵懒卷发"
        prompt: 自定义提示词（可选）
    返回:
        成功时返回图片保存路径，失败时返回错误信息
    """
    image_path = os.path.abspath(image_path.strip('"').strip("'"))
    if not os.path.exists(image_path):
        return f"找不到照片：{image_path}"
    if prompt is None:
        prompt = DEFAULT_PROMPT.format(hair_desc=hair_desc)
    try:
        with open(image_path, "rb") as img_file:
            res = client.images.edit(
                model="step-image-edit-2",
                image=img_file,
                prompt=prompt,
                response_format="b64_json",
                extra_body={
                    "steps": 25,
                    "cfg_scale": 8.5,
                    "negative_prompt": "脸部变形,扭曲,模糊,低画质,五官错乱"
                }
            )
        img_bytes = base64.b64decode(res.data[0].b64_json)
        safe_name = "".join(c for c in hair_desc if c.isalnum() or c in (' ', '-', '_')).strip()
        output_path = f"results/result_{safe_name[:20]}.png"
        os.makedirs("results", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        return f"已保存至：{os.path.abspath(output_path)}"
    except Exception as e:
        return f"失败：{str(e)}"