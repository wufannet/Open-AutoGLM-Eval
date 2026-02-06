import abc
import time
import base64
import numpy as np
from PIL import Image
from io import BytesIO
from openai import OpenAI
from typing import Any, Optional
from qwen_vl_utils import smart_resize

ERROR_CALLING_LLM = 'Error calling LLM'

def pil_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG") 
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def image_to_base64(image_path):
    dummy_image = Image.open(image_path)
    MIN_PIXELS=3136
    MAX_PIXELS=10035200 #1000完,相当于 3K * 3k 分辨率
    # resized_height, resized_width  = smart_resize(dummy_image.height,
    #     dummy_image.width,
    #     factor=28,
    #     min_pixels=MIN_PIXELS,
    #     max_pixels=MAX_PIXELS,)
    # 图片判别缩放,720就不缩放了,优先保证准确率.1080 的缩放下
    if dummy_image.width >= 1080:
        resized_height, resized_width = int(dummy_image.height/2), int(dummy_image.width/2)
    # elif dummy_image.width >= 720:
    #     resized_height, resized_width = int(dummy_image.height*0.75), int(dummy_image.width * 0.75)
    else:
        resized_height, resized_width = dummy_image.width, dummy_image.height



    # resized_height, resized_width = 780, 360 #1560 720
    # resized_height, resized_width = 1560, 720 #1560 720
    # resized_height, resized_width = 1200, 540

    print(f"image_to_base64 resized_height resized_width {resized_height} {resized_width} ")
    dummy_image = dummy_image.resize((resized_width, resized_height))
    return f"data:image/png;base64,{pil_to_base64(dummy_image)}"

class LlmWrapper(abc.ABC):
    """Abstract interface for (text only) LLM."""
    @abc.abstractmethod
    def predict(
        self,
        text_prompt: str,
    ) -> tuple[str, Optional[bool], Any]:
        """Calling multimodal LLM with a prompt and a list of images.

        Args:
        text_prompt: Text prompt.

        Returns:
        Text output, is_safe, and raw output.
        """

class MultimodalLlmWrapper(abc.ABC):
    """Abstract interface for Multimodal LLM."""
    @abc.abstractmethod
    def predict_mm(
        self, text_prompt: str, images: list[np.ndarray]
    ) -> tuple[str, Optional[bool], Any]:
        """Calling multimodal LLM with a prompt and a list of images.

        Args:
        text_prompt: Text prompt.
        images: List of images as numpy ndarray.

        Returns:
        Text output and raw output.
        """

class GUIOwlWrapper(LlmWrapper, MultimodalLlmWrapper):

    RETRY_WAITING_SECONDS = 3

    def __init__(
            self,
            api_key: str,
            base_url: str,
            model_name: str,
            max_retry: int = 10,
            temperature: float = 0.0,
    ):
        if max_retry <= 0:
            max_retry = 10
            print('Max_retry must be positive. Reset it to 3')
        self.max_retry = min(max_retry, 10)
        self.temperature = temperature
        self.model = model_name
        self.bot = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30
        )

    def convert_messages_format_to_openaiurl(self, messages):
      converted_messages = []
      for message in messages:
          new_content = []
          for item in message['content']:
              if list(item.keys())[0] == 'text':
                  new_content.append({'type': 'text', 'text': item['text']})
              elif list(item.keys())[0] == 'image':
                new_content.append({'type': 'image_url', 'image_url': {'url': image_to_base64(item['image'])}})
          converted_messages.append({'role': message['role'], 'content': new_content})

      return converted_messages
    
    def predict(
            self,
            text_prompt: str,
    ) -> tuple[str, Optional[bool], Any]:
        return self.predict_mm(text_prompt, [])

    def predict_mm(
            self, text_prompt: str, images: list[np.ndarray], messages = None
    ) -> tuple[str, Optional[bool], Any]:
        # 设置temperature=0, top_p=1。
        # TODO 设置可选的json结构化输出,先不做,如果有问题再做
        if messages is None:
          payload = [
              {
                  "role": "user",
                  "content": [
                      {"text": text_prompt},
                  ]
              }
          ]
          
          for image in images: #上面的content中添加 image类型
            payload[0]['content'].append({
                'image': image
            })
        else:
          payload = messages
            
        payload = self.convert_messages_format_to_openaiurl(payload)

        counter = self.max_retry
        wait_seconds = self.RETRY_WAITING_SECONDS
        while counter > 0:
            try:
              chat_completion_from_url = self.bot.chat.completions.create(
                  model=self.model,
                  messages=payload,
                  temperature=0,
                  # top_p=1,
              )
              return (chat_completion_from_url.choices[0].message.content, payload, chat_completion_from_url)
            except Exception as e:
                time.sleep(wait_seconds)
                wait_seconds *= 1
                counter -= 1
                print('Error calling LLM, will retry soon...')
                print(e)
        return ERROR_CALLING_LLM, None, None