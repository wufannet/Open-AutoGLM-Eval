import datetime
from typing import Dict
import json
from utils.call_mobile_agent_e import GUIOwlWrapper


# llm请求,包装了打印时间耗时和token开销
class RideLlmServer(object):

    def __init__(
            self,
            api_key: str,
            base_url: str,
            model_name: str,
    ):
        self.vllm = GUIOwlWrapper(api_key, base_url, model_name)
        self.model_name = model_name

    def request(self, data: Dict) -> Dict|None:
        # LOG_TAG = self.__class__.__name__
        image_dir = data['image_dir']
        app_name = data['app_name']
        LOG_TAG = data['LOG_TAG']
        prompt = data['prompt']
        # target = data['target']
        print(f"\n###=== {LOG_TAG} {app_name} {self.model_name} === ###")
        # 获取当前方法名
        import inspect
        method_name = inspect.currentframe().f_code.co_name
        # print(f"当前方法名: {method_name}")

        # prompt = RideAppCompareServer.PROMPT
        # print("\n=== request Operator prompt_action ===\n" + prompt_action)
        # -- Timing for operator LLM call
        # prompt = self.PROMPT + target
        # print(f"prompt: {prompt}")
        request_start_time = datetime.datetime.now()
        output_action, message_operator, raw_response = self.vllm.predict_mm(
            prompt,
            [image_dir],
        )
        response_end_time = datetime.datetime.now()
        request_duration = (response_end_time - request_start_time).total_seconds()
        print(f"{LOG_TAG} 请求开始时间: {request_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{LOG_TAG} 请求结束时间: {response_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{LOG_TAG} 请求耗时秒: {request_duration:.1f} 秒")
        # Extract token usage for operator
        if raw_response and hasattr(raw_response, "usage"):
            operator_usage = {
                "prompt_tokens": getattr(raw_response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(raw_response.usage, "completion_tokens", 0),
                "total_tokens": getattr(raw_response.usage, "total_tokens", 0),
            }
            # token打印.
            print(
                f"{LOG_TAG} prompt_tokens: {operator_usage['prompt_tokens']}")
            print(
                f"{LOG_TAG} completion_tokens: {operator_usage['completion_tokens']}")
            print(f"{LOG_TAG} total_tokens: {operator_usage['total_tokens']}")

        if not raw_response:
            # raise RuntimeError('Error calling LLM in operator phase.')
            return None
        try:
            output_action = output_action.replace("```", "").replace("json", "").strip()
            result = json.loads(output_action)
            print('result json开始:\n' + str(result)+'\nresult结束\n' )
            return result
        except Exception as e:
            print(f"⚠️ 无法格式化响应内容: {e}")
            print('output_action开始:\n' + str(output_action) + '\noutput_action结束\n')
            return None

