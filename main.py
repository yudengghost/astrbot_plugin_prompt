from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from openai import OpenAI
import os
import re

@register("prompt", "yudengghost", "AI提示词助手插件", "1.0.0", "repo url")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.client = OpenAI(
            api_key=self.config.get("deepinfra_api_key"),
            base_url="https://api.deepinfra.com/v1/openai"
        )
    
    @filter.command("提示词")
    async def prompt(self, event: AstrMessageEvent):
        """使用AI模型生成回复的提示词命令"""
        # 获取用户消息
        user_message = event.message_str

        yield event.plain_result("收到了，请稍候🥸...")
        
        try:
            # 创建聊天完成请求
            messages = [{"role": "system", "content": self.config.get("system_message")}] if self.config.get("system_message") else []
            messages.append({"role": "user", "content": user_message})
            
            chat_completion = self.client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1",
                messages=messages,
                temperature=self.config.get("model_settings", {}).get("temperature", 0.7),
                max_tokens=self.config.get("model_settings", {}).get("max_tokens", 4096)
            )
            
            # 获取响应并处理
            response_text = chat_completion.choices[0].message.content
            # 使用正则表达式删除<think></think>标签中的内容
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
            # 移除可能的多余空行
            response_text = re.sub(r'\n\s*\n', '\n\n', response_text.strip())
            
            # 返回响应
            yield event.plain_result(response_text)
            
        except Exception as e:
            logger.error(f"处理提示词命令时出错: {str(e)}")
            yield event.plain_result(f"抱歉，处理请求时出现错误: {str(e)}")